from typing import Dict, Any, Optional
import logging
from datetime import datetime

from core.agent import TEAOptimizedAgent
from services.ip_utils import get_client_ip

logger = logging.getLogger(__name__)

class ConversationOrchestrator:
    """
    Orquestador único.
    Gestiona agente y sesiones en RAM.
    NO persiste conversaciones.
    """
    
    def __init__(self):
        self.agent = TEAOptimizedAgent()
        logger.info("ConversationOrchestrator initialized")
    
    def handle_message(self, message: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Procesa mensaje sin persistencia.
        
        Args:
            message: Mensaje del usuario
            session_id: ID de sesión (IP del usuario)
        
        Returns:
            Respuesta del agente
        """
        if not session_id:
            session_id = get_client_ip() or f"session_{datetime.now().timestamp()}"
        
        try:
            response = self.agent.process_message(session_id, message)
            return response
            
        except Exception as e:
            logger.error(f"Orchestrator error: {e}", exc_info=True)
            return {
                "response": "Lo siento, ocurrió un error interno.",
                "error": str(e)
            }
    
    def clear_session(self, session_id: str) -> bool:
        """Limpia una sesión específica"""
        return self.agent.clear_session(session_id)
    
    def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """Estadísticas de sesión"""
        return self.agent.get_session_stats(session_id)
    
    
    def reset_session(self, session_id: str) -> bool:
        """
        Resetea una sesión específica.
        Limpia la memoria de la conversación y los metadatos.
        
        Args:
            session_id: ID de la sesión a resetear
        
        Returns:
            bool: True si se reseteó correctamente
        """
        try:
            # 1. Limpiar metadata de la sesión
            if session_id in self.session_metadata:
                del self.session_metadata[session_id]
                logger.info(f"Session metadata cleared for {session_id}")
            
            # 2. Limpiar memoria del agente
            if hasattr(self, 'agent'):
                # Si el agente tiene memory_manager (tu implementación actual)
                if hasattr(self.agent, 'memory_manager'):
                    self.agent.memory_manager.delete_memory(session_id)
                    logger.info(f"Agent memory cleared for {session_id}")
                
                # Si el agente tiene método clear_session
                elif hasattr(self.agent, 'clear_session'):
                    self.agent.clear_session(session_id)
                
                # Si el agente tiene método reset_conversation
                elif hasattr(self.agent, 'reset_conversation'):
                    self.agent.reset_conversation(session_id)
            
            return True
            
        except Exception as e:
            logger.error(f"Error resetting session {session_id}: {e}")
            return False