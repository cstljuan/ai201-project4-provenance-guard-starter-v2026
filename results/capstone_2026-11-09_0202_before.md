# Capstone run (before)

- Produced by: `run_capstone.py::main`
- Service: `app.py::submit` with AI201_FAULTS=1, 2026-11-09_0202

| Criterion | Target | Run 1 | Run 2 | Run 3 | Verdict |
|---|---|---|---|---|---|
| 1. Broken detector never accuses | 10 of 10 | 10/10 | 10/10 | 10/10 | MET |
| 2. Stalled detector answers under 9.0 s | 5 of 5 | 5/5 | 5/5 | 5/5 | MET |
| 3. Refused requests don't spend quota | 5 of 5 valid accepted | 5/5 (0 x 429) | 5/5 (0 x 429) | 5/5 (0 x 429) | MET |
| 4. Every request leaves one run record | 20 of 20 | 20/20 | 20/20 | 20/20 | MET |
| 5. Normal path fast right after a stall | 9+ of 10 under 1.0 s, 0 degraded | 10/10 fast, 0 degraded | 10/10 fast, 0 degraded | 10/10 fast, 0 degraded | MET |

## Timings

- Trial 1: criterion 2 times [8.018, 8.019, 8.016, 8.02, 8.02]; criterion 5 times [0.053, 0.029, 0.021, 0.034, 0.045, 0.041, 0.041, 0.051, 0.03, 0.028]
- Trial 2: criterion 2 times [8.018, 8.021, 8.017, 8.017, 8.016]; criterion 5 times [0.064, 0.03, 0.022, 0.035, 0.043, 0.041, 0.041, 0.051, 0.03, 0.029]
- Trial 3: criterion 2 times [8.021, 8.014, 8.013, 8.013, 8.024]; criterion 5 times [0.06, 0.03, 0.022, 0.035, 0.043, 0.041, 0.042, 0.05, 0.03, 0.028]

## Raw results

Full JSON for all three trials: the `.json` file with the same name.

