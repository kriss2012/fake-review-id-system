import os
import logging
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

# --- SETUP LOGGING ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev_secret_key")

# --- RENDER HTTPS FIX ---
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# --- DATABASE CONFIG ---
database_url = os.environ.get("DATABASE_URL")
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url or 'sqlite:///reviews.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# --- CONFIGS ---
razorpay_client = razorpay.Client(
    auth=(os.environ.get("RAZORPAY_KEY_ID"), os.environ.get("RAZORPAY_KEY_SECRET"))
)
SUBSCRIPTION_AMOUNT_INR = 49900 
MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
ADMIN_EMAIL_ADDRESS = "202krishnapatil@gmail.com"

# --- AUTH SETUP ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'index'

@login_manager.user_loader
def load_user(user_id):
    try:
        return User.query.get(int(user_id))
    except:
        return None

oauth = OAuth(app)

# --- GOOGLE OAUTH CONFIGURATION (THE FIX) ---
# We removed manual URLs. 'server_metadata_url' handles EVERYTHING automatically.
google = oauth.register(
    name='google',
    client_id=os.environ.get("GOOGLE_CLIENT_ID"),
    client_secret=os.environ.get("GOOGLE_CLIENT_SECRET"),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'},
)

# --- ROUTES ---

@app.route('/')
def index():
    return render_template('index.html', user=current_user, admin_email=ADMIN_EMAIL_ADDRESS)

@app.route('/login')
def login():
    # Force _external=True to get https:// on Render
    redirect_uri = url_for('authorize', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route('/authorize')
def authorize():
    try:
        # 1. Get the Token
        token = google.authorize_access_token()
        
        # 2. Get User Info
        # Since we used server_metadata_url, we can now use the standard .userinfo() method
        # or parse the id_token automatically.
        if 'userinfo' in token:
            user_info = token['userinfo']
        else:
            # Fallback if userinfo isn't inside token
            user_info = google.userinfo()
        
        # 3. Database Logic
        # Google returns 'sub' as the ID in the new flow
        google_id = user_info.get('sub') or user_info.get('id')
        email = user_info.get('email')
        name = user_info.get('name')
        picture = user_info.get('picture')

        user = User.query.filter_by(google_id=google_id).first()
        
        if not user:
            user = User(
                google_id=google_id,
                email=email,
                name=name,
                profile_pic=picture
            )
            db.session.add(user)
            db.session.commit()
        
        login_user(user)
        return redirect(url_for('index'))
    
    except Exception as e:
        logger.error(f"Auth Error: {e}")
        # PRINT ERROR TO SCREEN SO WE CAN SEE IT
        return f"<h3>Login Failed</h3><p>Error details: {str(e)}</p><a href='/'>Go Back</a>"

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
        order_data = {'amount': SUBSCRIPTION_AMOUNT_INR, 'currency': 'INR', 'payment_capture': 1}
        order = razorpay_client.order.create(data=order_data)
        return jsonify({
            'order_id': order['id'], 
            'amount': order['amount'],
            'key_id': os.environ.get("RAZORPAY_KEY_ID"),
            'user_email': current_user.email,
            'user_name': current_user.name
        })
    except Exception as e:
        logger.error(f"Order Create Error: {e}")
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
        
        if MAIL_USERNAME and MAIL_PASSWORD:
            try:
                msg = MIMEMultipart()
                msg['From'] = MAIL_USERNAME
                msg['To'] = current_user.email
                msg['Subject'] = "Subscription Confirmed"
                msg.attach(MIMEText("Welcome to Premium!", 'plain'))
                server = smtplib.SMTP('smtp.gmail.com', 587)
                server.starttls()
                server.login(MAIL_USERNAME, MAIL_PASSWORD)
                server.sendmail(MAIL_USERNAME, current_user.email, msg.as_string())
                server.quit()
            except: pass

        return jsonify({'status': 'success'})
    except Exception as e:
        logger.error(f"Payment Verify Error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/predict', methods=['POST'])
@login_required
def predict():
    review_text = ""
    try:
        if 'text_input' in request.form and request.form['text_input'].strip():
            review_text = request.form['text_input']
        elif 'file_input' in request.files:
            file = request.files['file_input']
            if file and file.filename.endswith('.txt'):
                review_text = file.read().decode('utf-8', errors='ignore')
        elif 'image_input' in request.files:
            file = request.files['image_input']
            if file:
                img = Image.open(file.stream)
                review_text = pytesseract.image_to_string(img)
        
        if not review_text.strip():
            return jsonify({'error': 'No text extracted.'}), 400

        prediction = predict_review(review_text)
        
        return jsonify({
            'prediction': prediction,
            'extracted_text': review_text[:300] + "..." if len(review_text) > 300 else review_text
        })
    except Exception as e:
        logger.error(f"Prediction Crash: {e}")
        return jsonify({'error': f"Processing Error: {str(e)}"}), 500

@app.route('/admin')
@login_required
def admin_panel():
    if current_user.email != ADMIN_EMAIL_ADDRESS:
        return "Access Denied", 403
    users = User.query.all()
    payments = Payment.query.order_by(Payment.created_at.desc()).all()
    return render_template('admin.html', users=users, payments=payments)

# --- SAFE DB CREATION ---
with app.app_context():
    try:
        db.create_all()
        logger.info("Database tables created.")
    except Exception as e:
        logger.error(f"Database creation failed: {e}")

if __name__ == '__main__':
    app.run(debug=True)