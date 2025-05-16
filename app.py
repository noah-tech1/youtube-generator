import os
from flask import Flask, redirect, url_for, session, render_template, request
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

app = Flask(__name__)

# ⚠️ Use a fixed secret key so session persists across requests
app.secret_key = os.getenv("FLASK_SECRET_KEY", "replace-with-a-fixed-random-string")

# Ensure secure cookies on Render (HTTPS)
app.config.update(
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_HTTPONLY=True
)

# OAuth2 settings
GOOGLE_CLIENT_ID     = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
OAUTH_REDIRECT_URI   = os.getenv("OAUTH_REDIRECT_URI")
SCOPES = [
    "openid",
    "email",
    "profile",
    "https://www.googleapis.com/auth/youtube.upload"
]

def make_flow(state=None):
    return Flow.from_client_config(
        {
            "web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token"
            }
        },
        scopes=SCOPES,
        state=state,
        redirect_uri=OAUTH_REDIRECT_URI
    )

# In-memory store
USERS = {}

@app.route("/")
def home():
    user = USERS.get(session.get("user_email"))
    return render_template("home.html", user=user)

@app.route("/login")
def login():
    flow = make_flow()
    auth_url, state = flow.authorization_url(
        access_type="offline",
        prompt="consent"
    )
    session["state"] = state
    return redirect(auth_url)

@app.route("/oauth/callback")
def callback():
    # Check that we set state
    state = session.get("state")
    if not state:
        return "Missing OAuth state. Please <a href='/login'>log in</a> first.", 400

    flow = make_flow(state=state)
    flow.fetch_token(authorization_response=request.url)

    if not flow.credentials:
        return "Failed to fetch OAuth token.", 400

    # Get user email
    oauth2 = build("oauth2", "v2", credentials=flow.credentials)
    userinfo = oauth2.userinfo().get().execute()
    email = userinfo.get("email")
    if not email:
        return "Could not retrieve email from Google.", 400

    # Save user and credentials
    USERS[email] = {
        "credentials": flow.credentials,
        "frequency": 1
    }
    session["user_email"] = email
    return redirect(url_for("home"))

@app.route("/settings", methods=["GET","POST"])
def settings():
    email = session.get("user_email")
    if not email:
        return redirect(url_for("login"))
    user = USERS[email]
    if request.method == "POST":
        try:
            user["frequency"] = int(request.form["frequency"])
        except:
            pass
    return render_template("settings.html", user=user)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
