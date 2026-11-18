import json
import os
import shutil
import subprocess
import sys
import tempfile
import pandas as pd
import streamlit as st
from mapreduce_jobs import mapper, reducer

def mapreduce_page():
    st.title("Distributed analysis")
    st.caption("Run a Hadoop Streaming MapReduce job, or execute the same mapper and reducer locally.")
    upload = st.file_uploader("Reviews or predictions CSV", type="csv", key="mapreduce_upload")
    path = os.path.join("Predicted Data", "predicted_data.csv")
    if upload:
        try:
            data = pd.read_csv(upload)
        except Exception as error:
            st.error(f"Could not read CSV: {error}")
            return
    elif os.path.exists(path):
        data = pd.read_csv(path)
        st.caption(f"Using {path}")
    else:
        st.info("Upload a CSV or analyze reviews first.")
        return
    if st.button("Run MapReduce", type="primary"):
        with tempfile.TemporaryDirectory() as temp:
            source = os.path.join(temp, "reviews.jsonl")
            mapped = os.path.join(temp, "mapped.tsv")
            reduced = os.path.join(temp, "results.tsv")
            data.to_json(source, orient="records", lines=True, force_ascii=False)
            with open(source, encoding="utf-8") as input_file, open(mapped, "w", encoding="utf-8") as output:
                mapper(input_file, output)
            with open(mapped, encoding="utf-8") as input_file, open(reduced, "w", encoding="utf-8") as output:
                reducer(sorted(input_file), output)
            result = pd.read_csv(reduced, sep="\t", names=["key", "count"])
            st.success(f"Local MapReduce completed across {len(data):,} review records.")
            st.dataframe(result, use_container_width=True)
            st.download_button("Download aggregation", result.to_csv(index=False), "mapreduce_results.csv", "text/csv")
    st.divider()
    st.subheader("Run on Hadoop")
    st.caption("The job uses Hadoop Streaming and JSON Lines input. Hadoop must be installed and configured in the environment.")
    st.code("hdfs dfs -put reviews.jsonl /reviews/input/\nhadoop jar $HADOOP_HOME/share/hadoop/tools/lib/hadoop-streaming-*.jar \\\n  -input /reviews/input -output /reviews/output \\\n  -mapper 'python3 mapreduce_jobs.py mapper' \\\n  -reducer 'python3 mapreduce_jobs.py reducer' \\\n  -files mapreduce_jobs.py")
