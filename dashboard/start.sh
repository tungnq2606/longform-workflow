#!/bin/bash
# Start the Studio dashboard and open it in the browser:  dashboard/start.sh
cd "$(dirname "$0")/.."
if ! curl -s -o /dev/null http://127.0.0.1:8765/api/state; then
  nohup python3 dashboard/server.py > dashboard/jobs/server.log 2>&1 &
  sleep 1
fi
open http://127.0.0.1:8765
