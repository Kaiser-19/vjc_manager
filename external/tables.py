# tables.py

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class CodeTable(db.Model):
    code = db.Column(db.String(11), primary_key=True)
    used = db.Column(db.Boolean, default=False)
    time = db.Column(db.Integer, default=False)

class Registration(db.Model):
    ip_address = db.Column(db.String(20), primary_key=True)
    code = db.Column(db.String(11))
    mac = db.Column(db.String(20))

class TodayDate(db.Model):
    date = db.Column(db.String(10), primary_key=True)
    router_password = db.Column(db.String(20))