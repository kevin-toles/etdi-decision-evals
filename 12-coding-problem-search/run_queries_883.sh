#!/bin/zsh
# Re-encode only the FastPrep queries (docs.npy is cached) for all eight models on the 883-gold / 7,466-query set,
# one model at a time, only when memory is calm (level 1, >= 40% free). jina-v5-small uses the COS venv (has peft).
X="$1"; D=${0:A:h}
for k in minilm-l6 nomic-v1.5 bge-large-v1.5 e5-large-ml bge-m3 jina-v3 jina-v5-small nomic-v2-moe; do
  [[ -f "$X/emb/$k/scores.json" ]] && { echo "$k already scored"; continue; }
  w=0
  while true; do
    lvl=$(sysctl -n kern.memorystatus_vm_pressure_level); free=$(memory_pressure | tail -1 | awk '{print $NF}' | tr -d '%')
    (( lvl == 1 && free >= 40 )) && break
    (( w >= 1800 )) && { echo "$k SKIPPED: memory not calm (level $lvl, free $free%)"; continue 2; }
    sleep 30; w=$(( w + 30 ))
  done
  PY=python3; [[ $k == jina-v5-small ]] && PY=<COS_REPO>/.venv/bin/python
  echo "$(date '+%H:%M:%S') $k queries start (level $lvl, free $free%)"
  (cd /private/tmp && HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 $PY -I $D/embed_eval.py "$X" $k 2>&1 | grep -vi warning | tail -3) || echo "$k FAILED"
done
echo "$(date '+%H:%M:%S') done"
