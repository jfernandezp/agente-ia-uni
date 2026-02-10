import streamlit as st
import boto3
from langchain_aws import ChatBedrock  # Cambiado de BedrockChat a ChatBedrock
from langchain_core.memory import ConversationBufferMemory  # Cambiado de langchain_core
from langchain_core.chains import ConversationChain  # Cambiado de langchain_core
from langchain_core.prompts import PromptTemplate
from botocore.exceptions import ClientError
import sys

def initialize_deepseek_chatbot(system_instructions=None):
    """
    Inicializa un chatbot con DeepSeek en AWS Bedrock usando LangChain.
    
    Args:
        system_instructions (str): Instrucciones del sistema para el chatbot
    
    Returns:
        ConversationChain: Cadena de conversación configurada
    """
    
    # Configuración de AWS Bedrock
    AWS_BEDROCK_MODEL_ID = "deepseek.mistral.mistral-large-2402-v1:0"
    AWS_REGION = "us-east-1"
    
    # Instrucciones por defecto si no se proporcionan
    if system_instructions is None:
        system_instructions = """Eres un asistente de IA útil y educado llamado Asistente USIL. 
Responde preguntas sobre la Universidad San Ignacio de Loyola (USIL) y San Ignacio University (SIU).
Sé preciso, conciso y amable en tus respuestas.
Si no sabes algo, admítelo honestamente.
Usa español para todas las respuestas."""
    
    try:
        # Inicializar cliente de Bedrock
        bedrock_client = boto3.client(
            service_name="bedrock-runtime",
            region_name=AWS_REGION
        )
        
        # Configurar el modelo de chat de Bedrock - ACTUALIZADO
        llm = ChatBedrock(
            client=bedrock_client,
            model_id=AWS_BEDROCK_MODEL_ID,
            model_kwargs={
                "temperature": 0.7,
                "max_tokens": 1000,
                "top_p": 0.9,
            },
            streaming=False
        )
        
        # Crear template del prompt con instrucciones del sistema
        prompt_template = PromptTemplate(
            input_variables=["history", "input"],
            template=f"""{system_instructions}

Historial de conversación:
{{history}}

Usuario: {{input}}
Asistente:"""
        )
        
        # Configurar memoria para la conversación - ACTUALIZADO
        memory = ConversationBufferMemory(
            memory_key="history",
            return_messages=True,
            human_prefix="Usuario",
            ai_prefix="Asistente"
        )
        
        # Crear cadena de conversación - ACTUALIZADO
        conversation_chain = ConversationChain(
            llm=llm,
            memory=memory,
            prompt=prompt_template,
            verbose=False
        )
        
        return conversation_chain
        
    except ClientError as e:
        st.error(f"Error de AWS Bedrock: {e.response['Error']['Message']}")
        return None
    except Exception as e:
        exc_type, exc_obj, tb = sys.exc_info()
        line_number = tb.tb_lineno
        st.error(f"Error al inicializar el chatbot: {str(e)} - Línea: {line_number}")
        return None

def create_chat_interface(conversation_chain, title="Chatbot USIL", greeting=None):
    """
    Crea una interfaz de chat en Streamlit.
    
    Args:
        conversation_chain (ConversationChain): Cadena de conversación inicializada
        title (str): Título del chat
        greeting (str): Mensaje de bienvenida inicial
    """
    
    if greeting is None:
        greeting = "¡Hola! Soy tu asistente de USIL. ¿En qué puedo ayudarte hoy?"
    
    # Configurar título
    st.title(f"🤖 {title}")
    
    # Inicializar historial de chat en session_state
    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": greeting}]
    
    if "conversation" not in st.session_state:
        st.session_state.conversation = conversation_chain
    
    # Mostrar historial de mensajes
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])
    
    # Input del usuario
    if prompt := st.chat_input("Escribe tu pregunta aquí..."):
        # Añadir mensaje del usuario
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)
        
        # Obtener respuesta del chatbot
        with st.chat_message("assistant"):
            with st.spinner("Pensando..."):
                try:
                    # Usar la cadena de conversación - ACTUALIZADO
                    response = st.session_state.conversation.run(input=prompt)
                    
                    # Limpiar respuesta si es necesario
                    response = response.strip()
                    
                    # Mostrar respuesta
                    st.write(response)
                    
                    # Añadir al historial
                    st.session_state.messages.append(
                        {"role": "assistant", "content": response}
                    )
                    
                except Exception as e:
                    error_msg = f"Lo siento, hubo un error al procesar tu pregunta: {str(e)}"
                    st.write(error_msg)
                    st.session_state.messages.append(
                        {"role": "assistant", "content": error_msg}
                    )
    
    # Sidebar con opciones adicionales
    with st.sidebar:
        st.header("⚙️ Configuración del Chat")
        
        # Botón para limpiar conversación
        if st.button("🧹 Limpiar Conversación"):
            st.session_state.messages = [{"role": "assistant", "content": greeting}]
            if st.session_state.conversation:
                st.session_state.conversation.memory.clear()
            st.rerun()
        
        # Mostrar información del modelo
        st.subheader("ℹ️ Información")
        st.write(f"**Modelo:** DeepSeek")
        st.write(f"**Plataforma:** AWS Bedrock")

