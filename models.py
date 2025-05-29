from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    google_id = db.Column(db.String(255), unique=True, nullable=False)
    email = db.Column(db.String(255))  # not unique, nullable
    name = db.Column(db.String(255))
    frequency = db.Column(db.Integer, default=1)
    access_token = db.Column(db.String(512))
    refresh_token = db.Column(db.String(512))
