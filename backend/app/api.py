from __future__ import annotations
import io, json, os, pickle, tempfile
from typing import Any
import pandas as pd
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from app.ml_pipeline import clean_review, create_estimator, encode_labels, feature_matrix, predict_bundle
from app.mapreduce_jobs import mapper, reducer

app = FastAPI(title="Verity Review Intelligence API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
MODELS = os.path.join("data", "models")

@app.get("/api/health")
def health():
    os.makedirs(MODELS, exist_ok=True)
    bundles = sorted(name for name in os.listdir(MODELS) if name.endswith("_bundle.pkl"))
    return {"status": "ok", "models": bundles}

async def read_csv(file: UploadFile) -> pd.DataFrame:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(400, "Please upload a CSV file.")
    try:
        data = pd.read_csv(io.BytesIO(await file.read()))
    except Exception as error:
        raise HTTPException(400, f"Could not parse CSV: {error}")
    if data.empty:
        raise HTTPException(400, "The CSV has no rows.")
    return data

@app.post("/api/train")
async def train(file: UploadFile = File(...), algorithm: str = Form("Logistic Regression")):
    data = await read_csv(file)
    if not {"text_", "label"}.issubset(data.columns):
        raise HTTPException(400, "Training CSV needs text_ and label columns.")
    data = data.dropna(subset=["label"]).copy()
    data["text_"] = data["text_"].fillna("").astype(str)
    data = data[data["text_"].map(clean_review).str.len() > 0]
    try:
        labels, _ = encode_labels(data["label"])
    except ValueError as error:
        raise HTTPException(400, str(error))
    if labels.value_counts().min() < 2:
        raise HTTPException(400, "Include at least two examples for each class.")
    if algorithm not in {"Logistic Regression", "Linear SVM", "Multinomial Naive Bayes", "Random Forest"}:
        raise HTTPException(400, "Choose a supported classifier.")
    try:
        train_idx, test_idx = train_test_split(range(len(data)), test_size=.2, random_state=42, stratify=labels)
        vectorizer = TfidfVectorizer(max_features=10000, ngram_range=(1, 2), min_df=1,
                                     sublinear_tf=True, stop_words="english")
        estimator, scaler = create_estimator(algorithm)
        train_x = feature_matrix(data.iloc[train_idx]["text_"], vectorizer, scaler, fit=True)
        test_x = feature_matrix(data.iloc[test_idx]["text_"], vectorizer, scaler)
        estimator.fit(train_x, labels.iloc[train_idx])
        prediction = estimator.predict(test_x)
        accuracy = accuracy_score(labels.iloc[test_idx], prediction)
        estimator.fit(feature_matrix(data["text_"], vectorizer, scaler), labels)
        bundle = {"estimator": estimator, "vectorizer": vectorizer, "scaler": scaler,
                  "labels": {0: "Likely fake", 1: "Genuine"}, "algorithm": algorithm}
        os.makedirs(MODELS, exist_ok=True)
        filename = algorithm.lower().replace(" ", "_") + "_bundle.pkl"
        with open(os.path.join(MODELS, filename), "wb") as output:
            pickle.dump(bundle, output)
        report = classification_report(labels.iloc[test_idx], prediction, labels=[0,1],
             target_names=["Likely fake", "Genuine"], output_dict=True, zero_division=0)
        return {"message": f"Model trained · {accuracy:.1%} holdout accuracy", "model": filename,
                "accuracy": accuracy, "report": report}
    except Exception as error:
        raise HTTPException(400, f"Training failed: {error}")

@app.post("/api/predict")
async def predict(file: UploadFile = File(...)):
    data = await read_csv(file)
    column = next((key for key in ["Review", "review", "text", "text_", "review_text"] if key in data.columns), None)
    if not column:
        raise HTTPException(400, "CSV needs a review column such as Review or text_.")
    available = sorted(name for name in os.listdir(MODELS) if name.endswith("_bundle.pkl")) if os.path.isdir(MODELS) else []
    if not available:
        raise HTTPException(400, "Train a model before analyzing uploaded reviews.")
    with open(os.path.join(MODELS, available[0]), "rb") as source:
        bundle = pickle.load(source)
    texts = data[column].fillna("").astype(str)
    predictions, confidence = predict_bundle(bundle, texts)
    rows = data.to_dict(orient="records")
    for row, label, score in zip(rows, predictions, confidence):
        row["predicted_label"] = bundle["labels"].get(int(label), str(label))
        row["confidence"] = round(float(score), 4)
    os.makedirs(os.path.join("data", "predictions"), exist_ok=True)
    pd.DataFrame(rows).to_csv(os.path.join("data", "predictions", "predicted_data.csv"), index=False)
    return {"rows": rows, "message": f"Analyzed {len(rows)} reviews and saved the results."}

@app.post("/api/mapreduce")
def mapreduce(payload: dict[str, Any]):
    rows = payload.get("rows", [])
    if not isinstance(rows, list) or not rows:
        raise HTTPException(400, "Analyze or load review rows before running MapReduce.")
    partitions = max(1, min(8, (len(rows) + 99) // 100))
    chunk_size = max(1, (len(rows) + partitions - 1) // partitions)
    with tempfile.TemporaryDirectory() as directory:
        source = os.path.join(directory, "input.jsonl")
        mapped = os.path.join(directory, "mapped.tsv")
        reduced = os.path.join(directory, "reduced.tsv")
        with open(mapped, "w", encoding="utf-8") as all_mapped:
            for index in range(0, len(rows), chunk_size):
                chunk = rows[index:index + chunk_size]
                with open(source, "w", encoding="utf-8") as file:
                    for row in chunk:
                        file.write(json.dumps(row, ensure_ascii=False) + "\n")
                with open(source, encoding="utf-8") as input_file:
                    mapper(input_file, all_mapped)
        with open(mapped, encoding="utf-8") as input_file, open(reduced, "w", encoding="utf-8") as output:
            reducer(sorted(input_file), output)
        counts = []
        with open(reduced, encoding="utf-8") as file:
            for line in file:
                key, count = line.rstrip("\n").split("\t", 1)
                counts.append([key, int(count)])
    return {"results": counts, "records": len(rows), "partitions": (len(rows) + chunk_size - 1) // chunk_size}

@app.post("/api/scrape")
def scrape(payload: dict[str, Any]):
    from app.csvgencode import get_reviews
    url = str(payload.get("url", "")).strip()
    pages = int(payload.get("pages", 1))
    if not 1 <= pages <= 10:
        raise HTTPException(400, "Choose between 1 and 10 pages.")
    if not url.startswith(("https://www.flipkart.com/", "https://flipkart.com/")):
        raise HTTPException(400, "Enter a valid Flipkart product URL.")
    reviews = get_reviews(1, pages, url)
    if not reviews:
        raise HTTPException(502, "No reviews were returned. The product page may block scraping or contain no reviews.")
    rows = [{"Rating": rating, "Review": text, "Username": user, "Date": date}
            for rating, text, user, date in reviews]
    os.makedirs(os.path.join("data", "generated-reviews"), exist_ok=True)
    pd.DataFrame(rows).to_csv(os.path.join("data", "generated-reviews", "flipkart_reviews.csv"), index=False)
    return {"rows": rows, "message": f"Collected {len(rows)} reviews."}
