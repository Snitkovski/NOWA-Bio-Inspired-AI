"""English / Russian UI strings for the Body Layer lab."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

DEFAULT_LANG = "en"
SUPPORTED = ("en", "ru")
FLAG_EN = "\U0001F1EC\U0001F1E7"
FLAG_RU = "\U0001F1F7\U0001F1FA"

STRINGS: Dict[str, Dict[str, str]] = {
    "en": {
        "app.title": "NOWA Body Layer Lab  —  Phase 1",
        "cli.description": "NOWA body layer lab",
        "cli.lang_help": "UI language. Overrides NOWA_LANG and the saved preference.",
        "tab.pipeline": "Pipeline",
        "tab.pending": "Approvals",
        "tab.memory": "Memory",
        "tab.mcp": "MCP log",
        "tab.log": "Log",
        "status.ready": "Ready. Reset the session, then press Tick.",
        "status.ticked": "Tick {tick}  ·  {action}  ·  {approval}",
        "status.auto": "Auto-tick running…",
        "status.auto_stopped": "Auto-tick stopped.",
        "status.error": "Error: {error}",
        "status.reset": "Session reset. Backend: {backend}",
        "status.approved": "Approved {action_id}",
        "status.rejected": "Rejected {action_id}",
        "status.modified": "Modified {action_id}",
        "status.probe_ok": "HIGH_WRITE bypass blocked (invariant and gate).",
        "status.probe_fail": "HIGH_WRITE probe did not raise as expected.",
        "status.no_pending": "Select a pending action first.",
        "lang.en": "EN",
        "lang.ru": "RU",
        "session.group": "Session",
        "session.reset": "Reset session",
        "session.seed_intuition": "Seed professional intuition",
        "session.auto_execute": "Lab: execute writes without approval (Reset to apply)",
        "session.backend": "Agent backend: {backend}",
        "scenario.group": "World (MockMCP)",
        "scenario.label": "Scenario",
        "scenario.quiet": "Quiet warehouse",
        "scenario.stock_critical": "Stock below reorder point",
        "scenario.supplier_defaulted": "Reliable supplier defaulted",
        "write.group": "WRITE outcome",
        "write.accepted": "accepted",
        "write.rejected": "rejected",
        "write.timeout": "timeout",
        "write.error": "error",
        "action.group": "Action",
        "action.label": "Force action",
        "action.auto": "auto (agent.step)",
        "action.wait_and_monitor": "wait_and_monitor",
        "action.mcp__1c__create_purchase_order": "create_purchase_order",
        "action.mcp__drivemcp__create_purchase_order": "create_purchase_order",
        "action.place_order_reliable_supplier": "place_order_reliable_supplier",
        "action.place_order_cheap_supplier": "place_order_cheap_supplier",
        "action.urgent_reorder": "urgent_reorder",
        "action.diversify_supplier": "diversify_supplier",
        "clock.group": "Clock / sleep",
        "clock.now": "Simulated time",
        "clock.day": "Day 14:00",
        "clock.night": "Night 03:00",
        "clock.advance_hour": "+1 hour",
        "sleep.min_ticks": "Min ticks between sleep",
        "sleep.fatigue": "Fatigue override (Process S)",
        "sleep.fatigue_enable": "Force Process S",
        "sensors.interval": "Sensor refresh, s",
        "run.group": "Run",
        "run.tick": "Tick once",
        "run.burst": "10 ticks",
        "run.auto_start": "Auto start",
        "run.auto_stop": "Auto stop",
        "run.auto_ms": "Auto interval, ms",
        "approval.group": "Human approval",
        "approval.approve": "Approve",
        "approval.reject": "Reject",
        "approval.modify": "Modify qty & approve",
        "approval.reason": "Rejection reason",
        "approval.qty": "New qty",
        "probe.high_write": "Probe HIGH_WRITE bypass",
        "live.line": (
            "Tick {tick}  |  {now}  |  {action}  |  {approval}  |  "
            "episodes {episodes}  |  Process S {pressure:.2f}  |  pending {pending}"
        ),
        "pipeline.context": "Context tokens",
        "pipeline.proposed": "Proposed action",
        "pipeline.execution": "Execution result",
        "pipeline.empty": "(no cycle yet)",
        "col.id": "id",
        "col.tool": "tool",
        "col.summary": "summary",
        "col.risk": "risk",
        "risk.read_only": "Read only",
        "risk.low_write": "Low write",
        "risk.medium_write": "Medium write",
        "risk.high_write": "High write",
        "risk.irreversible": "Irreversible",
        "col.params": "params",
        "col.path": "path",
        "col.consequence": "consequence",
        "col.reward": "reward",
        "col.result": "result",
        "hint.body": (
            "Stage 2: WRITE goes to Approvals. Quiet ticks must not grow Memory. "
            "Night 03:00 + enough ticks triggers circadian sleep. "
            "HIGH_WRITE probe must fail."
        ),
    },
    "ru": {
        "app.title": "Лаборатория слоя «тело» NOWA  —  Фаза 1",
        "cli.description": "Лаборатория слоя «тело» NOWA",
        "cli.lang_help": "Язык интерфейса. Важнее NOWA_LANG и сохранённого выбора.",
        "tab.pipeline": "Конвейер",
        "tab.pending": "Согласования",
        "tab.memory": "Память",
        "tab.mcp": "Журнал MCP",
        "tab.log": "Журнал",
        "status.ready": "Готово. Сбросьте сессию и нажмите «Тик».",
        "status.ticked": "Тик {tick}  ·  {action}  ·  {approval}",
        "status.auto": "Автотик идёт…",
        "status.auto_stopped": "Автотик остановлен.",
        "status.error": "Ошибка: {error}",
        "status.reset": "Сессия сброшена. Движок: {backend}",
        "status.approved": "Одобрено {action_id}",
        "status.rejected": "Отклонено {action_id}",
        "status.modified": "Изменено {action_id}",
        "status.probe_ok": "Обход HIGH_WRITE заблокирован (инвариант и шлюз).",
        "status.probe_fail": "Проба HIGH_WRITE не вызвала ожидаемое исключение.",
        "status.no_pending": "Сначала выберите заявку в очереди.",
        "lang.en": "EN",
        "lang.ru": "RU",
        "session.group": "Сессия",
        "session.reset": "Сбросить сессию",
        "session.seed_intuition": "Посеять профессиональную интуицию",
        "session.auto_execute": "Лаборатория: писать без согласования (сработает после сброса)",
        "session.backend": "Движок агента: {backend}",
        "scenario.group": "Мир (MockMCP)",
        "scenario.label": "Сценарий",
        "scenario.quiet": "Склад спокоен",
        "scenario.stock_critical": "Остаток ниже точки заказа",
        "scenario.supplier_defaulted": "Надёжный поставщик отказал",
        "write.group": "Исход WRITE",
        "write.accepted": "принят",
        "write.rejected": "отклонён",
        "write.timeout": "таймаут",
        "write.error": "ошибка",
        "action.group": "Действие",
        "action.label": "Принудительное действие",
        "action.auto": "авто (agent.step)",
        "action.wait_and_monitor": "wait_and_monitor",
        "action.mcp__1c__create_purchase_order": "create_purchase_order",
        "action.mcp__drivemcp__create_purchase_order": "create_purchase_order",
        "action.place_order_reliable_supplier": "place_order_reliable_supplier",
        "action.place_order_cheap_supplier": "place_order_cheap_supplier",
        "action.urgent_reorder": "urgent_reorder",
        "action.diversify_supplier": "diversify_supplier",
        "clock.group": "Часы / сон",
        "clock.now": "Модельные часы",
        "clock.day": "День 14:00",
        "clock.night": "Ночь 03:00",
        "clock.advance_hour": "+1 час",
        "sleep.min_ticks": "Мин. тиков между сном",
        "sleep.fatigue": "Принудительная усталость (процесс S)",
        "sleep.fatigue_enable": "Задать процесс S",
        "sensors.interval": "Опрос сенсоров, с",
        "run.group": "Прогон",
        "run.tick": "Один тик",
        "run.burst": "10 тиков",
        "run.auto_start": "Автостарт",
        "run.auto_stop": "Стоп",
        "run.auto_ms": "Интервал авто, мс",
        "approval.group": "Согласование человеком",
        "approval.approve": "Одобрить",
        "approval.reject": "Отклонить",
        "approval.modify": "Изменить qty и одобрить",
        "approval.reason": "Причина отклонения",
        "approval.qty": "Новый qty",
        "probe.high_write": "Проба обхода HIGH_WRITE",
        "live.line": (
            "Тик {tick}  |  {now}  |  {action}  |  {approval}  |  "
            "эпизоды {episodes}  |  процесс S {pressure:.2f}  |  очередь {pending}"
        ),
        "pipeline.context": "Токены контекста",
        "pipeline.proposed": "Предложенное действие",
        "pipeline.execution": "Результат исполнения",
        "pipeline.empty": "(конвейер ещё не запускался)",
        "col.id": "id",
        "col.tool": "тул",
        "col.summary": "суть",
        "col.risk": "риск",
        "risk.read_only": "Только чтение",
        "risk.low_write": "Небольшая запись",
        "risk.medium_write": "Средняя запись",
        "risk.high_write": "Опасная запись",
        "risk.irreversible": "Необратимо",
        "col.params": "параметры",
        "col.path": "путь",
        "col.consequence": "следствие",
        "col.reward": "награда",
        "col.result": "результат",
        "hint.body": (
            "Стадия 2: WRITE уходит в согласования. Тихие тики не должны копить память. "
            "Ночь 03:00 и достаточно тиков включают циркадный сон. "
            "Проба HIGH_WRITE должна провалиться."
        ),
    },
}


def assert_string_parity() -> None:
    en = set(STRINGS["en"])
    ru = set(STRINGS["ru"])
    if en != ru:
        raise AssertionError(
            f"i18n key mismatch; missing in ru={sorted(en - ru)}, "
            f"missing in en={sorted(ru - en)}"
        )


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
