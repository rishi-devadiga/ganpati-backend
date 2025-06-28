import os
from flask import Flask
from model import db, Transactions
from dotenv import load_dotenv

load_dotenv()

# --- App Initialization ---
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///donation.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# --- Extension Initialization ---
db.init_app(app)  # Initialize the db instance from models.py

# --- Create tables if they don't exist ---
with app.app_context():
    db.create_all()

from flask import request, jsonify
from flask_cors import CORS
import razorpay
import sqlite3
import hmac
import hashlib
from datetime import datetime
import requests


CORS(app)


client = razorpay.Client(auth=(os.getenv("RAZORPAY_KEY_ID"), os.getenv("RAZORPAY_KEY_SECRET")))
client.session = requests.Session()


@app.route('/create-order', methods=['POST'])
def register():
    data = request.get_json()
    amount = data.get('amount')

    order = client.order.create({
        'amount': amount,
        'currency': 'INR',
        'payment_capture': 1
    },timeout=300)

    return jsonify({"order":order, "userData": data})

# ...existing code...

@app.route('/cash-payment', methods=['POST'])
def cash_payment():
    data = request.get_json()
    try:
        transaction = Transactions(
            name=data.get('name'),
            address=data.get('address'),
            phone=data.get('phone'),
            email=data.get('email'),
            transaction_type='cash',
            amount=float(data.get('amount')),
            razorpay_order_id='CASH',
            razorpay_payment_id='CASH'
        )
        db.session.add(transaction)
        db.session.commit()
        return jsonify({"status": "success", "message": "Cash payment recorded."})
    except Exception as e:
        print("Cash payment error:", str(e))
        return jsonify({'status': 'failure', 'error': str(e)}), 500



@app.route('/verify-payment', methods=['POST'])
def verify_payment():
    data = request.get_json()

    # Extract Razorpay details
    razorpay_order_id = data.get('razorpay_order_id')
    razorpay_payment_id = data.get('razorpay_payment_id')
    razorpay_signature = data.get('razorpay_signature')

    # Verify the signature (assuming you already have this code working)
    generated_signature = hmac.new(
        bytes(os.getenv("RAZORPAY_KEY_SECRET"), 'utf-8'),
        bytes(data['razorpay_order_id'] + "|" + data['razorpay_payment_id'], 'utf-8'),
        hashlib.sha256
    ).hexdigest()

    if generated_signature == razorpay_signature:
        try:
            # Save transaction to DB using SQLAlchemy
            transaction = Transactions(
                name=data.get('name'),
                address=data.get('address'),
                phone=data.get('phone'),
                email=data.get('email'),
                transaction_type=data.get('transaction_type'),
                amount=float(data.get('amount')) / 100,
                razorpay_order_id=razorpay_order_id,
                razorpay_payment_id=razorpay_payment_id
            )

            db.session.add(transaction)
            db.session.commit()

            return jsonify({"status": "success", "message": "Payment verified and transaction saved."})

        except razorpay.errors.SignatureVerificationError as e:
            print("Signature verification failed:", str(e))
            return jsonify({'status': 'failure', 'message': 'Signature verification failed'}), 400
    
        except Exception as e:
            print("General error:", str(e))
            return jsonify({'status': 'failure', 'error': str(e)}), 500



import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
from sib_api_v3_sdk.models import SendSmtpEmail, SendSmtpEmailAttachment
import base64

@app.route('/send-receipt', methods=['POST'])
def send_receipt():
    email = request.form.get('email')
    pdf_file = request.files.get('pdf')

    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key['api-key'] = os.getenv("BREVO_API_KEY")
    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))

    attachments = []
    if pdf_file:
        encoded_pdf = base64.b64encode(pdf_file.read()).decode()
        attachments = [
            SendSmtpEmailAttachment(
                name="receipt.pdf",
                content=encoded_pdf
            )
        ]

    send_smtp_email = SendSmtpEmail(
        to=[{"email": email}],
        sender={"email": os.getenv("MAIL_USERNAME")},
        subject="Your Donation Receipt",
        html_content="<strong>Thank you for your donation!</strong>",
        attachments=attachments
    )

    try:
        api_instance.send_transac_email(send_smtp_email)
        return jsonify({'status': 'success'})
    except ApiException as e:
        print("Brevo error:", str(e))
        return jsonify({'status': 'failure', 'error': str(e)}), 500
    

import pandas as pd
from flask import send_file
from io import BytesIO
from model import Transactions  # adjust this import to your structure

@app.route('/export-transactions', methods=['GET'])
def export_transactions():
    # Query all transactions
    transactions = Transactions.query.all()

    # Convert to list of dicts
    data = [{
        'ID': t.id,
        'Name': t.name,
        'Address': t.address,
        'Phone': t.phone,
        'Email': t.email,
        'Transaction Type': t.transaction_type,
        'Amount': t.amount,
        'Date': t.date.strftime('%Y-%m-%d %H:%M:%S'),
        'Razorpay Order ID': t.razorpay_order_id,
        'Razorpay Payment ID': t.razorpay_payment_id
    } for t in transactions]

    # Create DataFrame and Excel file in memory
    df = pd.DataFrame(data)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Transactions')

    output.seek(0)
    return send_file(output, download_name="transactions.xlsx", as_attachment=True)


if __name__ == '__main__':
    app.run(port=5000, debug=True)
