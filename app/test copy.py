import streamlit as st
import boto3
import json
import sys
import requests
from bs4 import BeautifulSoup
import re

def scrape_usil_website(url):
    """
    Extrae contenido relevante de páginas web de USIL.
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remover scripts, estilos, elementos no deseados
        for script in soup(["script", "style", "nav", "footer", "header", "aside"]):
            script.decompose()
        
        # Extraer texto de elementos relevantes
        text_elements = []
        
        # Títulos principales
        for tag in soup.find_all(['h1', 'h2', 'h3']):
            text_elements.append(f"# {tag.get_text().strip()}")
        
        # Párrafos y listas
        for tag in soup.find_all(['p', 'li']):
            text = tag.get_text().strip()
            if text and len(text) > 10:  # Filtrar textos muy cortos
                text_elements.append(text)
        
        # Tablas (si las hay)
        for table in soup.find_all('table'):
            text_elements.append(table.get_text().strip())
        
        # Limpiar y unir el contenido
        content = '\n'.join(text_elements)
        
        # Limpieza adicional
        content = re.sub(r'\s+', ' ', content)  # Eliminar espacios múltiples
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)  # Eliminar líneas vacías múltiples
        
        return content[:4000]  # Limitar a 4000 caracteres para no exceder tokens
        
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return ""

def get_career_info(career_name):
    """
    Obtiene información específica de carreras de USIL.
    """
    career_urls = {
        "medicina humana": "https://usil.edu.pe/pregrado/medicina-humana/",
        "administración": "https://usil.edu.pe/pregrado/administracion/",
        "arquitectura": "https://usil.edu.pe/pregrado/arquitectura/",
        "derecho": "https://usil.edu.pe/pregrado/derecho/",
        "ingeniería": "https://usil.edu.pe/pregrado/ingenieria-civil/",
        "psicología": "https://usil.edu.pe/pregrado/psicologia/",
        "contabilidad": "https://usil.edu.pe/pregrado/contabilidad/",
        "marketing": "https://usil.edu.pe/pregrado/marketing/",
        "finanzas": "https://usil.edu.pe/pregrado/finanzas/",
        "economía": "https://usil.edu.pe/pregrado/economia/",
        # Agrega más carreras según sea necesario
    }
    
    career_lower = career_name.lower()
    for key, url in career_urls.items():
        if key in career_lower:
            return scrape_usil_website(url)
    
    return ""

def get_bedrock_response_deepseek(user_input):
    """
    Obtiene respuesta de DeepSeek con información actualizada de las webs.
    """
    try:
        bedrock_client = boto3.client("bedrock-runtime", region_name="us-east-1")
        AWS_BEDROCK_AI_MODELO_DEEPSEEK = "us.deepseek.r1-v1:0"
        
        # Detectar si es una pregunta sobre carreras
        scraped_content = ""
        
        # Lista de palabras clave para carreras
        career_keywords = [
            "medicina humana", "medicina", "administración", "arquitectura",
            "derecho", "ingeniería", "psicología", "contabilidad", "marketing",
            "finanzas", "economía", "carrera", "pregrado", "estudiar"
        ]
        
        user_input_lower = user_input.lower()
        
        # Si menciona una carrera específica, scrapear esa página
        for keyword in career_keywords:
            if keyword in user_input_lower:
                scraped_content = get_career_info(keyword)
                break
        
        # Si no se encontró contenido específico, scrapear página principal
        if not scraped_content and ("usil" in user_input_lower or "universidad" in user_input_lower):
            scraped_content = scrape_usil_website("https://usil.edu.pe/pregrado/")
        
        # Preparar el contexto con la información scrapeda
        context = ""
        if scraped_content:
            context = f"""
INFORMACIÓN ACTUALIZADA DE LA WEB DE USIL:
{scraped_content[:3000]}  # Limitar a 3000 caracteres

Usa esta información actualizada para responder. Si la pregunta es específica sobre una carrera y no encuentras la información en el contenido anterior, puedes decir que no tienes esa información específica pero ofrecer ayudar con otros temas.
"""
        
        # Crear el prompt con el contexto scrapedo
        formatted_prompt = f"""Eres LucIA, el Asistente Virtual de USIL y SIU.

CONTEXTO ACTUALIZADO:
{context}

PREGUNTA DEL USUARIO:
{user_input}

INSTRUCCIONES:
1. Usa la información del contexto para responder de manera precisa
2. Si no hay información relevante en el contexto, di: "No tengo esa información específica en mi base de datos actual, pero puedo ayudarte con otros temas sobre USIL"
3. Responde en español de manera clara y estructurada
4. Usa formato Markdown para organizar la información:
   - **Negritas** para títulos importantes
   - Listas con guiones (-) para enumerar
   - Saltos de línea para separar secciones

