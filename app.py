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

# Import DB models and ML logic
from models import db, User, Payment
from model import predict_review

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY")

# --- Configuration ---
# Database Config
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Tesseract Config (Update path if necessary for Windows, e.g., r'C:\Program Files\Tesseract-OCR\tesseract.exe')
# pytesseract.pytesseract.tesseract_cmd = r'/usr/bin/tesseract' 

# Razorpay Config
razorpay_client = razorpay.Client(
    auth=(os.environ.get("RAZORPAY_KEY_ID"), os.environ.get("RAZORPAY_KEY_SECRET"))
)
SUBSCRIPTION_AMOUNT_INR = 49900 # ₹499.00 (in paise)

# Email Config
MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
ADMIN_EMAIL_ADDRESS = os.environ.get("ADMIN_EMAIL")

# Setup Login Manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'index' # Redirect to home if not logged in

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
        print("Email credentials not set. Skipping email sending.")
        return

    msg = MIMEMultipart()
    msg['From'] = MAIL_USERNAME
    msg['To'] = user_email
    msg['Subject'] = "Fake Review Detector - Subscription Confirmed!"

    body = f"Hi {user_name},\n\nThank you for subscribing to the Premium Fake Review Detector! You now have unlimited access to all features.\n\nBest regards,\nThe Team"
    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(MAIL_USERNAME, MAIL_PASSWORD)
        text = msg.as_string()
        server.sendmail(MAIL_USERNAME, user_email, text)
        server.quit()
        print(f"Subscription email sent to {user_email}")
    except Exception as e:
        print(f"Failed to send email: {e}")

# --- Routes ---

@app.route('/')
def index():
    return render_template('index.html', user=current_user, admin_email=ADMIN_EMAIL_ADDRESS)

# --- Authentication Routes ---
@app.route('/login')
def login():
    # Ensure redirect URI matches Google Console settings
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

# --- Payment Routes ---
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
        # Verify signature to ensure data hasn't been tampered with
        razorpay_client.utility.verify_payment_signature({
            'razorpay_order_id': data['razorpay_order_id'],
            'razorpay_payment_id': data['razorpay_payment_id'],
            'razorpay_signature': data['razorpay_signature']
        })

        # Update user status
        current_user.is_subscribed = True
        
        # Record payment
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
    except razorpay.errors.SignatureVerificationError:
        return jsonify({'error': 'Payment verification failed'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# --- Core Application Logic (Prediction) ---
@app.route('/predict', methods=['POST'])
@login_required
def predict():
    # Check subscription limitation (Optional: allow few free tries, then block)
    # For now, allowing access to logged in users. 
    # Uncomment below to enforce subscription for usage:
    # if not current_user.is_subscribed and not current_user.is_admin(ADMIN_EMAIL_ADDRESS):
    #      return jsonify({'error': 'Subscription required for analysis.'}), 403

    review_text = ""

    if 'text_input' in request.form and request.form['text_input'].strip():
        review_text = request.form['text_input']

    elif 'file_input' in request.files:
        file = request.files['file_input']
        if file and file.filename.endswith('.txt'):
            review_text = file.read().decode('utf-8')
        else:
             return jsonify({'error': 'Invalid file type. Please upload a .txt file.'}), 400

    elif 'image_input' in request.files:
        file = request.files['image_input']
        if file and file.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            try:
                image = Image.open(file.stream)
                review_text = pytesseract.image_to_string(image)
            except Exception as e:
                 return jsonify({'error': f'Failed to process image: {str(e)}'}), 500
        else:
             return jsonify({'error': 'Invalid image type.'}), 400
    else:
        return jsonify({'error': 'No valid input provided.'}), 400

    if not review_text.strip():
         return jsonify({'error': 'Could not extract text from input.'}), 400

    prediction = predict_review(review_text)
    return jsonify({'prediction': prediction, 'extracted_text': review_text[:200] + "..." if len(review_text) > 200 else review_text})


# --- Admin Section ---
@app.route('/admin')
@login_required
def admin_panel():
    if not current_user.is_admin(ADMIN_EMAIL_ADDRESS):
        return "Access Denied", 403
        
    users = User.query.all()
    payments = Payment.query.order_by(Payment.created_at.desc()).all()
    return render_template('admin.html', users=users, payments=payments) #You would need an admin.html

# Create DB tables before running
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    # Ensure HTTPS for OAuth in production, HTTP fine for local dev
    # os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1' 
    app.run(debug=True)