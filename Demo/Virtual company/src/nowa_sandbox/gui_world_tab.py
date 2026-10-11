"""World tab: authored curriculum (quarters × products/suppliers/offers)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, simpledialog, ttk
except ImportError:  # pragma: no cover - minimal Python builds omit Tk
    tk = None  # type: ignore[assignment]
    filedialog = None  # type: ignore[assignment]
    messagebox = None  # type: ignore[assignment]
    simpledialog = None  # type: ignore[assignment]
    ttk = None  # type: ignore[assignment]

from nowa_sandbox.procurement_fitness import GRADUATION_THRESHOLDS
from nowa_sandbox.procurement_world import ProcurementWorldConfig
from nowa_sandbox.world_curriculum import (
    WorldCurriculum,
    default_template_quarter,
)
from nowa_sandbox.world_editor import (
    OFFER_EDIT_FIELDS,
    PRODUCT_EDIT_FIELDS,
    SUPPLIER_EDIT_FIELDS,
)


PRODUCT_COLS = ("product_id",) + PRODUCT_EDIT_FIELDS
SUPPLIER_COLS = ("supplier_id",) + SUPPLIER_EDIT_FIELDS
OFFER_COLS = ("product_id", "supplier_id") + OFFER_EDIT_FIELDS


def init_world_vars(app: Any) -> None:
    if getattr(app, "thresh_vars", None):
        return
    defaults = dict(GRADUATION_THRESHOLDS)
    app.thresh_vars = {k: tk.StringVar(value=str(v)) for k, v in defaults.items()}
    app.products_var = tk.StringVar(value="10")
    app.suppliers_var = tk.StringVar(value="5")
    app.budget_var = tk.StringVar(value="100000")
    app.demand_shock_var = tk.StringVar(value="0.05")
    app.supplier_default_var = tk.StringVar(value="0.003")
    app.max_lead_var = tk.StringVar(value="10")
    app.max_demand_var = tk.StringVar(value="30")
    app.min_reliability_var = tk.StringVar(value="0.80")
    app.world_budget_edit_var = tk.StringVar(value="100000")
    app.world_info_var = tk.StringVar(value="")
    app.max_cycles_var = tk.StringVar(value="500")
    if not hasattr(app, "_curriculum") or app._curriculum is None:
        app._curriculum = WorldCurriculum.from_template(n_quarters=1)
    app._selected_curriculum_q = 1


def build_world_tab(app: Any) -> None:
    init_world_vars(app)
    root = app.tab_world
    root.columnconfigure(0, weight=1)
    root.rowconfigure(2, weight=1)

    app.frm_tuning = ttk.LabelFrame(root, padding=8)
    app.frm_tuning.grid(row=0, column=0, sticky="ew", padx=4, pady=4)
    for i in range(8):
        app.frm_tuning.columnconfigure(i, weight=1)

    app.lbl_th_cost = ttk.Label(app.frm_tuning)
    app.lbl_th_stock = ttk.Label(app.frm_tuning)
    app.lbl_th_budget = ttk.Label(app.frm_tuning)
    app.lbl_th_risk = ttk.Label(app.frm_tuning)
    app.lbl_th_div = ttk.Label(app.frm_tuning)
    app.lbl_th_cons = ttk.Label(app.frm_tuning)
    for lbl, key, col in (
        (app.lbl_th_cost, "cost_efficiency", 0),
        (app.lbl_th_stock, "stockout_avoidance", 2),
        (app.lbl_th_budget, "budget_discipline", 4),
        (app.lbl_th_risk, "reaction_to_risk_events", 6),
    ):
        lbl.grid(row=0, column=col, sticky="w")
        ttk.Entry(app.frm_tuning, textvariable=app.thresh_vars[key], width=6).grid(
            row=0, column=col + 1, sticky="w", padx=4
        )
    app.lbl_th_div.grid(row=1, column=0, sticky="w")
    ttk.Entry(
        app.frm_tuning, textvariable=app.thresh_vars["supplier_diversification"], width=6
    ).grid(row=1, column=1, sticky="w", padx=4)
    app.lbl_th_cons.grid(row=1, column=2, sticky="w")
    ttk.Entry(
        app.frm_tuning, textvariable=app.thresh_vars["decision_consistency"], width=6
    ).grid(row=1, column=3, sticky="w", padx=4)

    app.lbl_budget_amt = ttk.Label(app.frm_tuning)
    app.lbl_shock = ttk.Label(app.frm_tuning)
    app.lbl_default_p = ttk.Label(app.frm_tuning)
    app.lbl_max_cycles = ttk.Label(app.frm_tuning)

    app.lbl_budget_amt.grid(row=2, column=0, sticky="w")
    ttk.Entry(app.frm_tuning, textvariable=app.budget_var, width=10).grid(
        row=2, column=1, sticky="w", padx=4
    )
    app.lbl_shock.grid(row=2, column=2, sticky="w")
    ttk.Entry(app.frm_tuning, textvariable=app.demand_shock_var, width=6).grid(
        row=2, column=3, sticky="w", padx=4
    )
    app.lbl_default_p.grid(row=2, column=4, sticky="w")
    ttk.Entry(app.frm_tuning, textvariable=app.supplier_default_var, width=6).grid(
        row=2, column=5, sticky="w", padx=4
    )
    app.lbl_max_cycles.grid(row=3, column=0, sticky="w")
    ttk.Entry(app.frm_tuning, textvariable=app.max_cycles_var, width=6).grid(
        row=3, column=1, sticky="w", padx=4
    )

    # Keep legacy knobs for CLI/RNG fallbacks (hidden from main flow but used by config_from_app).
    app.lbl_products = ttk.Label(app.frm_tuning)
    app.lbl_suppliers = ttk.Label(app.frm_tuning)
    app.lbl_max_lead = ttk.Label(app.frm_tuning)
    app.lbl_max_demand = ttk.Label(app.frm_tuning)
    app.lbl_min_rel = ttk.Label(app.frm_tuning)

    mid = ttk.Frame(root)
    mid.grid(row=1, column=0, sticky="ew", padx=4, pady=4)
    mid.columnconfigure(1, weight=1)

    qframe = ttk.LabelFrame(mid, padding=4)
    qframe.grid(row=0, column=0, sticky="nsw", padx=(0, 8))
    app.frm_world_quarters = qframe
    app.lbl_world_quarters = ttk.Label(qframe)
    app.lbl_world_quarters.pack(anchor="w")
    app.list_quarters = tk.Listbox(qframe, height=10, width=14, exportselection=False)
    app.list_quarters.pack(fill="y", pady=4)
    app.list_quarters.bind("<<ListboxSelect>>", lambda _e: _on_quarter_select(app))

    qbtns = ttk.Frame(qframe)
    qbtns.pack(fill="x")
    app.btn_q_add = ttk.Button(qbtns, command=lambda: add_curriculum_quarter(app))
    app.btn_q_dup = ttk.Button(qbtns, command=lambda: duplicate_curriculum_quarter(app))
    app.btn_q_del = ttk.Button(qbtns, command=lambda: remove_curriculum_quarter(app))
    app.btn_q_add.pack(fill="x", pady=1)
    app.btn_q_dup.pack(fill="x", pady=1)
    app.btn_q_del.pack(fill="x", pady=1)

    bar = ttk.Frame(mid)
    bar.grid(row=0, column=1, sticky="ew")
    app.btn_world_apply = ttk.Button(bar, command=lambda: apply_editor_to_curriculum(app))
    app.btn_world_save_file = ttk.Button(bar, command=lambda: save_curriculum_file(app))
    app.btn_world_load_file = ttk.Button(bar, command=lambda: load_curriculum_file(app))
    app.btn_world_template = ttk.Button(bar, command=lambda: fill_template_quarter(app))
    for b in (
        app.btn_world_apply,
        app.btn_world_save_file,
        app.btn_world_load_file,
        app.btn_world_template,
    ):
        b.pack(side="left", padx=3)
    ttk.Label(bar, textvariable=app.world_info_var, foreground="#555").pack(
        side="left", padx=8
    )

    paned = ttk.Panedwindow(root, orient="vertical")
    paned.grid(row=2, column=0, sticky="nsew", padx=4, pady=4)

    products_frame = ttk.LabelFrame(paned, padding=4)
    suppliers_frame = ttk.LabelFrame(paned, padding=4)
    offers_frame = ttk.LabelFrame(paned, padding=4)
    paned.add(products_frame, weight=2)
    paned.add(suppliers_frame, weight=1)
    paned.add(offers_frame, weight=1)
    app.frm_world_products = products_frame
    app.frm_world_suppliers = suppliers_frame
    app.frm_world_offers = offers_frame

    # --- Products: command bar ABOVE the table (buttons left, budget right) ---
    prod_bar = ttk.Frame(products_frame)
    prod_bar.pack(fill="x", pady=(0, 4))
    app.btn_prod_add, app.btn_prod_del = _pack_table_command_bar(
        prod_bar,
        on_add=lambda: _add_product_row(app),
        on_delete=lambda: _delete_product_rows(app),
        side="left",
    )
    budget_box = ttk.Frame(prod_bar)
    budget_box.pack(side="right")
    app.lbl_world_budget = ttk.Label(budget_box)
    app.lbl_world_budget.pack(side="left")
    ttk.Entry(budget_box, textvariable=app.world_budget_edit_var, width=12).pack(
        side="left", padx=(4, 0)
    )

    app.tree_products = ttk.Treeview(
        products_frame, columns=PRODUCT_COLS, show="headings", height=5
    )
    for c in PRODUCT_COLS:
        app.tree_products.heading(c, text=c)
        app.tree_products.column(c, width=100 if c != "product_id" else 90, anchor="e")
    app.tree_products.pack(fill="both", expand=True)
    app.tree_products.bind(
        "<Double-1>", lambda e: _edit_tree_cell(app, app.tree_products, PRODUCT_COLS)
    )
    app.tree_products.bind("<Delete>", lambda _e: _delete_product_rows(app))

    # --- Suppliers ---
    sup_bar = ttk.Frame(suppliers_frame)
    sup_bar.pack(fill="x", pady=(0, 4))
    app.btn_sup_add, app.btn_sup_del = _pack_table_command_bar(
        sup_bar,
        on_add=lambda: _add_supplier_row(app),
        on_delete=lambda: _delete_supplier_rows(app),
        side="left",
    )

    app.tree_suppliers = ttk.Treeview(
        suppliers_frame, columns=SUPPLIER_COLS, show="headings", height=4
    )
    for c in SUPPLIER_COLS:
        app.tree_suppliers.heading(c, text=c)
        app.tree_suppliers.column(c, width=100 if c != "supplier_id" else 90, anchor="e")
    app.tree_suppliers.pack(fill="both", expand=True)
    app.tree_suppliers.bind(
        "<Double-1>", lambda e: _edit_tree_cell(app, app.tree_suppliers, SUPPLIER_COLS)
    )
    app.tree_suppliers.bind("<Delete>", lambda _e: _delete_supplier_rows(app))

    # --- Offers ---
    offer_bar = ttk.Frame(offers_frame)
    offer_bar.pack(fill="x", pady=(0, 4))
    app.btn_offer_add, app.btn_offer_del = _pack_table_command_bar(
        offer_bar,
        on_add=lambda: _add_offer_row(app),
        on_delete=lambda: _delete_offer_rows(app),
        side="left",
    )

    app.tree_offers = ttk.Treeview(
        offers_frame, columns=OFFER_COLS, show="headings", height=4
    )
    for c in OFFER_COLS:
        app.tree_offers.heading(c, text=c)
        app.tree_offers.column(c, width=90, anchor="e")
    app.tree_offers.pack(fill="both", expand=True)
    app.tree_offers.bind(
        "<Double-1>", lambda e: _edit_tree_cell(app, app.tree_offers, OFFER_COLS)
    )
    app.tree_offers.bind("<Delete>", lambda _e: _delete_offer_rows(app))

    refresh_quarter_list(app)
    load_selected_quarter_into_editor(app)


def _pack_table_command_bar(
    parent: ttk.Frame,
    *,
    on_add,
    on_delete,
    side: str = "left",
) -> tuple:
    """Visible toolbar with labeled Add / Delete buttons (icons + text)."""
    bar = ttk.Frame(parent)
    bar.pack(side=side)
    btn_add = tk.Button(
        bar,
        text="➕ Добавить",
        command=on_add,
        padx=10,
        pady=2,
        cursor="hand2",
        relief="raised",
    )
    btn_del = tk.Button(
        bar,
        text="🗑 Удалить",
        command=on_delete,
        padx=10,
        pady=2,
        cursor="hand2",
        relief="raised",
    )
    btn_add.pack(side="left", padx=(0, 6))
    btn_del.pack(side="left")
    return btn_add, btn_del


def apply_world_column_headers(app: Any) -> None:
    t = app.t
    if hasattr(app, "tree_products"):
        for c in PRODUCT_COLS:
            app.tree_products.heading(c, text=t(f"col.{c}"))
    if hasattr(app, "tree_suppliers"):
        for c in SUPPLIER_COLS:
            app.tree_suppliers.heading(c, text=t(f"col.{c}"))
    if hasattr(app, "tree_offers"):
        for c in OFFER_COLS:
            app.tree_offers.heading(c, text=t(f"col.{c}"))


def config_from_app(app: Any) -> ProcurementWorldConfig:
    n_prod = 1
    n_sup = 1
    try:
        cur = getattr(app, "_curriculum", None)
        if cur is not None and cur.n_quarters >= 1:
            spec = cur.get_quarter(1)
            n_prod = max(1, len(spec.get("products") or []))
            n_sup = max(1, len(spec.get("suppliers") or []))
    except Exception:
        pass
    return ProcurementWorldConfig(
        initial_budget=float(app.budget_var.get()),
        n_products=n_prod,
        n_suppliers=n_sup,
        days_per_quarter=int(app.days_var.get()),
        demand_shock_probability=float(app.demand_shock_var.get()),
        supplier_default_probability=float(app.supplier_default_var.get()),
        seed=int(app.seed_var.get()),
        max_lead_time_days=int(getattr(app, "max_lead_var", tk.StringVar(value="10")).get()),
        max_demand_per_day=float(
            getattr(app, "max_demand_var", tk.StringVar(value="30")).get()
        ),
        min_supplier_reliability=float(
            getattr(app, "min_reliability_var", tk.StringVar(value="0.80")).get()
        ),
    )


def refresh_quarter_list(app: Any) -> None:
    cur: WorldCurriculum = app._curriculum
    app.list_quarters.delete(0, tk.END)
    for q in cur.quarter_indices():
        app.list_quarters.insert(tk.END, f"Q{q}")
    if cur.n_quarters:
        idx = max(0, min(app._selected_curriculum_q, cur.n_quarters) - 1)
        app.list_quarters.selection_clear(0, tk.END)
        app.list_quarters.selection_set(idx)
        app.list_quarters.activate(idx)
        app._selected_curriculum_q = idx + 1
    _update_info(app)


def _on_quarter_select(app: Any) -> None:
    sel = app.list_quarters.curselection()
    if not sel:
        return
    # Persist current editor into previously selected quarter first.
    apply_editor_to_curriculum(app, silent=True)
    app._selected_curriculum_q = int(sel[0]) + 1
    load_selected_quarter_into_editor(app)


def load_selected_quarter_into_editor(app: Any) -> None:
    cur: WorldCurriculum = app._curriculum
    q = int(app._selected_curriculum_q)
    if q not in cur.quarter_indices():
        if cur.n_quarters:
            q = 1
            app._selected_curriculum_q = 1
        else:
            _fill_tree(app.tree_products, PRODUCT_COLS, [])
            _fill_tree(app.tree_suppliers, SUPPLIER_COLS, [])
            _fill_tree(app.tree_offers, OFFER_COLS, [])
            return
    spec = cur.get_quarter(q)
    app.world_budget_edit_var.set(str(spec.get("budget", app.budget_var.get())))
    _fill_tree(app.tree_products, PRODUCT_COLS, list(spec.get("products") or []))
    _fill_tree(app.tree_suppliers, SUPPLIER_COLS, list(spec.get("suppliers") or []))
    _fill_tree(app.tree_offers, OFFER_COLS, list(spec.get("offers") or []))
    _update_info(app)


def apply_editor_to_curriculum(app: Any, *, silent: bool = False) -> bool:
    cur: WorldCurriculum = app._curriculum
    q = int(app._selected_curriculum_q)
    if cur.n_quarters < 1:
        return False
    try:
        budget = float(app.world_budget_edit_var.get())
    except ValueError:
        if not silent:
            messagebox.showerror(app.t("dialog.invalid"), app.t("world.bad_budget"))
        return False
    products = _rows_from_tree(app.tree_products, PRODUCT_COLS)
    suppliers = _rows_from_tree(app.tree_suppliers, SUPPLIER_COLS)
    offers = _rows_from_tree(app.tree_offers, OFFER_COLS)
    cur.set_quarter(
        q,
        {
            "budget": budget,
            "products": products,
            "suppliers": suppliers,
            "offers": offers,
        },
    )
    if not silent:
        app.world_info_var.set(app.t("world.info_saved", q=q, n=cur.n_quarters))
        app.status_var.set(app.world_info_var.get())
    _update_info(app)
    _sync_run_curriculum_label(app)
    return True


def add_curriculum_quarter(app: Any) -> None:
    apply_editor_to_curriculum(app, silent=True)
    cur: WorldCurriculum = app._curriculum
    src = app._selected_curriculum_q if cur.n_quarters else None
    new_q = cur.add_quarter(copy_from=src) if src else cur.add_quarter()
    app._selected_curriculum_q = new_q
    refresh_quarter_list(app)
    load_selected_quarter_into_editor(app)


def duplicate_curriculum_quarter(app: Any) -> None:
    apply_editor_to_curriculum(app, silent=True)
    cur: WorldCurriculum = app._curriculum
    if cur.n_quarters < 1:
        return
    new_q = cur.duplicate_quarter(app._selected_curriculum_q)
    app._selected_curriculum_q = new_q
    refresh_quarter_list(app)
    load_selected_quarter_into_editor(app)


def remove_curriculum_quarter(app: Any) -> None:
    cur: WorldCurriculum = app._curriculum
    if cur.n_quarters <= 1:
        messagebox.showinfo(app.t("tab.world"), app.t("world.need_one_quarter"))
        return
    apply_editor_to_curriculum(app, silent=True)
    cur.remove_quarter(app._selected_curriculum_q)
    app._selected_curriculum_q = min(app._selected_curriculum_q, cur.n_quarters)
    refresh_quarter_list(app)
    load_selected_quarter_into_editor(app)


def fill_template_quarter(app: Any) -> None:
    cur: WorldCurriculum = app._curriculum
    if cur.n_quarters < 1:
        cur.add_quarter()
        app._selected_curriculum_q = 1
    try:
        budget = float(app.budget_var.get())
    except ValueError:
        budget = 100_000.0
    cur.set_quarter(app._selected_curriculum_q, default_template_quarter(budget=budget))
    load_selected_quarter_into_editor(app)
    app.world_info_var.set(app.t("world.info_template", q=app._selected_curriculum_q))


def save_curriculum_file(app: Any) -> None:
    apply_editor_to_curriculum(app, silent=True)
    cur: WorldCurriculum = app._curriculum
    errors = cur.validate()
    if errors:
        messagebox.showerror(
            app.t("dialog.invalid"),
            app.t("world.invalid_curriculum") + "\n" + "\n".join(errors[:8]),
        )
        return
    worlds_dir = Path(getattr(app, "demo_root", Path("."))) / "worlds"
    worlds_dir.mkdir(parents=True, exist_ok=True)
    path = filedialog.asksaveasfilename(
        parent=app,
        initialdir=str(worlds_dir),
        defaultextension=".json",
        filetypes=[("JSON", "*.json")],
        title=app.t("world.save_file"),
    )
    if not path:
        return
    cur.save_json(path)
    msg = app.t("world.info_file_saved", path=path, n=cur.n_quarters)
    app.world_info_var.set(msg)
    app.status_var.set(msg)


def load_curriculum_file(app: Any) -> None:
    worlds_dir = Path(getattr(app, "demo_root", Path("."))) / "worlds"
    worlds_dir.mkdir(parents=True, exist_ok=True)
    path = filedialog.askopenfilename(
        parent=app,
        initialdir=str(worlds_dir),
        filetypes=[("JSON", "*.json")],
        title=app.t("world.load_file"),
    )
    if not path:
        return
    try:
        cur = WorldCurriculum.load_json(path)
        errors = cur.validate()
        if errors:
            messagebox.showerror(
                app.t("dialog.invalid"),
                app.t("world.invalid_curriculum") + "\n" + "\n".join(errors[:8]),
            )
            return
        app._curriculum = cur
        app._selected_curriculum_q = 1
        refresh_quarter_list(app)
        load_selected_quarter_into_editor(app)
        msg = app.t("world.info_file_loaded", path=path, n=cur.n_quarters)
        app.world_info_var.set(msg)
        app.status_var.set(msg)
    except Exception as exc:
        messagebox.showerror(app.t("dialog.invalid"), str(exc))


def get_curriculum_for_run(app: Any) -> WorldCurriculum:
    apply_editor_to_curriculum(app, silent=True)
    cur: WorldCurriculum = app._curriculum
    errors = cur.validate()
    if errors:
        raise ValueError("; ".join(errors))
    return cur


def _update_info(app: Any) -> None:
    cur: WorldCurriculum = getattr(app, "_curriculum", None)
    if cur is None:
        return
    q = int(getattr(app, "_selected_curriculum_q", 1) or 1)
    n_offers = 0
    try:
        n_offers = len(cur.get_quarter(q).get("offers") or [])
    except Exception:
        pass
    app.world_info_var.set(
        app.t("world.info_status", n=cur.n_quarters, q=q, offers=n_offers)
    )
    _sync_run_curriculum_label(app)


def _sync_run_curriculum_label(app: Any) -> None:
    cur = getattr(app, "_curriculum", None)
    var = getattr(app, "curriculum_summary_var", None)
    if var is None or cur is None:
        return
    try:
        max_cycles = int(app.max_cycles_var.get())
    except Exception:
        max_cycles = 500
    var.set(
        app.t(
            "run.curriculum_summary",
            n=cur.n_quarters,
            cycles=max_cycles,
        )
    )


def _fill_tree(tree: ttk.Treeview, cols: tuple, rows: List[Dict[str, Any]]) -> None:
    for item in tree.get_children():
        tree.delete(item)
    for row in rows:
        values = []
        for c in cols:
            val = row.get(c, "")
            if isinstance(val, float):
                values.append(f"{val:.4g}")
            elif isinstance(val, bool):
                values.append("1" if val else "0")
            else:
                values.append(val)
        tree.insert("", "end", values=values)


def _rows_from_tree(tree: ttk.Treeview, cols: tuple) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for item in tree.get_children():
        values = tree.item(item, "values")
        row: Dict[str, Any] = {}
        for i, c in enumerate(cols):
            raw = values[i] if i < len(values) else ""
            if c.endswith("_id"):
                row[c] = str(raw)
            elif c == "is_defaulted":
                row[c] = str(raw).strip() in ("1", "true", "True", "yes", "да")
            elif c == "lead_time_days":
                try:
                    row[c] = int(float(raw))
                except Exception:
                    row[c] = 5
            else:
                try:
                    row[c] = float(raw)
                except Exception:
                    row[c] = 0.0
        rows.append(row)
    return rows


def _delete_selected(tree: ttk.Treeview) -> None:
    for item in tree.selection():
        tree.delete(item)


def _next_id(prefix: str, existing: List[str]) -> str:
    n = 1
    have = set(existing)
    while f"{prefix}_{n:03d}" in have:
        n += 1
    return f"{prefix}_{n:03d}"


def _default_product(pid: str) -> Dict[str, Any]:
    return {
        "product_id": pid,
        "base_demand_per_day": 10.0,
        "demand_volatility": 0.15,
        "holding_cost_per_unit": 1.0,
        "stockout_penalty_per_unit": 10.0,
        "current_stock": 200.0,
        "reorder_point": 80.0,
    }


def _default_supplier(sid: str) -> Dict[str, Any]:
    return {"supplier_id": sid, "reputation": 0.5, "is_defaulted": False}


def _default_offer(pid: str, sid: str) -> Dict[str, Any]:
    return {
        "product_id": pid,
        "supplier_id": sid,
        "unit_price": 1.0,
        "lead_time_days": 5,
        "reliability": 0.9,
        "price_volatility": 0.05,
    }


def _offer_pairs(offers: List[Dict[str, Any]]) -> set:
    return {
        (str(r.get("product_id") or ""), str(r.get("supplier_id") or ""))
        for r in offers
    }


def _selected_ids(tree: ttk.Treeview, id_col: str) -> List[str]:
    ids: List[str] = []
    for item in tree.selection():
        ids.append(str(tree.set(item, id_col)))
    return ids


def _focus_or_first_id(tree: ttk.Treeview, id_col: str, rows: List[Dict[str, Any]]) -> Optional[str]:
    item = tree.focus()
    if item:
        return str(tree.set(item, id_col))
    if rows:
        return str(rows[0].get(id_col) or "")
    return None


def _refresh_offers_keeping(app: Any, offers: List[Dict[str, Any]]) -> None:
    _fill_tree(app.tree_offers, OFFER_COLS, offers)
    _update_info(app)


def _delete_product_rows(app: Any) -> None:
    pids = set(_selected_ids(app.tree_products, "product_id"))
    if not pids:
        messagebox.showinfo(app.t("tab.world"), app.t("world.select_row"))
        return
    products = [
        r
        for r in _rows_from_tree(app.tree_products, PRODUCT_COLS)
        if str(r.get("product_id")) not in pids
    ]
    offers = [
        r
        for r in _rows_from_tree(app.tree_offers, OFFER_COLS)
        if str(r.get("product_id")) not in pids
    ]
    _fill_tree(app.tree_products, PRODUCT_COLS, products)
    _refresh_offers_keeping(app, offers)
    app.world_info_var.set(app.t("world.info_cascade_product", n=len(pids)))


def _delete_supplier_rows(app: Any) -> None:
    sids = set(_selected_ids(app.tree_suppliers, "supplier_id"))
    if not sids:
        messagebox.showinfo(app.t("tab.world"), app.t("world.select_row"))
        return
    suppliers = [
        r
        for r in _rows_from_tree(app.tree_suppliers, SUPPLIER_COLS)
        if str(r.get("supplier_id")) not in sids
    ]
    offers = [
        r
        for r in _rows_from_tree(app.tree_offers, OFFER_COLS)
        if str(r.get("supplier_id")) not in sids
    ]
    _fill_tree(app.tree_suppliers, SUPPLIER_COLS, suppliers)
    _refresh_offers_keeping(app, offers)
    app.world_info_var.set(app.t("world.info_cascade_supplier", n=len(sids)))


def _delete_offer_rows(app: Any) -> None:
    if not app.tree_offers.selection():
        messagebox.showinfo(app.t("tab.world"), app.t("world.select_row"))
        return
    _delete_selected(app.tree_offers)
    _update_info(app)


def _ensure_link_offer(
    app: Any,
    *,
    product_id: str,
    supplier_id: str,
) -> None:
    offers = _rows_from_tree(app.tree_offers, OFFER_COLS)
    pairs = _offer_pairs(offers)
    if (product_id, supplier_id) not in pairs:
        offers.append(_default_offer(product_id, supplier_id))
        _fill_tree(app.tree_offers, OFFER_COLS, offers)


def _choose_offer_link(
    products: List[Dict[str, Any]],
    suppliers: List[Dict[str, Any]],
    offers: List[Dict[str, Any]],
    *,
    preferred_product_id: Optional[str] = None,
    preferred_supplier_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Pick product/supplier keys for a new offer without inventing a new product.

    Prefers ``preferred_product_id`` (else first product). Uses an unused
    supplier for that product; if every supplier already has an offer, asks
    the caller to create a new supplier (``create_supplier=True``).
    Only asks for a new product when the products table is empty.
    """
    pairs = _offer_pairs(offers)
    product_ids = [str(r.get("product_id") or "") for r in products if r.get("product_id")]
    supplier_ids = [str(r.get("supplier_id") or "") for r in suppliers if r.get("supplier_id")]

    if not product_ids:
        return {
            "product_id": preferred_product_id or "product_001",
            "supplier_id": preferred_supplier_id or (supplier_ids[0] if supplier_ids else "supplier_001"),
            "create_product": True,
            "create_supplier": not bool(supplier_ids),
        }

    pid = preferred_product_id if preferred_product_id in product_ids else product_ids[0]

    # Prefer preferred supplier if free for this product.
    if (
        preferred_supplier_id
        and preferred_supplier_id in supplier_ids
        and (pid, preferred_supplier_id) not in pairs
    ):
        return {
            "product_id": pid,
            "supplier_id": preferred_supplier_id,
            "create_product": False,
            "create_supplier": False,
        }

    for sid in supplier_ids:
        if (pid, sid) not in pairs:
            return {
                "product_id": pid,
                "supplier_id": sid,
                "create_product": False,
                "create_supplier": False,
            }

    # All existing suppliers already linked to this product → new supplier.
    return {
        "product_id": pid,
        "supplier_id": _next_id("supplier", supplier_ids),
        "create_product": False,
        "create_supplier": True,
    }


