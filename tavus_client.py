import requests
import os

TAVUS_API_URL = "https://api.tavus.io/v1/videos"
TAVUS_API_KEY = os.environ.get("TAVUS_API_KEY")

def create_tavus_video(script, title, description):
    payload = {
        "script": script,
        "title": title,
        "description": description
    }
    headers = {
        "Authorization": f"Bearer {TAVUS_API_KEY}",
        "Content-Type": "application/json"
    }
    response = requests.post(TAVUS_API_URL, json=payload, headers=headers)
    if response.status_code == 201:
        return response.json()
    else:
        print("Tavus API error:", response.text)
        return None
