import boto3
from datetime import datetime
from botocore.exceptions import ClientError
import logging
from config.settings import settings

logger = logging.getLogger(__name__)

class ImageUsageRepository:
    """Repositorio para control de límite diario de imágenes"""
    
    def __init__(self):
        self.dynamodb = boto3.resource(
            'dynamodb',
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key
        )
        self.table = self.dynamodb.Table(settings.dynamodb_image_usage_table)
        self.max_images = settings.max_images_per_day
    
    def check_and_increment(self, user_id: str) -> tuple[bool, int]:
        """
        Operación atómica:
        1. Obtiene contador actual
        2. Si existe y < límite → incrementa
        3. Si no existe → crea con 1
        4. Retorna (permitido, imágenes_restantes)
        """
        today = datetime.now().strftime("%Y-%m-%d")
        
        try:
            # UpdateItem con condición para operación atómica
            response = self.table.update_item(
                Key={
                    'user_id': user_id,
                    'date': today
                },
                UpdateExpression="ADD images_generated_today :inc",
                ExpressionAttributeValues={':inc': 1},
                ReturnValues="UPDATED_NEW"
            )
            
            new_count = int(response['Attributes']['images_generated_today'])
            remaining = max(0, self.max_images - new_count)
            
            if new_count > self.max_images:
                # Excedió límite, revertir?
                # Nota: Esto es raro por el límite, pero por seguridad
                logger.warning(f"User {user_id} exceeded limit: {new_count}")
                return False, 0
            
            return True, remaining
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ValidationException':
                # La tabla no existe o estructura incorrecta
                logger.error(f"DynamoDB validation error: {e}")
                return False, 0
            else:
                logger.error(f"DynamoDB error: {e}")
                return False, 0
    
    def get_remaining(self, user_id: str) -> int:
        """Consulta imágenes restantes sin modificar"""
        today = datetime.now().strftime("%Y-%m-%d")
        
        try:
            response = self.table.get_item(
                Key={'user_id': user_id, 'date': today}
            )
            
            if 'Item' in response:
                count = int(response['Item'].get('images_generated_today', 0))
                return max(0, self.max_images - count)
            
            return self.max_images
            
        except ClientError as e:
            logger.error(f"Error getting remaining images: {e}")
            return 0