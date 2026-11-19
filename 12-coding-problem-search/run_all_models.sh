#!/bin/zsh
# Run embed_eval.py for each model, one process at a time, only when memory is calm
# (pressure level 1 and >= 40% free); waits up to 30 min per model, else skips it.
X="$1"; D=${0:A:h}
for k in nomic-v1.5 bge-large-v1.5 e5-large-ml bge-m3 nomic-v2-moe jina-v3 jina-v5-small; do
  [[ -f "$X/emb/$k/scores.json" ]] && { echo "$k already scored"; continue; }
  w=0
  while true; do
    lvl=$(sysctl -n kern.memorystatus_vm_pressure_level); free=$(memory_pressure | tail -1 | awk '{print $NF}' | tr -d '%')
    (( lvl == 1 && free >= 40 )) && break
    (( w >= 1800 )) && { echo "$k SKIPPED: memory not calm (level $lvl, free $free%)"; continue 2; }
    sleep 30; w=$(( w + 30 ))
  done
  echo "$(date '+%H:%M:%S') $k start (level $lvl, free $free%)"
  (cd /private/tmp && HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 python3 -I $D/embed_eval.py "$X" $k 2>&1 | grep -vi warning | tail -4) || echo "$k FAILED"
done
echo done
