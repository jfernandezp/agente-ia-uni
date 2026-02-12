from langchain.tools import BaseTool
from typing import Type, Optional
from pydantic import BaseModel, Field
from langchain_core.prompts import PromptTemplate
import logging

logger = logging.getLogger(__name__)

class ExpandExplanationInput(BaseModel):
    """Input para expandir explicaciones"""
    topic: str = Field(description="Tema específico a expandir paso a paso")

class ExpandExplanationTool(BaseTool):
    """Tool para expandir explicaciones paso a paso"""
    
    name: str = "expand_explanation"
    description: str = """
    Expande una explicación previa con detalles paso a paso.
    Úsala cuando el usuario diga: 'más detalles', 'explica paso a paso', 'expandir'.
    """
    args_schema: Type[BaseModel] = ExpandExplanationInput
    
    llm: Optional[any] = None
    memory: Optional[any] = None
    
    def __init__(self, llm=None, memory=None, **kwargs):
        super().__init__(**kwargs)
        self.llm = llm
        self.memory = memory
    
    def _run(self, topic: str) -> str:
        """Genera explicación estructurada paso a paso"""
        try:
            # Recuperar último mensaje del historial
            context = "No hay contexto previo"
            if self.memory:
                history = self.memory.load_memory_variables({})
                last_exchange = history.get("chat_history", [])
                if last_exchange and len(last_exchange) > 0:
                    context = str(last_exchange[-2:]) if len(last_exchange) >= 2 else str(last_exchange)
            
            prompt = PromptTemplate.from_template("""
            Crea una explicación PASO A PASO sobre: {topic}
            
            Contexto conversacional: {context}
            
            FORMATO OBLIGATORIO:
            1. [Primer paso concreto]
            2. [Segundo paso concreto]  
            3. [Tercer paso concreto]
            ...
            
            Cada paso debe ser UNA acción específica.
            No uses viñetas, solo números.
            Máximo 6 pasos.
            Usa lenguaje literal y claro.
            
            EXPLICACIÓN PASO A PASO:
            """)
            
            if self.llm:
                chain = prompt | self.llm
                response = chain.invoke({
                    "topic": topic,
                    "context": context
                })
                return response.content if hasattr(response, 'content') else str(response)
            else:
                return f"Paso a paso para {topic}:\n1. Primero...\n2. Luego...\n3. Finalmente..."
            
        except Exception as e:
            logger.error(f"Error in expand_explanation: {e}")
            return f"No pude generar una explicación paso a paso para '{topic}'. Por favor intenta de nuevo."
    
    async def _arun(self, topic: str) -> str:
        """Versión async"""
        return self._run(topic)