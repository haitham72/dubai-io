#!/bin/sh
# usage: run_s2_replay.sh <outdir> <llm_days csv>   (E9b: offline replay of results/e9b-base/s2_attempts.json)
LOCK=G:/Haitham/VsCode/contest-memory/apps/memory/upgrade/reports/DOCKER_LOCK
echo "E9b $(date +%H:%M) S2 replay" > $LOCK
trap 'rm -f $LOCK' EXIT
mkdir -p "$1"
export PYTHONPATH=$(pwd)/../src PYTHONIOENCODING=utf-8 S2_REPLAY=$(pwd)/results/e9b-base/s2_attempts.json S2_NOJUDGE=1 S2_LLM_DAYS="$2"
G:/Haitham/VsCode/contest-memory/apps/memory/.venv/Scripts/python.exe s2_extract_cost.py "$1" > "$1/log.txt" 2>&1
