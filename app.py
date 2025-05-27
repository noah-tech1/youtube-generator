import os
from flask import Flask, redirect, url_for, session, request, render_template, flash
from flask_sqlalchemy import SQLAlchemy
from flask_dance.contrib.google import make_google_blueprint, google
from models import db, User
import requests

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "supersekrit")
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///youtube_generator.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# Google OAuth setup with modern scopes for compatibility
app.config['OAUTHLIB_INSECURE_TRANSPORT'] = True
google_bp = make_google_blueprint(
    client_id=os.environ.get("GOOGLE_CLIENT_ID"),
    client_secret=os.environ.get("GOOGLE_CLIENT_SECRET"),
    scope=[
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile",
        "https://www.googleapis.com/auth/youtube.upload"
    ],
    redirect_url="/login/google/authorized"
)
app.register_blueprint(google_bp, url_prefix="/login")

# YouTube OAuth endpoints
YOUTUBE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
YOUTUBE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
YOUTUBE_OAUTH_REDIRECT = os.environ.get("YOUTUBE_OAUTH_REDIRECT", "http://localhost:5000/youtube/callback")
YOUTUBE_AUTH_URL = (
    "https://accounts.google.com/o/oauth2/v2/auth"
    "?client_id={client_id}"
    "&redirect_uri={redirect_uri}"
    "&scope=https://www.googleapis.com/auth/youtube.upload"
    "&access_type=offline"
    "&response_type=code"
    "&prompt=consent"
)

@app.route("/")
def home():
    if not google.authorized:
        return render_template("home.html", logged_in=False)
    resp = google.get("/oauth2/v2/userinfo")
    assert resp.ok, resp.text
    userinfo = resp.json()
    user = User.query.filter_by(google_id=userinfo["id"]).first()
    # Create or update user on login
    if not user:
        user = User(
            google_id=userinfo["id"],
            email=userinfo.get("email", ""),
            name=userinfo.get("name", ""),
            frequency=1
        )
        db.session.add(user)
        db.session.commit()
    else:
        updated = False
        if user.email != userinfo.get("email", user.email):
            user.email = userinfo.get("email", user.email)
            updated = True
        if user.name != userinfo.get("name", user.name):
            user.name = userinfo.get("name", user.name)
            updated = True
        if updated:
            db.session.commit()
    youtube_connected = bool(user.access_token and user.refresh_token)
    return render_template(
        "home.html",
        logged_in=True,
        name=user.name,
        email=user.email,
        frequency=user.frequency,
        youtube_connected=youtube_connected
    )

@app.route("/settings", methods=["GET", "POST"])
def settings():
    if not google.authorized:
        return redirect(url_for("home"))
    resp = google.get("/oauth2/v2/userinfo")
    assert resp.ok, resp.text
    userinfo = resp.json()
    user = User.query.filter_by(google_id=userinfo["id"]).first()
    if request.method == "POST":
        freq = int(request.form.get("frequency", 1))
        user.frequency = freq
        db.session.commit()
        return redirect(url_for("home"))
    return render_template("settings.html", name=user.name, frequency=user.frequency)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

@app.route("/youtube/authorize", methods=["POST"])
def youtube_authorize():
    # Redirect user to Google OAuth for YouTube
    url = YOUTUBE_AUTH_URL.format(
        client_id=YOUTUBE_CLIENT_ID,
        redirect_uri=YOUTUBE_OAUTH_REDIRECT
    )
    return redirect(url)

@app.route("/youtube/callback")
def youtube_callback():
    if not google.authorized:
        flash("You must be logged in with Google first.")
        return redirect(url_for("home"))
    code = request.args.get("code")
    if not code:
        flash("Authorization failed or denied.")
        return redirect(url_for("home"))
    # Exchange code for tokens
    data = {
        "code": code,
        "client_id": YOUTUBE_CLIENT_ID,
        "client_secret": YOUTUBE_CLIENT_SECRET,
        "redirect_uri": YOUTUBE_OAUTH_REDIRECT,
        "grant_type": "authorization_code"
    }
    token_resp = requests.post("https://oauth2.googleapis.com/token", data=data)
    if token_resp.status_code != 200:
        flash("Failed to obtain tokens from Google.")
        return redirect(url_for("home"))
    tokens = token_resp.json()
    access_token = tokens.get("access_token")
    refresh_token = tokens.get("refresh_token")
    # Update user in DB
    resp = google.get("/oauth2/v2/userinfo")
    userinfo = resp.json()
    user = User.query.filter_by(google_id=userinfo["id"]).first()
    user.access_token = access_token
    user.refresh_token = refresh_token
    db.session.commit()
    flash("YouTube account connected!")
    return redirect(url_for("home"))

# Ensure tables are created on every start (for gunicorn/Render)
with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True)
