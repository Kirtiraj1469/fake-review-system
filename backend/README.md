# Backend and Hadoop Streaming

From this directory, install `requirements.txt` and start the API with `python -m uvicorn app.api:app --host 0.0.0.0 --port 5001`.

The API implements the local multi-partition MapReduce flow. For a configured Hadoop cluster, prepare JSON Lines input and run from `backend/app`:

```bash
python - <<'PY'
import pandas as pd
pd.read_csv("data/predictions/predicted_data.csv").to_json("reviews.jsonl", orient="records", lines=True, force_ascii=False)
PY
hdfs dfs -mkdir -p /reviews/input
hdfs dfs -put -f reviews.jsonl /reviews/input/
hadoop jar "$HADOOP_HOME"/share/hadoop/tools/lib/hadoop-streaming-*.jar \
  -input /reviews/input -output /reviews/output \
  -mapper 'python3 mapreduce_jobs.py mapper' \
  -reducer 'python3 mapreduce_jobs.py reducer' \
  -files mapreduce_jobs.py
hdfs dfs -cat /reviews/output/part-*
```

Delete `/reviews/output` in HDFS before rerunning the same job because Hadoop requires a new output path.
