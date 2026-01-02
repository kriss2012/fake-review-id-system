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
from werkzeug.middleware.proxy_fix import ProxyFix  # CRITICAL FOR RENDER

# Import DB models and ML logic
from models import db, User, Payment
from model import predict_review

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev_key") # Fallback key for dev

# --- RENDER CONFIGURATION (CRITICAL) ---
# This tells Flask to trust the HTTPS headers from Render
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# --- Database Config ---
# Render provides DATABASE_URL starting with postgres:// but SQLAlchemy needs postgresql://
database_url = os.environ.get("DATABASE_URL")
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url or 'sqlite:///reviews.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# Tesseract Config (Update if using a custom buildpack on Render, otherwise default is usually fine)
# On Render, you often need to install tesseract via a build script or use a docker image.
# For standard python environment, ensure apt packages are installed.

# Razorpay Config
razorpay_client = razorpay.Client(
    auth=(os.environ.get("RAZORPAY_KEY_ID"), os.environ.get("RAZORPAY_KEY_SECRET"))
)
SUBSCRIPTION_AMOUNT_INR = 49900 

# Email Config
MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
ADMIN_EMAIL_ADDRESS = os.environ.get("ADMIN_EMAIL")

# Setup Login Manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'index' 

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Setup Google OAuth
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

# --- Helper Functions ---
def send_subscription_email(user_email, user_name):
    if not MAIL_USERNAME or not MAIL_PASSWORD:
        return

    msg = MIMEMultipart()
    msg['From'] = MAIL_USERNAME
    msg['To'] = user_email
    msg['Subject'] = "Fake Review Detector - Subscription Confirmed!"
    body = f"Hi {user_name},\n\nThank you for subscribing to the Premium Fake Review Detector!\n\nBest regards,\nThe Team"
    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(MAIL_USERNAME, MAIL_PASSWORD)
        server.sendmail(MAIL_USERNAME, user_email, msg.as_string())
        server.quit()
    except Exception as e:
        print(f"Failed to send email: {e}")

# --- Routes ---

@app.route('/')
def index():
    return render_template('index.html', user=current_user, admin_email=ADMIN_EMAIL_ADDRESS)

@app.route('/login')
def login():
    # Force _external=True to get the full URL (https://...)
    redirect_uri = url_for('authorize', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route('/authorize')
def authorize():
    token = google.authorize_access_token()
    resp = google.get('userinfo')
    user_info = resp.json()

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

@app.route('/create-order', methods=['POST'])
@login_required
def create_order():
    if current_user.is_subscribed:
         return jsonify({'error': 'Already subscribed'}), 400

    try:
        order_data = {
            'amount': SUBSCRIPTION_AMOUNT_INR,
            'currency': 'INR',
            'receipt': f'receipt_order_{current_user.id}',
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

        current_user.is_subscribed = True
        
        payment = Payment(
            user_id=current_user.id,
            payment_id=data['razorpay_payment_id'],
            order_id=data['razorpay_order_id'],
            amount=SUBSCRIPTION_AMOUNT_INR / 100.0,
            status='success'
        )
        db.session.add(payment)
        db.session.commit()

        send_subscription_email(current_user.email, current_user.name)

        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/predict', methods=['POST'])
@login_required
def predict():
    review_text = ""
    if 'text_input' in request.form and request.form['text_input'].strip():
        review_text = request.form['text_input']
    elif 'file_input' in request.files:
        file = request.files['file_input']
        if file: review_text = file.read().decode('utf-8')
    elif 'image_input' in request.files:
        file = request.files['image_input']
        if file:
            try:
                image = Image.open(file.stream)
                review_text = pytesseract.image_to_string(image)
            except:
                return jsonify({'error': 'OCR Failed'}), 500

    if not review_text.strip():
         return jsonify({'error': 'No text found.'}), 400

    prediction = predict_review(review_text)
    return jsonify({'prediction': prediction, 'extracted_text': review_text[:200]})

@app.route('/admin')
@login_required
def admin_panel():
    if current_user.email != ADMIN_EMAIL_ADDRESS:
        return "Access Denied", 403
        
    users = User.query.all()
    payments = Payment.query.order_by(Payment.created_at.desc()).all()
    # You need to create an admin.html template for this
    return render_template('admin.html', users=users, payments=payments)

# --- CRITICAL: Create tables inside the context ---
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    # Local development
    # os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1' 
    app.run(debug=True)