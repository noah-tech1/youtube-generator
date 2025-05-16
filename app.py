import os
from flask import Flask, redirect, url_for, session, render_template, request
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from pytrends.request import TrendReq

app = Flask(__name__)

# Use a fixed secret key so sessions persist across deploys
app.secret_key = os.getenv("FLASK_SECRET_KEY", "replace-with-your-own-constant-key")

# Secure cookies for production on HTTPS
app.config.update(
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_HTTPONLY=True,
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

# In‐memory user store (for demo purposes)
USERS = {}

def create_flow():
    """Returns a fresh Flow object for the current request."""
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

@app.route("/")
def home():
    user = USERS.get(session.get("user_email"))
    return render_template("home.html", user=user)

@app.route("/login")
def login():
    flow = create_flow()
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        prompt="consent"
    )
    return redirect(auth_url)

@app.route("/oauth/callback")
def oauth_callback():
    # Note: we've removed the state parameter entirely to simplify session handling
    flow = create_flow()
    flow.fetch_token(authorization_response=request.url)

    if not flow.credentials:
        return "Error: No credentials returned by Google", 400

    # Fetch the user's email
    oauth2_client = build("oauth2", "v2", credentials=flow.credentials)
    userinfo = oauth2_client.userinfo().get().execute()
    email = userinfo.get("email")
    if not email:
        return "Error: Unable to retrieve email from Google", 400

    # Store credentials & default frequency
    USERS[email] = {
        "credentials": flow.credentials,
        "frequency": 1
    }
    session["user_email"] = email
    return redirect(url_for("home"))

@app.route("/settings", methods=["GET", "POST"])
def settings():
    email = session.get("user_email")
    if not email:
        return redirect(url_for("login"))

    user = USERS[email]
    if request.method == "POST":
        try:
            user["frequency"] = int(request.form.get("frequency", 1))
        except ValueError:
            pass

    return render_template("settings.html", user=user)

def fetch_and_upload():
    # Example: fetch top 5 Google Trends
    try:
        pytrends = TrendReq()
        top5 = pytrends.trending_searches(pn="united_states")[0].tolist()[:5]
        print("Top 5 Trends:", top5)
        # TODO: Fetch YouTube trends, generate prompts for InVideo AI,
        #       call InVideo API to create videos, then upload via YouTube API.
    except Exception as e:
        print("Error in fetch_and_upload:", e)

from flask_apscheduler import APScheduler
class SchedulerConfig:
    SCHEDULER_API_ENABLED = True
app.config.from_object(SchedulerConfig())
scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()

@scheduler.task("cron", id="daily_task", hour="0", minute="0")
def daily_task():
    fetch_and_upload()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
