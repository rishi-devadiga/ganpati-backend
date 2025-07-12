from flask_sqlalchemy import SQLAlchemy
from datetime import datetime



db = SQLAlchemy()
class Transactions(db.Model):
    __tablename__ = 'transactions'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(15), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    transaction_type = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(50), nullable=True)  # e.g., 'pending', 'completed', 'failed'
    half_payment = db.Column(db.Integer, nullable=True)  # Amount in paise or INR, match your logic
    amount_pending = db.Column(db.Integer, nullable=True)  # Amount in paise or INR
    razorpay_order_id = db.Column(db.String(100), nullable=False)
    razorpay_payment_id = db.Column(db.String(100), nullable=False)

    def __repr__(self):
        return f'<Transaction {self.id}>'