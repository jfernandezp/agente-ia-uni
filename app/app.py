
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
import streamlit as st
import os
import boto3
from botocore.exceptions import NoCredentialsError
import json
from google import genai
from google.genai import types
import io
import base64
from datetime import datetime
import socket
import requests
from PIL import Image
import sys
from google.oauth2 import service_account
from google.cloud import bigquery

os.environ["AWS_ACCESS_KEY_ID"] = st.secrets["AWS_ACCESS_KEY_ID"]
os.environ["AWS_SECRET_ACCESS_KEY"] = st.secrets["AWS_SECRET_ACCESS_KEY"]
os.environ["AWS_REGION"] = st.secrets["AWS_REGION"]

# GOOGLE_VERTEX_AI_MODELO = os.getenv("GOOGLE_VERTEX_AI_MODELO")
# AWS_BEDROCK_REGION = os.getenv("AWS_BEDROCK_REGION")
# GOOGLE_VERTEX_AI_LOCATION = os.getenv("GOOGLE_VERTEX_AI_LOCATION")
# GOOGLE_VERTEX_AI_PROJECT = os.getenv("GOOGLE_VERTEX_AI_PROJECT")
# GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
# AWS_DYNAMODB_REGION = os.getenv("AWS_DYNAMODB_REGION")
# MAX_IMAGENES_PER_DAY = os.getenv("MAX_IMAGENES_PER_DAY")
# AWS_BEDROCK_AI_MODELO = os.getenv("AWS_BEDROCK_AI_MODELO")

GOOGLE_VERTEX_AI_MODELO = st.secrets['GOOGLE']['GOOGLE_VERTEX_AI_MODELO']
GOOGLE_VERTEX_AI_LOCATION = st.secrets['GOOGLE']['GOOGLE_VERTEX_AI_LOCATION']
GOOGLE_VERTEX_AI_PROJECT = st.secrets['GOOGLE']['GOOGLE_VERTEX_AI_PROJECT']
GOOGLE_APPLICATION_CREDENTIALS = st.secrets['GOOGLE']['GOOGLE_APPLICATION_CREDENTIALS']
AWS_BEDROCK_REGION = st.secrets['AWS']['AWS_BEDROCK_REGION']
AWS_DYNAMODB_REGION = st.secrets['AWS']['AWS_DYNAMODB_REGION']
AWS_BEDROCK_AI_MODELO = st.secrets['AWS']['AWS_BEDROCK_AI_MODELO']
MAX_IMAGENES_PER_DAY = st.secrets['FEATURES']['MAX_IMAGENES_PER_DAY']

# Definir los scopes necesarios para Vertex AI
SCOPES = [
    'https://www.googleapis.com/auth/cloud-platform',
    'https://www.googleapis.com/auth/cloud-platform.read-only'
]

#Cargar credenciales
# if "GCP_SERVICE_ACCOUNT" in st.secrets:
#     # En Streamlit Cloud
#     print("PRD")
#     credentials = service_account.Credentials.from_service_account_info(
#         st.secrets["GCP_SERVICE_ACCOUNT"],
#         scopes=SCOPES
#     )
#     #client_vertex_ai = bigquery.DocumentProcessorServiceClient(credentials=credentials)
#     print(credentials)
# else:
#     # En local
#     print("DEV")

#     credentials = service_account.Credentials.from_service_account_info(
#         st.secrets["GCP_SERVICE_ACCOUNT"],
#         scopes=SCOPES
#     )

def cargar_credenciales_gcp(scope):
    b64 = st.secrets["GCP_SERVICE_ACCOUNT_B64"]
    print(b64)
    info = json.loads(base64.b64decode(b64).decode("utf-8"))
    return service_account.Credentials.from_service_account_info(
        info,
        scopes=scope
    )
    
#print (GOOGLE_APPLICATION_CREDENTIALS)
#os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = GOOGLE_APPLICATION_CREDENTIALS
    # Inicializar Vertex AI
