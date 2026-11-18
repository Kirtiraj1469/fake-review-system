# Mac Setup · Apple Silicon

This starts the original Streamlit application and an optional single-node Docker Hadoop/YARN/Spark cluster. The Hadoop and Spark jobs run inside Docker and on YARN. The Docker Engine must be available on the Mac.

## 1. Get the implementation branch

```bash
git clone --branch feat/hadoop-spark-integration https://github.com/Kirtiraj1469/fake-review-system.git
cd fake-review-system
```

If you already cloned the repository, use:

```bash
git fetch origin
git switch feat/hadoop-spark-integration
git pull --ff-only
```

## 2. Start and verify Docker Hadoop

Open Docker Desktop and wait until it reports that the engine is running. From the repository root:

```bash
docker version
docker compose version
./scripts/bigdata.sh start
./scripts/bigdata.sh status
```

The Docker image is built from the multi-architecture Eclipse Temurin 11 JRE image. Hadoop 3.3.6 and Spark 3.5.3 are downloaded at pinned versions during build. The setup contains one HDFS NameNode, one DataNode, a YARN ResourceManager, one NodeManager, and a Spark client. HDFS replication is one because this is a single-node demo cluster.

Check the web consoles in a browser:

- HDFS NameNode at `http://localhost:9870`
- YARN ResourceManager at `http://localhost:8088`
- YARN NodeManager at `http://localhost:8042`

Verify HDFS and YARN from the terminal:

```bash
docker compose ps
docker compose exec spark-client hdfs dfsadmin -report
docker compose exec spark-client yarn node -list -all
docker compose exec spark-client hdfs dfs -ls /
```

## 3. Put the labeled dataset in HDFS

The repository does not contain the course dataset. Copy your real `reviews.csv` to the Mac and run this command with its actual path:

```bash
./scripts/bigdata.sh upload /absolute/path/to/reviews.csv
```

The upload step reads CSV with Python's quoted-field-aware CSV parser, checks for `label` and review text (`text_`, `review`, `review_text`, or `text`), skips rows with empty text or labels, writes JSON Lines, and uploads it to `/fake-review-detection/input/reviews.jsonl` in HDFS. `category` and `rating` are optional and show `(missing)` in aggregation output when absent.

Verify the file and size:

```bash
docker compose exec spark-client hdfs dfs -ls -h /fake-review-detection/input/reviews.jsonl
docker compose exec spark-client hdfs dfs -count /fake-review-detection/input/reviews.jsonl
docker compose exec spark-client hdfs dfs -cat /fake-review-detection/input/reviews.jsonl | head -n 2
```

## 4. Submit real Hadoop MapReduce through YARN

```bash
./scripts/bigdata.sh mapreduce
```

The command removes only its previous MapReduce output directory, submits Hadoop Streaming to YARN, prints the YARN application list, and reads the actual result from HDFS. Verify the job is recorded in YARN:

```bash
docker compose exec spark-client yarn application -list -appStates ALL
docker compose exec spark-client hdfs dfs -cat /fake-review-detection/mapreduce/category-rating-label-counts/part-*
```

The job counts rows by category, rating, and original label. It processes JSON Lines created from the CSV so quoted commas in reviews do not corrupt fields. No pandas aggregation is used for this job.

## 5. Train and evaluate Spark MLlib on YARN

```bash
./scripts/bigdata.sh spark
```

This submits Spark with `--master yarn --deploy-mode client`, one 512 MiB executor and a 512 MiB driver. The PySpark MLlib pipeline uses regex tokenization, English stop-word removal, HashingTF, IDF, and Logistic Regression. It uses a seeded 80/20 split and saves accuracy, weighted precision, weighted recall, F1, class counts, confusion-matrix counts, actual master/deploy mode, and the fitted pipeline model to HDFS.

Read metrics and check the model output:

```bash
docker compose exec spark-client hdfs dfs -cat /fake-review-detection/spark/logistic-regression/metrics/part-*
docker compose exec spark-client hdfs dfs -ls /fake-review-detection/spark/logistic-regression/model
docker compose exec spark-client yarn application -list -appStates ALL
```

The model is trained by Spark MLlib. The existing scikit-learn training and testing pages remain separate and do not silently use Spark predictions.

## 6. Run Streamlit and the existing workflow

In a second terminal from the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements.txt
streamlit run main.py
```

Use the existing Scrape Reviews, Training, and Testing pages as before. The new **Hadoop / Spark** page reads live NameNode, HDFS, and ResourceManager status, YARN applications, actual HDFS MapReduce output, and actual Spark metrics. The streamlit process connects to the locally published Docker ports, not to a Codex Docker daemon.

The React frontend remains available separately:

```bash
cd frontend
npm install
npm run dev
```

## 7. Full demonstration and shutdown

After Docker is running and you have the dataset path:

```bash
./scripts/bigdata.sh all /absolute/path/to/reviews.csv
```

Stop containers and preserve HDFS data:

```bash
./scripts/bigdata.sh stop
```

To intentionally erase HDFS and YARN local data, use `docker compose down -v`. That command is destructive to the Docker volumes.

## Troubleshooting

- **Docker daemon unavailable:** Start Docker Desktop, wait for its engine, then retry `./scripts/bigdata.sh start`.
- **Apple Silicon image platform:** The base Temurin tag has an ARM64 manifest. Check the built image using `docker image inspect fake-review-detection-namenode --format '{{.Os}}/{{.Architecture}}'` after build. Hadoop's optional native libraries in the Apache x86-built archive may fall back to Java implementations on ARM64. A successful Mac ARM64 container build and cluster run still must be confirmed on the target Mac.
- **Build takes a while:** The first build downloads pinned Hadoop and Spark archives. Later starts reuse the image.
- **Port conflict:** Stop the process using `9870`, `9000`, `9864`, `8088`, or `8042`, or change the host-side port before the colon in `docker-compose.yml`. If changing `9870` or `8088`, update the dashboard URLs in `backend/legacy/bigdata_dashboard.py`.
- **Resource pressure:** Keep one DataNode and one NodeManager. The compose memory limits total about 5.5 GiB. Spark is intentionally limited to one small executor. Quit other large Docker workloads if Docker reports allocation failures.
- **Services fail readiness:** Run `docker compose ps` and `docker compose logs --tail=100 namenode datanode resourcemanager nodemanager`. The start script prints these logs after timeout.
- **YARN job fails:** Check `docker compose logs nodemanager resourcemanager` and `docker compose exec spark-client yarn application -list -appStates ALL`.
- **Dataset schema rejected:** Inspect the header and make sure it contains a label field plus review text under one of the accepted names. The actual course CSV was absent during implementation, so its schema must be checked by running the upload command.
- **Rerun outputs:** MapReduce and Spark scripts remove only their own previous HDFS output directories before resubmission. Stop preserves all volumes.