# Versión alternativa si tienes problemas con langchain-aws
def initialize_deepseek_chatbot_alternative(system_instructions=None):
    """
    Versión alternativa usando directamente boto3 si hay problemas con LangChain.
    """
    
    AWS_BEDROCK_MODEL_ID = "deepseek.mistral.mistral-large-2402-v1:0"
    
    if system_instructions is None:
        system_instructions = """Eres un asistente de IA útil y educado. Responde en español."""
    
    # Crear una clase simple para simular el comportamiento de LangChain
    class SimpleDeepSeekChat:
        def __init__(self, system_instructions):
            self.system_instructions = system_instructions
            self.memory = []
            self.client = boto3.client("bedrock-runtime", region_name="us-east-1")
        
        def run(self, input_text):
            try:
                # Formatear el prompt con historial
                history_text = "\n".join([f"{msg['role']}: {msg['content']}" 
                                        for msg in self.memory[-5:]])  # Últimos 5 mensajes
                
                prompt = f"""{self.system_instructions}

Historial previo:
{history_text}

Usuario: {input_text}
Asistente:"""
                
                body = {
                    "prompt": prompt,
                    "max_tokens": 1000,
                    "temperature": 0.7,
                    "top_p": 0.9
                }
                
                response = self.client.invoke_model(
                    modelId=AWS_BEDROCK_MODEL_ID,
                    body=json.dumps(body)
                )
                
                response_body = json.loads(response["body"].read())
                response_text = response_body["choices"][0]["text"].strip()
                
                # Guardar en memoria
                self.memory.append({"role": "Usuario", "content": input_text})
                self.memory.append({"role": "Asistente", "content": response_text})
                
                return response_text
                
            except Exception as e:
                return f"Error: {str(e)}"
        
        def clear_memory(self):
            self.memory = []
    
    return SimpleDeepSeekChat(system_instructions)

# Función principal actualizada
def main():
    """
    Ejemplo de implementación principal.
    """
    st.set_page_config(
        page_title="Chatbot USIL - DeepSeek",
        page_icon="🎓",
        layout="wide"
    )
    
    st.markdown("<h1 style='text-align: center; color: #2E86C1;'>🎓 Asistente Virtual USIL</h1>", 
                unsafe_allow_html=True)
    
    # Opción para elegir método
    method = st.sidebar.selectbox(
        "Selecciona el método:",
        ["LangChain (Recomendado)", "Directo Boto3"]
    )
    
    if method == "LangChain (Recomendado)":
        try:
            # Intentar con LangChain actualizado
            chatbot = initialize_deepseek_chatbot()
            if chatbot:
                create_chat_interface(
                    conversation_chain=chatbot,
                    title="Asistente USIL (LangChain)",
                    greeting="¡Hola! Soy tu asistente, ¿en qué puedo ayudarte?"
                )
            else:
                st.error("No se pudo inicializar con LangChain. Probando método alternativo...")
                # Fallback al método alternativo
                chatbot_alt = initialize_deepseek_chatbot_alternative()
                create_simple_interface(chatbot_alt)
        except Exception as e:
            st.error(f"Error con LangChain: {e}")
            st.info("Intentando método alternativo...")
            chatbot_alt = initialize_deepseek_chatbot_alternative()
            create_simple_interface(chatbot_alt)
    
    else:
        # Método directo con Boto3
        chatbot_alt = initialize_deepseek_chatbot_alternative()
        create_simple_interface(chatbot_alt)

def create_simple_interface(chatbot, title="Chatbot USIL"):
    """Interfaz simple para el método alternativo."""
    
    st.title(f"🤖 {title}")
    
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])
    
    if prompt := st.chat_input("Escribe tu mensaje..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)
        
        with st.chat_message("assistant"):
            with st.spinner("Pensando..."):
                response = chatbot.run(prompt)
                st.write(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
    
    if st.sidebar.button("Limpiar chat"):
        st.session_state.messages = []
        chatbot.clear_memory()
        st.rerun()

if __name__ == "__main__":
    import json  # Asegúrate de importar json si usas el método alternativo
    main()