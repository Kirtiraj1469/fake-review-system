"""Live status and result viewer for the optional Docker Hadoop/Spark stack."""
import json
import subprocess
from pathlib import Path

import pandas as pd
import requests
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
COMPOSE_FILE = PROJECT_ROOT / "docker-compose.yml"
HDFS_INPUT = "/fake-review-detection/input/reviews.jsonl"
HDFS_MAPREDUCE = "/fake-review-detection/mapreduce/category-rating-label-counts"
HDFS_SPARK = "/fake-review-detection/spark/logistic-regression"


def _docker_exec(*args):
    result = subprocess.run(
        ["docker", "compose", "-f", str(COMPOSE_FILE), "exec", "-T", "spark-client", *args],
        cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=20, check=False,
    )
    if result.returncode:
        raise RuntimeError((result.stderr or result.stdout).strip() or "Docker command failed")
    return result.stdout


def _webhdfs_status():
    response = requests.get(
        "http://localhost:9870/webhdfs/v1" + HDFS_INPUT,
        params={"op": "GETFILESTATUS", "user.name": "hadoop"}, timeout=3,
    )
    if response.status_code == 404:
        return None
    response.raise_for_status()
    return response.json()["FileStatus"]


def _read_mapreduce():
    text = _docker_exec("hdfs", "dfs", "-cat", HDFS_MAPREDUCE + "/part-*")
    return pd.DataFrame([line.split("\t", 1) for line in text.splitlines()], columns=["Metric", "Count"])


def _read_spark_metrics():
    text = _docker_exec("hdfs", "dfs", "-cat", HDFS_SPARK + "/metrics/part-*")
    return json.loads(text.strip().splitlines()[-1])


def bigdata_dashboard():
    st.title("Big Data · Hadoop & Spark")
    st.caption("Live HDFS and YARN status, real Hadoop Streaming results, and Spark MLlib evaluation.")
    st.info("This dashboard reads the local Docker Compose cluster. It does not use Codex or a cloud Hadoop service.")

    namenode_ok = yarn_info = None
    namenode_error = yarn_error = None
    try:
        response = requests.get("http://localhost:9870/jmx", timeout=3)
        response.raise_for_status()
        namenode_ok = True
    except requests.RequestException as error:
        namenode_error = str(error)
    try:
        response = requests.get("http://localhost:8088/ws/v1/cluster/info", timeout=3)
        response.raise_for_status()
        yarn_info = response.json().get("clusterInfo", {})
    except requests.RequestException as error:
        yarn_error = str(error)

    left, right, third = st.columns(3)
    left.metric("HDFS NameNode", "Connected" if namenode_ok else "Unavailable")
    right.metric("YARN ResourceManager", yarn_info.get("state", "Unavailable") if yarn_info else "Unavailable")
    dataset = None
    if namenode_ok:
        try:
            dataset = _webhdfs_status()
        except (requests.RequestException, KeyError, ValueError):
            dataset = None
    third.metric("HDFS input", f"{dataset['length']:,} bytes" if dataset else "Not uploaded")

    if namenode_error:
        st.warning("NameNode not reachable at localhost:9870. Start the stack with `./scripts/bigdata.sh start`. " + namenode_error)
    if yarn_error:
        st.warning("ResourceManager not reachable at localhost:8088. Start the stack with `./scripts/bigdata.sh start`. " + yarn_error)

    st.subheader("Dataset on HDFS")
    if dataset:
        st.success(f"{HDFS_INPUT} · {dataset['length']:,} bytes · replication {dataset.get('replication', 'unknown')}")
    else:
        st.caption("No HDFS input file was found. Upload a local CSV with `./scripts/bigdata.sh upload /path/to/reviews.csv`.")

    st.subheader("YARN applications")
    if yarn_info:
        try:
            response = requests.get("http://localhost:8088/ws/v1/cluster/apps", timeout=3)
            response.raise_for_status()
            apps = response.json().get("apps", {}).get("app", []) or []
            if apps:
                st.dataframe(pd.DataFrame([{
                    "Application ID": app.get("id"), "Name": app.get("name"),
                    "Type": app.get("applicationType"), "State": app.get("state"),
                    "Final status": app.get("finalStatus"), "Progress": app.get("progress"),
                } for app in apps]), use_container_width=True)
            else:
                st.caption("YARN is reachable. No submitted applications are recorded yet.")
        except (requests.RequestException, ValueError) as error:
            st.warning(f"Could not read YARN application state: {error}")

    st.subheader("Hadoop MapReduce output")
    try:
        mapreduce = _read_mapreduce()
        mapreduce["Count"] = pd.to_numeric(mapreduce["Count"], errors="coerce")
        st.dataframe(mapreduce, use_container_width=True, hide_index=True)
        st.bar_chart(mapreduce.set_index("Metric"), y="Count")
    except (RuntimeError, ValueError):
        st.caption("No Hadoop Streaming output exists yet. Run `./scripts/bigdata.sh mapreduce` after uploading the dataset.")

    st.subheader("Spark MLlib evaluation")
    try:
        metrics = _read_spark_metrics()
        st.caption(f"Actual backend: {metrics.get('algorithm')} · Spark master `{metrics.get('spark_master')}` · deploy mode `{metrics.get('deploy_mode')}`")
        cols = st.columns(4)
        for col, key in zip(cols, ("accuracy", "precision", "recall", "f1")):
            col.metric(key.title(), f"{metrics[key]:.3f}")
        st.write("Confusion matrix rows", metrics.get("confusion_matrix", []))
        st.caption(f"Rows evaluated: {metrics['test_rows']:,} · train/test seed: {metrics['seed']}")
    except (RuntimeError, ValueError, KeyError, IndexError):
        st.caption("No Spark evaluation metrics have been saved to HDFS yet. Run `./scripts/bigdata.sh spark` after uploading the dataset.")

    sklearn_metrics = st.session_state.get("local_sklearn_metrics")
    st.subheader("Existing scikit-learn comparison")
    if sklearn_metrics:
        st.dataframe(pd.DataFrame([sklearn_metrics]), use_container_width=True, hide_index=True)
    else:
        st.caption("No scikit-learn evaluation is available in this session. Train a local model on the Training page to create real comparison metrics.")
