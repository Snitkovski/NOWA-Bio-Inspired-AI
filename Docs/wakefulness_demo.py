"""
Quick Start Guide: Wakefulness, Sleep and Prefrontal Cortex Modulation

Демонстрация новой функциональности Phase 2 Extension

Запуск:
    python wakefulness_demo.py
"""

import sys
sys.path.insert(0, 'src')

from wakefulness import WakefulnessState
from neuromodulators import NeuromodulatorState


def demo_wakefulness_accumulation():
    """Демонстрация накопления усталости"""
    print("\n" + "="*60)
    print("DEMO 1: Накопление усталости (16 часов бодрствования)")
    print("="*60)
    
    w = WakefulnessState()
    print(f"Начальное состояние: {w}")
    
    # Симулируем бодрствование на протяжении 16 часов
    hours_awake = [0, 4, 8, 12, 16]
    for hours in hours_awake:
        if hours > 0:
            w.update_waking(hours * 3600)
        stats = w.get_statistics()
        print(f"\nПосле {hours}ч бодрствования:")
        print(f"  Усталость: {stats['current']:.3f}")
        print(f"  Надежность: {stats['cognitive_reliability']:.3f} ({'ВЫСОКАЯ' if stats['cognitive_reliability'] > 0.7 else 'НИЗКАЯ'})")


def demo_sleep_recovery():
    """Демонстрация восстановления при сне"""
    print("\n" + "="*60)
    print("DEMO 2: Восстановление при сне (из полной депривации)")
    print("="*60)
    
    w = WakefulnessState()
    w.wakefulness = 1.0  # Полная депривация
    print(f"Начальное состояние (полная депривация): {w}")
    
    # Симулируем сон на разные периоды
    sleep_periods = [0, 2, 4, 8]
    for hours in sleep_periods:
        if hours > 0:
            w.update_sleeping(hours * 3600)
        stats = w.get_statistics()
        print(f"\nПосле {hours}ч сна:")
        print(f"  Усталость: {stats['current']:.3f}")
        print(f"  Надежность: {stats['cognitive_reliability']:.3f}")


def demo_neuromodulator_interaction():
    """Демонстрация взаимодействия с нейромодуляторами"""
    print("\n" + "="*60)
    print("DEMO 3: Влияние усталости на нейромодуляторы")
    print("="*60)
    
    nm = NeuromodulatorState()
    
    print(f"Базовые нейромодуляторы:")
    print(f"  DA (дофамин): {nm.dopamine:.3f}")
    print(f"  NE (норадреналин): {nm.norepinephrine:.3f}")
    print(f"  5-HT (серотонин): {nm.serotonin:.3f}")
    print(f"  CORT (кортизол): {nm.cortisol:.3f}")
    
    # При разных уровнях усталости
    for wakefulness_level in [0.0, 0.5, 1.0]:
        w = WakefulnessState()
        w.wakefulness = wakefulness_level
        
        deltas = w.get_neuromodulator_deltas()
        
        print(f"\nПри усталости = {wakefulness_level:.1f}:")
        print(f"  Δ Кортизол: {deltas['cortisol']:+.4f}")
        print(f"  Δ Норадреналин: {deltas['norepinephrine']:+.4f}")
        print(f"  Δ Серотонин: {deltas['serotonin']:+.4f}")


def demo_pfc_modulation():
    """Демонстрация модуляции PFC"""
    print("\n" + "="*60)
    print("DEMO 4: Модуляция сигналов Префронтальной Коры (PFC)")
    print("="*60)
    
    w = WakefulnessState()
    conflicts = [0.0, 0.5, 1.0]
    
    for wakefulness in [0.0, 0.5, 1.0]:
        w.wakefulness = wakefulness
        print(f"\nУровень усталости: {wakefulness:.1f}")
        print(f"  Усилие PFC-сигнала: {w.get_pfc_signal_strength_modifier():.2f}x")
        print(f"  Шум PFC-сигнала: {w.get_pfc_signal_noise_modifier():.2f}x")
        
        print(f"  Вес PFC при конфликте:")
        for conflict in conflicts:
            weight = w.get_pfc_weight_modifier(conflict)
            print(f"    Конфликт {conflict:.1f}: {weight:.2f}")


def demo_realistic_day_cycle():
    """Симуляция реального суточного цикла"""
    print("\n" + "="*60)
    print("DEMO 5: Реалистичный суточный цикл (24 часа)")
    print("="*60)
    
    w = WakefulnessState()
    
    schedule = [
        ("Ночь / Сон", 8, "sleeping"),
        ("Утро / Отдых", 2, "waking"),
        ("День / Работа", 8, "waking"),
        ("Вечер / Активность", 4, "waking"),
        ("Ночь / Сон", 2, "sleeping"),
    ]
    
    print("\nЧас | Деятельность      | Усталость | Надежность | статус")
    print("-" * 65)
    
    total_hours = 0
    for activity, duration, mode in schedule:
        method = w.update_sleeping if mode == "sleeping" else w.update_waking
        method(duration * 3600)
        
        total_hours += duration
        stats = w.get_statistics()
        
        status = "✓" if stats['cognitive_reliability'] > 0.7 else "⚠" if stats['cognitive_reliability'] > 0.4 else "✗"
        print(f"{total_hours:3d} | {activity:17} | {stats['current']:9.3f} | {stats['cognitive_reliability']:10.3f} | {status}")


def main():
    """Запуск всех демонстраций"""
    print("\n" + "█"*60)
    print("█ Wakefulness System - Демонстрация")
    print("█ Phase 2 Extension: Sleep and Prefrontal Cortex Modulation")
    print("█"*60 + "\n")
    
    try:
        demo_wakefulness_accumulation()
        demo_sleep_recovery()
        demo_neuromodulator_interaction()
        demo_pfc_modulation()
        demo_realistic_day_cycle()
        
        print("\n" + "="*60)
        print("✓ ВСЕ ДЕМОНСТРАЦИИ ЗАВЕРШЕНЫ УСПЕШНО")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
