# Capstone run (after)

- Produced by: `run_capstone.py::main`
- Service: `app.py::submit` with AI201_FAULTS=1, 2026-11-09_0207

| Criterion | Target | Run 1 | Run 2 | Run 3 | Verdict |
|---|---|---|---|---|---|
| 1. Broken detector never accuses | 10 of 10 | 10/10 | 10/10 | 10/10 | MET |
| 2. Stalled detector answers under 9.0 s | 5 of 5 | 5/5 | 5/5 | 5/5 | MET |
| 3. Refused requests don't spend quota | 5 of 5 valid accepted | 5/5 (0 x 429) | 5/5 (0 x 429) | 5/5 (0 x 429) | MET |
| 4. Every request leaves one run record | 20 of 20 | 20/20 | 20/20 | 20/20 | MET |
| 5. Normal path fast right after a stall | 9+ of 10 under 1.0 s, 0 degraded | 4/10 fast, 6 degraded | 0/10 fast, 10 degraded | 4/10 fast, 6 degraded | MISSED |

## Timings

- Trial 1: criterion 2 times [2.015, 2.013, 2.013, 2.014, 2.015]; criterion 5 times [2.012, 2.014, 2.015, 2.015, 2.01, 2.009, 0.172, 0.052, 0.03, 0.028]
- Trial 2: criterion 2 times [2.016, 2.009, 2.017, 2.016, 2.015]; criterion 5 times [2.019, 2.016, 2.014, 2.016, 2.011, 2.015, 2.015, 2.015, 2.015, 2.015]
- Trial 3: criterion 2 times [2.009, 2.015, 2.016, 2.015, 2.017]; criterion 5 times [2.013, 2.016, 2.013, 2.016, 2.009, 2.009, 0.192, 0.05, 0.031, 0.029]

## Raw results

Full JSON for all three trials: the `.json` file with the same name.

