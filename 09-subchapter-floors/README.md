# E5: the filing floors applied below chapter level (measured 2026-11-18, no decision)

This folder answers the user's E5 request: what would applying the chapter filing floors to sub-chapter units hold back? It uses recorded data only. No model was loaded and nothing was classified live.

## Inputs

- `../three_way_eval/nomic-v2/`: the ETDI-1.0.742 nomic-v2 run.
  - `anchors.npz`: 461 subdomain and 4 KF query vectors.
  - `pieces/<i>.npz`: each of the 1,049 held-out SE chapters read whole, as 480-token document pieces, 40,008 pieces in total.
- `../three_way_eval/heldout.json`: the chapters keyed by their verified subdomain slug.
- `../three_way_eval/scored_2026-11-10/score_nomic-v2.json`: the chapter peak percentiles used as candidate floors.

## Two limits on what could be measured

1. **Spans and paragraph groups were never embedded in any recorded run**, so their own similarities do not exist. The measured unit is the recorded 480-token piece, the only recorded sub-chapter unit. It is a proxy for spans and groups. Measuring the real units would need a live run.
2. **`HTC_NOISE_FLOOR` and `HTC_KF_FLOOR` have no value yet** (§7, calibrated per profile, OQ#24; the .742 scoring used -1). The candidate floors are the chapter peak percentiles:

   | Candidate | `HTC_NOISE_FLOOR` (best raw subdomain) | `HTC_KF_FLOOR` (best raw KF) |
   |---|---|---|
   | p1 | 0.5366 | 0.3413 |
   | p5 | 0.5783 | 0.3883 |
   | p10 | 0.5967 | 0.4040 |

   A chapter floor at p_k quarantines k% of chapters. A unit falls below when its best subdomain similarity is under the noise floor or its best KF similarity is under the KF floor (BEH-11.01 step 5). T 0.03 and ratio 0.6 do not affect raw-similarity floors.

## Files

- `measure_piece_floors.py` produces `e5_piece_floors.json`: every number, plus 10 random examples below and 10 above per floor, and 10 per kind.
- `e5_examples_p1.md`: 10 verbatim examples per heuristic kind at p1.
- Example text uses token-proportional character positions, because pieces carry no offsets. The characters are verbatim; the boundaries are approximate.
- The kinds are a regex heuristic, not a judgement. It is noisy: it tags maths as "code" and "in this chapter" inside prose as "summary/intro".
