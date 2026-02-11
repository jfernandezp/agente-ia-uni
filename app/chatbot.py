import streamlit as st
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from botocore.exceptions import NoCredentialsError


def get_bedrock_response_deepseek(bedrock_client, model_id_deepseek: str, user_input: str) -> str:
    
    formatted_prompt = f"""Eres Asistente de USIL y SIU con nombre LucIA , un experto en la Universidad San Ignacio de Loyola (USIL) y San Ignacio University (SIU).
            Pregunta: {user_input}
            INSTRUCCIONES:
            1. Responde exclusivamente en español e Inglés de ser el caso.
            2. Sé preciso y veraz con la información
            3. Si no sabes algo, di: "No tengo esa información específica, pero puedo ayudarte con otros temas sobre USIL"
            4. Mantén un tono profesional y amable
            5. Proporciona información clara y estructurada cuando sea apropiado
            6. Cuando te pregunten de  Universidad San Ignacio de Loyola (USIL) toma como referencia esta página web https://usil.edu.pe/ y https://descubre.usil.edu.pe/landings/pregrado/admision/
            7. Cuando te pregunten de San Ignacio University (SIU) toma como referencia esta página web https://www.sanignaciouniversity.edu/
            8. Cuando te pregunten por la carrera Medicina Humana, responde en base a esta web: https://usil.edu.pe/pregrado/medicina-humana/
            
            NO hagas:
            - No inventes información
            - No uses jerga técnica excesiva
            - No incluyas opiniones personales
            - No proporciones información desactualizada
            
            Instrucciones de formato:
            1. Usa **negritas** para puntos importantes
            2. Usa listas con guiones (-) para enumerar
            3. Separa con saltos de línea
            4. Mantén respuestas claras y organizadas
            
            Respuesta:
            """

    body = {
        "prompt": formatted_prompt,
        "max_tokens": 512,
        "temperature": 0.5,
        "top_p": 0.9,
    }

    response = bedrock_client.invoke_model(modelId=model_id_deepseek, body=__import__("json").dumps(body))
    model_response = __import__("json").loads(response["body"].read())

    choices = model_response.get("choices", [])
    if not choices:
        return "No recibí una respuesta del modelo."

    return choices[0].get("text", "").strip().replace("</think>", "")


def render_chatbot(bedrock_client, model_id_deepseek: str) -> None:
    st.title("🎓 LucIA - Chat")
    st.info("*LucIA* is the official virtual assistant of the SIU. Type your message!")
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []
        
    if st.button("🗑️ New chat", key="chat_btn_new"):
        st.session_state.chat_messages = []
        st.rerun()
        
    # Pintar historial
    # for msg in st.session_state.messages:
    #     if isinstance(msg, SystemMessage):
    #         continue

    #     role = "assistant" if isinstance(msg, AIMessage) else "user"
    #     with st.chat_message(role):
    #         if hasattr(msg, "content") and msg.content:
    #             st.markdown(msg.content)
    
    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
        
    pregunta = st.chat_input("Enter message ...", key="chat_input_main")
    if not pregunta:
        return

    with st.chat_message("user"):
        st.markdown(pregunta)

    with st.chat_message("assistant"):
        placeholder = st.empty()
        try:
            respuesta = get_bedrock_response_deepseek(bedrock_client, model_id_deepseek, pregunta)
            placeholder.markdown(respuesta)
        except NoCredentialsError:
            st.error("AWS credentials could not be found.")
            return
        except Exception as e:
            st.error(f"Error generating response: {e}")
            return

    # st.session_state.messages.append(HumanMessage(content=pregunta))
    # st.session_state.messages.append(AIMessage(content=respuesta))
    st.session_state.chat_messages.append({
        "role": "user",
        "content": pregunta
    })

    st.session_state.chat_messages.append({
        "role": "assistant",
        "content": respuesta
    })
