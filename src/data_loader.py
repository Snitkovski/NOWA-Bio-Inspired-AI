import json
import os
import sys
from pathlib import Path
from sample import ExperienceSample
from dataset import ExperienceDataset
from experience import Experience, Path as ExpPath, Event, EventType
from action_intent import RealizationExperience, IntentType

def _resolve_base_path() -> str:
    """Return base path where the datasets directory should be searched."""
    module_dir = os.path.dirname(os.path.abspath(__file__))

    candidates = []
    if getattr(sys, "frozen", False):
        # In standalone/onefile builds data files live next to extracted/bundled binaries.
        candidates.extend([
            module_dir,
            os.path.dirname(getattr(sys, "executable", module_dir)),
            os.getcwd(),
        ])
    else:
        # In source mode this file is in src/, so project root is one level up.
        candidates.extend([
            os.path.dirname(module_dir),
            os.getcwd(),
        ])

    for base in candidates:
        if os.path.exists(os.path.join(base, "datasets")):
            return base

    # Fallback to the first candidate for predictable behavior and diagnostics.
    return candidates[0]

def load_json_dataset(path: str) -> ExperienceDataset:
    """Загружает датасет из JSON файла в ExperienceDataset"""
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    samples = []
    for row in raw:
        samples.append(
            ExperienceSample(
                context=row["context"],
                action=row["action"],
                reward=row["reward"]
            )
        )

    return ExperienceDataset(samples)


def load_experience_from_dataset(path: str) -> list:
    """
    Загружает опыт из JSON датасета в формате Experience объектов.
    
    Ожидает JSON с массивом объектов:
    {
        "context": строка или список,
        "action": строка,
        "reward": число
    }
    """
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    
    experiences = []
    for row in raw:
        exp_path = ExpPath()
        
        # Добавляем контекст как события с префиксом "user:" (EventType.CONTEXT)
        context = row.get("context", [])
        if isinstance(context, str):
            context = [context]
        
        for event_name in context:
            # Добавляем префикс "user:" если его еще нет
            if not event_name.startswith("user:"):
                event_name = f"user:{event_name}"
            exp_path = exp_path.add_event(Event(event_name, EventType.CONTEXT))
        
        # Добавляем действие как событие с префиксом "action:" (EventType.ACTION)
        action_name = row.get("action", "")
        exp_path = exp_path.add_event(Event(f"action:{action_name}", EventType.ACTION))
        
        # Конвертируем reward в intensity [0-2]
        # Если reward в диапазоне [-1, 1], маппируем на [0, 2]
        reward = float(row.get("reward", 0))
        intensity = max(0, min(2, reward + 1))  # Clamp to [0, 2]
        
        experience = Experience(exp_path, intensity=intensity, reward=reward)
        experiences.append(experience)
    
    return experiences


def load_experiences_from_directory(directory: str) -> list:
    """
    Загружает опыт из всех JSON файлов в директории.
    
    Args:
        directory: путь к директории с JSON файлами
        
    Returns:
        Список всех загруженных Experience объектов
    """
    all_experiences = []
    
    if not os.path.exists(directory):
        print(f"Директория не найдена: {directory}")
        return all_experiences
    
    for filename in os.listdir(directory):
        if filename.endswith(".json"):
            file_path = os.path.join(directory, filename)
            try:
                experiences = load_experience_from_dataset(file_path)
                all_experiences.extend(experiences)
                print(f"Загружено {len(experiences)} опытов из {filename}")
            except Exception as e:
                print(f"Ошибка при загрузке {filename}: {e}")
    
    return all_experiences


def load_experiences_from_datasets_folder(base_path: str = None) -> list:
    """
    Загружает опыт из папки datasets в корне проекта.
    
    Args:
        base_path: базовый путь к проекту (если None, используется текущая директория)
        
    Returns:
        Список всех загруженных Experience объектов
    """
    if base_path is None:
        base_path = _resolve_base_path()
    
    datasets_path = os.path.join(base_path, "datasets")
    return load_experiences_from_directory(datasets_path)


