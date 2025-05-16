import os
import traceback
from flask import Flask, redirect, url_for, session, render_template, request, make_response
from flask_apscheduler import APScheduler
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from pytrends.request import TrendReq

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Config for APScheduler
class Config:
    SCHEDULER_API_ENABLED = True

app.config.from_object(Config())
scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()

# OAuth2 setup
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
OAUTH_REDIRECT_URI = os.getenv("OAUTH_REDIRECT_URI")

SCOPES = [
    "openid",
    "email",
    "profile",
    "https://www.googleapis.com/auth/youtube.upload"
]

def create_flow():
    return Flow.from_client_config(
        {
            "web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=SCOPES,
        redirect_uri=OAUTH_REDIRECT_URI,
    )

# Simple in-memory store
USERS = {}

@app.route("/")
def home():
    user = USERS.get(session.get("user_email"))
    return render_template("home.html", user=user)

@app.route("/login")
def login():
    flow = create_flow()
    auth_url, state = flow.authorization_url(prompt="consent", access_type="offline", include_granted_scopes="true")
    session["oauth_state"] = state
    return redirect(auth_url)

@app.route("/oauth/callback")
def oauth_callback():
    try:
        state = session.get("oauth_state")
        if not state:
            return make_response("Missing OAuth state in session. Please go to /login first.", 400)

        flow = create_flow()
        flow.fetch_token(authorization_response=request.url)

        creds = flow.credentials
        oauth2_client = build("oauth2", "v2", credentials=creds)
        userinfo = oauth2_client.userinfo().get().execute()

        email = userinfo.get("email")
        if not email:
            return make_response("Failed to retrieve email.", 400)

        USERS[email] = {"creds": creds, "frequency": 1}
        session["user_email"] = email
        return redirect(url_for("home"))

    except Exception:
        tb = traceback.format_exc()
        print("=== CALLBACK EXCEPTION ===")
        print(tb)
        return make_response(f"<pre>{tb}</pre>", 500)

@app.route("/settings", methods=["GET", "POST"])
def settings():
    email = session.get("user_email")
    if not email:
        return redirect(url_for("login"))
    user = USERS[email]
    if request.method == "POST":
        try:
            user["frequency"] = int(request.form["frequency"])
        except ValueError:
            return "Invalid frequency", 400
    return render_template("settings.html", user=user)

def fetch_and_upload():
    print("Fetching trends and preparing video upload...")
    pytrends = TrendReq()
    try:
        trends = pytrends.trending_searches(pn="united_states")[0].tolist()[:5]
        print("Top trends:", trends)
        # TODO: generate script, generate video (e.g., with Renderforest API), and upload using YouTube API
    except Exception as e:
        print("Trend fetch/upload error:", str(e))

# Runs daily at midnight UTC
@scheduler.task("cron", id="daily_job", day="*", hour="0")
def scheduled_job():
    fetch_and_upload()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