def _add_product_row(app: Any) -> None:
    products = _rows_from_tree(app.tree_products, PRODUCT_COLS)
    suppliers = _rows_from_tree(app.tree_suppliers, SUPPLIER_COLS)
    pid = _next_id("product", [r.get("product_id", "") for r in products])
    products.append(_default_product(pid))
    _fill_tree(app.tree_products, PRODUCT_COLS, products)

    if not suppliers:
        sid = _next_id("supplier", [])
        suppliers = [_default_supplier(sid)]
        _fill_tree(app.tree_suppliers, SUPPLIER_COLS, suppliers)
    else:
        sid = (
            _focus_or_first_id(app.tree_suppliers, "supplier_id", suppliers)
            or suppliers[0]["supplier_id"]
        )

    _ensure_link_offer(app, product_id=pid, supplier_id=str(sid))
    _update_info(app)
    app.world_info_var.set(app.t("world.info_linked_product", pid=pid, sid=sid))


def _add_supplier_row(app: Any) -> None:
    products = _rows_from_tree(app.tree_products, PRODUCT_COLS)
    suppliers = _rows_from_tree(app.tree_suppliers, SUPPLIER_COLS)
    sid = _next_id("supplier", [r.get("supplier_id", "") for r in suppliers])
    suppliers.append(_default_supplier(sid))
    _fill_tree(app.tree_suppliers, SUPPLIER_COLS, suppliers)

    if not products:
        pid = _next_id("product", [])
        products = [_default_product(pid)]
        _fill_tree(app.tree_products, PRODUCT_COLS, products)
    else:
        pid = (
            _focus_or_first_id(app.tree_products, "product_id", products)
            or products[0]["product_id"]
        )

    _ensure_link_offer(app, product_id=str(pid), supplier_id=sid)
    _update_info(app)
    app.world_info_var.set(app.t("world.info_linked_supplier", sid=sid, pid=pid))


