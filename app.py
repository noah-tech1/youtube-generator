import os
from flask import Flask, redirect, url_for, session, render_template, request
from flask_apscheduler import APScheduler
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from pytrends.request import TrendReq

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Scheduler setup
class Config:
    SCHEDULER_API_ENABLED = True
app.config.from_object(Config())
scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()

# OAuth2 config
GOOGLE_CLIENT_ID     = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
OAUTH_REDIRECT_URI   = os.getenv("OAUTH_REDIRECT_URI")
SCOPES = ["openid", "email", "profile", "https://www.googleapis.com/auth/youtube.upload"]

flow = Flow.from_client_config(
    {"web": {
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
    }},
    scopes=SCOPES,
    redirect_uri=OAUTH_REDIRECT_URI,
)

# In-memory store
USERS = {}

@app.route("/")
def home():
    user = USERS.get(session.get("user_email"))
    return render_template("home.html", user=user)

@app.route("/login")
def login():
    auth_url, _ = flow.authorization_url(prompt="consent", access_type="offline")
    return redirect(auth_url)

@app.route("/oauth/callback")
def callback():
    flow.fetch_token(authorization_response=request.url)
    creds = flow.credentials
    userinfo = build("oauth2", "v2", credentials=creds).userinfo().get().execute()
    email = userinfo["email"]
    USERS[email] = {"creds": creds, "frequency": 1}
    session["user_email"] = email
    return redirect(url_for("home"))

@app.route("/settings", methods=["GET","POST"])
def settings():
    email = session.get("user_email")
    if not email:
        return redirect(url_for("login"))
    user = USERS[email]
    if request.method == "POST":
        user["frequency"] = int(request.form["frequency"])
    return render_template("settings.html", user=user)

def fetch_and_upload():
    # Example: fetch top 5 Google Trends
    pytrends = TrendReq()
    top_google = pytrends.trending_searches(pn="united_states")[0].tolist()[:5]
    # TODO: fetch YouTube trends, generate prompts, call InVideo, upload via YouTube API

@scheduler.task("cron", id="weekly_job", day="*", hour="0")
def scheduled_job():
    fetch_and_upload()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
