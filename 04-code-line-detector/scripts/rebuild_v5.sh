set -e
S=<SCRATCH> cd $S
python3 build_answer_key_v5.py answer_key_v5.jsonl 1000 2>&1 | grep -v MuPDF > build_v5.log
python3 build_answer_key_v5.py answer_key_v5_old40.jsonl 1000 --stems-from answer_key.json 2>&1 | grep -v MuPDF | tail -1 > strata_v5.log
cp strata_transcript.jsonl strata_v5_transcript.jsonl; cp strata_codefree.jsonl strata_v5_codefree.jsonl
EX=$S/answer_key_v5.jsonl
MODE=code MIN_PAGES=1 MAX_PAGES=7 TARGET=150 EXCLUDE_KEYS=$EX python3 build_strata_v5.py strata_v5_tiny.jsonl 2>&1 | grep -v MuPDF | tail -1 >> strata_v5.log
MODE=code MIN_PAGES=60 TARGET=200 EXCLUDE_KEYS=$EX python3 build_strata_v5.py strata_v5_books.jsonl 2>&1 | grep -v MuPDF | tail -1 >> strata_v5.log
MODE=lowcode MIN_PAGES=1 TARGET=200 EXCLUDE_KEYS=$EX SEED=20261031 python3 build_strata_v5.py strata_v5_lowcode.jsonl 2>&1 | grep -v MuPDF | tail -1 >> strata_v5.log
STRATA_BUILDER=build_strata_v5.py python3 census_v4.py 3000 census_v5.json 2>&1 | grep -v MuPDF > census_v5.log
echo REBUILD_V5_DONE >> strata_v5.log
