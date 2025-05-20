from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    google_id = db.Column(db.String(255), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    name = db.Column(db.String(255))
    frequency = db.Column(db.Integer, default=1)  # videos per week
    access_token = db.Column(db.String(512))      # For YouTube upload (optional, future step)
    refresh_token = db.Column(db.String(512))     # For YouTube upload (optional, future step)
