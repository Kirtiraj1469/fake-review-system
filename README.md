# Fake Review Detection · Big Data Essentials

The existing Streamlit application remains available at the repository root entry point `main.py`. The optional Docker stack adds real HDFS, YARN MapReduce, and Spark MLlib services. The React dashboard from the earlier revision remains under `frontend/` and runs independently.

## Repository layout

- `main.py` and `backend/legacy/` — existing Streamlit UI, scraping, training, and testing pages, plus Big Data dashboard
- `backend/app/` — shared preprocessing, scraper support, FastAPI routes, and distributed job code
- `backend/app/bigdata/jobs/` — schema-aware CSV-to-JSONL conversion, Hadoop Streaming mapper/reducer, and Spark MLlib trainer
- `docker-compose.yml` and `docker/hadoop/` — HDFS, YARN, and Spark containers with pinned Hadoop/Spark versions
- `scripts/bigdata.sh` — idempotent start, upload, MapReduce, Spark, status, and shutdown commands
- `backend/data/` — runtime data and model directories; local datasets and outputs are git-ignored
- `frontend/` — optional React UI

## Start the existing Streamlit system

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements.txt
streamlit run main.py
```

## Start real Hadoop, HDFS, YARN, and Spark in Docker

Docker Desktop must be running. See [MAC_SETUP.md](MAC_SETUP.md) for first-run, verification, dataset upload, and troubleshooting details.

```bash
./scripts/bigdata.sh start
./scripts/bigdata.sh upload /absolute/path/to/reviews.csv
./scripts/bigdata.sh mapreduce
./scripts/bigdata.sh spark
```

The uploader handles CSV quotes and missing values, requires review text and labels, then converts valid rows to JSON Lines. Hadoop Streaming counts category, rating, and label values in an actual YARN MapReduce job. Spark MLlib reads the resulting JSON Lines from HDFS, trains Logistic Regression, evaluates the held-out set, and writes a model and metrics back to HDFS.

The Streamlit navigation includes **Hadoop / Spark**, which reads live HDFS and YARN endpoints and actual output files. It does not fabricate results. The original scikit-learn pages remain independent.

Pinned container versions are Hadoop 3.3.6 and Spark 3.5.3, running on a multi-architecture Eclipse Temurin 11 image. The setup is a single-node learning cluster with HDFS replication one. Hadoop’s optional native libraries may use Java fallbacks on ARM64.

## Key URLs while the stack is running

- HDFS NameNode: `http://localhost:9870`
- YARN ResourceManager: `http://localhost:8088`
- YARN NodeManager: `http://localhost:8042`

## Status and limitations

The course `reviews.csv` was not present in the connected GitHub tree during implementation, so its shape and class balance have not been verified. It is not committed to the repository. See [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md) for exactly what was checked and what still requires a run on the Mac Docker Desktop ARM64 engine.
