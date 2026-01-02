import pickle
import os
import re
import nltk
from nltk.corpus import stopwords
from nltk.stem.porter import PorterStemmer

# --- NLTK Setup (Fail-safe) ---
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    try:
        nltk.download('stopwords', quiet=True)
    except:
        pass 

try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    try:
        nltk.download('punkt', quiet=True)
    except:
        pass

MODEL_FILE = 'model.pkl'
model_pipeline = None

def preprocess_text(text):
    """
    Must match exactly how you cleaned text during training.
    """
    ps = PorterStemmer()
    review = re.sub('[^a-zA-Z]', ' ', str(text))
    review = review.lower()
    review = review.split()
    
    try:
        # Try using NLTK stopwords
        STOPWORDS = set(stopwords.words('english'))
        review = [ps.stem(word) for word in review if not word in STOPWORDS]
    except:
        # Fallback if NLTK failed (just stem, don't remove stopwords)
        review = [ps.stem(word) for word in review]
        
    review = ' '.join(review)
    return review

def predict_review(review_text):
    """
    Loads model ON DEMAND (Lazy Loading) to prevent server crash on startup.
    """
    global model_pipeline
    
    # 1. Lazy Load the Model
    if model_pipeline is None:
        if not os.path.exists(MODEL_FILE):
            return "Error: 'model.pkl' not found in repository."
        
        try:
            print(f"Attempting to load {MODEL_FILE}...")
            with open(MODEL_FILE, 'rb') as f:
                model_pipeline = pickle.load(f)
            print("Model loaded successfully!")
        except Exception as e:
            return f"Model Error: {str(e)} (Check scikit-learn version mismatch)"

    # 2. Validate Input
    if not review_text:
        return "Invalid Input"

    # 3. Predict
    try:
        clean_text = preprocess_text(review_text)
        prediction = model_pipeline.predict([clean_text])
        res = prediction[0]
        
        # Check result type (handles both string 'OR'/'CG' and int 0/1)
        if str(res) in ['0', 'OR', 'Original']:
            return "Original Review"
        else:
            return "Computer Generated (Fake) Review"
            
    except Exception as e:
        return f"Prediction Error: {str(e)}"