credentials = cargar_credenciales_gcp(SCOPES)
client_vertex_ai = genai.Client(
    vertexai=True, 
    project=GOOGLE_VERTEX_AI_PROJECT, 
    location=GOOGLE_VERTEX_AI_LOCATION
    ,credentials=credentials
)

bedrock_client = boto3.client('bedrock-runtime', region_name=AWS_BEDROCK_REGION)  # Ajusta la región según sea necesario
# Configura AWS DynamoDB
dynamodb = boto3.resource('dynamodb', region_name=AWS_DYNAMODB_REGION)  # Ajusta la región según sea necesario
table = dynamodb.Table('tbl_image_usage')

# Función para verificar cuántas imágenes ha generado el cliente hoy
def check_image_limit(client_ip):
    today = datetime.now().strftime('%Y-%m-%d')  # Fecha actual (por ejemplo: '2026-02-02')
    try:
        # Consulta la tabla para obtener el registro del cliente para hoy
        response = table.get_item(
            Key={'user_id': client_ip, 'date': today}
        )
        
        if 'Item' in response:
            images_generated_today = response['Item']['images_generated_today']
            if images_generated_today >= int(MAX_IMAGENES_PER_DAY):
                return False  # Límite alcanzado, no se puede generar más imágenes
            else:
                return True  # Puede generar más imágenes
        else:
            # Si no hay registro para el día de hoy, crear un nuevo registro
            table.put_item(
                Item={'user_id': client_ip, 'date': today, 'images_generated_today': 0}
            )
            return True  # Puede generar la primera imagen del día

    except Exception as e:
        st.error(f"Error querying DynamoDB: {e}")
        return False

# Función para actualizar el contador de imágenes generadas por el cliente
def increment_image_count(client_ip):
    today = datetime.now().strftime('%Y-%m-%d')
    
    try:
        # Intenta obtener el item existente
        response = table.get_item(
            Key={'user_id': client_ip, 'date': today}
        )
        
        if 'Item' in response:
            # Si ya existe, incrementa el contador
            current_count = response['Item']['images_generated_today']
            if current_count < int(MAX_IMAGENES_PER_DAY):
                table.update_item(
                    Key={'user_id': client_ip, 'date': today},
                    UpdateExpression="SET images_generated_today = :val",
                    ExpressionAttributeValues={':val': current_count + 1}
                )
                return True  # Se actualizó correctamente
            else:
                return False  # Límite alcanzado
        else:
            # Si no existe, crea el registro con la primera imagen
            table.put_item(
                Item={'user_id': client_ip, 'date': today, 'images_generated_today': 0}
            )
            return True  # Se creó el nuevo registro

    except Exception as e:
        st.error(f"Error updating DynamoDB: {e}")
        return False
    
# Función para obtener la IP del cliente
def get_client_ip():
    """Obtiene la dirección IP del cliente"""
    try:
        # Método 1: Usando streamlit (IP local en desarrollo)
        session = st.runtime.get_instance()._session_mgr.list_active_sessions()
        if session:
            # En producción con Streamlit Cloud o servidor
            ip = st.context.headers.get("X-Forwarded-For")
            if ip:
                # Tomar la primera IP si hay múltiples
                return ip.split(",")[0].strip()
        
        # Método 2: Obtener IP pública usando servicio externo
        response = requests.get('https://api.ipify.org?format=json', timeout=3)
        if response.status_code == 200:
            return response.json()['ip']
    except:
        pass
    
    try:
        # Método 3: IP local de la máquina
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        return local_ip
    except:
        return "No disponible"

# Función para obtener información adicional de la IP
def get_ip_info(ip):
    """Obtiene información geográfica de la IP"""
    try:
        if ip and ip != "No disponible" and not ip.startswith("127.") and not ip.startswith("192.168."):
            response = requests.get(f'https://ipapi.co/{ip}/json/', timeout=3)
            if response.status_code == 200:
                return response.json()
    except:
        pass
    return None

# Función para inicializar Vertex AI
@st.cache_resource
def initialize_vertex_ai():
    """Inicializa la conexión con Vertex AI"""
    try:
        return GOOGLE_VERTEX_AI_MODELO
    except Exception as e:
        st.error(f"Error initializing Vertex AI: {str(e)}")
        return None
    
         
