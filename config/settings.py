from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
import streamlit as st

class Settings(BaseSettings):
    """Configuración centralizada usando Pydantic y Streamlit secrets"""
    
    # AWS
    aws_access_key_id: str = Field(default="")
    aws_secret_access_key: str = Field(default="")
    aws_region: str = Field(default="us-east-1")
    
    # Bedrock Models
    bedrock_text_model_id: str = Field(default="us.anthropic.claude-3-5-haiku-20241022-v1:0")
    bedrock_image_model_id: str = Field(default="amazon.titan-image-generator-v2:0")
    
    # DynamoDB
    dynamodb_image_usage_table: str = Field(default="tbl_image_usage")
    
    # Limits
    max_images_per_day: int = Field(default=5)
    
    # TEA Configuration
    tea_default_verbosity: str = Field(default="brief")  # brief, detailed, step_by_step
    tea_avoid_metaphors: bool = Field(default=True)
    tea_use_literal_language: bool = Field(default=True)
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"
    
    @classmethod
    def from_streamlit_secrets(cls):
        """Carga configuración desde st.secrets"""
        settings = cls()
        
        try:
            # AWS
            settings.aws_access_key_id = st.secrets.get("AWS_ACCESS_KEY_ID", "")
            settings.aws_secret_access_key = st.secrets.get("AWS_SECRET_ACCESS_KEY", "")
            settings.aws_region = st.secrets.get("AWS_REGION", "us-east-1")
            
            # Bedrock
            settings.bedrock_text_model_id = st.secrets.get("AWS",{}).get("AWS_BEDROCK_AI_MODELO_CLAUDE", settings.bedrock_text_model_id)
            settings.bedrock_image_model_id = st.secrets.get("AWS",{}).get("AWS_BEDROCK_AI_MODELO_TITAN", settings.bedrock_image_model_id)
            
            # DynamoDB
            settings.dynamodb_image_usage_table = st.secrets.get("AWS",{}).get("AWS_DYNAMODB_IMAGE_USAGE_TABLE", settings.dynamodb_image_usage_table)
            
            # Limits
            settings.max_images_per_day = st.secrets.get("FEATURES", {}).get("MAX_IMAGENES_PER_DAY", settings.max_images_per_day)
            
            # TEA
            settings.tea_default_verbosity = st.secrets.get("TEA_DEFAULT_VERBOSITY", "brief")
            settings.tea_avoid_metaphors = st.secrets.get("TEA_AVOID_METAPHORS", "true").lower() == "true"
            settings.tea_use_literal_language = st.secrets.get("TEA_USE_LITERAL_LANGUAGE", "true").lower() == "true"
            
        except Exception as e:
            print(f"Error loading from streamlit secrets: {e}")
        
        return settings

# Instancia global de configuración
settings = Settings.from_streamlit_secrets()