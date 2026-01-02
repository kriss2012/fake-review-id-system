import pickle
import os
import re
import nltk
from nltk.corpus import stopwords
from nltk.stem.porter import PorterStemmer

# --- NLTK Setup for Render ---
# We download these only if missing to speed up boot time
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')

try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

STOPWORDS = set(stopwords.words('english'))
MODEL_FILE = 'model.pkl'
model_pipeline = None

def preprocess_text(text):
    """
    Must match exactly how you cleaned text during training.
    """
    ps = PorterStemmer()
    # Remove non-alphabetic characters and lowercase
    review = re.sub('[^a-zA-Z]', ' ', str(text))
    review = review.lower()
    review = review.split()
    # Remove stopwords and stem
    review = [ps.stem(word) for word in review if not word in STOPWORDS]
    review = ' '.join(review)
    return review

def load_model():
    """
    Strictly loads model.pkl. Does NOT train.
    """
    global model_pipeline
    
    if os.path.exists(MODEL_FILE):
        print(f"Loading {MODEL_FILE}...")
        try:
            with open(MODEL_FILE, 'rb') as f:
                model_pipeline = pickle.load(f)
            print("Model loaded successfully!")
        except Exception as e:
            print(f"ERROR: Could not load {MODEL_FILE}. File might be corrupted.")
            print(f"Details: {e}")
            model_pipeline = None
    else:
        print("CRITICAL ERROR: 'model.pkl' not found.")
        print("You explicitly disabled training. Please upload 'model.pkl' to your GitHub repo.")
        model_pipeline = None

# Load immediately on import
load_model()

def predict_review(review_text):
    """
    Returns the prediction string.
    """
    if model_pipeline is None:
        return "System Error: Model file missing."

    if not review_text:
        return "Invalid Input"

    try:
        # Preprocess using the helper
        clean_text = preprocess_text(review_text)
        
        # Predict
        # Note: The pipeline usually handles vectorization internally
        prediction = model_pipeline.predict([clean_text])

        # Map result (Adjust based on how your specific model was trained)
        # Assuming 0/1 or 'OR'/'CG' based on your dataset
        res = prediction[0]
        
        if res == 'OR' or res == 0 or res == '0':
            return "Original Review"
        else:
            return "Computer Generated (Fake) Review"
            
    except Exception as e:
        return f"Prediction Error: {str(e)}"