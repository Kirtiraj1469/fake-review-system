import os
import pickle
import pandas as pd
import streamlit as st
from ml_pipeline import predict_bundle

def test_model():
    st.title("Review analysis")
    st.caption("Score reviews with a saved model, then inspect and export the predictions.")
    models_dir = "models"
    models = sorted(name for name in os.listdir(models_dir) if name.endswith("_bundle.pkl")) if os.path.isdir(models_dir) else []
    if not models:
        st.info("Train a model first. Saved model bundles will appear here.")
        return
    selected = st.selectbox("Model", models)
    upload = st.file_uploader("Upload reviews CSV", type="csv", key="test_upload")
    default_path = os.path.join("Generated reviews", "flipkart_reviews.csv")
    df = None
    if upload:
        try:
            df = pd.read_csv(upload)
        except Exception as error:
            st.error(f"Could not read CSV: {error}")
            return
    elif os.path.exists(default_path):
        df = pd.read_csv(default_path)
        st.caption(f"Using {default_path}")
    else:
        st.info("Upload a CSV or scrape reviews first.")
        return
    column = next((name for name in ["Review", "review", "text", "text_", "review_text"] if name in df.columns), None)
    if column is None:
        st.error("CSV needs a review text column such as Review or text_.")
        return
    if st.button("Analyze reviews", type="primary"):
        try:
            with open(os.path.join(models_dir, selected), "rb") as source:
                bundle = pickle.load(source)
            valid = df[column].fillna("").astype(str)
            predictions, confidence = predict_bundle(bundle, valid)
            result = df.copy()
            result["predicted_label"] = [bundle["labels"].get(int(label), str(label)) for label in predictions]
            result["confidence"] = confidence
            os.makedirs("Predicted Data", exist_ok=True)
            result.to_csv(os.path.join("Predicted Data", "predicted_data.csv"), index=False)
            fake = int((predictions == 0).sum())
            genuine = int((predictions == 1).sum())
            one, two, three = st.columns(3)
            one.metric("Reviews analyzed", len(result))
            two.metric("Likely fake", fake)
            three.metric("Likely genuine", genuine)
            st.dataframe(result, use_container_width=True)
            st.download_button("Download predictions", result.to_csv(index=False), "review_predictions.csv", "text/csv")
        except Exception as error:
            st.error(f"Could not analyze reviews: {error}")
