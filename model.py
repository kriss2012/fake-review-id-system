import pickle
import os
import re
import sys
import logging

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# NLTK Setup
import nltk
from nltk.corpus import stopwords
from nltk.stem.porter import PorterStemmer

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords', quiet=True)
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)

MODEL_FILE = 'model.pkl'
model_pipeline = None

def preprocess_text(text):
    """
    Cleaning logic matching training data
    """
    ps = PorterStemmer()
    review = re.sub('[^a-zA-Z]', ' ', str(text))
    review = review.lower()
    review = review.split()
    
    try:
        STOPWORDS = set(stopwords.words('english'))
        review = [ps.stem(word) for word in review if not word in STOPWORDS]
    except:
        review = [ps.stem(word) for word in review]
        
    review = ' '.join(review)
    return review

def load_model_safe():
    global model_pipeline
    if model_pipeline is not None:
        return True, "Loaded"

    if not os.path.exists(MODEL_FILE):
        return False, "model.pkl not found in repository"

    try:
        with open(MODEL_FILE, 'rb') as f:
            model_pipeline = pickle.load(f)
        return True, "Loaded"
    except Exception as e:
        logger.error(f"Model Load Failed: {e}")
        return False, str(e)

def predict_review(review_text):
    """
    Safe prediction function
    """
    # 1. Try to load model
    success, message = load_model_safe()
    
    if not success:
        return f"System Error: Could not load AI Model. Details: {message}"

    if not review_text:
        return "Invalid Input"

    # 2. Predict
    try:
        clean_text = preprocess_text(review_text)
        prediction = model_pipeline.predict([clean_text])
        res = prediction[0]
        
        # Handle different output types from the model
        if str(res) in ['0', 'OR', 'Original', 0]:
            return "Original Review"
        else:
            return "Computer Generated (Fake) Review"
            
    except Exception as e:
        logger.error(f"Prediction Error: {e}")
        return f"Prediction Error: {str(e)}"