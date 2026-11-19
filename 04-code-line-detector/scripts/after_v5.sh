S=<SCRATCH> cd $S
until grep -q REBUILD_V5_DONE strata_v5.log 2>/dev/null; do sleep 60; done
TESTS=$S/answer_key_v5.jsonl,$S/strata_v5_lowcode.jsonl,$S/strata_v5_codefree.jsonl,$S/strata_v5_tiny.jsonl,$S/strata_v5_books.jsonl
MODE=lowcode MIN_PAGES=1 TARGET=300 EXCLUDE_KEYS=$TESTS SEED=20261105 python3 build_strata_v5.py train_v5_lowcode.jsonl 2>&1 | grep -v MuPDF | tail -1 >> strata_v5.log
MODE=codefree MIN_PAGES=1 TARGET=300 EXCLUDE_KEYS=$TESTS SEED=20261106 python3 build_strata_v5.py train_v5_codefree.jsonl 2>&1 | grep -v MuPDF | tail -1 >> strata_v5.log
cd <COS_REPO>
OMP_NUM_THREADS=8 python3 $S/eval_segments_v5.py $S/census_v5.json $S/report_segments_v5_base.json 2>&1 | grep -v MuPDF > $S/segments_v5_base.log
OMP_NUM_THREADS=8 TRAIN_EXTRA=train_v5_lowcode.jsonl,train_v5_codefree.jsonl python3 $S/eval_segments_v5.py $S/census_v5.json $S/report_segments_v5_extra.json 2>&1 | grep -v MuPDF > $S/segments_v5_extra.log
echo AFTER_V5_DONE >> $S/strata_v5.log