def _add_offer_row(app: Any) -> None:
    """Add an offer for the selected/first product; never invent a new product."""
    products = _rows_from_tree(app.tree_products, PRODUCT_COLS)
    suppliers = _rows_from_tree(app.tree_suppliers, SUPPLIER_COLS)
    offers = _rows_from_tree(app.tree_offers, OFFER_COLS)

    preferred_pid = _focus_or_first_id(app.tree_products, "product_id", products)
    preferred_sid = _focus_or_first_id(app.tree_suppliers, "supplier_id", suppliers)
    choice = _choose_offer_link(
        products,
        suppliers,
        offers,
        preferred_product_id=preferred_pid,
        preferred_supplier_id=preferred_sid,
    )

    if choice["create_product"]:
        products = products + [_default_product(choice["product_id"])]
        _fill_tree(app.tree_products, PRODUCT_COLS, products)

    if choice["create_supplier"]:
        suppliers = suppliers + [_default_supplier(choice["supplier_id"])]
        _fill_tree(app.tree_suppliers, SUPPLIER_COLS, suppliers)

    pid = str(choice["product_id"])
    sid = str(choice["supplier_id"])
    pairs = _offer_pairs(offers)
    if (pid, sid) in pairs:
        messagebox.showinfo(app.t("tab.world"), app.t("world.offer_exists", pid=pid, sid=sid))
        return

    offers.append(_default_offer(pid, sid))
    _fill_tree(app.tree_offers, OFFER_COLS, offers)
    _update_info(app)
    app.world_info_var.set(app.t("world.info_linked_offer", pid=pid, sid=sid))


