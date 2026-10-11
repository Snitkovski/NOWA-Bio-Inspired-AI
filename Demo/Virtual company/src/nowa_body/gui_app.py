"""NOWA Body Layer — laboratory GUI for Phase 1 final testing.

Launch::

    python -m nowa_body.gui_app
    # or run_body_gui.bat
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import tkinter as tk
    from tkinter import messagebox, ttk
except ImportError:  # pragma: no cover - minimal Python builds omit Tk
    tk = None  # type: ignore[assignment]
    messagebox = None  # type: ignore[assignment]
    ttk = None  # type: ignore[assignment]

if __package__ in (None, ""):  # pragma: no cover
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from nowa_body.gui_i18n import I18n
from nowa_body.lab_session import (
    FORCE_ACTIONS,
    FORCE_AUTO,
    SCENARIOS,
    WRITE_OUTCOMES,
    BodyLabSession,
    LabSettings,
)

DEMO_ROOT = Path(__file__).resolve().parents[2]


def _idle_button_bg(widget) -> str:
    """Windows system button color when this Tk knows it."""

    if tk is None:
        return "#f0f0f0"
    try:
        widget.tk.call("winfo", "rgb", widget, "SystemButtonFace")
    except tk.TclError:
        return "#f0f0f0"
    return "SystemButtonFace"


class BodyLabApp(tk.Tk if tk is not None else object):
    """Interactive MockMCP lab: tick, approve, inspect memory and sleep."""

    def __init__(self, lang: str | None = None) -> None:
        super().__init__()
        self.geometry("1280x820")
        self.minsize(1040, 700)
        self.i18n = I18n(
            lang=lang or "en",
            pref_path=DEMO_ROOT / "results" / ".body_lab_lang.json",
            force=lang in ("en", "ru"),
        )
        self.session = BodyLabSession()
        self._auto_job: Optional[str] = None
        self._build()
        self._apply_language()
        self._refresh_view()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def t(self, key: str, **kwargs: Any) -> str:
        return self.i18n.t(key, **kwargs)

    # ------------------------------------------------------------------ UI
    def _build(self) -> None:
        style = ttk.Style(self)
        if "vista" in style.theme_names():
            style.theme_use("vista")

        header = ttk.Frame(self)
        header.pack(fill="x", padx=8, pady=(8, 0))
        self.lbl_title = ttk.Label(header, font=("Segoe UI", 11, "bold"))
        self.lbl_title.pack(side="left")
        lang_bar = ttk.Frame(header)
        lang_bar.pack(side="right")
        self.btn_lang_en = tk.Button(
            lang_bar, text="EN", command=lambda: self._set_language("en"),
            relief="raised", padx=8, pady=2, font=("Segoe UI", 10), cursor="hand2",
        )
        self.btn_lang_ru = tk.Button(
            lang_bar, text="RU", command=lambda: self._set_language("ru"),
            relief="raised", padx=8, pady=2, font=("Segoe UI", 10), cursor="hand2",
        )
        self.btn_lang_en.pack(side="left", padx=(0, 4))
        self.btn_lang_ru.pack(side="left")

        self.lbl_live = ttk.Label(self, font=("Consolas", 10))
        self.lbl_live.pack(fill="x", padx=10, pady=(6, 0))

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True, padx=8, pady=8)
        left = ttk.Frame(body, width=360)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)
        right = ttk.Frame(body)
        right.pack(side="left", fill="both", expand=True, padx=(8, 0))

        self._build_controls(left)
        self._build_tabs(right)

        self.lbl_hint = ttk.Label(self, wraplength=1200, justify="left")
        self.lbl_hint.pack(fill="x", padx=10, pady=(0, 4))
        self.lbl_status = ttk.Label(self)
        self.lbl_status.pack(fill="x", padx=10, pady=(0, 8))

    def _build_controls(self, parent: ttk.Frame) -> None:
        self.var_seed = tk.BooleanVar(value=True)
        self.var_auto_exec = tk.BooleanVar(value=False)
        self.var_fatigue_on = tk.BooleanVar(value=False)
        self.var_fatigue = tk.DoubleVar(value=0.9)
        self.var_min_ticks = tk.IntVar(value=8)
        self.var_sensor_s = tk.DoubleVar(value=5.0)
        self.var_auto_ms = tk.IntVar(value=400)
        self.var_reason = tk.StringVar(value="")
        self.var_qty = tk.StringVar(value="")
        self.var_clock = tk.StringVar(value="14:00:00")

        self.grp_session = ttk.LabelFrame(parent, padding=6)
        self.grp_session.pack(fill="x", pady=(0, 6))
        self.chk_seed = ttk.Checkbutton(self.grp_session, variable=self.var_seed)
        self.chk_seed.pack(anchor="w")
        self.chk_auto_exec = ttk.Checkbutton(self.grp_session, variable=self.var_auto_exec)
        self.chk_auto_exec.pack(anchor="w")
        self.lbl_backend = ttk.Label(self.grp_session)
        self.lbl_backend.pack(anchor="w", pady=(4, 0))
        self.btn_reset = ttk.Button(self.grp_session, command=self._on_reset)
        self.btn_reset.pack(fill="x", pady=(4, 0))

        self.grp_world = ttk.LabelFrame(parent, padding=6)
        self.grp_world.pack(fill="x", pady=(0, 6))
        row = ttk.Frame(self.grp_world)
        row.pack(fill="x")
        self.lbl_scenario = ttk.Label(row)
        self.lbl_scenario.pack(side="left")
        self.cmb_scenario = ttk.Combobox(row, state="readonly", width=28)
        self.cmb_scenario.pack(side="right", fill="x", expand=True)
        self.cmb_scenario.bind("<<ComboboxSelected>>", self._on_scenario)
        row2 = ttk.Frame(self.grp_world)
        row2.pack(fill="x", pady=(4, 0))
        self.lbl_write = ttk.Label(row2)
        self.lbl_write.pack(side="left")
        self.cmb_write = ttk.Combobox(row2, state="readonly", width=18)
        self.cmb_write.pack(side="right")
        self.cmb_write.bind("<<ComboboxSelected>>", self._on_write)

        self.grp_action = ttk.LabelFrame(parent, padding=6)
        self.grp_action.pack(fill="x", pady=(0, 6))
        self.lbl_force = ttk.Label(self.grp_action)
        self.lbl_force.pack(anchor="w")
        self.cmb_force = ttk.Combobox(self.grp_action, state="readonly")
        self.cmb_force.pack(fill="x")
        self.cmb_force.bind("<<ComboboxSelected>>", self._on_force)

        self.grp_clock = ttk.LabelFrame(parent, padding=6)
        self.grp_clock.pack(fill="x", pady=(0, 6))
        clock_row = ttk.Frame(self.grp_clock)
        clock_row.pack(fill="x")
        self.lbl_clock = ttk.Label(clock_row)
        self.lbl_clock.pack(side="left")
        self.ent_clock = ttk.Entry(clock_row, textvariable=self.var_clock, width=12)
        self.ent_clock.pack(side="right")
        self.ent_clock.bind("<Return>", self._on_clock_entry)
        btns = ttk.Frame(self.grp_clock)
        btns.pack(fill="x", pady=(4, 0))
        self.btn_day = ttk.Button(btns, command=lambda: self._set_hour(14))
        self.btn_night = ttk.Button(btns, command=lambda: self._set_hour(3))
        self.btn_plus_hour = ttk.Button(btns, command=self._advance_hour)
        self.btn_day.pack(side="left", expand=True, fill="x", padx=(0, 2))
        self.btn_night.pack(side="left", expand=True, fill="x", padx=2)
        self.btn_plus_hour.pack(side="left", expand=True, fill="x", padx=(2, 0))
        ticks_row = ttk.Frame(self.grp_clock)
        ticks_row.pack(fill="x", pady=(4, 0))
        self.lbl_min_ticks = ttk.Label(ticks_row)
        self.lbl_min_ticks.pack(side="left")
        self.spn_min_ticks = ttk.Spinbox(
            ticks_row, from_=0, to=3600, textvariable=self.var_min_ticks, width=8
        )
        self.spn_min_ticks.pack(side="right")
        sens_row = ttk.Frame(self.grp_clock)
        sens_row.pack(fill="x", pady=(4, 0))
        self.lbl_sensor = ttk.Label(sens_row)
        self.lbl_sensor.pack(side="left")
        self.spn_sensor = ttk.Spinbox(
            sens_row, from_=0, to=3600, increment=1, textvariable=self.var_sensor_s, width=8
        )
        self.spn_sensor.pack(side="right")
        self.chk_fatigue = ttk.Checkbutton(
            self.grp_clock, variable=self.var_fatigue_on, command=self._on_fatigue
        )
        self.chk_fatigue.pack(anchor="w", pady=(4, 0))
        self.scl_fatigue = ttk.Scale(
            self.grp_clock, from_=0.0, to=1.0, variable=self.var_fatigue,
            command=lambda _v: self._on_fatigue(),
        )
        self.scl_fatigue.pack(fill="x")

        self.grp_run = ttk.LabelFrame(parent, padding=6)
        self.grp_run.pack(fill="x", pady=(0, 6))
        run_row = ttk.Frame(self.grp_run)
        run_row.pack(fill="x")
        self.btn_tick = ttk.Button(run_row, command=self._on_tick)
        self.btn_burst = ttk.Button(run_row, command=self._on_burst)
        self.btn_tick.pack(side="left", expand=True, fill="x", padx=(0, 2))
        self.btn_burst.pack(side="left", expand=True, fill="x", padx=(2, 0))
        auto_row = ttk.Frame(self.grp_run)
        auto_row.pack(fill="x", pady=(4, 0))
        self.btn_auto = ttk.Button(auto_row, command=self._on_auto_start)
        self.btn_stop = ttk.Button(auto_row, command=self._on_auto_stop)
        self.btn_auto.pack(side="left", expand=True, fill="x", padx=(0, 2))
        self.btn_stop.pack(side="left", expand=True, fill="x", padx=(2, 0))
        ms_row = ttk.Frame(self.grp_run)
        ms_row.pack(fill="x", pady=(4, 0))
        self.lbl_auto_ms = ttk.Label(ms_row)
        self.lbl_auto_ms.pack(side="left")
        self.spn_auto_ms = ttk.Spinbox(
            ms_row, from_=80, to=5000, increment=50, textvariable=self.var_auto_ms, width=8
        )
        self.spn_auto_ms.pack(side="right")
        self.btn_probe = ttk.Button(self.grp_run, command=self._on_probe)
        self.btn_probe.pack(fill="x", pady=(6, 0))

        self.grp_approval = ttk.LabelFrame(parent, padding=6)
        self.grp_approval.pack(fill="both", expand=True)
        reason_row = ttk.Frame(self.grp_approval)
        reason_row.pack(fill="x")
        self.lbl_reason = ttk.Label(reason_row)
        self.lbl_reason.pack(side="left")
        self.ent_reason = ttk.Entry(reason_row, textvariable=self.var_reason)
        self.ent_reason.pack(side="right", fill="x", expand=True)
        qty_row = ttk.Frame(self.grp_approval)
        qty_row.pack(fill="x", pady=(4, 0))
        self.lbl_qty = ttk.Label(qty_row)
        self.lbl_qty.pack(side="left")
        self.ent_qty = ttk.Entry(qty_row, textvariable=self.var_qty, width=10)
        self.ent_qty.pack(side="right")
        appr_btns = ttk.Frame(self.grp_approval)
        appr_btns.pack(fill="x", pady=(6, 0))
        self.btn_approve = ttk.Button(appr_btns, command=self._on_approve)
        self.btn_reject = ttk.Button(appr_btns, command=self._on_reject)
        self.btn_modify = ttk.Button(self.grp_approval, command=self._on_modify)
        self.btn_approve.pack(side="left", expand=True, fill="x", padx=(0, 2))
        self.btn_reject.pack(side="left", expand=True, fill="x", padx=(2, 0))
        self.btn_modify.pack(fill="x", pady=(4, 0))

    def _build_tabs(self, parent: ttk.Frame) -> None:
        self.notebook = ttk.Notebook(parent)
        self.notebook.pack(fill="both", expand=True)
        self.tab_pipeline = ttk.Frame(self.notebook, padding=6)
        self.tab_pending = ttk.Frame(self.notebook, padding=6)
        self.tab_memory = ttk.Frame(self.notebook, padding=6)
        self.tab_mcp = ttk.Frame(self.notebook, padding=6)
        self.tab_log = ttk.Frame(self.notebook, padding=6)
        self.notebook.add(self.tab_pipeline, text="Pipeline")
        self.notebook.add(self.tab_pending, text="Approvals")
        self.notebook.add(self.tab_memory, text="Memory")
        self.notebook.add(self.tab_mcp, text="MCP")
        self.notebook.add(self.tab_log, text="Log")

        self.lbl_ctx = ttk.Label(self.tab_pipeline)
        self.lbl_ctx.pack(anchor="w")
        self.txt_ctx = tk.Text(self.tab_pipeline, height=6, wrap="word", font=("Consolas", 9))
        self.txt_ctx.pack(fill="x", pady=(0, 6))
        self.lbl_prop = ttk.Label(self.tab_pipeline)
        self.lbl_prop.pack(anchor="w")
        self.txt_prop = tk.Text(self.tab_pipeline, height=10, wrap="word", font=("Consolas", 9))
        self.txt_prop.pack(fill="both", expand=True, pady=(0, 6))
        self.lbl_exec = ttk.Label(self.tab_pipeline)
        self.lbl_exec.pack(anchor="w")
        self.txt_exec = tk.Text(self.tab_pipeline, height=6, wrap="word", font=("Consolas", 9))
        self.txt_exec.pack(fill="x")

        self.tree_pending = ttk.Treeview(
            self.tab_pending, columns=("id", "tool", "risk", "summary"), show="headings"
        )
        self.tree_pending.pack(fill="both", expand=True)
        self.tree_pending.bind("<<TreeviewSelect>>", self._on_pending_select)

        self.tree_memory = ttk.Treeview(
            self.tab_memory, columns=("path", "consequence", "reward"), show="headings"
        )
        self.tree_memory.pack(fill="both", expand=True)

        self.tree_mcp = ttk.Treeview(
            self.tab_mcp, columns=("tool", "params", "result"), show="headings"
        )
        self.tree_mcp.pack(fill="both", expand=True)

        self.txt_log = tk.Text(self.tab_log, wrap="word", font=("Consolas", 9))
        self.txt_log.pack(fill="both", expand=True)

    # ------------------------------------------------------------------ language
    def _set_language(self, lang: str) -> None:
        self.i18n.set_language(lang)
        self._apply_language()
        self._refresh_view()

    def _highlight_lang_buttons(self) -> None:
        active = {"relief": "sunken", "bg": "#dbeafe"}
        idle = {"relief": "raised", "bg": _idle_button_bg(self.btn_lang_en)}
        if self.i18n.lang == "en":
            self.btn_lang_en.configure(**active)
            self.btn_lang_ru.configure(**idle)
        else:
            self.btn_lang_ru.configure(**active)
            self.btn_lang_en.configure(**idle)

    def _apply_language(self) -> None:
        self.title(self.t("app.title"))
        self.lbl_title.configure(text=self.t("app.title"))
        self._highlight_lang_buttons()
        tabs = (
            (0, "tab.pipeline"),
            (1, "tab.pending"),
            (2, "tab.memory"),
            (3, "tab.mcp"),
            (4, "tab.log"),
        )
        for index, key in tabs:
            self.notebook.tab(index, text=self.t(key))
        self.grp_session.configure(text=self.t("session.group"))
        self.chk_seed.configure(text=self.t("session.seed_intuition"))
        self.chk_auto_exec.configure(text=self.t("session.auto_execute"))
        self.btn_reset.configure(text=self.t("session.reset"))
        self.grp_world.configure(text=self.t("scenario.group"))
        self.lbl_scenario.configure(text=self.t("scenario.label"))
        self.lbl_write.configure(text=self.t("write.group"))
        self.cmb_scenario["values"] = [self.t(f"scenario.{sid}") for sid in SCENARIOS]
        self.cmb_write["values"] = [self.t(f"write.{wid}") for wid in WRITE_OUTCOMES]
        self._select_combo(self.cmb_scenario, SCENARIOS, self.session.settings.scenario)
        self._select_combo(self.cmb_write, WRITE_OUTCOMES, self.session.world.write_status)
        self.grp_action.configure(text=self.t("action.group"))
        self.lbl_force.configure(text=self.t("action.label"))
        self.cmb_force["values"] = [self.t(f"action.{aid}") for aid in FORCE_ACTIONS]
        self._select_combo(self.cmb_force, FORCE_ACTIONS, self.session.agent.force_action or FORCE_AUTO)
        self.grp_clock.configure(text=self.t("clock.group"))
        self.lbl_clock.configure(text=self.t("clock.now"))
        self.btn_day.configure(text=self.t("clock.day"))
        self.btn_night.configure(text=self.t("clock.night"))
        self.btn_plus_hour.configure(text=self.t("clock.advance_hour"))
        self.lbl_min_ticks.configure(text=self.t("sleep.min_ticks"))
        self.lbl_sensor.configure(text=self.t("sensors.interval"))
        self.chk_fatigue.configure(text=self.t("sleep.fatigue_enable"))
        self.grp_run.configure(text=self.t("run.group"))
        self.btn_tick.configure(text=self.t("run.tick"))
        self.btn_burst.configure(text=self.t("run.burst"))
        self.btn_auto.configure(text=self.t("run.auto_start"))
        self.btn_stop.configure(text=self.t("run.auto_stop"))
        self.lbl_auto_ms.configure(text=self.t("run.auto_ms"))
        self.btn_probe.configure(text=self.t("probe.high_write"))
        self.grp_approval.configure(text=self.t("approval.group"))
        self.lbl_reason.configure(text=self.t("approval.reason"))
        self.lbl_qty.configure(text=self.t("approval.qty"))
        self.btn_approve.configure(text=self.t("approval.approve"))
        self.btn_reject.configure(text=self.t("approval.reject"))
        self.btn_modify.configure(text=self.t("approval.modify"))
        self.lbl_ctx.configure(text=self.t("pipeline.context"))
        self.lbl_prop.configure(text=self.t("pipeline.proposed"))
        self.lbl_exec.configure(text=self.t("pipeline.execution"))
        self.lbl_hint.configure(text=self.t("hint.body"))
        self._headings(self.tree_pending, ("col.id", "col.tool", "col.risk", "col.summary"))
        self._headings(self.tree_memory, ("col.path", "col.consequence", "col.reward"))
        self._headings(self.tree_mcp, ("col.tool", "col.params", "col.result"))

    def _headings(self, tree: ttk.Treeview, keys: tuple) -> None:
        for col, key in zip(tree["columns"], keys):
            tree.heading(col, text=self.t(key))
            tree.column(col, width=140 if col != "summary" and col != "path" else 360, stretch=True)

    def _select_combo(self, combo: ttk.Combobox, ids: tuple, current: str) -> None:
        try:
            index = list(ids).index(current)
        except ValueError:
            index = 0
        values = list(combo["values"] or [])
        if values:
            combo.current(min(index, len(values) - 1))

    def _combo_id(self, combo: ttk.Combobox, ids: tuple) -> str:
        values = list(combo["values"] or [])
        try:
            index = values.index(combo.get())
        except ValueError:
            index = 0
        return ids[index] if ids else ""

    # ------------------------------------------------------------------ actions
    def _collect_settings(self) -> LabSettings:
        clock = self._parse_clock(self.session.now)
        fatigue = None
        if self.var_fatigue_on.get():
            fatigue = float(self.var_fatigue.get())
        return LabSettings(
            seed_intuition=bool(self.var_seed.get()),
            auto_execute=bool(self.var_auto_exec.get()),
            scenario=self._combo_id(self.cmb_scenario, SCENARIOS),
            write_status=self._combo_id(self.cmb_write, WRITE_OUTCOMES),
            force_action=self._combo_id(self.cmb_force, FORCE_ACTIONS),
            clock=clock,
            sensor_refresh_interval_s=float(self.var_sensor_s.get() or 0.0),
            min_ticks_between_sleep=int(self.var_min_ticks.get() or 0),
            fatigue_override=fatigue,
        )

    def _parse_clock(self, fallback: datetime) -> datetime:
        raw = (self.var_clock.get() or "").strip()
        for fmt in ("%H:%M:%S", "%H:%M"):
            try:
                parsed = datetime.strptime(raw, fmt)
                return fallback.replace(hour=parsed.hour, minute=parsed.minute, second=getattr(parsed, "second", 0))
            except ValueError:
                continue
        return fallback

    def _on_reset(self) -> None:
        self._on_auto_stop()
        try:
            self.session.reset(self._collect_settings())
        except Exception as exc:
            self._set_status(self.t("status.error", error=str(exc)))
            messagebox.showerror(self.t("app.title"), str(exc))
            return
        self._refresh_view()
        snap = self.session.snapshot()
        self._set_status(self.t("status.reset", backend=snap["backend"]))

    def _on_scenario(self, _event=None) -> None:
        self.session.apply_scenario(self._combo_id(self.cmb_scenario, SCENARIOS))
        self._refresh_view()

    def _on_write(self, _event=None) -> None:
        self.session.set_write_status(self._combo_id(self.cmb_write, WRITE_OUTCOMES))

    def _on_force(self, _event=None) -> None:
        self.session.set_force_action(self._combo_id(self.cmb_force, FORCE_ACTIONS))

    def _on_clock_entry(self, _event=None) -> None:
        self.session.set_clock(self._parse_clock(self.session.now))
        self._refresh_view()

    def _set_hour(self, hour: int) -> None:
        self.session.set_clock(self.session.now.replace(hour=hour, minute=0, second=0))
        self._refresh_view()

    def _advance_hour(self) -> None:
        self.session.set_clock(self.session.now + timedelta(hours=1))
        self._refresh_view()

    def _on_fatigue(self) -> None:
        value = float(self.var_fatigue.get()) if self.var_fatigue_on.get() else None
        self.session.set_fatigue_override(value)

    def _sync_runtime_knobs(self) -> None:
        self.session.set_clock(self._parse_clock(self.session.now))
        settings = self.session.settings
        settings.min_ticks_between_sleep = int(self.var_min_ticks.get() or 0)
        settings.sensor_refresh_interval_s = float(self.var_sensor_s.get() or 0.0)
        if self.session.runtime is not None:
            self.session.runtime.sensor_refresh_interval_s = settings.sensor_refresh_interval_s
            self.session.runtime.sleep_scheduler.min_ticks_between_sleep = (
                settings.min_ticks_between_sleep
            )
        self._on_fatigue()
        self.session.set_force_action(self._combo_id(self.cmb_force, FORCE_ACTIONS))

    def _on_tick(self) -> None:
        self._sync_runtime_knobs()
        try:
            result = self.session.tick_once()
        except Exception as exc:
            self._set_status(self.t("status.error", error=str(exc)))
            messagebox.showerror(self.t("app.title"), str(exc))
            return
        self._refresh_view()
        self._set_status(self.t(
            "status.ticked",
            tick=self.session.tick_index,
            action=result.get("action_type") or "-",
            approval=result.get("approval_status") or "-",
        ))

    def _on_burst(self) -> None:
        self._sync_runtime_knobs()
        try:
            self.session.tick_many(10)
        except Exception as exc:
            self._set_status(self.t("status.error", error=str(exc)))
            messagebox.showerror(self.t("app.title"), str(exc))
            return
        self._refresh_view()
        self._set_status(self.t(
            "status.ticked",
            tick=self.session.tick_index,
            action=self.session.last_result.get("action_type") or "-",
            approval=self.session.last_result.get("approval_status") or "-",
        ))

    def _on_auto_start(self) -> None:
        if self._auto_job is not None:
            return
        self._set_status(self.t("status.auto"))
        self._auto_step()

    def _auto_step(self) -> None:
        self._on_tick()
        delay = max(80, int(self.var_auto_ms.get() or 400))
        self._auto_job = self.after(delay, self._auto_step)

    def _on_auto_stop(self) -> None:
        if self._auto_job is not None:
            self.after_cancel(self._auto_job)
            self._auto_job = None
            self._set_status(self.t("status.auto_stopped"))

    def _selected_action_id(self) -> Optional[str]:
        selection = self.tree_pending.selection()
        if not selection:
            pending = self.session.pending_rows()
            if len(pending) == 1:
                return pending[0]["action_id"]
            return None
        return selection[0]

    def _on_approve(self) -> None:
        action_id = self._selected_action_id()
        if not action_id:
            self._set_status(self.t("status.no_pending"))
            return
        self.session.approve(action_id)
        self._refresh_view()
        self._set_status(self.t("status.approved", action_id=action_id[:8]))

    def _on_reject(self) -> None:
        action_id = self._selected_action_id()
        if not action_id:
            self._set_status(self.t("status.no_pending"))
            return
        self.session.reject(action_id, reason=self.var_reason.get())
        self._refresh_view()
        self._set_status(self.t("status.rejected", action_id=action_id[:8]))

    def _on_modify(self) -> None:
        action_id = self._selected_action_id()
        if not action_id:
            self._set_status(self.t("status.no_pending"))
            return
        raw = (self.var_qty.get() or "").strip()
        try:
            qty = float(raw)
        except ValueError:
            self._set_status(self.t("status.error", error="qty"))
            return
        self.session.modify(action_id, {"qty": qty})
        self._refresh_view()
        self._set_status(self.t("status.modified", action_id=action_id[:8]))

    def _on_probe(self) -> None:
        result = self.session.probe_high_write_bypass()
        self._refresh_view()
        key = "status.probe_ok" if result.get("ok") else "status.probe_fail"
        self._set_status(self.t(key))

    def _on_pending_select(self, _event=None) -> None:
        action_id = self._selected_action_id()
        if not action_id:
            return
        for row in self.session.pending_rows():
            if row["action_id"] == action_id:
                qty = row.get("params", {}).get("qty")
                if qty is not None:
                    self.var_qty.set(str(qty))
                break

    # ------------------------------------------------------------------ view
    def _risk_label(self, code: str) -> str:
        key = f"risk.{code}"
        text = self.t(key)
        return str(code or "") if text == key else text

    def _refresh_view(self) -> None:
        snap = self.session.snapshot()
        self.var_clock.set(self.session.now.strftime("%H:%M:%S"))
        self.lbl_backend.configure(text=self.t("session.backend", backend=snap["backend"]))
        self.lbl_live.configure(text=self.t(
            "live.line",
            tick=snap["tick"],
            now=snap["now"],
            action=snap.get("action_type") or "-",
            approval=snap.get("approval_status") or "-",
            episodes=snap["episodes"],
            pressure=float(snap.get("sleep_pressure") or 0.0),
            pending=len(snap.get("pending") or []),
        ))
        self._set_text(self.txt_ctx, " ".join(snap.get("context_events") or []) or self.t("pipeline.empty"))
        proposed = snap.get("proposed")
        if proposed:
            self._set_text(self.txt_prop, json.dumps(proposed, ensure_ascii=False, indent=2, default=str))
        else:
            self._set_text(self.txt_prop, self.t("pipeline.empty"))
        execution = snap.get("execution_result")
        if execution:
            self._set_text(self.txt_exec, json.dumps(execution, ensure_ascii=False, indent=2, default=str))
        else:
            self._set_text(self.txt_exec, self.t("pipeline.empty"))

        self._fill_tree(
            self.tree_pending,
            [
                (row["action_id"], row["action_id"][:8], row["tool_id"], self._risk_label(row["risk"]), row["summary"])
                for row in snap.get("pending") or []
            ],
        )
        self._fill_tree(
            self.tree_memory,
            [
                (str(i), " ".join(row["path"]), row["consequence"], str(row.get("reward")))
                for i, row in enumerate(snap.get("episode_rows") or [])
            ],
        )
        self._fill_tree(
            self.tree_mcp,
            [
                (str(i), row["tool_id"], json.dumps(row["params"], ensure_ascii=False, default=str),
                 json.dumps(row["result"], ensure_ascii=False, default=str))
                for i, row in enumerate(snap.get("mcp_history") or [])
            ],
        )
        self._set_text(self.txt_log, "\n".join(snap.get("log") or []))

    def _fill_tree(self, tree: ttk.Treeview, rows: List[tuple]) -> None:
        selected = set(tree.selection())
        tree.delete(*tree.get_children())
        for row in rows:
            iid, values = row[0], row[1:]
            tree.insert("", "end", iid=iid, values=values)
            if iid in selected:
                tree.selection_add(iid)

    def _set_text(self, widget: tk.Text, value: str) -> None:
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", value)
        widget.see("end")
        widget.configure(state="normal")

    def _set_status(self, text: str) -> None:
        self.lbl_status.configure(text=text)

    def _on_close(self) -> None:
        self._on_auto_stop()
        self.destroy()


def main(argv: Optional[list[str]] = None) -> int:
    import argparse

    raw = list(sys.argv[1:] if argv is None else argv)
    preview = None
    if "--lang" in raw:
        index = raw.index("--lang")
        if index + 1 < len(raw):
            preview = raw[index + 1]
    help_i18n = I18n(lang=preview or "en", force=preview in ("en", "ru"))
    parser = argparse.ArgumentParser(description=help_i18n.t("cli.description"))
    parser.add_argument(
        "--lang",
        choices=("en", "ru"),
        default=None,
        help=help_i18n.t("cli.lang_help"),
    )
    args = parser.parse_args(argv)
    app = BodyLabApp(lang=args.lang)
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
