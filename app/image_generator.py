import streamlit as st
import json
import base64
import sys
from datetime import datetime
from langchain_aws import ChatBedrock
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser


def enhance_prompt_with_langchain(user_prompt: str) -> str:
    """Mejora el prompt usando LangChain para mejores resultados"""
    
    template = """Eres un experto en generación de prompts para imágenes AI. 
    Mejora el siguiente prompt para Amazon Titan Image Generator, siguiendo estas reglas:
    
    1. Añade detalles visuales específicos
    2. Incluye estilo artístico apropiado
    3. Especifica calidad y composición
    4. Mantén el significado original
    
    Prompt original: {user_prompt}
    
    Prompt mejorado (solo el prompt, sin explicaciones):"""
    
    # En una implementación real, usarías un modelo de texto para mejorar el prompt
    # Por ahora, simplemente añadimos detalles genéricos
    enhanced = f"{user_prompt}, digital art, high quality, detailed, 4k resolution, professional composition"
    
    return enhanced


def generate_image_from_text(bedrock_client, model_id_titan: str, prompt: str):
    """
    Retorna: ("", img_bytes) donde img_bytes es PNG bytes.
    """
    # Mejorar el prompt usando LangChain
    enhanced_prompt = enhance_prompt_with_langchain(prompt)
    
    payload = {
        "taskType": "TEXT_IMAGE",
        "textToImageParams": {"text": str(enhanced_prompt)},
        "imageGenerationConfig": {
            "numberOfImages": 1,
            "height": 1024,
            "width": 1024,
            "cfgScale": 8,
            "seed": int(datetime.now().timestamp() % 10000),  # Seed dinámico
            "quality": "standard",  # Cambiado a premium para mejor calidad
        },
    }

    with st.spinner("🎨 Generating image with AI magic..."):
        response = bedrock_client.invoke_model(
            modelId=model_id_titan,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(payload),
        )

    data = json.loads(response["body"].read())
    img_b64 = data["images"][0]
    img_bytes = base64.b64decode(img_b64)
    return enhanced_prompt, img_bytes


