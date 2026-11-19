"""Option 3: a small encoder (sentence-transformers/all-MiniLM-L6-v2, 22M parameters, local cache only) fine-tuned as
a code/not-code line classifier. Input: the line between markers inside two context lines either side. Training:
the same documents as the v5+extra line model (v5 key folds 1-3 plus the low-code and code-free training strata),
balanced sample of labelled non-blank lines, one epoch on MPS. Predicts every line of the evaluation documents
(all segments, both halves) and writes encoder_probs.pkl {stem: prob per line}. No download (HF_HUB_OFFLINE=1).
ENCODER / TAG / LR select the checkpoint (local cache only), output tag and learning rate. Memory safety: BS / MAXLEN
/ INFER_BS set batch sizes and sequence length; the run aborts when free RAM falls below MIN_FREE_RAM_PCT (checked
every 100 steps and every 50 prediction batches); the trained model is saved to models/<TAG> before prediction
(LOAD_MODEL=<dir> predicts with it, no training). CASCADE_FROM=<probs pkl> with CASCADE_MIN only sends lines whose
probability there is >= CASCADE_MIN to the encoder (the rest get 0). GOLD_DOCS=<json of
{stem: doc record}> drops those consensus documents from training and adds them to the predicted documents.
    cd Code-Orchestrator-Service && python3 <this> [N_TRAIN=120000]"""
import hashlib, json, os, pickle, random, subprocess, sys, time
os.environ["HF_HUB_OFFLINE"] = "1"; os.environ["TRANSFORMERS_OFFLINE"] = "1"
S = os.path.dirname(os.path.abspath(__file__))
N_TRAIN = int(sys.argv[1]) if len(sys.argv) > 1 else 120000
MODEL = os.environ.get("ENCODER", "sentence-transformers/all-MiniLM-L6-v2")
TAG = os.environ.get("TAG", "minilm"); LR = float(os.environ.get("LR", "5e-5"))
BS, MAXLEN, IBS = int(os.environ.get("BS", "32")), int(os.environ.get("MAXLEN", "128")), int(os.environ.get("INFER_BS", "256"))
CASCADE_FROM, CASCADE_MIN = os.environ.get("CASCADE_FROM"), float(os.environ.get("CASCADE_MIN", "0"))
LOAD_MODEL = os.environ.get("LOAD_MODEL")          # skip training, predict with a saved model


def free_ram_pct():
    out = subprocess.run(["memory_pressure"], capture_output=True, text=True).stdout.strip().splitlines()
    return int(out[-1].split(":")[-1].strip().rstrip("%"))


