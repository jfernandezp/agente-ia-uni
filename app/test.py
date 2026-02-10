import boto3
import json
import base64
from botocore.exceptions import ClientError
import re
import sys

bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")

def text_to_image():
    
    

    payload = {
        "taskType": "TEXT_IMAGE",
        "textToImageParams": {
            "text": "A car made out of vegetables."
        },
        "imageGenerationConfig": {
            "numberOfImages": 1,
            "height": 1024,
            "width": 1024,
            "cfgScale": 8,
            "seed": 12345,
            "quality": "standard"
        }
    }

    response = bedrock.invoke_model(
        modelId="amazon.titan-image-generator-v2:0",
        contentType="application/json",
        accept="application/json",
        body=json.dumps(payload),
    )

    data = json.loads(response["body"].read())

    # Titan devuelve base64 dentro de images[0] (string)
    img_b64 = data["images"][0]
    img_bytes = base64.b64decode(img_b64)

    with open("out.png", "wb") as f:
        f.write(img_bytes)

    print("OK -> out.png")


def get_bedrock_response_deepseek(user_input):
    
    try:
        # Create a Bedrock Runtime client in the AWS Region of your choice.
        #client = boto3.client("bedrock-runtime", region_name="us-east-1")
        # formatted_prompt = f"""
        # <｜begin▁of▁sentence｜><｜User｜>{user_input}<｜Assistant｜>
        # """
        
        # Modified system prompt in English only
        formatted_prompt = f"""Eres un asistente de IA de la Universidad San Ignacio de Loyola (USIL) y de San Ignacio University (SIU). Responde preguntas 
            generales de los estudiantes. En caso te pregunten por USIL responde con información de está web  https://usil.edu.pe/ y si preguntan por SIU responde
            unicamente con información de la web https://www.sanignaciouniversity.edu/
            Responda siempre en español o inglés.

            Query: {user_input}

            Response: """

        body = json.dumps({
            "prompt": formatted_prompt,
            "max_tokens": 512,
            "temperature": 0.5,
            "top_p": 0.9,
        })
        # Invoke the model with the request.
        response = bedrock.invoke_model(modelId="us.deepseek.r1-v1:0", body=body)

        # Read the response body.
        model_response = json.loads(response["body"].read())
        
        # Extract choices.
        choices = model_response["choices"]
        response = ""
        if len(choices) > 0:
            response = choices[0]['text'].replace("</think>", "")
        response_text = remove_thinking_tags(response)
        print(response_text)
        return response_text
        # # Print choices.
        # for index, choice in enumerate(choices):
        #     print(choice['text'])
        #     response = "".join(choice['text'])
        #     response = response.replace("</think>", "")
        #     print(response)
        
    except Exception as e:
        exc_type, exc_obj, tb = sys.exc_info()
        line_number = tb.tb_lineno
        return "I'm sorry, I can't answer at this time."

def remove_thinking_tags(response_content):
    """Removes the <think>...</think> block from the response string."""
    regex_pattern = r'<think>[\s\S]*?<\/think>\n*\n*'
    cleaned_content = re.sub(regex_pattern, '', response_content)
    return cleaned_content

if __name__ == '__main__':
    prompt = input()
    get_bedrock_response_deepseek(prompt)