#!/bin/sh
# usage: run_s2_full.sh <outdir>   (E9b: one full live S2 run with the real judge, under the DOCKER_LOCK)
LOCK=G:/Haitham/VsCode/contest-memory/apps/memory/upgrade/reports/DOCKER_LOCK
echo "E9b $(date +%H:%M) S2 full" > $LOCK
trap 'rm -f $LOCK' EXIT
mkdir -p "$1"
export PYTHONPATH=$(pwd)/../src PYTHONIOENCODING=utf-8
G:/Haitham/VsCode/contest-memory/apps/memory/.venv/Scripts/python.exe s2_extract_cost.py "$1" > "$1/log.txt" 2>&1
echo done >> "$1/log.txt"
