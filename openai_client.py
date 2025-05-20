import os
import requests

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"

def generate_script(topic):
    prompt = (
        f"Write a concise, engaging YouTube video script for the topic: '{topic}'. "
        "The script should be informative, friendly, and suitable for a general audience. "
        "Length: about 60-90 seconds."
    )
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    body = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role": "system", "content": "You are a helpful video script writer."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 500,
        "temperature": 0.7
    }
    resp = requests.post(OPENAI_API_URL, headers=headers, json=body)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()
