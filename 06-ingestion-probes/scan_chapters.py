import json,os,sys
R="<CORPUS_ROOT>/collections/software-engineering/raw"
books=chs=big=bigbooks=onech=bad=0; ex=[]
for e in os.scandir(R):
    if not e.name.endswith('.json'): continue
    try: d=json.load(open(e.path))
    except Exception: bad+=1; continue
    ch=d.get('chapters') or []; P=len(d.get('pages') or []); books+=1; chs+=len(ch); hit=False
    if P>=100 and len(ch)<=1: onech+=1
    for c in ch:
        span=(c.get('end_page') or 0)-(c.get('start_page') or 0)+1
        if P>=100 and span>=0.4*P: big+=1; hit=True
    bigbooks+=hit
    if hit and len(ex)<10: ex.append((e.name[:60],len(ch),P))
print(json.dumps({"books":books,"unreadable":bad,"chapters":chs,"oversize_chapters(>=40% of >=100p book)":big,"books_with_one":bigbooks,"books>=100p_with_<=1_chapter":onech,"examples":ex}))
