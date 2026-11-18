# Backend and local Hadoop/Spark stack

The FastAPI API is started from the repository root with:

```bash
python -m pip install -r backend/requirements.txt
python -m uvicorn backend.app.api:app --host 0.0.0.0 --port 5001
```

The original Streamlit application is preserved at the repository root. The real
HDFS, YARN MapReduce, and Spark MLlib demo is described in [`../MAC_SETUP.md`](../MAC_SETUP.md)
and is operated with `../scripts/bigdata.sh`. Hadoop Streaming and Spark both read
JSON Lines produced from the user's quoted CSV via Python's standard `csv` parser.
No dataset or trained model is included in this repository.
