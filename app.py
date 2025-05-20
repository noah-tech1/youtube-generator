import os
from flask import Flask, redirect, url_for, session, request, render_template_string
from flask_sqlalchemy import SQLAlchemy
from flask_dance.contrib.google import make_google_blueprint, google
from models import db, User

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "supersekrit")
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///youtube_generator.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# Google OAuth setup
app.config['OAUTHLIB_INSECURE_TRANSPORT'] = True
google_bp = make_google_blueprint(
    client_id=os.environ.get("GOOGLE_OAUTH_CLIENT_ID"),
    client_secret=os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET"),
    scope=["profile", "email"],
    redirect_url="/login/google/authorized"
)
app.register_blueprint(google_bp, url_prefix="/login")

# Simple HTML templates (for demo, replace with real templates!)
HOME_TEMPLATE = """
<h2>YouTube Generator Demo</h2>
{% if not logged_in %}
  <a href="{{ url_for('google.login') }}">Login with Google</a>
{% else %}
  <p>Welcome, {{ name }} ({{ email }})</p>
  <p>Your frequency: {{ frequency }} videos/week</p>
  <a href="{{ url_for('settings') }}">Change settings</a>
  <br>
  <a href="{{ url_for('logout') }}">Logout</a>
{% endif %}
"""

SETTINGS_TEMPLATE = """
<h2>Settings for {{ name }}</h2>
<form method="post">
  <label>Videos per week:</label>
  <input type="number" name="frequency" min="1" max="7" value="{{ frequency }}" required>
  <button type="submit">Save</button>
</form>
<a href="{{ url_for('home') }}">Back to Home</a>
"""

@app.route("/")
def home():
    if not google.authorized:
        return render_template_string(HOME_TEMPLATE, logged_in=False)
    resp = google.get("/oauth2/v2/userinfo")
    assert resp.ok, resp.text
    userinfo = resp.json()
    user = User.query.filter_by(google_id=userinfo["id"]).first()
    return render_template_string(
        HOME_TEMPLATE,
        logged_in=True,
        name=user.name,
        email=user.email,
        frequency=user.frequency
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
    return render_template_string(SETTINGS_TEMPLATE, name=user.name, frequency=user.frequency)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

# User creation/update after login
@google_bp.login_success
def logged_in(blueprint, token):
    resp = google.get("/oauth2/v2/userinfo")
    if not resp.ok:
        return False
    userinfo = resp.json()
    user = User.query.filter_by(google_id=userinfo["id"]).first()
    if not user:
        user = User(
            google_id=userinfo["id"],
            email=userinfo.get("email", ""),
            name=userinfo.get("name", ""),
            frequency=1
        )
        db.session.add(user)
    else:
        user.email = userinfo.get("email", user.email)
        user.name = userinfo.get("name", user.name)
    db.session.commit()
    return False  # Continue with normal flow

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
