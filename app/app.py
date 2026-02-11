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
import sys
from chatbot import render_chatbot
from image_generator import render_image_generator


# 1) SIEMPRE PRIMERO
st.set_page_config(
    page_title="Ignacio Connect - Asistente SIU",
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


# 4) GCP creds
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


# ==================== FUNCIONES PARA PANELES PERSONALIZADOS ====================

def render_chatbot_panel():
    """Panel decorativo para el chatbot"""
    
    # Panel superior con información
    col1, col2, col3 = st.columns([1, 3, 1])
    with col2:
        st.markdown("""
        <div style="background: linear-gradient(90deg, #667eea 0%, #764ba2 100%); 
                    padding: 20px; border-radius: 15px; color: white; text-align: center; 
                    margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
            <h2 style="margin:0; color:white;">🤖 Asistente Virtual Ignacio Connect</h2>
            <p style="margin:10px 0 0 0; opacity:0.9;">Ignacio Connect is the official virtual assistant of USIL and SIU. Feel free to ask about programs, admissions, and university services!</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Estadísticas rápidas
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("🏛️ Carreras", "30+", "Corporación")
    with col2:
        st.metric("🌎 Sedes", "3", "Perú - USA - Paraguay")
    with col3:
        st.metric("🎓 Estudiantes", "20K+", "Comunidad")
    # with col4:
    #     st.metric("⭐ Becas", "15%", "Promedio")
    
    st.divider()
    
    # Área de sugerencias
    with st.expander("💡 Sugerencias de preguntas", expanded=False):
        st.markdown("""
        - **Carreras:** ¿Qué carreras profesionales ofrece USIL?
        - **Admisión:** ¿Cómo es el proceso de admisión?
        - **SIU:** ¿Qué programas ofrece San Ignacio University en Miami?
        - **Medicina:** ¿Cuánto dura la carrera de Medicina Humana?
        """)
    
    return True


def render_image_panel(client_ip, remaining_images):
    """Panel decorativo para el generador de imágenes"""
    
    # Panel superior con información
    col1, col2, col3 = st.columns([1, 3, 1])
    with col2:
        st.markdown("""
        <div style="background: linear-gradient(90deg, #f093fb 0%, #f5576c 100%); 
                    padding: 20px; border-radius: 15px; color: white; text-align: center; 
                    margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
            <h2 style="margin:0; color:white;">🎨 Generador de Imágenes con IA</h2>
            <p style="margin:10px 0 0 0; opacity:0.9;">Transform your ideas into stunning visual art with AI!</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Límite de uso
    col1, col2, col3 = st.columns(3)
    with col2:
        # Crear un contenedor circular para mostrar el límite
        progress = (MAX_IMAGENES_PER_DAY - remaining_images) / MAX_IMAGENES_PER_DAY
        st.markdown(f"""
        <div style="text-align: center; padding: 15px; background: #f8f9fa; 
                    border-radius: 10px; margin-bottom: 20px;">
            <h3 style="margin:0; color: #333;">📊 Límite Diario</h3>
            <div style="font-size: 2em; font-weight: bold; color: {'#28a745' if remaining_images > 3 else '#dc3545'};">
                {remaining_images}/{MAX_IMAGENES_PER_DAY}
            </div>
            <p style="margin:5px 0 0 0; color: #666;">imágenes restantes hoy</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.divider()
    
    # Galería de estilos
    with st.expander("🎯 Estilos populares", expanded=False):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("**🎨 Realista**\n- Fotográfico\n- HD Quality\n- Natural lighting")
        with col2:
            st.markdown("**✨ Artístico**\n- Acuarela\n- Óleo\n- Digital art")
        with col3:
            st.markdown("**🚀 Futurista**\n- Cyberpunk\n- Sci-fi\n- Neon lights")
    
    return True


def render_usage_stats(client_ip):
    """Panel de estadísticas de uso en sidebar"""
    
    # st.sidebar.markdown("""
    # <div style="background: #f0f2f6; padding: 15px; border-radius: 10px; margin: 10px 0;">
    #     <h4 style="margin:0; color: #333;">📊 Tu Actividad</h4>
    # </div>
    # """, unsafe_allow_html=True)
    
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        response = table.get_item(Key={"user_id": client_ip, "date": today})
        
        if "Item" in response:
            count = response["Item"].get("images_generated_today", 0)
            remaining = max(0, MAX_IMAGENES_PER_DAY - count)
            
            #st.sidebar.metric("🎨 Imágenes hoy", f"{count}/{MAX_IMAGENES_PER_DAY}")
            #st.sidebar.progress(int(count / MAX_IMAGENES_PER_DAY))
            #st.sidebar.caption(f"💫 Te quedan {remaining} imágenes")
            
            return remaining
    except Exception as e:
        exc_type, exc_obj, tb = sys.exc_info()
        line_number = tb.tb_lineno
        st.markdown(f"Error:  {str(e)}; line_number: {line_number }")
        pass
    
    return MAX_IMAGENES_PER_DAY


def render_sidebar_header(client_ip):
    """Header personalizado del sidebar"""
    
    #st.sidebar.image("images/logo.PNG", width=150)
    
    st.sidebar.markdown("""
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                padding: 15px; border-radius: 10px; color: white; margin: 15px 0;">
        <h4 style="margin:0; color:white;">🎓 Universidad San Ignacio de Loyola</h4>
        <h4 style="margin:0; color:white;">🎓 San Ignacio University</h4>
    </div>
    """, unsafe_allow_html=True)
    
    # Información de IP (opcional)
    ip_info = get_ip_info(client_ip)
    #print(client_ip)
    # if ip_info:
    #     st.sidebar.info(f"""
    #     **📍 Ubicación:** {ip_info.get('city', 'N/A')}, {ip_info.get('country_name', 'N/A')}
    #     **🌍 ISP:** {ip_info.get('org', 'N/A')[:30]}
    #     """)


def main():
    client_ip = get_client_ip()
    
    # ========== SIDEBAR PERSONALIZADO ==========
    render_sidebar_header(client_ip)
    
    # Estadísticas de uso
    remaining_images = render_usage_stats(client_ip)
    #st.sidebar.divider()
    
    # ========== SELECCIÓN DE MODO CON ESTILO ==========
    st.sidebar.markdown("""
    <div style="background: #f8f9fa; padding: 10px; border-radius: 10px; margin: 10px 0;">
        <h4 style="margin:0; color: #333; text-align: center;">🔮 Selecciona un Modo</h4>
    </div>
    """, unsafe_allow_html=True)
    
    # Radio button con íconos y estilos
    option = st.sidebar.radio(
        "Opciones",
        ["🤖 AI Chatbot", "🎨 Image Generator"],
        key="nav_option",
        label_visibility="collapsed",
        help="Selecciona el modo de interacción"
    )
    
    # Limpiar el texto del ícono para obtener el valor real
    clean_option = "AI Chatbot" if "🤖" in option else "Image Generator"
    
    st.sidebar.divider()
    
    # ========== INFORMACIÓN ADICIONAL SEGÚN MODO ==========
    if clean_option == "AI Chatbot":
        st.sidebar.success("""
        **🤖 Modo Chatbot**
        - Pregunta sobre carreras
        - Información de admisión
        - Programas
        - Campus y sedes
        """)
    else:
        if remaining_images > 0:
            st.sidebar.warning(f"""
            **🎨 Modo Generador de Imágenes**
            - Usa /image [descripción]
            - {remaining_images} imágenes disponibles hoy
            - Calidad premium
            - Descarga directa
            """)
        else:
            st.sidebar.error("""
            **⚠️ Límite Alcanzado**
            Has usado todas tus imágenes hoy.
            ¡Vuelve mañana!
            """)
    
    
    # ========== CONTENIDO PRINCIPAL CON PANELES ==========
    
    # Detectar cambio de opción
    if "last_option" not in st.session_state:
        st.session_state.last_option = clean_option

    if st.session_state.last_option != clean_option:
        st.session_state.last_option = clean_option
        st.rerun()
    
    # ========== RENDERIZAR PANELES SEGÚN OPCIÓN ==========
    
    if clean_option == "AI Chatbot":
        # Panel decorativo para Chatbot
        render_chatbot_panel()
        
        # Chatbot
        render_chatbot(bedrock_client, AWS_BEDROCK_AI_MODELO_DEEPSEEK)
        
    else:
        # Panel decorativo para Image Generator
        render_image_panel(client_ip, remaining_images)
        
        # Verificar límite antes de mostrar el generador
        if remaining_images <= 0:
            st.error(f"""
            ### 🎨 Límite Diario Alcanzado
            
            Has generado el máximo de {MAX_IMAGENES_PER_DAY} imágenes hoy. 
            **¡Vuelve mañana para seguir creando!**
            
            Mientras tanto, puedes:
            - Explorar el chatbot
            - Revisar información de carreras
            - Conocer más sobre USIL y SIU
            """)
            
            # Botón para ir al chatbot
            if st.button("🤖 Ir al Chatbot", use_container_width=True, type="primary"):
                st.session_state.nav_option = "🤖 AI Chatbot"
                st.rerun()
        else:
            # Image Generator
            render_image_generator(
                client_ip=client_ip,
                bedrock_client=bedrock_client,
                model_id_titan=AWS_BEDROCK_AI_MODELO_TITAN,
                check_image_limit_fn=check_image_limit,
                increment_image_count_fn=increment_image_count,
            )
            
    st.sidebar.markdown("---")
    st.sidebar.caption("© 2026 USIL | SIU")

if __name__ == "__main__":
    main()