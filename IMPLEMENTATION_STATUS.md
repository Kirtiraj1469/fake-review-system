# Implementation Status

## Repository inspection

- Inspected the connected repository at commit `e09bc5d` and created a separate branch `feat/hadoop-spark-integration`.
- The repository had the React UI, FastAPI code, Streamlit source files under `backend/legacy/`, and empty placeholder data directories.
- No `reviews.csv`, training CSV, or saved user model was present in the repository tree. The claimed 40,432-row schema and prior accuracy could not be verified here.
- Existing dataset fields were not assumed. The upload converter requires review text and a label, with category/rating optional.
- The existing Streamlit pages were retained and a root `main.py` entry point was added. The active React UI remains available separately.

## Implemented

- Docker Compose defines a single-node NameNode, DataNode, ResourceManager, NodeManager, and Spark client.
- The image uses an ARM64-capable Temurin 11 base manifest and pinned Hadoop 3.3.6 / Spark 3.5.3 archives.
- HDFS storage, WebHDFS, YARN shuffle, YARN memory caps, service health checks, and local data mounts are configured.
- CSV-to-JSONL conversion uses Python's CSV reader, validates required text/label fields, and ignores blank rows.
- Hadoop Streaming mapper/reducer count records by category, rating, and original label. Submission uses `yarn jar` and output is stored in HDFS.
- PySpark MLlib reads JSON Lines from HDFS, uses tokenization, stop-word removal, HashingTF, IDF, Logistic Regression, seeded split, multiple metrics and confusion counts, then saves model/metrics to HDFS.
- `scripts/bigdata.sh` provides start, readiness, upload, MapReduce, Spark, status, stop, and end-to-end commands.
- Streamlit adds a live Hadoop/Spark dashboard backed by NameNode WebHDFS, ResourceManager REST, and actual HDFS output. Existing scikit-learn metrics remain separate.
- Added `MAC_SETUP.md`, `FACULTY_DEMO.md`, and this factual status file.

## Verification

- `python -m unittest discover -s backend/tests -v` — 3 focused tests passed for CSV quoting/newlines, blank-row handling, and MapReduce mapper/reducer counts. These use small test fixtures, not the course dataset.
- `python -m py_compile backend/app/bigdata/jobs/*.py backend/legacy/bigdata_dashboard.py backend/legacy/main.py main.py` — passed.
- `docker compose config --quiet` — passed.
- Parsed all four Hadoop XML configuration files with Python's XML parser — passed.
- Verified the pinned Temurin 11 base image has a `linux/arm64/v8` manifest. The Codex Docker daemon itself is separate and reports Linux/amd64.
- Attempted a Docker image build in the separate Codex Linux/amd64 daemon. The build was still downloading the large Hadoop archive from Apache after several minutes; it was stopped before the image completed. No Hadoop services or YARN jobs were started here.
- The user's Mac Docker Desktop ARM64 execution has not been observed and must not be represented as tested.
- The course dataset is absent, so data-specific schema validation, class balance, accuracy, precision, recall, F1, YARN application IDs, and model outputs remain unknown until the user runs with their actual CSV.

## Remaining user-side checks

- Pull `feat/hadoop-spark-integration` on the Mac and run the setup in `MAC_SETUP.md`.
- Verify the custom image builds/runs as `linux/arm64` under Docker Desktop.
- Upload the actual dataset, confirm its header/label counts, run YARN MapReduce and Spark MLlib, and capture real job IDs, metrics, and UI screenshots.
- Review and merge the pull request from the feature branch to `main` after the Mac integration checks.