RESPUESTA DE LucIA:
"""
        
        body = json.dumps({
            "prompt": formatted_prompt,
            "max_tokens": 1024,  # Aumentar tokens para respuestas más completas
            "temperature": 0.3,
            "top_p": 0.8,
        })
        
        # Invocar el modelo
        response = bedrock_client.invoke_model(
            modelId=AWS_BEDROCK_AI_MODELO_DEEPSEEK, 
            body=body
        )
        
        model_response = json.loads(response["body"].read())
        choices = model_response["choices"]
        
        if len(choices) > 0:
            response_text = choices[0]['text'].strip()
            
            # Limpieza de la respuesta
            unwanted_patterns = [
                "Respuesta de LucIA:",
                "LucIA:",
                "Asistente:",
                "# ",
            ]
            
            for pattern in unwanted_patterns:
                if response_text.startswith(pattern):
                    response_text = response_text[len(pattern):].strip()
            
            return response_text
        
        return "No recibí una respuesta del modelo."
        
    except Exception as e:
        exc_type, exc_obj, tb = sys.exc_info()
        line_number = tb.tb_lineno
        st.error(f"ERROR: {str(e)}")
        return "Lo siento, no puedo responder en este momento."

# Versión mejorada con caché para no hacer scraping repetido
import hashlib

class USILKnowledgeBase:
    """Clase para gestionar el conocimiento de USIL con caché."""
    
    def __init__(self):
        self.cache = {}
        self.base_urls = {
            "home": "https://usil.edu.pe/",
            "pregrado": "https://usil.edu.pe/pregrado/",
            "admision": "https://descubre.usil.edu.pe/landings/pregrado/admision/",
            "siu": "https://www.sanignaciouniversity.edu/",
            "medicina": "https://usil.edu.pe/pregrado/medicina-humana/",
            "administracion": "https://usil.edu.pe/pregrado/administracion/",
            "contacto": "https://usil.edu.pe/contacto/",
        }
    
    def get_content(self, url_key, force_refresh=False):
        """Obtiene contenido con caché."""
        if url_key not in self.base_urls:
            return ""
        
        url = self.base_urls[url_key]
        cache_key = hashlib.md5(url.encode()).hexdigest()
        
        if not force_refresh and cache_key in self.cache:
            return self.cache[cache_key]
        
        content = scrape_usil_website(url)
        self.cache[cache_key] = content
        return content
    
    def get_relevant_content(self, user_input):
        """Obtiene contenido relevante basado en la consulta."""
        user_input_lower = user_input.lower()
        relevant_content = []
        
        # Mapear palabras clave a URLs
        keyword_mapping = {
            "pregrado": ["carrera", "estudiar", "pregrado", "licenciatura", "bachiller"],
            "medicina": ["medicina", "médico", "hospital", "salud"],
            "admision": ["admision", "ingreso", "postular", "requisitos", "examen"],
            "contacto": ["contacto", "dirección", "teléfono", "email", "ubicación"],
            "administracion": ["administración", "negocios", "gerencia", "empresa"],
        }
        
        for url_key, keywords in keyword_mapping.items():
            if any(keyword in user_input_lower for keyword in keywords):
                content = self.get_content(url_key)
                if content:
                    relevant_content.append(f"=== Información de {url_key.upper()} ===\n{content}")
        
        # Si no se encontró contenido específico, usar página principal
        if not relevant_content and "usil" in user_input_lower:
            relevant_content.append(f"=== Información general de USIL ===\n{self.get_content('home')}")
        
        return "\n\n".join(relevant_content[:2])  # Máximo 2 fuentes

# Uso en Streamlit
def main():
    st.title("🤖 LucIA - Asistente USIL")
    
    # Inicializar base de conocimiento
    if "knowledge_base" not in st.session_state:
        st.session_state.knowledge_base = USILKnowledgeBase()
    
    # Input del usuario
    user_input = st.chat_input("¿Qué te gustaría saber sobre USIL?")
    
    if user_input:
        # Obtener contenido relevante
        with st.spinner("Buscando información actualizada..."):
            context = st.session_state.knowledge_base.get_relevant_content(user_input)
        
        # Mostrar respuesta
        with st.chat_message("user"):
            st.write(user_input)
        
        with st.chat_message("assistant"):
            with st.spinner("LucIA está pensando..."):
                response = get_bedrock_response_deepseek(user_input)
                st.markdown(response)
        
        # Opcional: Mostrar fuentes usadas
        with st.expander("🔍 Fuentes consultadas"):
            st.text(context[:1000] + "..." if len(context) > 1000 else context)

if __name__ == "__main__":
    # Instalar dependencias necesarias
    # pip install requests beautifulsoup4
    main()