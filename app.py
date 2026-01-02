import os
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv
from PIL import Image
import pytesseract
import razorpay
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from werkzeug.middleware.proxy_fix import ProxyFix 

# Import DB and Model
from models import db, User, Payment
from model import predict_review

# Load Environment Variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev_secret_key")

# --- RENDER HTTPS FIX ---
# This line makes Google Login work on Render
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# --- Database Config ---
# Auto-switch between Postgres (Render) and SQLite (Local)
database_url = os.environ.get("DATABASE_URL")
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url or 'sqlite:///reviews.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# --- Razorpay Config ---
razorpay_client = razorpay.Client(
    auth=(os.environ.get("RAZORPAY_KEY_ID"), os.environ.get("RAZORPAY_KEY_SECRET"))
)
SUBSCRIPTION_AMOUNT_INR = 49900 # ₹499.00

# --- Email Config ---
MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
ADMIN_EMAIL_ADDRESS = "202krishnapatil@gmail.com"

# --- Login Manager ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'index' # Redirect to home if not logged in

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- OAuth Setup ---
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=os.environ.get("GOOGLE_CLIENT_ID"),
    client_secret=os.environ.get("GOOGLE_CLIENT_SECRET"),
    access_token_url='https://accounts.google.com/o/oauth2/token',
    access_token_params=None,
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    authorize_params=None,
    api_base_url='https://www.googleapis.com/oauth2/v1/',
    userinfo_endpoint='https://www.googleapis.com/oauth2/v1/userinfo',
    client_kwargs={'scope': 'openid email profile'},
)

# --- Helper: Send Email ---
def send_subscription_email(user_email, user_name):
    if not MAIL_USERNAME or not MAIL_PASSWORD:
        return

    msg = MIMEMultipart()
    msg['From'] = MAIL_USERNAME
    msg['To'] = user_email
    msg['Subject'] = "Subscription Confirmed - VeriView"
    body = f"Hi {user_name},\n\nWelcome to VeriView Premium! Your payment was successful.\n\nEnjoy unlimited analysis.\n\nRegards,\nThe Team"
    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(MAIL_USERNAME, MAIL_PASSWORD)
        server.sendmail(MAIL_USERNAME, user_email, msg.as_string())
        server.quit()
    except Exception as e:
        print(f"Email error: {e}")

# --- ROUTES ---

@app.route('/')
def index():
    return render_template('index.html', user=current_user, admin_email=ADMIN_EMAIL_ADDRESS)

# Auth Routes
@app.route('/login')
def login():
    redirect_uri = url_for('authorize', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route('/authorize')
def authorize():
    token = google.authorize_access_token()
    user_info = google.get('userinfo').json()
    
    # Check if user exists
    user = User.query.filter_by(google_id=user_info['id']).first()
    
    if not user:
        user = User(
            google_id=user_info['id'],
            email=user_info['email'],
            name=user_info.get('name', 'User'),
            profile_pic=user_info.get('picture', '')
        )
        db.session.add(user)
        db.session.commit()
    
    login_user(user)
    return redirect(url_for('index'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# Payment Routes
@app.route('/create-order', methods=['POST'])
@login_required
def create_order():
    if current_user.is_subscribed:
        return jsonify({'error': 'Already subscribed'}), 400

    try:
        order_data = {
            'amount': SUBSCRIPTION_AMOUNT_INR,
            'currency': 'INR',
            'payment_capture': 1
        }
        order = razorpay_client.order.create(data=order_data)
        return jsonify({
            'order_id': order['id'], 
            'amount': order['amount'],
            'key_id': os.environ.get("RAZORPAY_KEY_ID"),
            'user_email': current_user.email,
            'user_name': current_user.name
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/verify-payment', methods=['POST'])
@login_required
def verify_payment():
    data = request.json
    try:
        razorpay_client.utility.verify_payment_signature({
            'razorpay_order_id': data['razorpay_order_id'],
            'razorpay_payment_id': data['razorpay_payment_id'],
            'razorpay_signature': data['razorpay_signature']
        })

        # Upgrade User
        current_user.is_subscribed = True
        
        # Log Payment
        payment = Payment(
            user_id=current_user.id,
            payment_id=data['razorpay_payment_id'],
            order_id=data['razorpay_order_id'],
            amount=SUBSCRIPTION_AMOUNT_INR / 100.0,
            status='success'
        )
        db.session.add(payment)
        db.session.commit()

        # Send Email
        send_subscription_email(current_user.email, current_user.name)

        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Prediction Route
@app.route('/predict', methods=['POST'])
@login_required
def predict():
    review_text = ""

    # 1. Text Input
    if 'text_input' in request.form and request.form['text_input'].strip():
        review_text = request.form['text_input']
    
    # 2. File Input
    elif 'file_input' in request.files:
        file = request.files['file_input']
        if file and file.filename.endswith('.txt'):
            review_text = file.read().decode('utf-8', errors='ignore')
    
    # 3. Image Input
    elif 'image_input' in request.files:
        file = request.files['image_input']
        if file:
            try:
                img = Image.open(file.stream)
                review_text = pytesseract.image_to_string(img)
            except Exception as e:
                return jsonify({'error': f'OCR Error: {str(e)}'}), 500
    
    if not review_text.strip():
        return jsonify({'error': 'Could not extract text.'}), 400

    # Run Prediction
    prediction = predict_review(review_text)
    
    return jsonify({
        'prediction': prediction,
        'extracted_text': review_text[:300] + "..." if len(review_text) > 300 else review_text
    })

# Admin Route
@app.route('/admin')
@login_required
def admin_panel():
    if current_user.email != ADMIN_EMAIL_ADDRESS:
        return "Access Denied: Admins Only", 403
        
    users = User.query.all()
    payments = Payment.query.order_by(Payment.created_at.desc()).all()
    # Ensure you have an admin.html template or reuse index with admin flag
    return render_template('admin.html', users=users, payments=payments)

# --- Initialization ---
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)