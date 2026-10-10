# Results — diagnostics + anti-monopoly (lab)

## Root cause (screenshot Q34–43)

Stage **1b** failures were dominated by **supplier monopoly**:
`supplier_diversification ≈ 0.133` = all accepted orders to one supplier.
High `decision_consistency` is the other side of the same habit.
Rare `ок=да` with `серия=0` = gating passed but **non-regression**
(often `reaction_to_risk_events`) blocked the streak.

## Lab changes

1. **Quarter diagnosis panel** — select a table row: verdict, gate fails,
   NR fails, monopoly flag, action mix.
2. **Global thresholds & world** controls on the Run tab (not per-quarter).
3. **Anti-monopoly scaffold** (on by default): if one supplier already owns
   ≥55% of the quarter’s accepted orders, attribute strategies redirect to
   `least_used`.

## How to verify

```bat
run_gui.bat
```

Load a Stage 1b results JSON into Results → “into Run”, click a failed
quarter (e.g. diversif 0.133) and read the diagnosis panel.