def render_image_generator(
    client_ip: str,
    bedrock_client,
    model_id_titan: str,
    check_image_limit_fn,
    increment_image_count_fn,
) -> None:
    
    st.title("🎨 Ignacio Connect - AI Image Generator")
    #st.info("Transform your ideas into stunning visual art with AI!")
    
    # Inicializar estado
    if "generated_images" not in st.session_state:
        st.session_state.generated_images = []
    
    if "current_prompt" not in st.session_state:
        st.session_state.current_prompt = ""
    
    # Sidebar con controles y estadísticas
    with st.sidebar:
        st.subheader("🛠️ Image Settings")
        
        # Selector de calidad
        # quality = st.selectbox(
        #     "Quality",
        #     ["standard", "premium"],
        #     index=1,
        #     help="Premium quality generates higher resolution images"
        # )
        
        # Selector de tamaño
        size_options = {
            #"Square (1024x1024)": (1024, 1024),
            "Portrait (768x1024)": (768, 1024),
            #"Landscape (1024x768)": (1024, 768),
        }
        
        selected_size = st.selectbox(
            "Aspect Ratio",
            list(size_options.keys()),
            index=0
        )
        
        width, height = size_options[selected_size]
        
        st.divider()
        
        st.subheader("📊 Usage Stats")
        try:
            if check_image_limit_fn(client_ip):
                st.success("✅ You can generate images today")
            else:
                st.warning("⚠️ Daily limit reached")
        except:
            pass
        
        st.caption(f"Generated today: {len(st.session_state.generated_images)}")
        
        if st.session_state.generated_images:
            if st.button("🗑️ Clear History", use_container_width=True):
                st.session_state.generated_images = []
                st.session_state.current_prompt = ""
                st.rerun()
    
    # Contenedor principal
    main_container = st.container()
    
    with main_container:
        # Si hay imágenes generadas, mostrar la última
        if st.session_state.generated_images:
            latest = st.session_state.generated_images[-1]
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.image(
                    latest["image_bytes"],
                    caption=f"🎨 {latest['prompt'][:50]}...",
                    use_container_width=True
                )
            
            with col2:
                st.subheader("📝 Prompt Used")
                st.info(latest["prompt"])
                
                st.download_button(
                    label="⬇️ Download Image",
                    data=latest["image_bytes"],
                    file_name=f"lucia_ai_art_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
                    mime="image/png",
                    use_container_width=True,
                    type="primary"
                )
                
                if st.button("🔄 Generate New", use_container_width=True):
                    st.session_state.current_prompt = ""
                    st.rerun()
        
        # Formulario de generación
        st.subheader("✨ Create New Image")
        
        prompt = st.text_area(
            "Describe your imagination...",
            value=st.session_state.current_prompt,
            height=120,
            placeholder="Example: A futuristic university campus with flying books and holographic professors, cyberpunk style, neon lights, detailed illustration...",
            help="Be as descriptive as possible for better results!"
        )
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            generate_disabled = not check_image_limit_fn(client_ip) if client_ip else False
            
            if st.button(
                "🚀 Generate Image",
                disabled=generate_disabled,
                use_container_width=True,
                type="primary"
            ):
                if not prompt.strip():
                    st.error("Please enter a description for the image!")
                    return
                
                try:
                    # Generar imagen
                    enhanced_prompt, img_bytes = generate_image_from_text(
                        bedrock_client,
                        model_id_titan,
                        prompt
                    )
                    
                    # Guardar en historial
                    st.session_state.generated_images.append({
                        "prompt": enhanced_prompt,
                        "original_prompt": prompt,
                        "image_bytes": img_bytes,
                        "timestamp": datetime.now(),
                        "size": f"{width}x{height}"
                    })
                    
                    # Actualizar contador
                    if increment_image_count_fn(client_ip):
                        st.success("✅ Image generated successfully!")
                    else:
                        st.warning("⚠️ Daily limit reached after this generation")
                    
                    st.session_state.current_prompt = prompt
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ Error generating image: {str(e)}")
        
        # with col2:
        #     if st.button("💡 Example Prompts", use_container_width=True):
        #         examples = [
        #             "A wise owl teaching in a library with floating books",
        #             "Futuristic university with transparent buildings and flying vehicles",
        #             "Graduation ceremony with holographic diplomas in space",
        #             "AI robot and human student collaborating in a lab",
        #             "Ancient wisdom meets modern technology in a study room"
        #         ]
        #         st.session_state.current_prompt = st.selectbox(
        #             "Select an example",
        #             examples
        #         )
        
        with col2:
            if st.button("🔄 Reset", use_container_width=True):
                st.session_state.current_prompt = ""
                st.rerun()
    
    # Historial de imágenes (si hay)
    if len(st.session_state.generated_images) > 1:
        st.divider()
        st.subheader("📚 Generation History")
        
        cols = st.columns(min(3, len(st.session_state.generated_images)))
        
        for idx, img_data in enumerate(reversed(st.session_state.generated_images[-6:])):  # Últimas 6 imágenes
            with cols[idx % 3]:
                with st.expander(f"Image {len(st.session_state.generated_images)-idx}", expanded=False):
                    st.image(img_data["image_bytes"], use_container_width=True)
                    st.caption(f"📅 {img_data['timestamp'].strftime('%H:%M')}")
                    st.caption(f"📏 {img_data['size']}")


# Función adicional para batch processing
def generate_multiple_images(bedrock_client, model_id_titan: str, prompts: list):
    """Genera múltiples imágenes en batch"""
    results = []
    for prompt in prompts:
        _, img_bytes = generate_image_from_text(bedrock_client, model_id_titan, prompt)
        results.append(img_bytes)
    return results