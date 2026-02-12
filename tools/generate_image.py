from langchain.tools import BaseTool
from typing import Type, Optional, Dict, Any
from pydantic import BaseModel, Field
import json
import base64
from datetime import datetime
import logging
import sys
from config.settings import settings

logger = logging.getLogger(__name__)

class GenerateImageInput(BaseModel):
    """Input para generación de imágenes"""
    prompt: str = Field(description="Descripción detallada de la imagen")
    style: Optional[str] = Field(default="digital art", description="Estilo artístico")

class GenerateImageTool(BaseTool):
    """Tool para generar imágenes con límite diario"""
    
    name: str = "generate_image"
    description: str = "Genera una imagen a partir de texto"
    args_schema: Type[BaseModel] = GenerateImageInput
    
    bedrock_client: Optional[Any] = None
    image_model_id: str =  settings.bedrock_image_model_id
    image_repo: Optional[Any] = None
    max_images_per_day: int = settings.max_images_per_day
    
    def __init__(self, bedrock_client=None, image_model_id=None, image_repo=None, max_images_per_day=5, **kwargs):
        super().__init__(**kwargs)
        self.bedrock_client = bedrock_client
        self.image_model_id = image_model_id or self.image_model_id
        self.image_repo = image_repo
        self.max_images_per_day = max_images_per_day
       
    def _run(self, prompt: str, session_id: str = "unknown", style: str = "digital art") -> str:
        """
        Ejecuta generación con control de límite
        """
        try:
            # Verificar límite
            if self.image_repo:
                allowed, remaining = self.image_repo.check_and_increment(session_id)
            else:
                allowed = True
                remaining = self.max_images_per_day - 1
            
            if not allowed:
                return json.dumps({
                    "success": False,
                    "message": f"You cannot generate more images today. Limit: {self.max_images_per_day}",
                    "remaining": 0
                })
            
            # Mejorar prompt
            enhanced_prompt = f"{prompt}, digital art, high quality, detailed, 4k resolution, professional composition"

            # Payload para Titan
            payload = {
                "taskType": "TEXT_IMAGE",
                "textToImageParams": {"text": enhanced_prompt},
                "imageGenerationConfig": {
                    "numberOfImages": 1,
                    "height": 512,
                    "width": 512,
                    "cfgScale": 8.0,
                    "seed": int(datetime.now().timestamp() % 10000),
                    "quality": "standard" #standard premium
                }
            }
            
            # Modo desarrollo sin Bedrock
            if not self.bedrock_client:
                import random
                import string
                dummy = ''.join(random.choices(string.ascii_letters, k=100))
                img_b64 = base64.b64encode(dummy.encode()).decode('utf-8')
                img_bytes = base64.b64decode(img_b64)
                return json.dumps({
                    "success": True,
                    "image_data": img_bytes,
                    "enhanced_prompt": enhanced_prompt,
                    "remaining": remaining,
                    "message": f"✅ Modo desarrollo. Te quedan {remaining} imágenes"
                })
            
            # Invocar Bedrock
            response = self.bedrock_client.invoke_model(
                modelId=self.image_model_id,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(payload)
            )
            
            data = json.loads(response["body"].read())
            img_b64 = data["images"][0]
            return json.dumps({
                "success": True,
                "image_data": img_b64,
                "enhanced_prompt": enhanced_prompt,
                "remaining": remaining,
                "message": f"Image generated ✅" # - Te quedan {remaining} imágenes hoy - {self.max_images_per_day}"
            })
            
        except Exception as e:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno
            logger.error(f"Error generating image: {e}, line_number: {line_number }")
            return json.dumps({
                "success": False,
                "message": f"Error: {str(e)}",
                "error": str(e)
            })