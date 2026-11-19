#!/bin/bash
# ETDI-1.0.954 (v0.25, OQ#26 widened): embed the held-out chapters under the three added candidates, smallest memory
# first, with the same embed_profile.py as the first three (ETDI-1.0.742). Runs in COS's .venv: jina-v5-small needs
# transformers >= 4.57 plus peft; the venv reproduces the stored nomic-v2 pieces exactly (cosine 1.00000 over 162 pieces,
# runs/U108_venv_parity.txt). Exit 3 = memory guard → retry after 10 minutes. Score afterwards with score_profile.py.
E=<EVIDENCE>/three_way_eval
cd <COS_REPO> || exit 1
export HF_HUB_OFFLINE=1
for p in multilingual-e5-large bge-m3 jina-v5-small; do
  until [ -f "$E/$p/DONE" ]; do
    .venv/bin/python "$E/embed_profile.py" "$p" "$E/heldout.json" <HTC_REPO>/config/taxonomy_manifest.json "$E/$p" >> "$E/$p.log" 2>&1
    rc=$?
    [ $rc -eq 0 ] && break
    echo "$(date) $p exited $rc" >> "$E/$p.log"
    [ $rc -eq 3 ] || exit $rc
    sleep 600
  done
done
echo "$(date) all candidate profiles embedded" >> "$E/run_all.log"
