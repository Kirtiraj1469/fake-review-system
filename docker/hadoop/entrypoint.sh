#!/usr/bin/env bash
set -euo pipefail
if [[ "${1:-}" == "namenode" && ! -f /hadoop/dfs/name/current/VERSION ]]; then
  hdfs namenode -format -nonInteractive
fi
exec "$@"