def _rename_offer_keys(
    offers: List[Dict[str, Any]],
    *,
    old_product: Optional[str] = None,
    new_product: Optional[str] = None,
    old_supplier: Optional[str] = None,
    new_supplier: Optional[str] = None,
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    seen = set()
    for row in offers:
        r = dict(row)
        if old_product and r.get("product_id") == old_product and new_product:
            r["product_id"] = new_product
        if old_supplier and r.get("supplier_id") == old_supplier and new_supplier:
            r["supplier_id"] = new_supplier
        pair = (str(r.get("product_id") or ""), str(r.get("supplier_id") or ""))
        if pair in seen:
            continue
        seen.add(pair)
        out.append(r)
    return out


def _edit_tree_cell(app: Any, tree: ttk.Treeview, cols: tuple) -> None:
    item = tree.focus()
    if not item:
        return
    col = tree.identify_column(tree.winfo_pointerx() - tree.winfo_rootx())
    try:
        col_index = int(col.replace("#", "")) - 1
    except Exception:
        col_index = 0
    if col_index < 0 or col_index >= len(cols):
        col_index = 0
    field = cols[col_index]
    old = tree.set(item, field)
    new = simpledialog.askstring(
        app.t("world.edit_title"), f"{field}:", initialvalue=str(old), parent=app
    )
    if new is None:
        return
    new_val = new.strip()
    if not new_val:
        return

    if field == "product_id" and tree is app.tree_products and new_val != old:
        existing = {
            str(r.get("product_id"))
            for r in _rows_from_tree(app.tree_products, PRODUCT_COLS)
        }
        if new_val in existing:
            messagebox.showerror(app.t("dialog.invalid"), app.t("world.dup_id", id=new_val))
            return
        tree.set(item, field, new_val)
        offers = _rename_offer_keys(
            _rows_from_tree(app.tree_offers, OFFER_COLS),
            old_product=str(old),
            new_product=new_val,
        )
        _refresh_offers_keeping(app, offers)
        return

    if field == "supplier_id" and tree is app.tree_suppliers and new_val != old:
        existing = {
            str(r.get("supplier_id"))
            for r in _rows_from_tree(app.tree_suppliers, SUPPLIER_COLS)
        }
        if new_val in existing:
            messagebox.showerror(app.t("dialog.invalid"), app.t("world.dup_id", id=new_val))
            return
        tree.set(item, field, new_val)
        offers = _rename_offer_keys(
            _rows_from_tree(app.tree_offers, OFFER_COLS),
            old_supplier=str(old),
            new_supplier=new_val,
        )
        _refresh_offers_keeping(app, offers)
        return

    if field in ("product_id", "supplier_id") and tree is app.tree_offers:
        # Keep offer pairs unique after manual key edit.
        tree.set(item, field, new_val)
        offers = _rows_from_tree(app.tree_offers, OFFER_COLS)
        # Drop duplicates that may appear after edit.
        deduped = []
        seen = set()
        for r in offers:
            pair = (str(r.get("product_id") or ""), str(r.get("supplier_id") or ""))
            if pair in seen:
                continue
            seen.add(pair)
            deduped.append(r)
        _fill_tree(app.tree_offers, OFFER_COLS, deduped)
        return

    tree.set(item, field, new_val)
