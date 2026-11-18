# Verity · Fake Review Intelligence

A review analysis platform with a React dashboard, FastAPI service, machine-learning training and inference, Flipkart review collection, and local/Hadoop Streaming MapReduce aggregation.

## Project layout

- `frontend/` React + Vite dashboard
- `backend/app/api.py` FastAPI routes for scraping, training, predictions, and MapReduce
- `backend/app/ml_pipeline.py` shared preprocessing and model feature pipeline
- `backend/app/mapreduce_jobs.py` Hadoop Streaming mapper and reducer
- `backend/data/` runtime datasets and saved model bundles

## Start locally on macOS or Linux

Use two terminals from the repository root.

Terminal 1 starts the API:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn app.api:app --host 0.0.0.0 --port 5001
```

Terminal 2 starts the dashboard:

```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```

Open the Vite URL, usually `http://localhost:5173`. The API documentation is at `http://localhost:5001/docs`.

## Workflow

1. Open **Models** and upload a labeled CSV containing `text_` and `label`. Labels `CG`/`0` mean likely fake. `OR`/`1` mean genuine. Select Logistic Regression, Linear SVM, Multinomial Naive Bayes, or Random Forest.
2. Open **Scrape reviews** to collect Flipkart feedback, or open **Review analysis** and upload a review CSV.
3. Open **MapReduce** to run partitioned local mapper/reducer aggregation. The Hadoop Streaming command is visible in the page and in `backend/README.md`.

Training saves model bundles under `backend/data/models/`. Review predictions are saved under `backend/data/predictions/`. These runtime files are excluded from Git.

## Hadoop Streaming

The local mapper/reducer do not require a Hadoop cluster. To run on Hadoop, configure Hadoop and HDFS, convert your review CSV to JSON Lines, then follow the command in `backend/README.md`. Hadoop worker nodes need Python and the `mapreduce_jobs.py` script.

## Notes

Flipkart may rate-limit or change its page markup, so scraping depends on current access and page structure. Existing legacy Streamlit files are retained in `backend/legacy/` for reference; the active interface is the React dashboard.
