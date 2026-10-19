
import pytest
from learning_guard import learning_allowed

@pytest.fixture(autouse=True)
def _allow_stable_writers_under_test():
    """Direct tests of stable writers. Sleep opens the same guard."""
    with learning_allowed():
        yield

"""
Tests для IntentMemory - память привычек.

Тестируем:
1. Создание и усиление traces
2. Активацию по контексту
3. Распределение давления
4. Confidence calculation
5. Ослабление при неиспользовании
6. Укрепление при повторении
"""

import pytest
import time
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from intent_memory import IntentTrace, IntentMemory


class TestIntentTrace:
    """Тесты для IntentTrace"""
    
    def test_trace_creation(self):
        """Trace создаётся с правильными параметрами"""
        trace = IntentTrace(
            intent_type="respond_about_self",
            context_signature="ctx123"
        )
        assert trace.intent_type == "respond_about_self"
        assert trace.context_signature == "ctx123"
        assert trace.strength == 1.0
        assert trace.recency == 0.0
    
    def test_trace_strengthen(self):
        """Trace усиливается при вызове strengthen()"""
        trace = IntentTrace("respond_about_self", "ctx123")
        initial_strength = trace.strength
        
        trace.strengthen()
        assert trace.strength == initial_strength + 1.0
        assert trace.recency == 1.0
    
    def test_trace_recency_decay(self):
        """Recency экспоненциально затухает со временем"""
        trace = IntentTrace("respond_about_self", "ctx123")
        trace.timestamp = time.time() - 1000  # 1000 секунд назад
        
        half_life = 1000.0
        trace.update_recency(half_life)
        
        # После одного half-life, recency должна быть ~0.5
        assert 0.48 < trace.recency < 0.52


class TestIntentMemory:
    """Тесты для IntentMemory"""
    
    def test_memory_creation(self):
        """IntentMemory создаётся с правильными параметрами"""
        memory = IntentMemory()
        assert len(memory.traces) == 0
        assert memory.context_signature_window == 1
    
    def test_record_single_trace(self):
        """Записывается одна trace"""
        memory = IntentMemory()
        context = ["user:кто ты"]
        intent = "respond_about_self"
        
        memory.record_trace(context, intent)
        
        assert len(memory.traces) == 1
        trace = list(memory.traces.values())[0]
        assert trace.intent_type == intent
        assert trace.strength == 1.0
    
    def test_record_duplicate_trace_strengthens(self):
        """Дублирующаяся trace усиливается"""
        memory = IntentMemory()
        context = ["user:кто ты"]
        intent = "respond_about_self"
        
        memory.record_trace(context, intent)
        memory.record_trace(context, intent)
        
        assert len(memory.traces) == 1
        trace = list(memory.traces.values())[0]
        assert trace.strength == 2.0
    
    def test_record_different_intents_same_context(self):
        """Разные намерения для одного контекста создают разные traces"""
        memory = IntentMemory()
        context = ["user:кто ты"]
        
        memory.record_trace(context, "respond_about_self")
        memory.record_trace(context, "greet_user")
        
        assert len(memory.traces) == 2
    
    def test_activate_by_context_no_matches(self):
        """Активация без matching traces возвращает пустой dict"""
        memory = IntentMemory()
        context = ["user:привет"]
        
        pressure = memory.activate_by_context(context)
        
        assert pressure == {}
    
    def test_activate_by_context_with_matches(self):
        """Активация находит релевантные traces"""
        memory = IntentMemory()
        context = ["user:кто ты"]
        
        memory.record_trace(context, "respond_about_self")
        memory.record_trace(context, "respond_about_self")
        
        pressure = memory.activate_by_context(context)
        
        assert "respond_about_self" in pressure
        # pressure = strength * recency, где recency ~1.0 для свежих traces
        assert pressure["respond_about_self"] > 0
    
    def test_activate_by_context_multiple_intents(self):
        """Активация распределяет давление по нескольким намерениям"""
        memory = IntentMemory()
        context = ["user:кто ты"]
        
        memory.record_trace(context, "respond_about_self")
        memory.record_trace(context, "respond_about_self")
        memory.record_trace(context, "greet_user")
        
        pressure = memory.activate_by_context(context)
        
        assert "respond_about_self" in pressure
        assert "greet_user" in pressure
        assert pressure["respond_about_self"] > pressure["greet_user"]
    
    def test_get_dominant_intent_high_confidence(self):
        """Получение доминирующего намерения с высокой confidence"""
        memory = IntentMemory()
        context = ["user:кто ты"]
        
        # Одно намерение с высокой strength
        memory.record_trace(context, "respond_about_self")
        memory.record_trace(context, "respond_about_self")
        memory.record_trace(context, "respond_about_self")
        
        intent, confidence = memory.get_dominant_intent(context)
        
        assert intent == "respond_about_self"
        assert confidence > 0.95
    
    def test_get_dominant_intent_conflict(self):
        """Конфликтные намерения дают пониженную confidence"""
        memory = IntentMemory()
        context = ["user:кто ты"]
        
        # Примерно равные traces
        memory.record_trace(context, "respond_about_self")
        memory.record_trace(context, "respond_about_self")
        memory.record_trace(context, "greet_user")
        memory.record_trace(context, "greet_user")
        
        intent, confidence = memory.get_dominant_intent(context)
        
        # Confidence должна быть ниже, но намерение ещё возвращается
        assert intent in ["respond_about_self", "greet_user"]
        assert confidence < 0.7
    
    def test_get_dominant_intent_no_traces(self):
        """Отсутствие traces возвращает None"""
        memory = IntentMemory()
        context = ["user:привет"]
        
        intent, confidence = memory.get_dominant_intent(context)
        
        assert intent is None
        assert confidence == 0.0
    
    def test_degrade_unused_removes_weak_traces(self):
        """Ослабление удаляет слабые traces"""
        memory = IntentMemory()
        context = ["user:кто ты"]
        
        memory.record_trace(context, "respond_about_self")
        memory.record_trace(context, "respond_about_self")
        
        initial_count = len(memory.traces)
        memory.degrade_unused(decay_factor=0.01)  # Очень сильное ослабление
        
        assert len(memory.traces) < initial_count
    
    def test_degrade_unused_keeps_strong_traces(self):
        """Ослабление сохраняет достаточно сильные traces"""
        memory = IntentMemory()
        context = ["user:кто ты"]
        
        # Создаём очень сильную trace
        for _ in range(100):
            memory.record_trace(context, "respond_about_self")
        
        memory.degrade_unused(decay_factor=0.8)
        
        assert len(memory.traces) == 1
        trace = list(memory.traces.values())[0]
        assert trace.strength > 0
    
    def test_strengthen_traces_during_sleep(self):
        """Укрепление traces во время сна"""
        memory = IntentMemory()
        context = ["user:кто ты"]
        
        memory.record_trace(context, "respond_about_self")
        initial_strength = list(memory.traces.values())[0].strength
        
        memory.strengthen_trace(context, "respond_about_self", factor=2.0)
        
        new_strength = list(memory.traces.values())[0].strength
        assert new_strength == initial_strength * 2.0
    
    def test_context_signature_consistency(self):
        """Context signature вычисляется консистентно"""
        memory = IntentMemory()
        context = ["user:кто ты"]
        
        sig1 = memory._compute_context_signature(context)
        sig2 = memory._compute_context_signature(context)
        
        assert sig1 == sig2
    
    def test_context_signature_different_for_different_contexts(self):
        """Разные контексты дают разные signatures"""
        memory = IntentMemory()
        context1 = ["user:кто ты"]
        context2 = ["user:привет"]
        
        sig1 = memory._compute_context_signature(context1)
        sig2 = memory._compute_context_signature(context2)
        
        assert sig1 != sig2
    
    def test_get_stats(self):
        """Получение статистики"""
        memory = IntentMemory()
        context = ["user:кто ты"]
        
        memory.record_trace(context, "respond_about_self")
        memory.record_trace(context, "respond_about_self")
        memory.record_trace(context, "greet_user")
        
        stats = memory.get_stats()
        
        assert stats["total_traces"] == 2
        assert "respond_about_self" in stats["by_intent"]
        assert "greet_user" in stats["by_intent"]


