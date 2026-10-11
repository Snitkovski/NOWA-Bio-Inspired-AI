"""English / Russian UI strings for the procurement sandbox lab."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

DEFAULT_LANG = "en"
SUPPORTED = ("en", "ru")

# Unicode regional-indicator flags (Segoe UI Emoji on Windows).
FLAG_EN = "\U0001F1EC\U0001F1E7"  # 🇬🇧
FLAG_RU = "\U0001F1F7\U0001F1FA"  # 🇷🇺

# Internal criterion ids → i18n key suffix (col.<id> / crit.<id>).
CRITERION_KEYS = (
    "cost_efficiency",
    "stockout_avoidance",
    "budget_discipline",
    "supplier_diversification",
    "decision_consistency",
    "reaction_to_risk_events",
)

STRINGS: Dict[str, Dict[str, str]] = {
    "en": {
        "app.title": "NOWA Procurement Sandbox Lab  v{version}",
        "tab.run": "Run",
        "tab.world": "World",
        "tab.sweep": "Multi-seed",
        "tab.report": "Report / Baseline",
        "tab.results": "Results",
        "status.ready": "Ready.",
        "status.running": "Running…",
        "status.error": "Error: {error}",
        "status.finished": "Finished.",
        "status.finished_graduated": "Finished — graduated",
        "status.soft_stop": "Soft-stop requested… finishing current quarter.",
        "status.added_files": "Added {n} file(s) to Report tab.",
        "status.baseline_written": "Baseline written: {path}",
        "status.loaded_run": "Loaded {n} quarters into Run view.",
        "lang.en": "EN",
        "lang.ru": "RU",
        "lang.tooltip_en": "English",
        "lang.tooltip_ru": "Русский",
        "run.config": "Configuration",
        "run.stage": "Stage",
        "run.seed": "Seed",
        "run.quarters": "Quarters",
        "run.curriculum": "Curriculum",
        "run.curriculum_summary": "{n} Q · cycle until learned (max {cycles})",
        "run.days_q": "Days/Q",
        "run.stop_grad": "Stop on graduation",
        "run.seed_intuition": "Seed intuition",
        "run.config_yaml": "Config file",
        "run.baseline": "Baseline (1b)",
        "run.resume_ckpt": "Resume from",
        "run.output_json": "Output file",
        "run.checkpoint": "Checkpoint",
        "run.start": "Start",
        "run.soft_stop": "Soft Stop",
        "run.resume": "Resume from checkpoint",
        "run.open_results": "Open results folder",
        "run.live_empty": "Quarter —  |  passed —/—  |  graduated@—  |  streak —",
        "run.live": (
            "Quarter {q}  |  passed {n_pass}/{n}  |  graduated@{grad_at}  |  streak {streak}"
        ),
        "run.log": "Log",
        "run.fitness": "Scores by quarter",
        "col.q": "Q",
        "col.pass": "pass",
        "col.streak": "streak",
        "col.cost_efficiency": "cost",
        "col.stockout_avoidance": "stockout",
        "col.budget_discipline": "budget",
        "col.supplier_diversification": "diversify",
        "col.decision_consistency": "consist.",
        "col.reaction_to_risk_events": "risk",
        "crit.cost_efficiency": "cost efficiency",
        "crit.stockout_avoidance": "stockout avoidance",
        "crit.budget_discipline": "budget discipline",
        "crit.supplier_diversification": "supplier diversification",
        "crit.decision_consistency": "decision consistency",
        "crit.reaction_to_risk_events": "reaction to risk",
        "yes": "yes",
        "no": "no",
        "sweep.title": "Stage 1a multi-seed run (section 26.7)",
        "sweep.seeds": "Seeds (comma-separated)",
        "sweep.quarters_each": "Quarters each",
        "sweep.writes": (
            "Writes results/stage1a_lab_seed{N}.json and matching checkpoints."
        ),
        "sweep.start": "Start multi-seed",
        "sweep.to_report": "Send outputs to Report tab",
        "sweep.note": (
            "Progress and scores stream into the Run tab log / table / chart."
        ),
        "report.title": "Stage 1a result files",
        "report.add": "Add files…",
        "report.remove": "Remove selected",
        "report.clear": "Clear",
        "report.add_sweep": "Add multi-seed outputs",
        "report.write_to": "Write baseline to",
        "report.check": "Check readiness",
        "report.check_write": "Check + write baseline",
        "results.browse": "Browse…",
        "results.load": "Load",
        "results.to_run": "Load into Run chart/table",
        "results.info_empty": "Load a results JSON to inspect.",
        "results.info": "{name}: {n} quarters, {n_pass} passed",
        "chart.empty": "No quarter data yet",
        "dialog.busy_title": "Busy",
        "dialog.busy": "A run is already in progress.",
        "dialog.invalid_config": "Invalid config",
        "dialog.cannot_start": "Cannot start",
        "dialog.resume_title": "Resume",
        "dialog.resume_need_ckpt": (
            "Set Resume from or Checkpoint path first."
        ),
        "dialog.cannot_resume": "Cannot resume",
        "dialog.invalid": "Invalid",
        "dialog.seeds_int": "Seeds must be integers; check quarters.",
        "dialog.need_seed": "Provide at least one seed.",
        "dialog.cannot_sweep": "Cannot start multi-seed run",
        "dialog.no_files_title": "No files",
        "dialog.no_files": (
            "No lab/v13 multi-seed result files found for those seeds."
        ),
        "dialog.report_title": "Report",
        "dialog.report_need_files": "Add at least one Stage 1a results JSON.",
        "dialog.baseline_refused": "Baseline refused",
        "dialog.report_failed": "Report failed",
        "dialog.load_failed": "Load failed",
        "dialog.run_failed": "Sandbox run failed",
        "dialog.quit_title": "Quit",
        "dialog.quit_busy": (
            "A run is in progress. Soft-stop and quit?\n"
            "(Current quarter will finish and checkpoint will be saved.)"
        ),
        "filetypes.all": "All",
        "filetypes.data": "JSON / YAML / checkpoint",
        "filetypes.json": "JSON",
        "err.stage": "Stage must be 1a or 1b",
        "err.baseline_1b": "Stage 1b requires a baseline JSON path",
        "log.soft_stop": "[UI] Soft-stop requested.",
        "readiness.header_run": "run",
        "readiness.header_grad": "grad",
        "readiness.header_q": "q*",
        "readiness.header_n_ok": "n_ok",
        "readiness.graduated_runs": "Graduated runs: {n}/{total} (need 3)",
        "readiness.grad_quarters": "Graduation quarters: {quarters}",
        "readiness.spread": (
            "Spread ratio: {ratio} (half-width={half}; {within} tolerance)"
        ),
        "readiness.within": "within",
        "readiness.outside": "outside",
        "readiness.ready": "READY for Stage 1b",
        "readiness.not_ready": "NOT READY for Stage 1b",
        "readiness.baseline_refused": "\nBaseline: {msg}",
        "readiness.baseline_from": "\nBaseline from {chosen} -> {path}",
        "yes_short": "yes",
        "no_short": "no",
        "world.max_lead": "Max lead days",
        "world.max_demand": "Max demand/day",
        "world.min_reliability": "Min reliability",
        "world.quarter": "Quarter",
        "world.tuning": "World model & graduation thresholds",
        "world.load": "Load / generate",
        "world.save": "Save overrides",
        "world.clear": "Clear overrides",
        "world.from_run": "From Run selection",
        "world.budget_edit": "Budget",
        "world.products": "Products",
        "world.suppliers": "Suppliers",
        "world.offers": "Offers (product ↔ supplier)",
        "world.quarters_list": "Training quarters",
        "world.q_add": "Add quarter",
        "world.q_dup": "Duplicate",
        "world.q_del": "Remove",
        "world.apply": "Apply to quarter",
        "world.save_file": "Save curriculum…",
        "world.load_file": "Load curriculum…",
        "world.template": "Fill template",
        "world.row_add": "Add",
        "world.row_del": "Delete",
        "world.row_add_btn": "➕ Add",
        "world.row_del_btn": "🗑 Delete",
        "world.select_row": "Select one or more rows first.",
        "world.dup_id": "ID already exists: {id}",
        "world.info_cascade_product": "Removed {n} product(s) and linked offers.",
        "world.info_cascade_supplier": "Removed {n} supplier(s) and linked offers.",
        "world.info_linked_product": "Added {pid} and offer with {sid}.",
        "world.info_linked_supplier": "Added {sid} and offer with {pid}.",
        "world.info_linked_offer": "Added offer {pid} ↔ {sid}.",
        "world.offer_exists": "Offer already exists for {pid} ↔ {sid}.",
        "world.max_cycles": "Max cycles",
        "world.need_one_quarter": "Keep at least one quarter in the curriculum.",
        "world.bad_budget": "Budget must be a number.",
        "world.invalid_curriculum": "Curriculum is invalid:",
        "world.info_status": "Curriculum: {n} quarter(s) · editing Q{q} · offers: {offers}",
        "world.info_template": "Filled template for quarter {q}.",
        "world.info_file_saved": "Saved curriculum ({n} Q) → {path}",
        "world.info_file_loaded": "Loaded curriculum ({n} Q) ← {path}",
        "col.product_id": "product",
        "col.base_demand_per_day": "demand/day",
        "col.demand_volatility": "demand vol.",
        "col.holding_cost_per_unit": "holding cost",
        "col.stockout_penalty_per_unit": "stockout pen.",
        "col.current_stock": "stock",
        "col.reorder_point": "reorder pt",
        "col.supplier_id": "supplier",
        "col.reliability": "reliability",
        "col.base_price_multiplier": "price mult.",
        "col.price_volatility": "price vol.",
        "col.lead_time_days": "lead days",
        "col.reputation": "reputation",
        "col.is_defaulted": "defaulted",
        "col.unit_price": "unit price",
        "world.edit_title": "Edit value",
        "world.bad_quarter": "Quarter must be a positive integer.",
        "world.need_run_row": "Select a quarter row on the Run tab first.",
        "world.info_override": "Quarter {q}: custom overrides loaded.",
        "world.info_record": "Quarter {q}: from run results snapshot.",
        "world.info_generated": "Quarter {q}: generated from seed {seed}.",
        "world.info_saved": "Saved quarter {q} ({n} quarter(s) in curriculum).",
        "world.info_cleared": "Cleared overrides for quarter {q}.",
        "col.gate": "gate",
        "col.nr": "NR",
        "run.tuning": "Thresholds & world (global for the run)",
        "run.products": "Products",
        "run.suppliers": "Suppliers",
        "run.budget": "Budget",
        "run.demand_shock": "Demand shock p",
        "run.supplier_default": "Supplier default p",
        "run.thresh_diversify": "Diversify ≥",
        "run.thresh_consist": "Consistency ≥",
        "run.thresh_cost": "Cost ≥",
        "run.thresh_stockout": "Stockout ≥",
        "run.thresh_budget": "Budget ≥",
        "run.thresh_risk": "Risk ≥",
        "diag.title": "Quarter diagnosis (select a table row)",
        "diag.empty": "Select a quarter row to see why it passed or failed.",
        "diag.header": "Quarter {q}  ·  stage {stage}",
        "diag.verdict_line": "Verdict: {text}",
        "diag.monopoly_flag": "Single-supplier monopoly detected (score ≈ {score}).",
        "diag.flags": "all_passed={all_passed}  ·  qualifies for streak={qualifies}",
        "diag.gate_fail": "Gate failures: {items}",
        "diag.nr_fail": "Non-regression failures: {items}",
        "diag.table_header": "[G]=gating criterion   value / threshold",
        "diag.actions_header": "Action mix this quarter:",
        "diag.verdict.qualifies": "Clean quarter — counts toward graduation streak.",
        "diag.verdict.nr_blocks": (
            "Gating passed, but non-regression blocked the streak ({items})."
        ),
        "diag.verdict.monopoly": (
            "Failed diversification: all orders went to one supplier (~0.133)."
        ),
        "diag.verdict.gate_fail": "Stage {stage} gating failed: {items}.",
        "diag.verdict.unknown": "Could not determine a specific failure mode.",
    },
    "ru": {
        "app.title": "Лаборатория NOWA Procurement Sandbox  v{version}",
        "tab.run": "Запуск",
        "tab.world": "Мир",
        "tab.sweep": "Перебор",
        "tab.report": "Отчёт / эталон",
        "tab.results": "Результаты",
        "status.ready": "Готово.",
        "status.running": "Выполняется…",
        "status.error": "Ошибка: {error}",
        "status.finished": "Завершено.",
        "status.finished_graduated": "Завершено — выпуск",
        "status.soft_stop": "Мягкая остановка… завершается текущий квартал.",
        "status.added_files": "Добавлено файлов во вкладку «Отчёт»: {n}.",
        "status.baseline_written": "Эталон записан: {path}",
        "status.loaded_run": "Загружено кварталов во вкладку «Запуск»: {n}.",
        "lang.en": "EN",
        "lang.ru": "RU",
        "lang.tooltip_en": "English",
        "lang.tooltip_ru": "Русский",
        "run.config": "Конфигурация",
        "run.stage": "Этап",
        "run.seed": "Зерно",
        "run.quarters": "Кварталы",
        "run.curriculum": "Учебный план",
        "run.curriculum_summary": "{n} кв. · цикл до обучения (макс. {cycles})",
        "run.days_q": "Дней/кв.",
        "run.stop_grad": "Остановить при выпуске",
        "run.seed_intuition": "Засеять интуицию",
        "run.config_yaml": "Файл конфигурации",
        "run.baseline": "Эталон (1b)",
        "run.resume_ckpt": "Продолжить с",
        "run.output_json": "Файл результатов",
        "run.checkpoint": "Контрольная точка",
        "run.start": "Старт",
        "run.soft_stop": "Мягкий стоп",
        "run.resume": "Продолжить с точки",
        "run.open_results": "Папка результатов",
        "run.live_empty": "Квартал —  |  успехов —/—  |  выпуск@—  |  серия —",
        "run.live": (
            "Квартал {q}  |  успехов {n_pass}/{n}  |  выпуск@{grad_at}  |  серия {streak}"
        ),
        "run.log": "Журнал",
        "run.fitness": "Показатели по кварталам",
        "col.q": "кв.",
        "col.pass": "ок",
        "col.streak": "серия",
        "col.cost_efficiency": "стоимость",
        "col.stockout_avoidance": "дефицит",
        "col.budget_discipline": "бюджет",
        "col.supplier_diversification": "разнообр.",
        "col.decision_consistency": "стабил.",
        "col.reaction_to_risk_events": "риски",
        "crit.cost_efficiency": "эффективность затрат",
        "crit.stockout_avoidance": "избежание дефицита",
        "crit.budget_discipline": "дисциплина бюджета",
        "crit.supplier_diversification": "разнообразие поставщиков",
        "crit.decision_consistency": "согласованность решений",
        "crit.reaction_to_risk_events": "реакция на риски",
        "yes": "да",
        "no": "нет",
        "sweep.title": "Перебор зёрен Stage 1a (разд. 26.7)",
        "sweep.seeds": "Зёрна (через запятую)",
        "sweep.quarters_each": "Кварталов на зерно",
        "sweep.writes": (
            "Пишет results/stage1a_lab_seed{N}.json "
            "и соответствующие контрольные точки."
        ),
        "sweep.start": "Запустить перебор",
        "sweep.to_report": "Отправить в «Отчёт»",
        "sweep.note": (
            "Ход и показатели идут в журнал / таблицу / график вкладки «Запуск»."
        ),
        "report.title": "Файлы результатов этапа 1a",
        "report.add": "Добавить…",
        "report.remove": "Удалить выбранные",
        "report.clear": "Очистить",
        "report.add_sweep": "Добавить выводы перебора",
        "report.write_to": "Записать эталон в",
        "report.check": "Проверить готовность",
        "report.check_write": "Проверить и записать эталон",
        "results.browse": "Обзор…",
        "results.load": "Загрузить",
        "results.to_run": "В график и таблицу «Запуск»",
        "results.info_empty": "Загрузите JSON результатов для просмотра.",
        "results.info": "{name}: {n} кварталов, пройдено {n_pass}",
        "chart.empty": "Пока нет данных по кварталам",
        "dialog.busy_title": "Занято",
        "dialog.busy": "Уже выполняется запуск.",
        "dialog.invalid_config": "Неверная конфигурация",
        "dialog.cannot_start": "Не удалось запустить",
        "dialog.resume_title": "Продолжение",
        "dialog.resume_need_ckpt": (
            "Сначала укажите путь «Продолжить с» или контрольную точку."
        ),
        "dialog.cannot_resume": "Не удалось продолжить",
        "dialog.invalid": "Ошибка",
        "dialog.seeds_int": (
            "Зёрна должны быть целыми числами; проверьте число кварталов."
        ),
        "dialog.need_seed": "Укажите хотя бы одно зерно.",
        "dialog.cannot_sweep": "Не удалось запустить перебор",
        "dialog.no_files_title": "Нет файлов",
        "dialog.no_files": (
            "Не найдены файлы результатов перебора (lab/v13) для этих зёрен."
        ),
        "dialog.report_title": "Отчёт",
        "dialog.report_need_files": (
            "Добавьте хотя бы один JSON результатов этапа 1a."
        ),
        "dialog.baseline_refused": "Эталон отклонён",
        "dialog.report_failed": "Ошибка отчёта",
        "dialog.load_failed": "Ошибка загрузки",
        "dialog.run_failed": "Ошибка запуска песочницы",
        "dialog.quit_title": "Выход",
        "dialog.quit_busy": (
            "Идёт запуск. Сделать мягкий стоп и выйти?\n"
            "(Текущий квартал завершится, контрольная точка будет сохранена.)"
        ),
        "filetypes.all": "Все",
        "filetypes.data": "JSON / YAML / контрольная точка",
        "filetypes.json": "JSON",
        "err.stage": "Этап должен быть 1a или 1b",
        "err.baseline_1b": "Для этапа 1b нужен путь к файлу эталона (JSON)",
        "log.soft_stop": "[UI] Запрошен мягкий стоп.",
        "readiness.header_run": "прогон",
        "readiness.header_grad": "вып.",
        "readiness.header_q": "кв*",
        "readiness.header_n_ok": "n_ok",
        "readiness.graduated_runs": "Прогоны с выпуском: {n}/{total} (нужно 3)",
        "readiness.grad_quarters": "Кварталы выпуска: {quarters}",
        "readiness.spread": (
            "Разброс: {ratio} (полуширина={half}; {within} допуска)"
        ),
        "readiness.within": "в пределах",
        "readiness.outside": "вне",
        "readiness.ready": "ГОТОВО к этапу 1b",
        "readiness.not_ready": "НЕ ГОТОВО к этапу 1b",
        "readiness.baseline_refused": "\nЭталон: {msg}",
        "readiness.baseline_from": "\nЭталон из {chosen} → {path}",
        "yes_short": "да",
        "no_short": "нет",
        "world.max_lead": "Макс. срок поставки (дни)",
        "world.max_demand": "Макс. спрос/день",
        "world.min_reliability": "Мин. надёжность",
        "world.quarter": "Квартал",
        "world.tuning": "Модель мира и пороги выпуска",
        "world.load": "Загрузить / сгенерировать",
        "world.save": "Сохранить правки",
        "world.clear": "Сбросить правки",
        "world.from_run": "Из выбора на Запуске",
        "world.budget_edit": "Бюджет",
        "world.products": "Товары",
        "world.suppliers": "Поставщики",
        "world.offers": "Оферты (товар ↔ поставщик)",
        "world.quarters_list": "Кварталы обучения",
        "world.q_add": "Добавить квартал",
        "world.q_dup": "Дублировать",
        "world.q_del": "Удалить",
        "world.apply": "Применить к кварталу",
        "world.save_file": "Сохранить план…",
        "world.load_file": "Загрузить план…",
        "world.template": "Заполнить шаблон",
        "world.row_add": "Добавить",
        "world.row_del": "Удалить",
        "world.row_add_btn": "➕ Добавить",
        "world.row_del_btn": "🗑 Удалить",
        "world.select_row": "Сначала выберите одну или несколько строк.",
        "world.dup_id": "Такой ID уже есть: {id}",
        "world.info_cascade_product": "Удалено товаров: {n}, связанные оферты тоже удалены.",
        "world.info_cascade_supplier": "Удалено поставщиков: {n}, связанные оферты тоже удалены.",
        "world.info_linked_product": "Добавлен {pid} и оферта с {sid}.",
        "world.info_linked_supplier": "Добавлен {sid} и оферта с {pid}.",
        "world.info_linked_offer": "Добавлена оферта {pid} ↔ {sid}.",
        "world.offer_exists": "Оферта для {pid} ↔ {sid} уже есть.",
        "world.max_cycles": "Макс. циклов",
        "world.need_one_quarter": "В учебном плане должен остаться хотя бы один квартал.",
        "world.bad_budget": "Бюджет должен быть числом.",
        "world.invalid_curriculum": "Учебный план некорректен:",
        "world.info_status": "План: {n} кв. · редактируется Q{q} · оферт: {offers}",
        "world.info_template": "Шаблон заполнен для квартала {q}.",
        "world.info_file_saved": "План сохранён ({n} кв.) → {path}",
        "world.info_file_loaded": "План загружен ({n} кв.) ← {path}",
        "col.product_id": "товар",
        "col.base_demand_per_day": "спрос/день",
        "col.demand_volatility": "волатил. спроса",
        "col.holding_cost_per_unit": "хранение",
        "col.stockout_penalty_per_unit": "штраф дефицита",
        "col.current_stock": "склад",
        "col.reorder_point": "точка заказа",
        "col.supplier_id": "поставщик",
        "col.reliability": "надёжность",
        "col.base_price_multiplier": "множ. цены",
        "col.price_volatility": "волатил. цены",
        "col.lead_time_days": "срок пост.",
        "col.reputation": "репутация",
        "col.is_defaulted": "дефолт",
        "col.unit_price": "цена ед.",
        "world.edit_title": "Изменить значение",
        "world.bad_quarter": "Квартал должен быть целым числом > 0.",
        "world.need_run_row": "Сначала выберите строку квартала на вкладке «Запуск».",
        "world.info_override": "Квартал {q}: загружены свои правки.",
        "world.info_record": "Квартал {q}: снимок из результатов прогона.",
        "world.info_generated": "Квартал {q}: сгенерировано из зерна {seed}.",
        "world.info_saved": "Сохранён квартал {q} (в плане кварталов: {n}).",
        "world.info_cleared": "Правки для квартала {q} сброшены.",
        "col.gate": "гейт",
        "col.nr": "NR",
        "run.tuning": "Пороги и мир (на весь прогон)",
        "run.products": "Товары",
        "run.suppliers": "Поставщики",
        "run.budget": "Бюджет",
        "run.demand_shock": "Шок спроса p",
        "run.supplier_default": "Дефолт пост. p",
        "run.thresh_diversify": "Разнообр. ≥",
        "run.thresh_consist": "Стабил. ≥",
        "run.thresh_cost": "Стоимость ≥",
        "run.thresh_stockout": "Дефицит ≥",
        "run.thresh_budget": "Бюджет ≥",
        "run.thresh_risk": "Риски ≥",
        "diag.title": "Разбор квартала (выберите строку таблицы)",
        "diag.empty": "Выберите квартал в таблице, чтобы увидеть причину успеха или провала.",
        "diag.header": "Квартал {q}  ·  этап {stage}",
        "diag.verdict_line": "Вердикт: {text}",
        "diag.monopoly_flag": "Обнаружена монополия одного поставщика (оценка ≈ {score}).",
        "diag.flags": "гейты={all_passed}  ·  в серию выпуска={qualifies}",
        "diag.gate_fail": "Провалы гейта: {items}",
        "diag.nr_fail": "Провалы non-regression: {items}",
        "diag.table_header": "[G]=гейт этапа   значение / порог",
        "diag.actions_header": "Смесь действий за квартал:",
        "diag.verdict.qualifies": "Чистый квартал — идёт в серию выпуска.",
        "diag.verdict.nr_blocks": (
            "Гейты пройдены, но non-regression обнулил серию ({items})."
        ),
        "diag.verdict.monopoly": (
            "Провал диверсификации: все заказы одному поставщику (~0.133)."
        ),
        "diag.verdict.gate_fail": "Не пройден гейт этапа {stage}: {items}.",
        "diag.verdict.unknown": "Не удалось определить конкретную причину.",
    },
}


def assert_string_parity() -> None:
    """Raise if EN/RU key sets diverge (used by tests)."""
    en = set(STRINGS["en"])
    ru = set(STRINGS["ru"])
    if en != ru:
        missing_ru = sorted(en - ru)
        missing_en = sorted(ru - en)
        raise AssertionError(
            f"i18n key mismatch; missing in ru={missing_ru}, missing in en={missing_en}"
        )


def criterion_column(i18n: "I18n", criterion_id: str) -> str:
    """Short table-header label for a fitness criterion."""
    return i18n.t(f"col.{criterion_id}")


def criterion_legend(i18n: "I18n", criterion_id: str) -> str:
    """Longer legend label for a fitness criterion."""
    return i18n.t(f"crit.{criterion_id}")


def criterion_labels(i18n: "I18n") -> Dict[str, str]:
    return {c: criterion_legend(i18n, c) for c in CRITERION_KEYS}


class I18n:
    """Simple key → string translator with optional preference file."""

    def __init__(
        self,
        lang: str = DEFAULT_LANG,
        pref_path: Optional[Path] = None,
        *,
        force: bool = False,
    ) -> None:
        """Resolve language: ``force`` (``--lang``) > ``NOWA_LANG`` > saved pref > argument."""

        self.pref_path = pref_path
        if lang not in SUPPORTED:
            lang = DEFAULT_LANG
        if not force:
            env = os.environ.get("NOWA_LANG", "").strip().lower()
            if env in SUPPORTED:
                lang = env
            elif pref_path and pref_path.exists():
                try:
                    data = json.loads(pref_path.read_text(encoding="utf-8"))
                    saved = data.get("lang")
                    if saved in SUPPORTED:
                        lang = saved
                except (OSError, json.JSONDecodeError, TypeError):
                    pass
        self._lang = lang

    @property
    def lang(self) -> str:
        return self._lang

    def set_language(self, lang: str) -> None:
        if lang not in SUPPORTED:
            raise ValueError(f"Unsupported language: {lang}")
        self._lang = lang
        if self.pref_path is not None:
            try:
                self.pref_path.parent.mkdir(parents=True, exist_ok=True)
                self.pref_path.write_text(
                    json.dumps({"lang": lang}, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
            except OSError:
                pass

    def t(self, key: str, **kwargs: Any) -> str:
        table = STRINGS.get(self._lang) or STRINGS[DEFAULT_LANG]
        text = table.get(key) or STRINGS[DEFAULT_LANG].get(key) or key
        if kwargs:
            try:
                return text.format(**kwargs)
            except (KeyError, ValueError):
                return text
        return text


def format_readiness_localized(
    report: Mapping[str, Any], i18n: I18n
) -> str:
    """Localized Stage 1a readiness summary (mirrors format_readiness_text)."""
    readiness = report.get("readiness") or {}
    rows = report.get("rows") or []
    t = i18n.t
    lines = [
        f"{t('readiness.header_run'):<28} "
        f"{t('readiness.header_grad'):>5} "
        f"{t('readiness.header_q'):>4} "
        f"{t('readiness.header_n_ok'):>5}",
        "-" * 48,
    ]
    for row in rows:
        q = row.get("first_graduation_quarter")
        yes = t("yes_short") if row.get("graduated") else t("no_short")
        lines.append(
            f"{row.get('name', '?'):<28} "
            f"{yes:>5} "
            f"{(q if q is not None else '-'):>4} "
            f"{row.get('n_graduated_quarters', 0):>5}"
        )
    lines.append("")
    lines.append(
        t(
            "readiness.graduated_runs",
            n=readiness.get("n_graduated", 0),
            total=readiness.get("n_runs", 0),
        )
    )
    lines.append(
        t("readiness.grad_quarters", quarters=readiness.get("graduation_quarters"))
    )
    half = readiness.get("spread_half_width") or 0.0
    within = (
        t("readiness.within")
        if readiness.get("spread_within_tolerance")
        else t("readiness.outside")
    )
    lines.append(
        t(
            "readiness.spread",
            ratio=readiness.get("spread_ratio"),
            half=f"{half:g}",
            within=within,
        )
    )
    lines.append(
        t("readiness.ready")
        if readiness.get("ready_for_stage_1b")
        else t("readiness.not_ready")
    )
    if report.get("refused"):
        lines.append(t("readiness.baseline_refused", msg=report["refused"]))
    elif report.get("baseline_path"):
        lines.append(
            t(
                "readiness.baseline_from",
                chosen=report.get("chosen"),
                path=report["baseline_path"],
            )
        )
        baseline = (report.get("baseline") or {}).get("stage_1a_baseline") or {}
        for key in CRITERION_KEYS:
            if key in baseline:
                lines.append(f"  {criterion_legend(i18n, key)}: {baseline[key]}")
    return "\n".join(lines)


__all__ = [
    "CRITERION_KEYS",
    "DEFAULT_LANG",
    "FLAG_EN",
    "FLAG_RU",
    "I18n",
    "STRINGS",
    "SUPPORTED",
    "assert_string_parity",
    "criterion_column",
    "criterion_labels",
    "criterion_legend",
    "format_readiness_localized",
]
