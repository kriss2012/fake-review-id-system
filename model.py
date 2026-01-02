import pandas as pd
import numpy as np
import pickle
import os
import nltk
from nltk.stem.porter import PorterStemmer
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline

# Ensure NLTK data is downloaded
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')

from nltk.corpus import stopwords

STOPWORDS = set(stopwords.words('english'))
MODEL_FILE = 'model.pkl'

def preprocess_text(text):
    ps = PorterStemmer()
    # Remove non-alphabetic characters and lowercase
    review = re.sub('[^a-zA-Z]', ' ', text)
    review = review.lower()
    review = review.split()
    # Remove stopwords and stem
    review = [ps.stem(word) for word in review if not word in STOPWORDS]
    review = ' '.join(review)
    return review

def load_or_train_model():
    """Loads model if available, else trains it."""
    if os.path.exists(MODEL_FILE):
        print("Loading existing model...")
        with open(MODEL_FILE, 'rb') as f:
            pipeline = pickle.load(f)
    else:
        print("Training new model...")
        # Load dataset
        if not os.path.exists('fake_review_dataset.csv'):
             raise FileNotFoundError("fake_review_dataset.csv not found. Please upload the dataset.")
             
        df = pd.read_csv('fake_review_dataset.csv')
        
        # Preprocess dataset
        # Using a temporary corpus list for TFIDF fit
        corpus = df['text_'].apply(preprocess_text).tolist()
        y = df['label']

        # Create a pipeline with TF-IDF and Naive Bayes
        pipeline = Pipeline([
            ('tfidf', TfidfVectorizer(max_features=5000, ngram_range=(1,3))),
            ('clf', MultinomialNB())
        ])

        # Train the pipeline
        pipeline.fit(corpus, y)

        # Save the trained pipeline
        with open(MODEL_FILE, 'wb') as f:
            pickle.dump(pipeline, f)
            print("Model trained and saved.")
            
    return pipeline

# Initialize model once when app starts
classifier_pipeline = load_or_train_model()

def predict_review(review_text):
    """
    Predicts whether a given review is Real or Fake.
    """
    if not review_text or not isinstance(review_text, str):
         return "Invalid Input"
         
    preprocessed_review = preprocess_text(review_text)
    # Pipeline handles vectorization automatically
    prediction = classifier_pipeline.predict([preprocessed_review])

    if prediction[0] == 'OR':
        return "Original Review"
    else:
        return "Computer Generated (Fake) Review"