def load_realization_from_dataset(path: str) -> list:
    """
    Загружает опыт реализации (форм выражения) из JSON датасета.
    
    Ожидает JSON с массивом объектов:
    {
        "context": список строк,
        "intent_type": строка (например "respond_about_self"),
        "output": строка (выходной текст),
        "intensity": число (0-2),
        "parameters": объект (опционально)
    }
    """
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    
    realizations = []
    for row in raw:
        intent_type_str = row.get("intent_type", "acknowledge")
        output = row.get("output", "")
        context = row.get("context", [])
        intensity = float(row.get("intensity", 1.0))
        parameters = row.get("parameters", {})
        
        # Конвертируем строку intent_type в IntentType enum
        try:
            intent_type = IntentType[intent_type_str.upper()]
        except KeyError:
            # Fallback if intent type not recognized
            intent_type = IntentType.ACKNOWLEDGE
        
        realization = RealizationExperience(
            intent_type=intent_type,
            output=output,
            context=context,
            intensity=intensity,
            parameters=parameters
        )
        realizations.append(realization)
    
    return realizations


def load_realizations_from_directory(directory: str) -> list:
    """
    Загружает опыт реализаций из всех JSON файлов в директории.
    
    Args:
        directory: путь к директории с JSON файлами
        
    Returns:
        Список всех загруженных RealizationExperience объектов
    """
    all_realizations = []
    
    if not os.path.exists(directory):
        print(f"Директория не найдена: {directory}")
        return all_realizations
    
    for filename in os.listdir(directory):
        if filename.endswith(".json") and "realization" in filename.lower():
            file_path = os.path.join(directory, filename)
            try:
                realizations = load_realization_from_dataset(file_path)
                all_realizations.extend(realizations)
                print(f"Загружено {len(realizations)} реализаций из {filename}")
            except Exception as e:
                print(f"Ошибка при загрузке {filename}: {e}")
    
    return all_realizations


def load_realizations_from_datasets(base_path: str = None) -> list:
    """
    Загружает опыт реализаций из папки datasets в корне проекта.
    
    Args:
        base_path: базовый путь к проекту (если None, используется текущая директория)
        
    Returns:
        Список всех загруженных RealizationExperience объектов
    """
    if base_path is None:
        base_path = _resolve_base_path()
    
    datasets_path = os.path.join(base_path, "datasets")
    return load_realizations_from_directory(datasets_path)


def load_habits_from_dataset(path: str) -> list:
    """
    Загружает привычки (контекст → действие) из JSON датасета.
    
    Ожидает JSON с массивом объектов:
    {
        "context": список строк,
        "action": строка (имя действия),
        "strength": число (опционально, по умолчанию 1.0)
    }
    
    Args:
        path: путь к JSON файлу с привычками
        
    Returns:
        Список кортежей (context, action, strength)
    """
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    
    habits = []
    for row in raw:
        context = row.get("context", [])
        if isinstance(context, str):
            context = [context]
        
        action = row.get("action", "")
        strength = float(row.get("strength", 1.0))
        
        habits.append({
            "context": context,
            "action": action,
            "strength": strength
        })
    
    return habits


def load_habits_from_datasets(base_path: str = None) -> list:
    """
    Загружает все привычки из папки datasets.
    
    Args:
        base_path: базовый путь к проекту (если None, используется текущая директория)
        
    Returns:
        Список привычек {context, action, strength}
    """
    if base_path is None:
        base_path = _resolve_base_path()
    
    datasets_path = os.path.join(base_path, "datasets")
    all_habits = []
    
    if not os.path.exists(datasets_path):
        print(f"Директория не найдена: {datasets_path}")
        return all_habits
    
    # Загруженные файлы с привычками
    for filename in os.listdir(datasets_path):
        if filename.endswith(".json") and ("habit" in filename.lower() or filename == "habits.json"):
            file_path = os.path.join(datasets_path, filename)
            try:
                habits = load_habits_from_dataset(file_path)
                all_habits.extend(habits)
                print(f"[Loader] Загружено {len(habits)} привычек из {filename}")
            except Exception as e:
                print(f"[Loader] Ошибка при загрузке {filename}: {e}")
    
    return all_habits