def chatbot_page():
    st.set_page_config(page_title="AI Chatbot SIU", page_icon="")
    st.title("AI Chatbot")
    st.markdown("This is a AI chatbot SIU. Type your message!")
    
    if st.button("🗑️ New chat"):
        st.session_state.messages = []
        st.rerun()
    
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    try:
        for msg in st.session_state.messages:
            if isinstance(msg, SystemMessage):
                print(f"Mensaje msg: {msg}")
                continue  # no mostrar mensajes del sistema al usuario

            role = "assistant" if isinstance(msg, AIMessage) else "user"
            with st.chat_message(role):
                if not isinstance(msg, dict):
                    if msg is not "":
                        st.markdown(msg.content)
    except Exception as e:
        st.markdown("Error")
    
    # Input de usuario
    pregunta = st.chat_input("Enter message")
    
    if pregunta:
        # Mostrar y almacenar mensaje del usuario
        with st.chat_message("user"):
            st.markdown(pregunta)

        try:
            #Mostrar la respuesta en el interfaz
            with st.chat_message("assistant"):
                response_placeholder = st.empty()
                full_response = ""

                try:
                    full_response = get_bedrock_response(pregunta)
                    response_placeholder.markdown(full_response)

                except NoCredentialsError:
                    st.error("AWS credentials could not be found.")
                    return

            #Almacenamos el mensaje
            st.session_state.messages.append(HumanMessage(content=pregunta))
            st.session_state.messages.append(AIMessage(content=full_response))

        except Exception as e:
            st.error(f"Error generating response: {str(e)}")
            st.info("Verify that your AWS API key credentials are configured correctly.")

# Función para mostrar la página de generación de imágenes
def image_generation_page(client_ip):

    st.title("Image Generator from Text")
    
    model = initialize_vertex_ai()
    
    if "images" not in st.session_state:
        st.session_state.images = bytes()
    
    if "text_content" not in st.session_state:
        st.session_state.text_content = ""
        
    # Create two columns with equal width
    col1, col2 = st.columns([3,1])
    
    try:
        if len(st.session_state.images) > 0:
            with col1:
                img_bytes = st.session_state.images
                st.text_area("📝 Describe the image you want to generate...", st.session_state.text_content, height=100)
                st.image(img_bytes, caption="Image", width='stretch')
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                st.download_button(
                    label=f"Download image",
                    data=img_bytes,
                    file_name=f"imagen_{ts}.png",
                    mime="image/png",
                )
        else:
            with col1:
                prompt = st.text_area(
                "📝 Describe the image you want to generate...",
                height=100,
                placeholder="Example: An astronaut cat floating in space, art nouveau style, vibrant colors, high quality.",
                
                )
                if st.button("Generate Image"):
                    if check_image_limit(client_ip):
                        if prompt:
                            #image = generate_image_from_text(model, prompt)
                            text_out, images_out = generate_image_from_text(model, prompt)
                            
                            if text_out:
                                st.markdown(text_out)
                                
                            if not images_out:
                                    st.warning("No image appeared. Write a message explicitly requesting an image.")
                            else:
                                for idx, img_bytes in enumerate(images_out, start=1):
                                    st.image(img_bytes, caption=f"Resultado {idx}", width='stretch')

                                    # Botón de descarga
                                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                                    st.download_button(
                                        label=f"Download image",
                                        data=img_bytes,
                                        file_name=f"imagen_{ts}_{idx}.png",
                                        mime="image/png",
                                    )
                                increment_image_count(client_ip)
                            # st.session_state.images.append(
                            #     {"role": "assistant", "text": text_out, "imagenes": images_out}
                            # )
                            st.session_state.images = img_bytes
                            st.session_state.text_content = prompt
                        else:
                            st.error("Enter a description to generate the image.")
                    else:
                        st.info("You've reached today's image limit. Please try again tomorrow.")
    except Exception as e:
        exc_type, exc_obj, tb = sys.exc_info()
        line_number = tb.tb_lineno
        st.markdown(f"Error:  {str(e)}; line_number: {line_number }")

    with col2:
        if st.button("New Image"):
            st.session_state.images = bytes()
            st.session_state.text_content = ""
            st.rerun()
     
