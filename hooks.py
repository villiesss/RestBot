import os
from mistralai import Mistral

api_key = "0jlqaSYejPTC3toCHSkHBzId5wIpiquB"
model = "pixtral-12b-2409"

def send_to_ai(text):
    client = Mistral(api_key=api_key)
    chat_response = client.chat.complete(
        model = model,
        messages = [
            {
                "role": "user",
                "content": text,
            }
        ]
    )
    return chat_response.choices[0].message.content