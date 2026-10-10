#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тесты для сохранения и загрузки аффективного состояния агента
"""

import sys
import os
import tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from agent import Agent
from hippocampus import NOWAHippocampus
from cortex import CortexMemory
from selector import ActionSelector
from sleep import SleepManager
from storage import AgentStorage
from affect import AffectiveState

def test_save_load_affect_state():
    """Тесты сохранения и загрузки аффективного состояния"""
    
    print("\n" + "="*70)
    print("🧪 ТЕСТЫ СОХРАНЕНИЯ И ЗАГРУЗКИ АФФЕКТИВНОГО СОСТОЯНИЯ")
    print("="*70)
    
    # Создание агента
    hippocampus = NOWAHippocampus()
    cortex = CortexMemory()
    selector = ActionSelector(actions=["greet", "ask", "refuse"])
    sleep_manager = SleepManager(hippocampus, cortex)
    agent = Agent(hippocampus, cortex, selector, sleep_manager=sleep_manager)
    
    # Создание хранилища
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = AgentStorage(save_dir=tmpdir)
        
        # Тест 1: Начальное состояние
        print("\n✅ Тест 1: Начальное аффективное состояние")
        print(f"   Valence: {agent.affect_state.valence:.2f}")
        print(f"   Arousal: {agent.affect_state.arousal:.2f}")
        print(f"   Threat: {agent.affect_state.threat:.2f}")
        print(f"   Curiosity: {agent.affect_state.curiosity:.2f}")
        
        initial_valence = agent.affect_state.valence
        initial_arousal = agent.affect_state.arousal
        initial_threat = agent.affect_state.threat
        initial_curiosity = agent.affect_state.curiosity
        
        # Тест 2: Обновление affect_state
        print("\n✅ Тест 2: Обновление аффективного состояния")
        agent.affect_state.update_from_reward(0.8)  # Положительная награда
        agent.affect_state.update_from_novelty(0.6)  # Новизна
        
        print(f"   Valence: {initial_valence:.2f} → {agent.affect_state.valence:.2f}")
        print(f"   Curiosity: {initial_curiosity:.2f} → {agent.affect_state.curiosity:.2f}")
        
        # Тест 3: Сохранение состояния
        print("\n✅ Тест 3: Сохранение состояния с affect_state")
        filepath = storage.save_agent(
            hippocampus,
            cortex,
            selector,
            affect_state=agent.affect_state,
            filename="test_save.pkl"
        )
        print(f"   Файл сохранён: {filepath}")
        print(f"   Файл существует: {os.path.exists(filepath)}")
        
        # Сохранённые значения
        saved_valence = agent.affect_state.valence
        saved_arousal = agent.affect_state.arousal
        saved_threat = agent.affect_state.threat
        saved_curiosity = agent.affect_state.curiosity
        
        # Тест 4: Изменение состояния
        print("\n✅ Тест 4: Изменение состояния перед загрузкой")
        agent.affect_state.update_from_reward(-0.9)  # Отрицательная награда
        print(f"   Valence до загрузки: {saved_valence:.2f} → {agent.affect_state.valence:.2f}")
        
        # Убедимся, что состояние действительно изменилось
        assert agent.affect_state.valence < saved_valence, "Valence должна была снизиться"
        print("   ✓ Состояние успешно изменено")
        
        # Тест 5: Загрузка состояния
        print("\n✅ Тест 5: Загрузка состояния с restore affect_state")
        
        # Создаём новое аффективное состояние для загрузки
        new_affect_state = AffectiveState()
        
        # Загружаем
        timestamp = storage.load_agent(
            hippocampus,
            cortex,
            selector,
            filepath,
            affect_state=new_affect_state
        )
        
        print(f"   Timestamp: {timestamp}")
        print(f"   Загруженное состояние:")
        print(f"   - Valence: {new_affect_state.valence:.2f} (было {saved_valence:.2f})")
        print(f"   - Arousal: {new_affect_state.arousal:.2f} (было {saved_arousal:.2f})")
        print(f"   - Threat: {new_affect_state.threat:.2f} (было {saved_threat:.2f})")
        print(f"   - Curiosity: {new_affect_state.curiosity:.2f} (было {saved_curiosity:.2f})")
        
        # Тест 6: Проверка корректности восстановления
        print("\n✅ Тест 6: Проверка корректности восстановления")
        
        tolerance = 0.01  # Допуск для float сравнения
        
        assert abs(new_affect_state.valence - saved_valence) < tolerance, \
            f"Valence не совпадает: {new_affect_state.valence} vs {saved_valence}"
        print(f"   ✓ Valence восстановлена корректно")
        
        assert abs(new_affect_state.arousal - saved_arousal) < tolerance, \
            f"Arousal не совпадает: {new_affect_state.arousal} vs {saved_arousal}"
        print(f"   ✓ Arousal восстановлена корректно")
        
        assert abs(new_affect_state.threat - saved_threat) < tolerance, \
            f"Threat не совпадает: {new_affect_state.threat} vs {saved_threat}"
        print(f"   ✓ Threat восстановлена корректно")
        
        assert abs(new_affect_state.curiosity - saved_curiosity) < tolerance, \
            f"Curiosity не совпадает: {new_affect_state.curiosity} vs {saved_curiosity}"
        print(f"   ✓ Curiosity восстановлена корректно")
        
        # Тест 7: Загрузка в исходный agent.affect_state
        print("\n✅ Тест 7: Загрузка в исходный agent.affect_state")
        
        # Сбросим agent.affect_state
        agent.affect_state.update_from_reward(-0.9)
        print(f"   Valence перед загрузкой: {agent.affect_state.valence:.2f}")
        
        # Загружаем в исходный agent.affect_state
        storage.load_agent(
            hippocampus,
            cortex,
            selector,
            filepath,
            affect_state=agent.affect_state
        )
        
        print(f"   Valence после загрузки: {agent.affect_state.valence:.2f}")
        assert abs(agent.affect_state.valence - saved_valence) < tolerance
        print(f"   ✓ Состояние успешно восстановлено в agent.affect_state")
        
        # Тест 8: Загрузка без affect_state (обратная совместимость)
        print("\n✅ Тест 8: Загрузка без affect_state (обратная совместимость)")
        storage.load_agent(
            hippocampus,
            cortex,
            selector,
            filepath
        )
        print(f"   ✓ Загрузка работает и без параметра affect_state")

    print("\n" + "="*70)
    print("✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
    print("="*70)
    print("\n📊 Итоги:")
    print("   • Сохранение affect_state работает корректно")
    print("   • Загрузка affect_state восстанавливает значения")
    print("   • Обратная совместимость сохранена")
    print("   • Система готова к использованию ✅\n")

if __name__ == "__main__":
    test_save_load_affect_state()
