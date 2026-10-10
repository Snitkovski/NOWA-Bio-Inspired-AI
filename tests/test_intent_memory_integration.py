"""
Integration tests for IntentMemory with Agent and Selector.

Тестируем полный цикл:
1. Agent выбирает действия на основе привычек (intent_memory)
2. Experiences записываются
3. Selector использует intent_pressure
4. Sleep консолидирует intent_memory
"""

import os
import random
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from agent import Agent
from selector import ActionSelector
from hippocampus import NOWAHippocampus
from cortex import CortexMemory
from sleep import SleepManager
from intent_memory import IntentMemory
from experience import Event, EventType


class TestIntentMemoryIntegration:
    """Интеграционные тесты IntentMemory с Agent"""
    
    def test_agent_step_records_intent_trace(self):
        """Agent.step() записывает action в intent_memory"""
        # Setup
        hippocampus = NOWAHippocampus()
        cortex = CortexMemory()
        intent_memory = IntentMemory()
        selector = ActionSelector(actions=[
            "ответить_кто_я",
            "сказать_привет",
            "отказаться",
            "помочь",
            "задать_вопрос"
        ])
        sleep_manager = SleepManager(hippocampus, cortex, intent_memory)
        agent = Agent(hippocampus, cortex, selector, sleep_manager, intent_memory)
        
        context = ["user:кто ты"]
        
        # Execute one step
        action = agent.step(context)
        
        # Verify
        assert action in selector.actions
        assert len(intent_memory.traces) > 0
    
    def test_repeated_context_creates_habit(self):
        """Повторение одного контекста создаёт привычку"""
        # Setup
        hippocampus = NOWAHippocampus()
        cortex = CortexMemory()
        intent_memory = IntentMemory()
        selector = ActionSelector(actions=[
            "ответить_кто_я",
            "сказать_привет",
            "отказаться",
            "помочь",
            "задать_вопрос"
        ])
        sleep_manager = SleepManager(hippocampus, cortex, intent_memory)
        agent = Agent(hippocampus, cortex, selector, sleep_manager, intent_memory)
        # Habit traces compete with deliberative/imagination exploration in the
        # BG+thalamic pipeline. Pin that noise so a repeated context can settle.
        random.seed(0)
        agent.deliberative_planning_enabled = False
        agent.imagination_enabled = False
        agent.thalamic_gate.base_temperature = 0.03
        agent.thalamic_gate.min_temperature = 0.03
        agent.basal_ganglia.temperature = 0.05

        context = ["user:кто ты"]
        for _ in range(8):
            agent.step(context)

        intent, confidence = intent_memory.get_dominant_intent(context)
        assert intent is not None
        assert confidence > 0.5  # Should have some habit
    
    def test_selector_uses_intent_pressure(self):
        """Selector использует intent_pressure от intent_memory"""
        # Setup
        hippocampus = NOWAHippocampus()
        cortex = CortexMemory()
        selector = ActionSelector(actions=[
            "ответить_кто_я",
            "сказать_привет",
            "отказаться",
            "помочь",
            "задать_вопрос"
        ])
        
        # Create intent pressure
        intent_pressure = {
            "ответить_кто_я": 10.0,
            "сказать_привет": 0.5
        }
        
        # Choose action
        action = selector.choose([], [], intent_pressure=intent_pressure)
        
        # Should choose action with high pressure
        assert action == "ответить_кто_я"
    
    def test_sleep_degrades_unused_intents(self):
        """Sleep degradирует неиспользуемые intents"""
        # Setup
        hippocampus = NOWAHippocampus()
        cortex = CortexMemory()
        intent_memory = IntentMemory()
        selector = ActionSelector(actions=[
            "ответить_кто_я",
            "сказать_привет",
            "отказаться",
            "помочь",
            "задать_вопрос"
        ])
        sleep_manager = SleepManager(hippocampus, cortex, intent_memory)
        agent = Agent(hippocampus, cortex, selector, sleep_manager, intent_memory)
        
        # Create two different intents
        context1 = ["user:кто ты"]
        context2 = ["user:привет"]
        
        # Use one context many times, other - once
        for _ in range(10):
            agent.step(context1)
        agent.step(context2)
        
        initial_traces = len(intent_memory.traces)
        
        # Sleep
        sleep_manager.deep_sleep(cycles=1)
        
        # Unused should be degraded/forgotten
        final_traces = len(intent_memory.traces)
        
        # Should have same or fewer traces after degradation
        assert final_traces <= initial_traces
    
    def test_intent_memory_with_agent_step(self):
        """Полный цикл: context → agent.step → intent_trace"""
        # Setup
        hippocampus = NOWAHippocampus()
        cortex = CortexMemory()
        intent_memory = IntentMemory()
        selector = ActionSelector(actions=[
            "ответить_кто_я",
            "сказать_привет",
            "отказаться",
            "помочь",
            "задать_вопрос"
        ])
        sleep_manager = SleepManager(hippocampus, cortex, intent_memory)
        agent = Agent(hippocampus, cortex, selector, sleep_manager, intent_memory)
        
        context = ["user:кто ты"]
        
        # Step 1: Initial step - creates random trace
        action1 = agent.step(context)
        traces1 = len(intent_memory.traces)
        
        # Step 2-5: Repeat same context to build habit
        for _ in range(4):
            agent.step(context)
        
        traces2 = len(intent_memory.traces)
        
        # Should have created or strengthened trace
        assert traces2 >= traces1
        
        # Check that we can get dominant intent
        intent, confidence = intent_memory.get_dominant_intent(context)
        assert intent is not None
    
    def test_habit_influences_selector_choice(self):
        """Привычка влияет на выбор селектора"""
        # Setup
        hippocampus = NOWAHippocampus()
        cortex = CortexMemory()
        intent_memory = IntentMemory()
        selector = ActionSelector(actions=[
            "ответить_кто_я",
            "сказать_привет",
            "отказаться",
            "помочь",
            "задать_вопрос"
        ])
        sleep_manager = SleepManager(hippocampus, cortex, intent_memory)
        agent = Agent(hippocampus, cortex, selector, sleep_manager, intent_memory)
        
        context = ["user:кто ты"]
        
        # Build strong habit
        for _ in range(10):
            agent.step(context)
        
        # Get the dominant intent
        dominant_intent, confidence = intent_memory.get_dominant_intent(context)
        
        # Now when selector chooses with this intent_pressure
        intent_pressure = intent_memory.activate_by_context(context)
        
        # Multiple choices should tend toward dominant_intent
        choices = []
        for _ in range(10):
            action = selector.choose([], [], intent_pressure=intent_pressure)
            choices.append(action)
        
        # Most choices should be the dominant intent
        dominant_count = sum(1 for a in choices if a == dominant_intent)
        assert dominant_count >= 6  # At least 60%


