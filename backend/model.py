from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import SVC
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score
import pandas as pd
from nltk.corpus import stopwords
import nltk
import pickle
nltk.download('stopwords')

def load_data():
    df = pd.read_csv('fake_review_dataset.csv')
    df.dropna(inplace=True)
    return df['review_text'], df['label']

def preprocess(texts):
    import re
    stop_words = set(stopwords.words('english'))
    cleaned = []
    for t in texts:
        t = re.sub(r'[^A-Za-z ]', '', t.lower())
        t = " ".join([w for w in t.split() if w not in stop_words])
        cleaned.append(t)
    return cleaned

def train_model():
    X, y = load_data()
    X = preprocess(X)
    pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(ngram_range=(1,2))),
        ("svc", SVC(probability=True, class_weight="balanced"))
    ])

    # Hyperparameter tuning
    params = {'svc__C': [1, 10, 100], 'svc__kernel': ['linear', 'rbf']}
    search = GridSearchCV(pipeline, params, cv=5)
    search.fit(X, y)

    print(f"Best params: {search.best_params_}")
    print(f"Model accuracy: {search.best_score_*100:.2f}%")

    with open("model.pkl", "wb") as f:
        pickle.dump(search.best_estimator_, f)

if __name__ == '__main__':
    train_model()
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import SVC
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score
import pandas as pd
from nltk.corpus import stopwords
import nltk
import pickle
import re

nltk.download('stopwords')

def load_data():
    # Reads dataset.csv and returns texts and labels
    df = pd.read_csv('fake_review_dataset.csv')
    df.dropna(inplace=True)
    return df['review_text'], df['label']

def preprocess(texts):
    stop_words = set(stopwords.words('english'))
    cleaned = []
    for t in texts:
        text = re.sub(r'[^A-Za-z ]+', ' ', str(t)).lower()
        text = " ".join([w for w in text.split() if w not in stop_words])
        cleaned.append(text)
    return cleaned

def train_model():
    X, y = load_data()
    X_clean = preprocess(X)

    pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(ngram_range=(1,2))),
        ("svc", SVC(probability=True, class_weight="balanced"))
    ])

    # Hyperparameter tuning with GridSearchCV
    params = {'svc__C': [1, 10, 100], 'svc__kernel': ['linear', 'rbf']}
    search = GridSearchCV(pipeline, params, cv=5, n_jobs=-1)
    search.fit(X_clean, y)

    print(f"Best params: {search.best_params_}")
    print(f"Best cross-val accuracy: {search.best_score_ * 100:.2f}%")

    # Optional: also show test accuracy for reference
    X_train, X_test, y_train, y_test = train_test_split(X_clean, y, test_size=0.2, random_state=42)
    best_model = search.best_estimator_
    best_model.fit(X_train, y_train)
    y_pred = best_model.predict(X_test)
    print(f"Test accuracy: {accuracy_score(y_test, y_pred) * 100:.2f}%")

    # Save the best model for API use
    with open("model.pkl", "wb") as f:
        pickle.dump(best_model, f)

def load_model():
    # For inference in app.py
    with open("model.pkl", "rb") as f:
        return pickle.load(f)

def fake_review_detector(text):
    # Used in Flask app: returns ('Fake Review', '...') or ('Genuine Review', '...')
    model = load_model()
    # Preprocess input the same as training
    stop_words = set(stopwords.words('english'))
    text_clean = re.sub(r'[^A-Za-z ]+', ' ', str(text)).lower()
    text_clean = " ".join([w for w in text_clean.split() if w not in stop_words])
    pred = model.predict([text_clean])[0]
    prob = model.predict_proba([text_clean])[0][int(pred)]
    label = "Fake Review" if pred == 1 else "Genuine Review"
    reason = f"Model confidence: {prob:.2%}"
    return label, reason

if __name__ == '__main__':
    train_model()
#.\krish\Scripts\Activate.ps1 to activate the venv
#pip install -r backend/requirements.txt