def generate_image_from_text(model, prompt):
    
    """Genera imágenes usando Vertex AI"""
    try:
        with st.spinner("Generando imágenes... ✨"):
            response = client_vertex_ai.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE"],
                ),
            )
            
            text_out = ""
            images_out: list[bytes] = []

            for part in response.candidates[0].content.parts:
                if getattr(part, "text", None):
                    text_out += part.text
                elif getattr(part, "inline_data", None) and getattr(part.inline_data, "data", None):
                    images_out.append(part.inline_data.data)

            return text_out.strip(), images_out
    except Exception as e:
        st.error(f"Error generating images: {str(e)}")
        return None

def bytes_to_png(image_bytes: bytes, output_filename: str):
    """
    Converts a bytes object to a PNG file using the Pillow library.

    Args:
        image_bytes: The input image data as a bytes object.
        output_filename: The name of the output PNG file (e.g., "output.png").
    """
    try:
        # Use io.BytesIO to treat the bytes object as a file
        image_stream = io.BytesIO(image_bytes)
        
        # Open the image from the stream using Pillow
        # Pillow automatically identifies the image format from the bytes
        img = Image.open(image_stream)
        
        # Save the image object as a PNG file
        img.save(output_filename, format="PNG")
        print(f"Image successfully saved as {output_filename}")

    except IOError as e:
        print(f"Error: Could not identify image file or save it. {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

# Función para convertir imagen a bytes para descargar
def get_image_download_link(img, filename):
    """Genera un link de descarga para la imagen"""
    buffered = io.BytesIO()
    img._pil_image.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    href = f'<a href="data:file/png;base64,{img_str}" download="{filename}">Download image</a>'
    return href

# Lógica para obtener la respuesta del modelo de Amazon Bedrock
def get_bedrock_response(user_input):
    model_id = AWS_BEDROCK_AI_MODELO #anthropic.claude-3-haiku-20240307-v1:0
    try:
        # Format the request payload using the model's native structure.
        native_request = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 512,
            "temperature": 0.7,
            "top_p": 0.6,
            "messages": [
                {
                    "role": "user",
                    "content": [{"type": "text", "text": user_input}],
                }
            ],
        }
        
        # Convert the native request to JSON.
        request = json.dumps(native_request)
        print("Request body:", request)
        
        response = bedrock_client.invoke_model(
            modelId=model_id, 
            body=request,
            contentType='application/json'
        )
        # Decode the response body.
        model_response = json.loads(response["body"].read())

        # Extract and print the response text.
        response_text = model_response["content"][0]["text"]
        print(response_text)

        return response_text
    except Exception as e:
        st.error(f"Error getting response: {e}")
        return "I'm sorry, I can't answer at this time."

def main_chat():
    
    # Crear los botones tipo TAB
    #with st.spinner("Obteniendo IP..."):
    client_ip = get_client_ip()
    #with st.sidebar:
    st.sidebar.image("images/image.png", width=200)
    st.sidebar.info(f"**IP:** `{client_ip}`")
    
    # Mostrar información geográfica si está disponible
    if client_ip and client_ip != "No disponible":
        ip_info = get_ip_info(client_ip)
        if ip_info:
            st.sidebar.caption(f"📍 {ip_info.get('city', '')}, {ip_info.get('country_name', '')}")
            st.sidebar.caption(f"🌍 {ip_info.get('org', 'ISP no disponible')}")
    
    
    option = st.sidebar.radio("Select an option", ("AI Chatbot", "Image Generator"))
        
    #st.markdown("---")
    if option == "AI Chatbot":
        chatbot_page()  # Redirige al chatbot
    elif option == "Image Generator":
        image_generation_page(client_ip)  # Redirige a la página de imágenes

if __name__ == '__main__':
    main_chat()