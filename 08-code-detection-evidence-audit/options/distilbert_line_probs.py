"""Challenger 1: LemiSt/code-segmentor-distilbert (Apache-2.0, DistilBERT multilingual token tagger Text/Code), used
zero-shot exactly as published: no training on our data. Each document's lines are fed in windows of consecutive
lines (newline-joined, <= MAXTOK tokens, OVERLAP lines repeated between windows); a line's probability is the mean
Code probability of its tokens, averaged over the windows that contain it. Predicts the same documents as
hgb_holdout.py (v5 key fold 0, all strata, the 40-book key, the consensus documents) and writes
encoder_probs_distilbert.pkl {stem: prob per line}. Local cache only; aborts below MIN_FREE_RAM_PCT free RAM.
    cd Code-Orchestrator-Service && python3 <this>"""
import hashlib, json, os, pickle, subprocess, sys, time
os.environ["HF_HUB_OFFLINE"] = "1"; os.environ["TRANSFORMERS_OFFLINE"] = "1"
S = os.path.dirname(os.path.abspath(__file__))
MODEL = "LemiSt/code-segmentor-distilbert"
MAXTOK, OVERLAP, IBS = int(os.environ.get("MAXTOK", "384")), int(os.environ.get("OVERLAP", "3")), int(os.environ.get("INFER_BS", "16"))


def free_ram_pct():
    out = subprocess.run(["memory_pressure"], capture_output=True, text=True).stdout.strip().splitlines()
    return int(out[-1].split(":")[-1].strip().rstrip("%"))


def main():
    sys.argv = ["compare_v3", "none", "none"]
    src = open(os.path.join(S, "compare_v3.py")).read()
    exec(src[:src.index('if MODE == "round":')], globals())
    import numpy as np, torch
    from transformers import AutoTokenizer, AutoModelForTokenClassification
    floor = int(os.environ.get("MIN_FREE_RAM_PCT", "20"))
    assert free_ram_pct() >= floor, f"less than {floor}% RAM free: not loading a model"
    fold = lambda s: int(hashlib.sha256(f"curve:{s}".encode()).hexdigest(), 16) % 4
    gold = json.load(open(os.path.join(S, "gold_docs.json")))
    docs = [d for d in load(os.path.join(S, "answer_key_v5.jsonl")) if fold(d["stem"]) == 0]
    for f in ("strata_v5_books.jsonl", "strata_v5_tiny.jsonl", "strata_v5_lowcode.jsonl", "strata_v5_codefree.jsonl", "strata_v5_transcript.jsonl", "answer_key_v5_old40.jsonl"):
        docs += load(os.path.join(S, f))
    have = {d["stem"] for d in docs}; docs += [d for st, d in gold.items() if st not in have]
    seen = set(); docs = [d for d in docs if not (d["stem"] in seen or seen.add(d["stem"]))]
    dev = "mps" if torch.backends.mps.is_available() else "cpu"
    tok = AutoTokenizer.from_pretrained(MODEL)
    model = AutoModelForTokenClassification.from_pretrained(MODEL).to(dev).eval()
    probs = {}; t0 = time.time(); nl = nw = 0
    for di, d in enumerate(docs):
        lines = book_text(d)[1]; n = len(lines)
        ntok = [len(tok.tokenize(l)) + 1 if l.strip() else 0 for l in lines]
        wins = []; i = 0                                           # windows of whole lines under the token budget
        while i < n:
            j, used = i, 0
            while j < n and (used + ntok[j] <= MAXTOK - 2 or j == i):
                used += ntok[j]; j += 1
            wins.append((i, j)); i = j if j >= n else max(i + 1, j - OVERLAP)
        acc = np.zeros(n, np.float64); cnt = np.zeros(n)
        texts = []
        for a, b in wins:
            starts, s, pos = [], "", 0
            for k in range(a, b):
                starts.append(len(s)); s += lines[k] + "\n"
            texts.append((a, b, s, starts))
        for k in range(0, len(texts), IBS):
            batch = texts[k:k + IBS]
            enc = tok([t[2] for t in batch], truncation=True, max_length=MAXTOK, padding=True, return_offsets_mapping=True, return_tensors="pt")
            offs = enc.pop("offset_mapping").numpy()
            with torch.no_grad():
                pc = torch.softmax(model(**{x: v.to(dev) for x, v in enc.items()}).logits, -1)[..., 1].float().cpu().numpy()
            for (a, b, s, starts), off, p in zip(batch, offs, pc):
                bounds = np.array(starts + [len(s)])
                for (o0, o1), pi in zip(off, p):
                    if o1 <= o0: continue
                    li = int(np.searchsorted(bounds, o0, side="right") - 1)
                    if 0 <= li < b - a:
                        acc[a + li] += pi; cnt[a + li] += 1
            nw += len(batch)
        out = np.where(cnt > 0, acc / np.maximum(cnt, 1), 0.0).astype(np.float32)
        out[[not l.strip() for l in lines]] = 0.0
        probs[d["stem"]] = out; nl += n
        if di % 50 == 0:
            f = free_ram_pct()
            print(f"  doc {di}/{len(docs)} lines {nl} windows {nw} {time.time() - t0:.0f}s free RAM {f}%", flush=True)
            if f < floor: raise SystemExit(f"ABORT: free RAM {f}% < {floor}%")
    print(f"predicted {nl} lines in {len(docs)} documents, {time.time() - t0:.0f}s", flush=True)
    pickle.dump(probs, open(os.path.join(S, "encoder_probs_distilbert.pkl"), "wb"))


if __name__ == "__main__":
    main()
