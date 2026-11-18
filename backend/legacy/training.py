import os
import pickle
import pandas as pd
import streamlit as st
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from ml_pipeline import clean_review, encode_labels, create_estimator, feature_matrix

def preprocess_text(text):
    return clean_review(text)

def get_sentiment(text):
    from textblob import TextBlob
    sentiment = TextBlob(str(text)).sentiment
    return sentiment.polarity, sentiment.subjectivity

def training():
    st.title("Model training")
    st.caption("Train and compare review classifiers with a consistent text and sentiment feature pipeline.")
    folder, models_folder = os.path.join("Predicted Data", "Training"), "models"
    os.makedirs(folder, exist_ok=True)
    files = sorted(f for f in os.listdir(folder) if f.lower().endswith(".csv"))
    upload = st.file_uploader("Upload a labeled CSV", type="csv", key="train_upload")
    df = None
    if upload:
        try:
            df = pd.read_csv(upload)
        except Exception as error:
            st.error(f"Could not read CSV: {error}")
            return
    elif files:
        chosen = st.selectbox("Training dataset", files)
        try:
            df = pd.read_csv(os.path.join(folder, chosen))
        except Exception as error:
            st.error(f"Could not read dataset: {error}")
            return
    else:
        st.info("Upload a CSV with text_ and label columns to begin training.")
        return
    if not {"text_", "label"}.issubset(df.columns):
        st.error("CSV must contain text_ and label columns.")
        return
    df = df.dropna(subset=["label"]).copy()
    df["text_"] = df["text_"].fillna("").astype(str)
    df = df[df["text_"].map(clean_review).str.len() > 0]
    st.dataframe(df.head(8), use_container_width=True)
    algorithm = st.selectbox("Classifier", ["Logistic Regression", "Linear SVM", "Multinomial Naive Bayes", "Random Forest"])
    if st.button("Train model", type="primary"):
        try:
            y, _ = encode_labels(df["label"])
            if y.value_counts().min() < 2:
                raise ValueError("At least two examples per class are needed for a stratified evaluation.")
            train_idx, test_idx = train_test_split(range(len(df)), test_size=0.2, random_state=42, stratify=y)
            estimator, scaler = create_estimator(algorithm)
            from sklearn.feature_extraction.text import TfidfVectorizer
            vectorizer = TfidfVectorizer(max_features=10000, ngram_range=(1, 2), min_df=1,
                                         sublinear_tf=True, stop_words="english")
            train_x = feature_matrix(df.iloc[train_idx]["text_"], vectorizer, scaler, fit=True)
            test_x = feature_matrix(df.iloc[test_idx]["text_"], vectorizer, scaler)
            estimator.fit(train_x, y.iloc[train_idx])
            predicted = estimator.predict(test_x)
            accuracy = accuracy_score(y.iloc[test_idx], predicted)
            st.metric("Holdout accuracy", f"{accuracy:.1%}")
            st.dataframe(pd.DataFrame(classification_report(y.iloc[test_idx], predicted,
                         labels=[0,1], target_names=["Fake", "Genuine"], output_dict=True, zero_division=0)).T,
                         use_container_width=True)
            st.write("Confusion matrix (rows are actual, columns are predicted)")
            st.dataframe(pd.DataFrame(confusion_matrix(y.iloc[test_idx], predicted, labels=[0,1]),
                                      index=["Fake", "Genuine"], columns=["Fake", "Genuine"]))
            estimator.fit(feature_matrix(df["text_"], vectorizer, scaler), y)
            bundle = {"estimator": estimator, "vectorizer": vectorizer, "scaler": scaler,
                      "labels": {0: "Fake", 1: "Genuine"}, "algorithm": algorithm}
            os.makedirs(models_folder, exist_ok=True)
            model_path = os.path.join(models_folder, algorithm.lower().replace(" ", "_") + "_bundle.pkl")
            with open(model_path, "wb") as output:
                pickle.dump(bundle, output)
            st.success(f"Saved model bundle to {model_path}")
        except Exception as error:
            st.error(f"Training failed: {error}")