def main():
    sys.argv = ["compare_v3", "none", "none"]
    src = open(os.path.join(S, "compare_v3.py")).read()
    exec(src[:src.index('if MODE == "round":')], globals())
    import numpy as np, torch
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    floor = int(os.environ.get("MIN_FREE_RAM_PCT", "25"))
    assert free_ram_pct() >= floor, f"less than {floor}% RAM free: not loading a model"
    fold = lambda s: int(hashlib.sha256(f"curve:{s}".encode()).hexdigest(), 16) % 4
    key = [d for d in load(os.path.join(S, "answer_key_v5.jsonl"))]
    train = [d for d in key if fold(d["stem"]) != 0] + load(os.path.join(S, "train_v5_lowcode.jsonl")) + load(os.path.join(S, "train_v5_codefree.jsonl"))
    evald = [d for d in key if fold(d["stem"]) == 0]
    for f in ("strata_v5_books.jsonl", "strata_v5_tiny.jsonl", "strata_v5_lowcode.jsonl", "strata_v5_codefree.jsonl", "strata_v5_transcript.jsonl", "answer_key_v5_old40.jsonl"):
        evald += load(os.path.join(S, f))
    GOLD = os.environ.get("GOLD_DOCS"); out_name = f"encoder_probs_{TAG}.pkl"
    if GOLD:                                   # consensus documents: never trained on, always predicted
        gold = json.load(open(GOLD)); train = [d for d in train if d["stem"] not in gold]
        have = {d["stem"] for d in evald}; evald += [d for st, d in gold.items() if st not in have]
    for d in train + evald:
        d["_t"] = book_text(d)

    def ctx(lines, i):
        nz = [j for j in range(max(0, i - 8), min(len(lines), i + 9)) if lines[j].strip() and j != i]
        before = [lines[j] for j in nz if j < i][-2:]; after = [lines[j] for j in nz if j > i][:2]
        return " \n ".join(before) + " \n >>> " + lines[i] + " <<< \n " + " \n ".join(after)

    pos, neg = [], []
    for d in train:
        lines, labels = d["_t"][1], d["_t"][2]
        for i, lab in enumerate(labels):
            if lab is not None and lines[i].strip():
                (pos if lab else neg).append((d["stem"], i))
    rng = random.Random(20261110); rng.shuffle(pos); rng.shuffle(neg)
    by = {d["stem"]: d for d in train}
    sample = [(x, 1) for x in pos[:N_TRAIN // 2]] + [(x, 0) for x in neg[:N_TRAIN - min(len(pos), N_TRAIN // 2)]]
    rng.shuffle(sample)
    print(f"train lines available: {len(pos)} code / {len(neg)} not code; sampled {len(sample)}", flush=True)

    dev = "mps" if torch.backends.mps.is_available() else "cpu"
    def guard(where):
        f = free_ram_pct()
        if f < floor:
            raise SystemExit(f"ABORT at {where}: free RAM {f}% < {floor}%")
    src_model = LOAD_MODEL or MODEL
    tok = AutoTokenizer.from_pretrained(src_model)
    model = AutoModelForSequenceClassification.from_pretrained(src_model, num_labels=2).to(dev)
    if LOAD_MODEL: sample = []
    FREEZE = int(os.environ.get("FREEZE_LAYERS", "0"))   # memory: freeze embeddings plus the bottom N encoder layers
    if FREEZE:
        base = model.base_model
        for prm in base.embeddings.parameters(): prm.requires_grad = False
        for layer in base.encoder.layer[:FREEZE]:
            for prm in layer.parameters(): prm.requires_grad = False
        print(f"frozen: embeddings + {FREEZE} of {len(base.encoder.layer)} layers; trainable {sum(p.numel() for p in model.parameters() if p.requires_grad):,}", flush=True)
    opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=LR, weight_decay=0.01)
    steps = max(1, (len(sample) + BS - 1) // BS); sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda s: min(1.0, (s + 1) / 200) * max(0.0, 1 - s / steps))
    model.train(); t0 = time.time()
    for k in range(0, len(sample), BS):
        batch = sample[k:k + BS]
        if (k // BS) % 100 == 0: guard(f"train step {k // BS}")
        enc = tok([ctx(by[s]["_t"][1], i) for (s, i), _ in batch], truncation=True, max_length=MAXLEN, padding=True, return_tensors="pt").to(dev)
        out = model(**enc, labels=torch.tensor([y for _, y in batch], device=dev))
        out.loss.backward(); torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0); opt.step(); sched.step(); opt.zero_grad()
        if (k // BS) % 500 == 0:
            print(f"  step {k // BS}/{steps} loss {out.loss.item():.4f} {time.time() - t0:.0f}s free RAM {free_ram_pct()}%", flush=True)
    if not LOAD_MODEL:
        mdir = os.path.join(S, "models", TAG); os.makedirs(mdir, exist_ok=True)
        model.save_pretrained(mdir); tok.save_pretrained(mdir); print(f"saved model to {mdir}", flush=True)
    casc = pickle.load(open(CASCADE_FROM, "rb")) if CASCADE_FROM else None
    model.eval(); probs = {}; t0 = time.time(); n = 0; nb = 0
    with torch.no_grad():
        for d in evald:
            lines = d["_t"][1]; idx = [i for i, l in enumerate(lines) if l.strip()]; p = np.zeros(len(lines), np.float32)
            if casc is not None:
                cp = casc[d["stem"]]; idx = [i for i in idx if cp[i] >= CASCADE_MIN]
            for k in range(0, len(idx), IBS):
                part = idx[k:k + IBS]; nb += 1
                if nb % 50 == 0: guard(f"predict batch {nb}")
                enc = tok([ctx(lines, i) for i in part], truncation=True, max_length=MAXLEN, padding=True, return_tensors="pt").to(dev)
                p[part] = torch.softmax(model(**enc).logits, -1)[:, 1].float().cpu().numpy()
            probs[d["stem"]] = p; n += len(idx)
    print(f"predicted {n} lines in {len(evald)} documents, {time.time() - t0:.0f}s", flush=True)
    pickle.dump(probs, open(os.path.join(S, out_name), "wb"))


if __name__ == "__main__":
    main()
