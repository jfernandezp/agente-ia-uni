import streamlit as st
import logging
import sys
import os

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

# Configuración de página (DEBE SER EL PRIMER COMANDO DE STREAMLIT)
st.set_page_config(
    page_title="Ignatius Assistant",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.sidebar.image("images\image.png", width=220)
 
from core.orchestrator import ConversationOrchestrator
from ui.chat_interface import render_tea_chat_interface

logger = logging.getLogger(__name__)

def main():
    """Punto de entrada único"""
    
    try:
        # Instanciar orquestador (singleton en session_state)
        if "orchestrator" not in st.session_state:
            with st.spinner("Inicializando asistente..."):
                st.session_state.orchestrator = ConversationOrchestrator()
                logger.info("Orchestrator initialized successfully")
        
        # Renderizar interfaz TEA
        render_tea_chat_interface(st.session_state.orchestrator)
        
    except Exception as e:
        st.error(f"Error inicializando la aplicación: {str(e)}")
        logger.error(f"Fatal error in main: {e}", exc_info=True)
        
        # Mostrar información de depuración en desarrollo
        st.exception(e)

    st.sidebar.markdown("---")
    st.sidebar.caption("© 2026 USIL | SIU")
    
if __name__ == "__main__":
    main()