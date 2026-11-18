#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
DC=(docker compose -f docker-compose.yml)
DATA_DIR="$ROOT/backend/data/training"
INPUT_DIR=/fake-review-detection/input
OUTPUT_DIR=/fake-review-detection/mapreduce/category-rating-label-counts
SPARK_OUTPUT=/fake-review-detection/spark/logistic-regression

wait_for_cluster() {
  echo "Waiting for NameNode, DataNode, and YARN NodeManager..."
  for attempt in $(seq 1 60); do
    if "${DC[@]}" exec -T spark-client hdfs dfsadmin -safemode get 2>/dev/null | grep -q "OFF" \
      && "${DC[@]}" exec -T spark-client hdfs dfsadmin -report 2>/dev/null | grep -q "Live datanodes (1)" \
      && curl -fsS http://localhost:8088/ws/v1/cluster/info 2>/dev/null | grep -q '"state":"STARTED"' \
      && curl -fsS 'http://localhost:8088/ws/v1/cluster/nodes?states=RUNNING' 2>/dev/null \
        | python3 -c 'import json,sys; nodes=json.load(sys.stdin).get("nodes",{}).get("node",[]); nodes=nodes if isinstance(nodes,list) else [nodes]; sys.exit(0 if any(n.get("state")=="RUNNING" for n in nodes) else 1)'; then
      echo "HDFS and YARN are ready."
      "${DC[@]}" exec -T spark-client hdfs dfs -mkdir -p "$INPUT_DIR"
      return 0
    fi
    sleep 5
  done
  echo "Cluster did not become ready. Inspect: docker compose -f docker-compose.yml ps" >&2
  "${DC[@]}" logs --tail=100 namenode datanode resourcemanager nodemanager >&2 || true
  return 1
}

case "${1:-help}" in
  start)
    "${DC[@]}" up -d --build
    wait_for_cluster
    "${DC[@]}" ps
    ;;
  stop)
    "${DC[@]}" down
    ;;
  reset)
    echo "This removes the Hadoop HDFS/YARN named volumes and all data they contain. Use 'stop' to preserve data." >&2
    exit 2
    ;;
  status)
    "${DC[@]}" ps
    curl -fsS http://localhost:8088/ws/v1/cluster/info || true
    echo
    "${DC[@]}" exec -T spark-client hdfs dfsadmin -report || true
    ;;
  upload)
    [[ $# -eq 2 ]] || { echo "Usage: $0 upload /path/to/reviews.csv" >&2; exit 2; }
    [[ -f "$2" ]] || { echo "CSV not found: $2" >&2; exit 2; }
    wait_for_cluster
    mkdir -p "$DATA_DIR"
    cp "$2" "$DATA_DIR/reviews.csv"
    "${DC[@]}" exec -T spark-client python3 /opt/jobs/prepare_reviews.py \
      /workspace/data/training/reviews.csv /tmp/reviews.jsonl
    "${DC[@]}" exec -T spark-client hdfs dfs -mkdir -p "$INPUT_DIR"
    "${DC[@]}" exec -T spark-client hdfs dfs -put -f /tmp/reviews.jsonl "$INPUT_DIR/reviews.jsonl"
    echo "HDFS input file:"
    "${DC[@]}" exec -T spark-client hdfs dfs -ls -h "$INPUT_DIR/reviews.jsonl"
    "${DC[@]}" exec -T spark-client hdfs dfs -count "$INPUT_DIR/reviews.jsonl"
    ;;
  mapreduce)
    wait_for_cluster
    "${DC[@]}" exec -T spark-client hdfs dfs -test -e "$INPUT_DIR/reviews.jsonl" || {
      echo "Upload a reviews CSV first with: $0 upload /path/to/reviews.csv" >&2; exit 2;
    }
    "${DC[@]}" exec -T spark-client hdfs dfs -rm -r -f "$OUTPUT_DIR" >/dev/null 2>&1 || true
    "${DC[@]}" exec -T spark-client yarn jar \
      /opt/hadoop/share/hadoop/tools/lib/hadoop-streaming-3.3.6.jar \
      -D mapreduce.job.name=fake-review-category-rating-label-counts \
      -D mapreduce.job.reduces=1 \
      -files /opt/jobs/mapreduce_mapper.py,/opt/jobs/mapreduce_reducer.py \
      -input "$INPUT_DIR/reviews.jsonl" -output "$OUTPUT_DIR" \
      -mapper "python3 mapreduce_mapper.py" -reducer "python3 mapreduce_reducer.py"
    echo "YARN application record:"
    "${DC[@]}" exec -T spark-client yarn application -list -appStates ALL | tail -n +3
    echo "MapReduce results from HDFS:"
    "${DC[@]}" exec -T spark-client hdfs dfs -cat "$OUTPUT_DIR/part-*"
    ;;
  spark)
    wait_for_cluster
    "${DC[@]}" exec -T spark-client hdfs dfs -test -e "$INPUT_DIR/reviews.jsonl" || {
      echo "Upload a reviews CSV first with: $0 upload /path/to/reviews.csv" >&2; exit 2;
    }
    "${DC[@]}" exec -T spark-client spark-submit \
      --master yarn --deploy-mode client --num-executors 1 --executor-cores 1 \
      --executor-memory 512m --driver-memory 512m \
      --conf spark.yarn.am.memory=512m \
      --conf spark.executor.memoryOverhead=256m \
      /opt/jobs/spark_mllib_train.py "$INPUT_DIR/reviews.jsonl" "$SPARK_OUTPUT"
    echo "Persisted Spark metrics from HDFS:"
    "${DC[@]}" exec -T spark-client hdfs dfs -cat "$SPARK_OUTPUT/metrics/part-*"
    ;;
  all)
    "$0" start
    [[ $# -eq 2 ]] || { echo "Usage: $0 all /path/to/reviews.csv" >&2; exit 2; }
    "$0" upload "$2"
    "$0" mapreduce
    "$0" spark
    ;;
  help|*)
    cat <<USAGE
Usage: $0 {start|stop|status|upload CSV|mapreduce|spark|all CSV}

  start       Build pinned images and start HDFS + YARN + Spark client containers
  upload CSV  Validate quoted CSV, convert it to JSON Lines, and put it in HDFS
  mapreduce   Submit real Hadoop Streaming mapper/reducer work through YARN
  spark       Submit Spark MLlib logistic regression to YARN and print saved metrics
  all CSV     Run the full upload, YARN MapReduce, and YARN Spark workflow
  status      Show service, HDFS DataNode, and YARN status
  stop        Stop containers but preserve their named-volume data

Use 'docker compose -f docker-compose.yml down -v' only when you intentionally want
 to erase HDFS data and the YARN local work volume.
USAGE
    ;;
esac
