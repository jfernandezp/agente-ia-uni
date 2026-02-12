from langchain.tools import BaseTool
from typing import Type, Optional
from pydantic import BaseModel, Field
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
import logging

logger = logging.getLogger(__name__)

class AskGeneralInput(BaseModel):
    """Input para preguntas generales"""
    question: str = Field(description="Pregunta del usuario sobre USIL/SIU")

class AskGeneralTool(BaseTool):
    """Tool para responder preguntas sobre USIL y SIU"""
    
    name: str = "ask_general"
    description: str = """
    Responde preguntas sobre la Universidad San Ignacio de Loyola (USIL) 
    y San Ignacio University (SIU). Carreras, admisión, costos, sedes.
    """
    args_schema: Type[BaseModel] = AskGeneralInput
    
    llm: Optional[any] = None
    memory: Optional[any] = None
    
    def __init__(self, llm=None, memory=None, **kwargs):
        super().__init__(**kwargs)
        self.llm = llm
        self.memory = memory
    
    def _run(self, question: str) -> str:
        """Genera respuesta factual, literal, sin metáforas"""
        try:
            prompt = PromptTemplate.from_template("""
            Eres un asistente especializado en comunicación clara y literal.
            
            PREGUNTA: {question}
            
            Responde con:
            1. Hechos concretos (números, fechas, nombres)
            2. Oraciones cortas (máx 15 palabras)
            3. Sin metáforas ni sarcasmo
            4. Si no sabes: "No tengo información sobre eso."
            
            RESPUESTA LITERAL:
            """)
            
            if self.llm:
                chain = prompt | self.llm | StrOutputParser()
                response = chain.invoke({"question": question})
            else:
                response = "No tengo información sobre eso en este momento."
            
            # Post-procesamiento TEA
            response = response.replace("¡", "").replace("¿", "")
            response = response.replace(" fascinante ", " ")
            response = response.replace(" increíble ", " ")
            
            # Añadir opción de expandir
            response += "\n\n¿Quieres que explique esto paso a paso?"
            
            return response
            
        except Exception as e:
            logger.error(f"Error in ask_general: {e}")
            return "Lo siento, no pude procesar tu pregunta. Por favor intenta de nuevo."
    
    async def _arun(self, question: str) -> str:
        """Versión async"""
        return self._run(question)