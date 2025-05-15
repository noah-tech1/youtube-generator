from flask import Flask, redirect, request, session, url_for
import os
import requests

app = Flask(__name__)
app.secret_key = os.urandom(24)

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
OAUTH_REDIRECT_URI = os.getenv("OAUTH_REDIRECT_URI")

@app.route("/")
def index():
    return "YouTube Generator App is running!"

@app.route("/login")
def login():
    google_auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        "?response_type=code"
        f"&client_id={GOOGLE_CLIENT_ID}"
        f"&redirect_uri={OAUTH_REDIRECT_URI}"
        "&scope=https://www.googleapis.com/auth/youtube.upload"
        "&access_type=offline"
        "&prompt=consent"
    )
    return redirect(google_auth_url)

@app.route("/oauth/callback")
def callback():
    code = request.args.get("code")
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": OAUTH_REDIRECT_URI,
        "grant_type": "authorization_code",
    }
    response = requests.post(token_url, data=data)
    return response.json()

if __name__ == "__main__":
    app.run(debug=True)
