import boto3
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import sys
from config.settings import settings
from config.constants import TEA_SYSTEM_PROMPT
from services.dynamodb import ImageUsageRepository
from services.ip_utils import get_client_ip
from tools.generate_image import GenerateImageTool
from core.memory import RAMConversationMemory, SessionMemoryManager

logger = logging.getLogger(__name__)


class TEAOptimizedAgent:
    """
    Agente conversacional con memoria RAM pura.
    NO usa langchain.memory (deprecated).
    """
    
    def __init__(self):
        """Inicializa el agente con memoria RAM y clientes AWS"""
        
        # Cliente Bedrock para texto
        self.bedrock_client = boto3.client(
            'bedrock-runtime',
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key
        )
        
        # Modelos
        self.model_id = settings.bedrock_text_model_id
        self.image_model_id = settings.bedrock_image_model_id
        self.max_images_per_day = settings.max_images_per_day
        
        # MEMORIA EN RAM - SIN LANGCHAIN
        self.memory_manager = SessionMemoryManager(
            max_sessions=100,
            messages_per_session=20
        )
        
        # Repositorio DynamoDB para límite de imágenes
        self.image_repo = ImageUsageRepository()
        
        logger.info(f"TEAOptimizedAgent initialized with model: {self.model_id}")
    
    def _get_session_memory(self, session_id: str) -> RAMConversationMemory:
        """Obtiene memoria para una sesión específica"""
        return self.memory_manager.get_or_create_memory(session_id)
    
    def process_message(self, session_id: str, message: str) -> Dict[str, Any]:
        """
        Procesa mensaje de usuario.
        
        Args:
            session_id: Identificador único de sesión (IP del usuario)
            message: Mensaje del usuario
        
        Returns:
            Dict con respuesta y metadatos
        """
        try:
            # 1. Obtener memoria de la sesión
            memory = self._get_session_memory(session_id)
            
            # 2. Guardar mensaje del usuario
            memory.add_user_message(message)
            
            # 3. Detectar intención y ejecutar herramientas
            tool_result = self._detect_and_execute_tool(message, session_id, memory)
            
            # 4. Si es imagen, retornar directamente
            if tool_result and tool_result.get("tool") == "generate_image":
                response_data = tool_result["result"]
                
                # Guardar respuesta en memoria
                if response_data.get("success"):
                    memory.add_ai_message(f"Imagen generada: {response_data.get('message', '')}")
                else:
                    memory.add_ai_message(f"Error: {response_data.get('message', 'No se pudo generar la imagen')}")
                
                return {
                    "response": json.dumps(response_data),
                    "tool_used": "generate_image",
                    "memory_stats": memory.get_conversation_summary()
                }
            
            # 5. Generar respuesta con LLM
            response = self._generate_response(message, memory)
            
            # 6. Guardar respuesta en memoria
            memory.add_ai_message(response)
            
            # 7. Si hay tool result de expansión, agregarlo
            if tool_result and tool_result.get("tool") == "expand_explanation":
                response += f"\n\n{tool_result['result']}"
            
            return {
                "response": response,
                "tool_used": tool_result.get("tool") if tool_result else None,
                "memory_stats": memory.get_conversation_summary()
            }
            
        except Exception as e:
            logger.error(f"Error processing message for session {session_id}: {e}", exc_info=True)
            return {
                "response": "Lo siento, ocurrió un error. Por favor intenta de nuevo.",
                "error": str(e),
                "tool_used": None
            }
    
    def _generate_response(self, message: str, memory: RAMConversationMemory) -> str:
        """Genera respuesta usando Bedrock Claude"""
        try:
            # Obtener contexto de la conversación
            context = memory.get_context_string(n=5)
            
            # Construir prompt completo
            prompt = f"""{TEA_SYSTEM_PROMPT}

            CONVERSACIÓN PREVIA:
            {context}

            USUARIO: {message}

            ASISTENTE (respuesta literal, clara, sin metáforas):"""
                        
            # Payload para Claude 3.5 Sonnet
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1024,
                "temperature": 0.1,
                "top_p": 0.9,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }
            
            
            logger.debug(f"Invoking Bedrock model: {self.model_id}")
            
            response = self.bedrock_client.invoke_model(
                modelId=self.model_id,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(body)
            )
            
            response_body = json.loads(response['body'].read())
            generated_text = response_body['content'][0]['text']
                
            # Post-procesamiento TEA
            generated_text = self._apply_tea_formatting(generated_text)
            
            return generated_text
            
        except Exception as e:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno
            logger.error(f"Bedrock generation failed: {e}")
            return f"Lo siento, no pude generar una respuesta en este momento, Error:  {str(e)}; line_number: {line_number }, {self.model_id}, {self.bedrock_client}"
    
    
    def _generate_response_deepseek(self, message: str, memory: RAMConversationMemory) -> str:
        """Genera respuesta usando Bedrock Claude"""
        try:
            # Obtener contexto de la conversación
            context = memory.get_context_string(n=5)
            
            # Construir prompt completo
            prompt = f"""{TEA_SYSTEM_PROMPT}

            CONVERSACIÓN PREVIA:
            {context}

            USUARIO: {message}

            ASISTENTE (respuesta literal, clara, sin metáforas):"""
            
            body = json.dumps({
            "prompt": prompt,
            "max_tokens": 512,
            "temperature": 0.5,
            "top_p": 0.9,
            
            })
            
            logger.debug(f"Invoking Bedrock model: {self.model_id}")
            
            response = self.bedrock_client.invoke_model(modelId=self.model_id, body=body)
            
            response_body = json.loads(response['body'].read())
            
            choices = response_body["choices"]
            response_text = ""
            if len(choices) > 0:
                response_text = choices[0]['text'].strip().replace("</think>", "")
                
            # Post-procesamiento TEA
            generated_text = self._apply_tea_formatting(response_text)
            
            return generated_text
            
        except Exception as e:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno
            logger.error(f"Bedrock generation failed: {e}")
            return f"Lo siento, no pude generar una respuesta en este momento, Error:  {str(e)}; line_number: {line_number }, {self.model_id}, {self.bedrock_client}"
    
    def _detect_and_execute_tool(self, message: str, session_id: str, memory: RAMConversationMemory) -> Optional[Dict[str, Any]]:
        """Detecta intención y ejecuta herramientas"""
        message_lower = message.lower()
        
        # === DETECCIÓN DE IMAGEN ===
        image_keywords = [
            'genera', 'dibuja', 'crea una imagen', 'imagen de', 'imagen sobre',
            'generate', 'draw', 'create an image', 'picture of', 'imagen',
            'dibujar', 'crear imagen', 'haz una imagen', 'quiero una imagen'
        ]
        
        if any(keyword in message_lower for keyword in image_keywords):
            # Extraer prompt
            prompt = message
            for kw in image_keywords:
                prompt = prompt.replace(kw, "").replace(kw.capitalize(), "")
            
            # Limpiar prompt
            prompt = prompt.strip().strip('.,:;!¿?')
            
            if not prompt or len(prompt) < 3:
                prompt = "universidad moderna con estudiantes y tecnología"
            
            logger.info(f"Image generation requested. Prompt: {prompt[:50]}...")
            
            # Ejecutar tool
            result = self._execute_image_tool(prompt, session_id)
            return {"tool": "generate_image", "result": result}
        
        # === DETECCIÓN DE EXPANSIÓN ===
        expand_keywords = [
            'más detalles', 'explica paso a paso', 'expandir', 'más información',
            'more details', 'step by step', 'explain more', 'detalles',
            'explicación detallada', 'ampliar', 'desarrolla'
        ]
        
        if any(keyword in message_lower for keyword in expand_keywords):
            logger.info("Expansion explanation requested")
            expansion = self._generate_expansion(message, memory)
            return {"tool": "expand_explanation", "result": expansion}
        
        return None
    
    def _execute_image_tool(self, prompt: str, session_id: str) -> Dict[str, Any]:
        """Ejecuta generación de imagen con control de límite"""
        try:
            tool = GenerateImageTool(
                bedrock_client=self.bedrock_client,
                image_model_id=self.image_model_id,
                image_repo=self.image_repo,
                max_images_per_day=self.max_images_per_day
            )
            
            result = tool._run(prompt, session_id)
            
            if isinstance(result, str):
                try:
                    return json.loads(result)
                except:
                    return {
                        "success": False,
                        "message": result,
                        "error": "Invalid response format"
                    }
            return result
            
        except Exception as e:
            logger.error(f"Image tool error: {e}")
            return {
                "success": False,
                "message": f"Error al generar imagen: {str(e)}",
                "error": str(e)
            }
    
    def _generate_expansion(self, message: str, memory: RAMConversationMemory) -> str:
        """Genera explicación paso a paso"""
        try:
            # Obtener contexto reciente
            context = memory.get_context_string(n=3)
            
            prompt = f"""Basado en esta conversación:
{context}

El usuario pide más detalles.

Genera una explicación PASO A PASO con:
1. Formato numérico (1., 2., 3.)
2. Máximo 6 pasos
3. Lenguaje claro y literal
4. Cada paso una acción o concepto específico

EXPLICACIÓN PASO A PASO:"""
            
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 800,
                "temperature": 0.1,
                "messages": [{"role": "user", "content": prompt}]
            }
            
            response = self.bedrock_client.invoke_model(
                modelId=self.model_id,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(body)
            )
            
            response_body = json.loads(response['body'].read())
            expansion = response_body['content'][0]['text']
            
            return expansion
            
        except Exception as e:
            logger.error(f"Expansion generation error: {e}")
            return "No pude generar una explicación paso a paso. Por favor intenta de nuevo."
    
    def _apply_tea_formatting(self, text: str) -> str:
        """Aplica formato amigable para TEA"""
        if not text:
            return text
        
        # 1. Eliminar signos de exclamación/inversión
        text = text.replace('¡', '').replace('¿', '')
        
        # 2. Limitar emojis
        import re
        emoji_pattern = re.compile("["
            u"\U0001F600-\U0001F64F"  # emoticones
            u"\U0001F300-\U0001F5FF"  # símbolos
            u"\U0001F680-\U0001F6FF"  # transporte
            u"\U0001F1E0-\U0001F1FF"  # banderas
            "]+", flags=re.UNICODE)
        text = emoji_pattern.sub('', text)
        
        # 3. Asegurar oraciones cortas
        sentences = text.split('. ')
        formatted = []
        
        for sentence in sentences:
            words = sentence.split()
            if len(words) > 20:
                # Dividir cada 15 palabras
                chunks = []
                for i in range(0, len(words), 15):
                    chunks.append(' '.join(words[i:i+15]))
                formatted.append('. '.join(chunks))
            else:
                formatted.append(sentence)
        
        text = '. '.join(formatted)
        
        # 4. Asegurar punto final
        if text and not text.endswith(('.', '!', '?')):
            text += '.'
        
        return text
    
    def clear_session(self, session_id: str) -> bool:
        """Limpia la memoria de una sesión"""
        return self.memory_manager.delete_memory(session_id)
    
    def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """Obtiene estadísticas de una sesión"""
        memory = self.memory_manager.get_memory(session_id)
        if memory:
            return memory.get_conversation_summary()
        return {"total_messages": 0, "session_id": session_id}
    
    def get_global_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas globales del agente"""
        return self.memory_manager.get_stats()