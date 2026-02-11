import streamlit as st
import json
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_aws import ChatBedrock
from botocore.exceptions import NoCredentialsError
import re


def clean_deepseek_response(text: str) -> str:
    """
    Limpia la respuesta de DeepSeek eliminando tokens especiales y formateo no deseado
    """
    if not text:
        return text
    
    # Eliminar todos los tokens especiales de DeepSeek
    tokens_to_remove = [
        "<|begin_of_sentence|>",
        "<|end_of_sentence|>",
        "<|User|>",
        "<|Assistant|>",
        "<|system|>",
        "<|end|>",
        "<|endoftext|>",
        "<｜User｜>",  # Versiones con caracteres diferentes
        "<｜Assistant｜>",
        "<｜tool▁outputs▁end｜>",  # Otro token común
        "<｜fim▁end｜>",  # Tokens en chino
        "<｜fim▁begin｜>## DeepSeek",
        "<｜DS▁User｜>",  # Token de usuario en chino
        "<｜DS▁Assistant｜>",  # Token de asistente en chino
    ]
    
    cleaned = text
    for token in tokens_to_remove:
        cleaned = cleaned.replace(token, "")
    
    # Eliminar líneas que comienzan con "User:" o "Assistant:" 
    lines = cleaned.split('\n')
    filtered_lines = []
    
    for line in lines:
        line = line.strip()
        # Saltar líneas que sean solo tokens o encabezados
        if line and not line.startswith(('User:', 'Assistant:', 'Human:', 'AI:', 'Respuesta:', 'LucIA:')):
            filtered_lines.append(line)
    
    cleaned = '\n'.join(filtered_lines)
    
    # Limpiar espacios extras
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    cleaned = cleaned.strip()
    
    # Si la respuesta está vacía después de limpiar, devolver mensaje por defecto
    if not cleaned:
        return "Lo siento, no pude generar una respuesta válida."
    
    return cleaned

def create_deepseek_chat_chain(bedrock_client, model_id_deepseek: str):
    """Crea una cadena de chat con LangChain para DeepSeek"""
    
    system_prompt = """Eres LucIA, el Asistente de IA oficial de la Universidad San Ignacio de Loyola (USIL) y San Ignacio University (SIU).

Tu función es proporcionar información precisa y actualizada sobre:
1. Universidad San Ignacio de Loyola (USIL) - Perú
2. San Ignacio University (SIU) - Estados Unidos
3. Carreras, programas, admisiones y servicios universitarios

INSTRUCCIONES:
1. Responde exclusivamente en español e inglés según corresponda
2. Sé preciso y veraz con la información
3. Si no sabes algo, di: "No tengo esa información específica, pero puedo ayudarte con otros temas sobre USIL/SIU"
4. Mantén un tono profesional y amable
5. Proporciona información clara y estructurada cuando sea apropiado

FUENTES DE INFORMACIÓN:
- Para USIL: https://usil.edu.pe/ y https://descubre.usil.edu.pe/landings/pregrado/admision/
- Para SIU: https://www.sanignaciouniversity.edu/
- Para Medicina Humana: https://usil.edu.pe/pregrado/medicina-humana/

RESTRICCIONES:
- No inventes información
- No uses jerga técnica excesiva
- No incluyas opiniones personales
- No proporciones información desactualizada

FORMATO:
- Usa **negritas** para puntos importantes
- Usa listas con viñetas para enumerar
- Separa con saltos de línea para claridad
- Mantén respuestas organizadas y concisas"""
    
    # Crear el modelo Bedrock con LangChain
    llm = ChatBedrock(
        client=bedrock_client,
        model_id=model_id_deepseek,
        model_kwargs={
            "max_tokens": 1024,
            "temperature": 0.5,
            "top_p": 0.9,
        },
        streaming=False
    )
    
    # Crear prompt template con historial de conversación
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}")
    ])
    
    # Crear cadena
    chain = prompt | llm | StrOutputParser()
    
    return chain


def get_bedrock_response_deepseek(bedrock_client, model_id_deepseek: str, user_input: str, chat_history: list = None) -> str:
    """Obtiene respuesta usando LangChain"""
    
    if chat_history is None:
        chat_history = []
    
    try:
        # Crear cadena de chat
        chain = create_deepseek_chat_chain(bedrock_client, model_id_deepseek)
        
        # Formatear historial para LangChain
        langchain_messages = []
        for msg in chat_history:
            if msg["role"] == "user":
                langchain_messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                langchain_messages.append(AIMessage(content=msg["content"]))
        
        # Invocar la cadena
        response = chain.invoke({
            "input": user_input,
            "chat_history": langchain_messages
        })
        
        return response
        
    except Exception as e:
        return f"Error al generar respuesta: {str(e)}"


def render_chatbot(bedrock_client, model_id_deepseek: str) -> None:
    st.title("🎓 LucIA - Chat Assistant")
    st.info("**LucIA** is the official virtual assistant of USIL and SIU. Feel free to ask about programs, admissions, and university services!")
    
    # Inicializar estado de sesión - SIMPLIFICADO
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # Sidebar con controles
    with st.sidebar:
        st.subheader("📊 Chat Controls")
        
        if st.button("🗑️ New Chat", use_container_width=True, type="primary"):
            st.session_state.messages = []
            st.rerun()
        
        st.divider()
        
        st.subheader("📝 Conversation Info")
        st.caption(f"Messages: {len(st.session_state.messages)}")
        
        if st.session_state.messages:
            if st.button("💾 Export Chat", use_container_width=True):
                chat_text = "\n".join([
                    f"{msg['role'].upper()}: {msg['content']}" 
                    for msg in st.session_state.messages
                ])
                st.download_button(
                    label="Download as TXT",
                    data=chat_text,
                    file_name=f"lucia_chat_session.txt",
                    mime="text/plain",
                    use_container_width=True
                )
    
    # Mostrar historial del chat de manera SIMPLE
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Input del usuario
    if prompt := st.chat_input("Escribe tu mensaje aquí..."):
        # Mostrar mensaje del usuario
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Agregar a historial
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Generar respuesta
        with st.chat_message("assistant"):
            with st.spinner("🤔 Thinking..."):
                try:
                    # Preparar historial para LangChain
                    chat_history = []
                    for msg in st.session_state.messages[:-1]:  # Excluir el último mensaje (el actual)
                        chat_history.append({
                            "role": msg["role"],
                            "content": msg["content"]
                        })
                    
                    respuesta = get_bedrock_response_deepseek(
                        bedrock_client,
                        model_id_deepseek,
                        prompt,
                        chat_history
                    )
                    
                    cleaned_response = clean_deepseek_response(respuesta)
                    
                    # Mostrar respuesta
                    st.markdown(cleaned_response)
                    
                    # Agregar respuesta al historial
                    st.session_state.messages.append({"role": "assistant", "content": cleaned_response})
                    
                except NoCredentialsError:
                    error_msg = "❌ AWS credentials could not be found."
                    st.error(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})
                except Exception as e:
                    error_msg = f"❌ Error generating response: {e}"
                    st.error(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})