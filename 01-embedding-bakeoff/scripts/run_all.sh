#!/bin/bash
# ETDI-1.0.742 phase B driver: the three profiles one after another (smallest memory first); exit 3 = memory guard → retry.
E=<EVIDENCE>/three_way_eval
cd <COS_REPO> || exit 1
for p in nomic-v2 nomic-v1.5 jina-v3; do
  until [ -f "$E/$p/DONE" ]; do
    python3 "$E/embed_profile.py" "$p" "$E/heldout.json" <HTC_REPO>/config/taxonomy_manifest.json "$E/$p" >> "$E/$p.log" 2>&1
    rc=$?
    [ $rc -eq 0 ] && break
    echo "$(date) $p exited $rc" >> "$E/$p.log"
    [ $rc -eq 3 ] || exit $rc
    sleep 600
  done
done
echo "$(date) all profiles embedded" >> "$E/run_all.log"
