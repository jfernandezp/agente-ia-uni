import os
import json
import base64
import socket
import requests
import boto3
import streamlit as st
from datetime import datetime
from google.oauth2 import service_account
from google import genai

from chatbot import render_chatbot
from image_generator import render_image_generator


# 1) SIEMPRE PRIMERO
st.set_page_config(
    page_title="LucIA - Asistente SIU",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 2) Secrets / Env
os.environ["AWS_ACCESS_KEY_ID"] = st.secrets["AWS_ACCESS_KEY_ID"]
os.environ["AWS_SECRET_ACCESS_KEY"] = st.secrets["AWS_SECRET_ACCESS_KEY"]
os.environ["AWS_REGION"] = st.secrets["AWS_REGION"]

GOOGLE_VERTEX_AI_MODELO = st.secrets["GOOGLE"]["GOOGLE_VERTEX_AI_MODELO"]
GOOGLE_VERTEX_AI_LOCATION = st.secrets["GOOGLE"]["GOOGLE_VERTEX_AI_LOCATION"]
GOOGLE_VERTEX_AI_PROJECT = st.secrets["GOOGLE"]["GOOGLE_VERTEX_AI_PROJECT"]

AWS_BEDROCK_REGION = st.secrets["AWS"]["AWS_BEDROCK_REGION"]
AWS_DYNAMODB_REGION = st.secrets["AWS"]["AWS_DYNAMODB_REGION"]
AWS_BEDROCK_AI_MODELO_DEEPSEEK = st.secrets["AWS"]["AWS_BEDROCK_AI_MODELO_DEEPSEEK"]
AWS_BEDROCK_AI_MODELO_TITAN = st.secrets["AWS"]["AWS_BEDROCK_AI_MODELO_TITAN"]

MAX_IMAGENES_PER_DAY = int(st.secrets["FEATURES"]["MAX_IMAGENES_PER_DAY"])
GCP_SERVICE_ACCOUNT_B64 = st.secrets["GCP_SERVICE_ACCOUNT"]["GCP_SERVICE_ACCOUNT_B64"]


# 3) Clientes AWS
bedrock_client = boto3.client("bedrock-runtime", region_name=AWS_BEDROCK_REGION)
dynamodb = boto3.resource("dynamodb", region_name=AWS_DYNAMODB_REGION)
table = dynamodb.Table("tbl_image_usage")


# 4) GCP creds (solo si luego lo necesitas)
SCOPES = ["https://www.googleapis.com/auth/cloud-platform", "https://www.googleapis.com/auth/cloud-platform.read-only"]


def cargar_credenciales_gcp(scopes):
    info = json.loads(base64.b64decode(GCP_SERVICE_ACCOUNT_B64).decode("utf-8"))
    return service_account.Credentials.from_service_account_info(info, scopes=scopes)


credentials = cargar_credenciales_gcp(SCOPES)
client_vertex_ai = genai.Client(
    vertexai=True,
    project=GOOGLE_VERTEX_AI_PROJECT,
    location=GOOGLE_VERTEX_AI_LOCATION,
    credentials=credentials,
)


# 5) IP helpers
def get_client_ip() -> str:
    try:
        ip = st.context.headers.get("X-Forwarded-For")
        if ip:
            return ip.split(",")[0].strip()
    except Exception:
        pass

    try:
        response = requests.get("https://api.ipify.org?format=json", timeout=3)
        if response.status_code == 200:
            return response.json().get("ip", "No disponible")
    except Exception:
        pass

    try:
        hostname = socket.gethostname()
        return socket.gethostbyname(hostname)
    except Exception:
        return "No disponible"


def get_ip_info(ip: str):
    try:
        if ip and ip != "No disponible" and not ip.startswith(("127.", "192.168.")):
            response = requests.get(f"https://ipapi.co/{ip}/json/", timeout=3)
            if response.status_code == 200:
                return response.json()
    except Exception:
        pass
    return None


# 6) DynamoDB control de límite
def check_image_limit(client_ip: str) -> bool:
    today = datetime.now().strftime("%Y-%m-%d")
    try:
        response = table.get_item(Key={"user_id": client_ip, "date": today})
        if "Item" in response:
            count = int(response["Item"].get("images_generated_today", 0))
            return count < MAX_IMAGENES_PER_DAY

        table.put_item(Item={"user_id": client_ip, "date": today, "images_generated_today": 0})
        return True
    except Exception as e:
        st.error(f"Error querying DynamoDB: {e}")
        return False


def increment_image_count(client_ip: str) -> bool:
    today = datetime.now().strftime("%Y-%m-%d")
    try:
        response = table.get_item(Key={"user_id": client_ip, "date": today})
        if "Item" in response:
            current = int(response["Item"].get("images_generated_today", 0))
            if current >= MAX_IMAGENES_PER_DAY:
                return False

            table.update_item(
                Key={"user_id": client_ip, "date": today},
                UpdateExpression="SET images_generated_today = :val",
                ExpressionAttributeValues={":val": current + 1},
            )
            return True

        table.put_item(Item={"user_id": client_ip, "date": today, "images_generated_today": 1})
        return True
    except Exception as e:
        st.error(f"Error updating DynamoDB: {e}")
        return False


def main():
    client_ip = get_client_ip()

    st.sidebar.image("images/logo.PNG", width=150)
    st.sidebar.info(f"**IP:** `{client_ip}`")

    ip_info = get_ip_info(client_ip)
    if ip_info:
        st.sidebar.caption(f"📍 {ip_info.get('city', '')}, {ip_info.get('country_name', '')}")
        st.sidebar.caption(f"🌍 {ip_info.get('org', 'ISP no disponible')}")

    option = st.sidebar.radio("Select an option", ["AI Chatbot", "Image Generator"], key="nav_option")
    
    # Detectar cambio de opción
    if "last_option" not in st.session_state:
        st.session_state.last_option = option

    if st.session_state.last_option != option:
        st.session_state.last_option = option
        st.rerun()
    
    if option == "AI Chatbot":
        render_chatbot(bedrock_client, AWS_BEDROCK_AI_MODELO_DEEPSEEK)
    else:
        render_image_generator(
            client_ip=client_ip,
            bedrock_client=bedrock_client,
            model_id_titan=AWS_BEDROCK_AI_MODELO_TITAN,
            check_image_limit_fn=check_image_limit,
            increment_image_count_fn=increment_image_count,
        )


if __name__ == "__main__":
    main()