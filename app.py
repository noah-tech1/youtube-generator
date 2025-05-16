import os
from flask import Flask, redirect, url_for, session, render_template, request
from flask_apscheduler import APScheduler
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from pytrends.request import TrendReq

app = Flask(__name__)

# ⚠️ Use a fixed secret key (not os.urandom) to keep session stable across restarts
app.secret_key = os.getenv("FLASK_SECRET_KEY", "replace-this-with-a-random-string")

# Secure session settings (important for OAuth on Render)
app.config.update(
    SESSION_COOKIE_SECURE=True,      # Required for HTTPS on Render
    SESSION_COOKIE_SAMESITE="Lax",   # Needed for Google redirects
    SESSION_COOKIE_HTTPONLY=True
)

# Scheduler setup
class Config:
    SCHEDULER_API_ENABLED = True
app.config.from_object(Config())
scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()

# OAuth2 setup
GOOGLE_CLIENT_ID     = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
OAUTH_REDIRECT_URI   = os.getenv("OAUTH_REDIRECT_URI")
SCOPES = [
    "openid", "email", "profile",
    "https://www.googleapis.com/auth/youtube.upload"
]

def create_flow(state=None):
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token"
            }
        },
        scopes=SCOPES,
        redirect_uri=OAUTH_REDIRECT_URI
    )
    if state:
        flow.fetch_token(authorization_response=request.url)
    return flow

# Simple in-memory store
USERS = {}

@app.route("/")
def home():
    user = USERS.get(session.get("user_email"))
    return render_template("home.html", user=user)

@app.route("/login")
def login():
    flow = create_flow()
    auth_url, state = flow.authorization_url(prompt="consent", access_type="offline")
    session["state"] = state
    return redirect(auth_url)

@app.route("/oauth/callback")
def callback():
    if "state" not in session:
        return "Missing OAuth state in session. Please go to /login first.", 400

    flow = create_flow()
    flow.fetch_token(authorization_response=request.url)

    creds = flow.credentials
    userinfo = build("oauth2", "v2", credentials=creds).userinfo().get().execute()
    email = userinfo.get("email")
    if not email:
        return "Failed to retrieve email from Google", 400

    USERS[email] = {"creds": creds, "frequency": 1}
    session["user_email"] = email
    return redirect(url_for("home"))

@app.route("/settings", methods=["GET", "POST"])
def settings():
    email = session.get("user_email")
    if not email:
        return redirect(url_for("login"))

    user = USERS[email]
    if request.method == "POST":
        user["frequency"] = int(request.form.get("frequency", 1))

    return render_template("settings.html", user=user)

def fetch_and_upload():
    try:
        pytrends = TrendReq()
        top_trends = pytrends.trending_searches(pn="united_states")[0].tolist()[:5]
        print("Top trends:", top_trends)
    except Exception as e:
        print("Error fetching trends:", e)

@scheduler.task("cron", id="daily_job", day="*", hour="0")
def scheduled_job():
    fetch_and_upload()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