def test_apply_outcome_is_bounded_and_signed():
    """C06: success moves toward 1, failure toward 0, affect cannot overflow."""
    memory = IntentMemory()
    context = ["ctx"]
    for _ in range(40):
        memory.apply_outcome(context, "go", 1.0, affect_gain=5.0)
    strength = list(memory.traces.values())[0].strength
    assert 0.9 <= strength <= 1.0
    for _ in range(40):
        memory.apply_outcome(context, "go", -1.0, affect_gain=5.0)
    strength = list(memory.traces.values())[0].strength
    assert 0.0 <= strength <= 0.05


class TestIntentMemoryScenarios:
    """Интеграционные тесты для типичных сценариев"""
    
    def test_scenario_habit_formation(self):
        """Сценарий А - привычка формируется"""
        memory = IntentMemory()
        context = ["user:кто ты"]
        
        # Три одинаковых trace
        for _ in range(3):
            memory.record_trace(context, "respond_about_self")
        
        intent, confidence = memory.get_dominant_intent(context)
        
        assert intent == "respond_about_self"
        assert confidence > 0.95  # Высокая уверенность
    
    def test_scenario_habit_conflict(self):
        """Сценарий B - конфликт привычек"""
        memory = IntentMemory()
        context = ["user:кто ты"]
        
        memory.record_trace(context, "respond_about_self")
        memory.record_trace(context, "greet_user")
        
        intent, confidence = memory.get_dominant_intent(context)
        
        # Есть доминирующее намерение, но confidence низкая
        assert intent is not None
        assert confidence < 0.7
    
    def test_scenario_sleep_consolidation(self):
        """Сценарий сна - укрепление и ослабление"""
        memory = IntentMemory()
        context1 = ["user:кто ты"]
        context2 = ["user:привет"]
        
        # Два намерения, одно часто повторяется
        for _ in range(10):
            memory.record_trace(context1, "respond_about_self")
        memory.record_trace(context2, "greet_user")
        
        initial_traces = len(memory.traces)
        
        # Укрепляем часто используемое
        memory.strengthen_trace(context1, "respond_about_self", factor=2.0)
        
        # Ослабляем редко используемое (очень сильное ослабление)
        memory.degrade_unused(decay_factor=0.05)
        
        # Редкое должно быть удалено
        assert len(memory.traces) < initial_traces
        
        # Частое должно остаться сильным
        intent, confidence = memory.get_dominant_intent(context1)
        assert intent == "respond_about_self"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