class TestIntentMemoryWithSelector:
    """Тесты интеграции IntentMemory и Selector"""
    
    def test_selector_resolves_conflict_with_intent_pressure(self):
        """Selector использует intent_pressure для разрешения конфликта"""
        selector = ActionSelector(actions=[
            "ответить_кто_я",
            "сказать_привет",
            "отказаться",
            "помочь",
            "задать_вопрос"
        ])
        
        # Strong intent pressure
        intent_pressure = {
            "помочь": 5.0,
            "задать_вопрос": 0.5
        }
        
        # Choose multiple times
        choices = []
        for _ in range(10):
            action = selector.choose([], [], intent_pressure=intent_pressure)
            choices.append(action)
        
        # Should prefer помочь due to intent pressure
        help_count = sum(1 for a in choices if a == "помочь")
        assert help_count >= 7  # At least 70%


class TestIntentMemorySleep:
    """Тесты сна с IntentMemory"""
    
    def test_sleep_strengthens_frequently_used_intents(self):
        """Sleep укрепляет часто используемые intents"""
        intent_memory = IntentMemory()
        
        # Create traces with different strengths
        context1 = ["user:кто ты"]
        context2 = ["user:привет"]
        
        # Strong habit
        for _ in range(20):
            intent_memory.record_trace(context1, "ответить_кто_я")
        
        # Weak habit
        intent_memory.record_trace(context2, "сказать_привет")
        
        initial_stats = intent_memory.get_stats()
        initial_count = len(intent_memory.traces)
        
        # Simulate sleep - degrade unused
        intent_memory.degrade_unused(decay_factor=0.5)
        
        final_count = len(intent_memory.traces)
        
        # Weak habit might be removed, strong should remain
        # But this depends on strength values
        assert final_count <= initial_count
        
        # Check that strong habit is still there
        intent, confidence = intent_memory.get_dominant_intent(context1)
        assert intent == "ответить_кто_я"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
