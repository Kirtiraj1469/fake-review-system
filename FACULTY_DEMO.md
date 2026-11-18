# Faculty Demo · Five Minutes

## Before the review

Run these once on the Mac using the exact dataset supplied for the course:

```bash
./scripts/bigdata.sh start
./scripts/bigdata.sh upload /absolute/path/to/reviews.csv
./scripts/bigdata.sh mapreduce
./scripts/bigdata.sh spark
streamlit run main.py
```

Do not present expected output as run output. Capture actual outputs from the current run only. If a job fails, show its real YARN state and logs rather than quoting a sample success.

## Presentation script

### 0:00–0:45 · Architecture

Show the repository structure and `docker-compose.yml`. Explain that the Streamlit app remains the existing interface. Docker provides a single-node HDFS and YARN environment. Spark MLlib submits a distributed job to YARN, rather than using Spark local mode.

### 0:45–1:30 · HDFS

Open `http://localhost:9870` and show the NameNode. In Terminal run:

```bash
docker compose exec spark-client hdfs dfs -ls -h /fake-review-detection/input
docker compose exec spark-client hdfs dfs -count /fake-review-detection/input/reviews.jsonl
```

Explain that the CSV is parsed with the standard quoted-field-aware Python CSV reader, converted to JSON Lines, and stored in HDFS. This preserves commas inside quoted review text.

### 1:30–2:30 · MapReduce on YARN

Open `http://localhost:8088` and show the actual application record. In Terminal run:

```bash
docker compose exec spark-client yarn application -list -appStates ALL
docker compose exec spark-client hdfs dfs -cat /fake-review-detection/mapreduce/category-rating-label-counts/part-*
```

Explain that the Hadoop Streaming mapper emits counts by category, rating, and source label. YARN runs the mapper and reducer containers, and the reducer output is persisted in HDFS. Point out the actual application ID and terminal state from this run.

### 2:30–3:45 · Spark MLlib

Run or show the actual recent job in the YARN console. Display the saved metrics:

```bash
docker compose exec spark-client hdfs dfs -cat /fake-review-detection/spark/logistic-regression/metrics/part-*
```

Explain the Spark ML pipeline: tokenization, stop-word filtering, HashingTF, IDF, Logistic Regression, seeded train/test split, and held-out evaluation. State the master and deploy mode printed in the metrics. Do not describe scikit-learn as Spark.

### 3:45–4:45 · Streamlit dashboard

Open **Hadoop / Spark** in Streamlit. Show live HDFS input size, current YARN applications, MapReduce output, and Spark metrics. Then briefly show that the existing Scrape Reviews, Training, and Testing sections remain available. Explain that local scikit-learn model predictions remain separate from the Spark training model.

### 4:45–5:00 · Close

Summarize that HDFS stores the dataset and results, YARN schedules both actual jobs, Hadoop Streaming performs distributed counts, and Spark MLlib trains/evaluates a separate distributed classifier.

## Screenshots to capture after a successful Mac run

1. NameNode browser overview with the cluster started.
2. HDFS file listing showing the JSONL input and file size.
3. YARN overview showing the completed MapReduce and Spark application IDs.
4. HDFS MapReduce `part-*` output.
5. HDFS Spark metrics JSON with actual values and mode.
6. Streamlit **Hadoop / Spark** page displaying those same live outputs.

Only capture these if the corresponding component actually ran on the Mac. The screenshots are not included as pre-made evidence.
