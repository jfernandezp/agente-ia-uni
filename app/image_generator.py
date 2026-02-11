import streamlit as st
import json
import base64
import sys
from datetime import datetime

def generate_image_from_text(bedrock_client, model_id_titan: str, prompt: str):
    """
    Retorna: ("", img_bytes) donde img_bytes es PNG bytes.
    """
    payload = {
        "taskType": "TEXT_IMAGE",
        "textToImageParams": {"text": str(prompt)},
        "imageGenerationConfig": {
            "numberOfImages": 1,
            "height": 1024,
            "width": 1024,
            "cfgScale": 8,
            "seed": 12345,
            "quality": "standard",
        },
    }

    with st.spinner("Generating image... ✨"):
        response = bedrock_client.invoke_model(
            modelId=model_id_titan,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(payload),
        )

    data = json.loads(response["body"].read())
    img_b64 = data["images"][0]
    img_bytes = base64.b64decode(img_b64)
    return "", img_bytes


def render_image_generator(
    client_ip: str,
    bedrock_client,
    model_id_titan: str,
    check_image_limit_fn,
    increment_image_count_fn,
) -> None:
    st.title("🎓 LucIA - Image Generator from Text")

    if "images" not in st.session_state:
        st.session_state.images = bytes()

    if "text_content" not in st.session_state:
        st.session_state.text_content = ""

    if st.button("New Image", key="img_btn_new"):
        st.session_state.images = bytes()
        st.session_state.text_content = ""
        st.rerun()

    try:
        # Si ya hay imagen, muéstrala + descarga
        if len(st.session_state.images) > 0:
            img_bytes = st.session_state.images
            st.text_area(
                "📝 Describe the image you want to generate...",
                st.session_state.text_content,
                height=100,
                key="img_prompt_view",
            )
            st.image(img_bytes, caption="Image", width='content')
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            st.download_button(
                label="Download image",
                data=img_bytes,
                file_name=f"imagen_{ts}.png",
                mime="image/png",
                key="img_btn_download",
            )
            return

        # Si no hay imagen, formulario de generación
        prompt = st.text_area(
            "📝 Describe the image you want to generate...",
            height=100,
            placeholder="Example: An astronaut cat floating in space, art nouveau style, vibrant colors, high quality.",
            key="img_prompt_edit",
        )

        if st.button("Generate Image", key="img_btn_generate"):
            if not check_image_limit_fn(client_ip):
                st.info("You've reached today's image limit. Please try again tomorrow.")
                return

            if not prompt.strip():
                st.error("Enter a description to generate the image.")
                return

            text_out, img_bytes = generate_image_from_text(bedrock_client, model_id_titan, prompt)

            if text_out:
                st.markdown(text_out)

            st.image(img_bytes, caption="Resultado", width='content')

            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            st.download_button(
                label="Download image",
                data=img_bytes,
                file_name=f"imagen_{ts}.png",
                mime="image/png",
                key="img_btn_download_now",
            )

            increment_image_count_fn(client_ip)
            st.session_state.images = img_bytes
            st.session_state.text_content = prompt

    except Exception as e:
        tb = sys.exc_info()[2]
        line_number = tb.tb_lineno if tb else "?"
        st.error(f"Error: {e}. Line: {line_number}")
