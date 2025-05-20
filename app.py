import os
import traceback
from flask import Flask, redirect, url_for, session, render_template, request, make_response, jsonify
from flask_apscheduler import APScheduler
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from pytrends.request import TrendReq
import requests

app = Flask(__name__)
# Use a fixed secret so sessions persist across deploys
app.secret_key = os.getenv("FLASK_SECRET_KEY", "YOUR_FIXED_SECRET_HERE")

# Ensure secure session cookies on HTTPS
app.config.update(
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_HTTPONLY=True,
)

# Scheduler (optional)
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

# *** Crucial: include the userinfo scopes so they match what Google returns ***
SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/youtube.upload"
]

def create_flow():
    return Flow.from_client_config(
        {
            "web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "auth_uri":    "https://accounts.google.com/o/oauth2/auth",
                "token_uri":   "https://oauth2.googleapis.com/token",
            }
        },
        scopes=SCOPES,
        redirect_uri=OAUTH_REDIRECT_URI,
    )

# In-memory user store
USERS = {}

@app.route("/")
def home():
    user = USERS.get(session.get("user_email"))
    return render_template("home.html", user=user)

@app.route("/login")
def login():
    flow = create_flow()
    auth_url, state = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        include_granted_scopes="true"
    )
    session["oauth_state"] = state
    return redirect(auth_url)

@app.route("/oauth/callback")
def oauth_callback():
    try:
        # Recreate flow with stored state
        flow = create_flow()
        flow.fetch_token(authorization_response=request.url)

        creds = flow.credentials
        if not creds:
            return make_response("No credentials returned by Google.", 400)

        # Build the OAuth2 service to fetch userinfo
        oauth2_client = build("oauth2", "v2", credentials=creds)
        userinfo = oauth2_client.userinfo().get().execute()
        email = userinfo.get("email")
        if not email:
            return make_response("Failed to retrieve email.", 400)

        # Store creds & default frequency
        USERS[email] = {
            "creds": creds,
            "email": email,
            "frequency": 1
        }
        session["user_email"] = email
        return redirect(url_for("home"))

    except Exception:
        tb = traceback.format_exc()
        print("=== CALLBACK EXCEPTION ===\n", tb)
        return make_response(f"<pre>{tb}</pre>", 500)

@app.route("/settings", methods=["GET", "POST"])
def settings():
    try:
        email = session.get("user_email")
        # Ensure both session and USERS entry are present
        if not email or email not in USERS:
            return redirect(url_for("login"))
        user = USERS[email]
        if request.method == "POST":
            try:
                user["frequency"] = int(request.form.get("frequency", user.get("frequency", 1)))
            except (ValueError, TypeError):
                pass
        return render_template("settings.html", user=user)
    except Exception as e:
        # Render the full error in the browser for debugging (remove this in production)
        return f"<pre>{traceback.format_exc()}</pre>", 500

def fetch_and_upload():
    try:
        pytrends = TrendReq()
        top5 = pytrends.trending_searches(pn="united_states")[0].tolist()[:5]
        print("Top 5 Google Trends:", top5)
        # TODO: fetch YouTube trends; generate titles/prompts; call InVideo AI; upload via YouTube API
    except Exception as e:
        print("Error in fetch_and_upload:", e)

@scheduler.task("cron", id="daily_job", day="*", hour="0")
def scheduled_job():
    fetch_and_upload()

# === Tavus API Integration ===

TAVUS_API_KEY = os.getenv("TAVUS_API_KEY")

def generate_video_with_tavus(script):
    """
    Calls the Tavus API to generate a video from a script using the specified replica.
    Returns the API's JSON response.
    """
    url = "https://tavusapi.com/v2/videos"
    headers = {
        "Content-Type": "application/json",
        "x-api-key": TAVUS_API_KEY
    }
    data = {
        "replica_id": "r92debe21318",  # Your hardcoded replica ID
        "script": script
    }
    response = requests.post(url, json=data, headers=headers)
    response.raise_for_status()
    return response.json()

@app.route('/generate-video', methods=['POST'])
def generate_video():
    # Expects a JSON body like { "script": "Hello world!" }
    data = request.get_json()
    script = data.get("script", "")
    if not script:
        return jsonify({"error": "Missing 'script' in request body"}), 400

    try:
        result = generate_video_with_tavus(script)
        return jsonify(result)
    except requests.RequestException as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
