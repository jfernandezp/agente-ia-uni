import boto3
import json
import base64
from botocore.exceptions import ClientError
import re

def text_to_image():
    
    bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")

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


def text():
    try:
        # Create a Bedrock Runtime client in the AWS Region of your choice.
        client = boto3.client("bedrock-runtime", region_name="us-east-1")

        # Set the cross Region inference profile ID for DeepSeek-R1
        model_id = "us.deepseek.r1-v1:0"

        # Define the prompt for the model.
        #prompt = "Describe the purpose of a 'hello world' program in one line."
        print("Input")
        prompt = input()
        # Embed the prompt in DeepSeek-R1's instruction format.
        formatted_prompt = f"""
        <｜begin▁of▁sentence｜><｜User｜>{prompt}<｜Assistant｜>
        """

        body = json.dumps({
            "prompt": formatted_prompt,
            "max_tokens": 512,
            "temperature": 0.5,
            "top_p": 0.9,
        })
        # Invoke the model with the request.
        response = client.invoke_model(modelId=model_id, body=body)

        # Read the response body.
        model_response = json.loads(response["body"].read())
        
        # Extract choices.
        choices = model_response["choices"]
        response = ""
        if len(choices) > 0:
            response = choices[0]['text'].replace("</think>", "")
        clean_response = remove_thinking_tags(response)
        print(clean_response)
        # # Print choices.
        # for index, choice in enumerate(choices):
        #     print(choice['text'])
        #     response = "".join(choice['text'])
        #     response = response.replace("</think>", "")
        #     print(response)
    except (ClientError, Exception) as e:
        print(f"ERROR: Can't invoke '{model_id}'. Reason: {e}")
        exit(1)

def remove_thinking_tags(response_content):
    """Removes the <think>...</think> block from the response string."""
    regex_pattern = r'<think>[\s\S]*?<\/think>\n*\n*'
    cleaned_content = re.sub(regex_pattern, '', response_content)
    return cleaned_content

if __name__ == '__main__':
    text()