# Results — v1.4 Laboratory GUI

Package version **1.4.0**.

## Deliverable

Full procurement sandbox laboratory (tkinter, no new dependencies):

| Piece | Role |
|---|---|
| `run_gui.bat` | Launcher |
| `gui_controller.py` | Threaded RunController, soft-stop, sweep, baseline report |
| `gui_charts.py` | Canvas multi-series fitness charts |
| `gui_app.py` | Tabs: Run / Sweep / Report / Results |

## Soft-stop

Finish the current quarter → write checkpoint → halt. Resume via **Resume ckpt**
or the Resume button.

## How to launch

```bat
cd "Demo\Virtual company"
run_gui.bat
```

or `python -m nowa_sandbox.gui_app` with `PYTHONPATH=src`.

## Tests

`tests/test_gui_controller.py` — controller run / soft-stop / resume / sweep,
chart smoke, readiness text (no long Stage 1a in CI).
