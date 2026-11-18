"""Consistent review text classification pipeline used for training and inference."""
import re
import numpy as np
import pandas as pd
from scipy.sparse import hstack, csr_matrix
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import MultinomialNB
from sklearn.svm import LinearSVC
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import MinMaxScaler
from textblob import TextBlob

def clean_review(value):
    value = "" if pd.isna(value) else str(value).lower()
    value = re.sub(r"https?://\S+|www\.\S+", " ", value)
    return re.sub(r"[^a-z0-9\s]", " ", value).strip()

def sentiment_features(texts):
    return np.asarray([[TextBlob(text).sentiment.polarity,
                        TextBlob(text).sentiment.subjectivity] for text in texts], dtype=float)

def encode_labels(labels):
    values = pd.Series(labels).astype(str).str.strip()
    mapping = {"CG": 0, "cg": 0, "fake": 0, "Fake": 0, "OR": 1, "or": 1,
               "genuine": 1, "Genuine": 1, "0": 0, "1": 1}
    encoded = values.map(mapping)
    if encoded.isna().any():
        unique = sorted(values.unique())
        if len(unique) != 2:
            raise ValueError("Training labels must contain exactly two classes (CG/OR or 0/1).")
        encoded = values.map({unique[0]: 0, unique[1]: 1})
    return encoded.astype(int), {0: "Fake", 1: "Genuine"}

def feature_matrix(texts, vectorizer, scaler=None, fit=False):
    cleaned = [clean_review(value) for value in texts]
    tfidf = vectorizer.fit_transform(cleaned) if fit else vectorizer.transform(cleaned)
    sentiments = sentiment_features(cleaned)
    if scaler is not None:
        sentiments = scaler.fit_transform(sentiments) if fit else scaler.transform(sentiments)
    return hstack([tfidf, csr_matrix(sentiments)], format="csr")

def create_estimator(name):
    if name == "Multinomial Naive Bayes":
        return MultinomialNB(alpha=0.5), MinMaxScaler(clip=True)
    if name == "Linear SVM":
        return LinearSVC(class_weight="balanced", random_state=42), None
    if name == "Random Forest":
        return RandomForestClassifier(n_estimators=250, min_samples_leaf=2,
                                      class_weight="balanced", random_state=42, n_jobs=-1), None
    return LogisticRegression(max_iter=2000, class_weight="balanced", random_state=42), None

def train_bundle(texts, labels, name):
    y, label_names = encode_labels(labels)
    vectorizer = TfidfVectorizer(max_features=10000, ngram_range=(1, 2),
                                 min_df=1, sublinear_tf=True, stop_words="english")
    estimator, scaler = create_estimator(name)
    X = feature_matrix(texts, vectorizer, scaler, fit=True)
    estimator.fit(X, y)
    return {"estimator": estimator, "vectorizer": vectorizer, "scaler": scaler,
            "labels": label_names, "algorithm": name}

def predict_bundle(bundle, texts):
    X = feature_matrix(texts, bundle["vectorizer"], bundle["scaler"])
    model = bundle["estimator"]
    predictions = model.predict(X)
    confidence = (model.predict_proba(X).max(axis=1) if hasattr(model, "predict_proba")
                  else 1 / (1 + np.exp(-np.abs(model.decision_function(X)))))
    return predictions, confidence
