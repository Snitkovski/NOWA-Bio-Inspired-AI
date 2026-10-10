# -*- coding: utf-8 -*-
"""Prepend bilingual abstracts. Temporary; deleted after use."""
from pathlib import Path

DOCS = Path(r"E:/git/NOWA-Cognitive/Demo/Tamagochi Chinchilla/Docs")

ABSTRACTS = {
    "NOWA_INTEGRATION_SPEC.md": """<!-- bilingual-abstract -->

**[Русский](#ru) · [English](#en)**

<a id="ru"></a>

## Аннотация

Документ задаёт нормативный протокол интеграции демонстрационного организма «шиншилла» с когнитивным ядром репозитория. Протокол предписывает замену локальных подсистем каноническими компонентами: четырёхмерного адаптера аффекта — восьмимерным аффективным пространством; локального планировщика трёх циклов потребностей — системой драйвов и системой энергии; эвристического отбора поведенческих цепочек — конкурирующим контуром базальных ганглиев с таламическим выбором; консолидации локальной памяти — менеджером сна, гиппокампом и корковой памятью. Отдельными задачами вводятся нейромодуляторное состояние, состояние бодрствования, слой эмоциональной регуляции и слой арбитража конфликта.

Десять задач образуют последовательность интерфейсных замен. Для каждой фиксируются удаляемая или сохраняемая локальная точка входа, инициализация модуля ядра, отображение драйвов на поведенческие цепочки и место вызова внутри шага симуляции. Обучение каналов базальных ганглиев и корковая консолидация отнесены к фазе сна. Бодрствование связывается с предпочтением цепочек отхода ко сну и с оценкой когнитивной надёжности, передаваемой слою визуализации. Завершающие задачи задают отладочное отображение слоёв ядра и сериализацию его состояния между сеансами.

Протокол фиксирует целевой состав замены и порядок работ. Точка входа демонстрации одновременно импортирует модули ядра, в том числе аффективное пространство, базальные ганглии, гиппокамп, сон, нейромодуляторы и бодрствование, и локальные классы SchedulingSystem и MemorySystem. Подключение отдельных модулей и завершение программы замены представляют собой различные статусы.

<a id="en"></a>

## Abstract

The document sets out a normative protocol for integrating the demonstration organism, the chinchilla, with the cognitive core of the repository. The protocol prescribes replacement of local subsystems by canonical components: the four-dimensional affect adapter by an eight-dimensional affective space; the local scheduler of three need cycles by the drive system together with the energy system; heuristic selection of behavioural chains by a competing basal-ganglia circuit with thalamic selection; and consolidation of local memory by the sleep manager, the hippocampus, and cortical memory. Separate tasks introduce neuromodulatory state, wakefulness state, an emotional-regulation layer, and a conflict-arbitration layer.

The ten tasks form a sequence of interface replacements. For each task the protocol records the local entry point to be removed or retained, the initialisation of the core module, the mapping from drives to behavioural chains, and the call site within the simulation step. Learning in basal-ganglia channels and cortical consolidation are assigned to the sleep phase. Wakefulness is linked to a preference for bedtime chains and to an estimate of cognitive reliability passed to the visualisation layer. The closing tasks specify a debug display of the core layers and serialisation of core state across sessions.

The protocol fixes the target composition of the replacement and the order of the work. The demonstration entry point simultaneously imports core modules, including affective space, basal ganglia, hippocampus, sleep, neuromodulators, and wakefulness, and the local classes SchedulingSystem and MemorySystem. Attachment of individual modules and completion of the replacement programme are distinct statuses.

---

""",
    "IMPLEMENTATION_SPEC.md": """<!-- bilingual-abstract -->

**[Русский](#ru) · [English](#en)**

<a id="ru"></a>

## Аннотация

Документ задаёт нормативный протокол доработки демонстрационного организма «шиншилла», предназначенный для агентной реализации. Десять задач упорядочены по приоритету и объявлены атомарными и взаимно независимыми. Начальные задачи относятся к локальной подсистеме памяти и к выбору поведенческих цепочек: согласование ключей функции оценки награды со словарём аффективного состояния, вызов сохранения памяти при завершении сеанса и с заданным периодом внутри шага симуляции, а также передача предложений локального планировщика в процедуру выбора цепочки.

Дальнейшие задачи касаются временной устойчивости и выразительности цикла pygame. Протокол требует ограничить приращение времени в проигрывателе анимации, включить в цепочки восемнадцать действий библиотеки, которые текст спецификации квалифицирует как не входящие ни в одну цепочку, заполнять постуральный слой по осям аффекта и микрослой в интервалах между действиями, а также допустить вероятностный пропуск шагов цепочки. Отдельными пунктами задаются циркадная окраска фона и индикатор благополучия.

Спецификация фиксирует причину каждого расхождения и ожидаемый вид правки в локальных модулях памяти, планировщика, конфигурации цепочек и графического движка. Она представляет собой протокол подлежащих выполнению изменений.

<a id="en"></a>

## Abstract

The document sets out a normative protocol for further work on the demonstration organism, the chinchilla, intended for agent implementation. Ten tasks are ordered by priority and are declared atomic and mutually independent. The opening tasks concern the local memory subsystem and the selection of behavioural chains: alignment of the reward-function keys with the affective-state dictionary, invocation of memory saving at session end and at a stated period inside the simulation step, and passage of the local scheduler’s suggestions into the chain-selection procedure.

The subsequent tasks concern temporal stability and expressiveness of the pygame loop. The protocol requires a bound on the time increment in the animation player, inclusion in the chains of eighteen library actions that the specification text classifies as belonging to no chain, filling of the postural layer from affect axes and of the micro layer during intervals between actions, and probabilistic omission of chain steps. Separate items specify circadian tinting of the background and a wellbeing indicator.

The specification records the cause of each discrepancy and the expected form of the edit in the local memory module, the scheduler, the chain configuration, and the graphics engine. It constitutes a protocol of changes that are to be carried out.

---

""",
    "PHASE3_SCHEDULING_SYSTEM.md": """<!-- bilingual-abstract -->

**[Русский](#ru) · [English](#en)**

<a id="ru"></a>

## Аннотация

Документ представляет отчёт о построенной локальной системе планирования демонстрационного организма, образующей третью фазу работ. Описаны класс автономного цикла и управляющий класс, которые ведут три потребности — голод, усталость и скуку — с раздельными скоростями нарастания и насыщения, порогами критического и удовлетворённого состояний и ускорением усталости в период активности. К циклам присоединён циркадный ритм с периодом порядка двадцати минут симуляционного времени. Предложения драйвов комбинируются с весами, накопленными подсистемой памяти, и участвуют в отборе поведенческих цепочек, когда суммарный вес превышает указанный в отчёте порог 0,8.

Отчёт фиксирует встраивание в шаг агента: обновление циклов по активным цепочкам, перенос приращений в аффективное состояние и включение статуса циклов, драйвов и циркадной фазы в снимок состояния. В качестве поведенческих следствий описаны конкуренция потребностей и регулярности, производные от голода, активности и скуки. Приведены настраиваемые параметры циклов и перечень созданных файлов локального планировщика вместе с сопровождающими проверками.

В разделе результатов отчёт сообщает о прохождении шестнадцати проверок планировщика, шести интеграционных проверок, пяти проверок базовой функциональности и десяти проверок памяти, суммируя их как тридцать семь из тридцати семи. Эти величины приводятся как сведения самого отчёта. Описанный контур является локальной системой SchedulingSystem; точка входа демонстрации импортирует её совместно с модулями когнитивного ядра.

<a id="en"></a>

## Abstract

The document is a report on the local scheduling system of the demonstration organism, constituting the third phase of the work. It describes an autonomous-cycle class and a controlling class that maintain three needs—hunger, tiredness, and boredom—with separate rates of increase and satiation, thresholds of critical and satisfied states, and an acceleration of tiredness during activity. A circadian rhythm with a period of about twenty minutes of simulation time is attached to the cycles. Drive suggestions are combined with weights accumulated by the memory subsystem and take part in behavioural-chain selection when the combined weight exceeds the threshold of 0.8 stated in the report.

The report records the embedding in the agent step: updating cycles from active chains, transferring increments into affective state, and including cycle status, drives, and circadian phase in the state snapshot. As behavioural consequences it describes competition among needs and regularities derived from hunger, activity, and boredom. Tunable cycle parameters are given, together with the list of files created for the local scheduler and the accompanying checks.

In the results section the report states that sixteen scheduler checks, six integration checks, five checks of basic functionality, and ten memory checks passed, summing these as thirty-seven out of thirty-seven. These figures are given as statements of the report itself. The circuit described is the local SchedulingSystem; the demonstration entry point imports it together with the modules of the cognitive core.

---

""",
    "PHASE2_MEMORY_SYSTEM.md": """<!-- bilingual-abstract -->

**[Русский](#ru) · [English](#en)**

<a id="ru"></a>

## Аннотация

Документ представляет отчёт о построенной локальной подсистеме обучения и консолидации памяти, образующей вторую фазу работ. Описаны запись взаимодействия с аффективным контекстом до и после поведенческой цепочки, накопление предпочтений по доле успеха, недавней успешности и убывающему бонусу новизны, а также оценка награды по изменениям, специфичным для типа цепочки, и по общему сдвигу аффективного тона. Награда ограничивается отрезком от минус единицы до единицы. Консолидация отнесена к периодам покоя; сохранение и загрузка выполняются в формате JSON с ограничением числа хранимых записей.

Отчёт фиксирует встраивание подсистемы в агента: инициализацию файла памяти, регистрацию завершённой цепочки, использование выученных весов при выборе поведения и сохранение при завершении сеанса. Приведены ёмкость журнала, интервал консолидации и порядок вычислительной стоимости основных операций. В качестве содержания следующей фазы названы циклы голода, усталости и скуки, сопряжённые с выученными предпочтениями.

В разделе покрытия отчёт перечисляет десять проверок подсистемы памяти как пройденные, пять из пяти проверок базовой функциональности как пройденные и отдельно указывает, что интеграционные проверки проходят для трёх случаев из четырёх, относя оставшийся сбой к шрифту графического интерфейса. Заключительная строка статуса сообщает о десяти пройденных проверках памяти из десяти. Указанные величины воспроизводятся как формулировки отчёта, каждая в той рубрике, в которой она приведена. Описанный контур является локальной системой MemorySystem; точка входа демонстрации импортирует её совместно с модулями когнитивного ядра.

<a id="en"></a>

## Abstract

The document is a report on the local learning and memory-consolidation subsystem, constituting the second phase of the work. It describes the recording of an interaction with affective context before and after a behavioural chain, the accumulation of preferences from success rate, recent success, and a decaying novelty bonus, and the evaluation of reward from chain-specific changes and from the general shift in affective tone. Reward is bounded to the interval from minus one to one. Consolidation is assigned to rest periods; saving and loading are performed in JSON, with a limit on the number of stored records.

The report records the embedding of the subsystem in the agent: initialisation of the memory file, registration of a completed chain, use of learned weights in behaviour selection, and saving at session end. Journal capacity, consolidation interval, and the computational cost of the principal operations are stated. The next phase is described as the introduction of hunger, tiredness, and boredom cycles coupled to the learned preferences.

In the coverage section the report lists ten checks of the memory subsystem as passed and five of five checks of basic functionality as passed, and it separately states that integration checks pass in three cases out of four, attributing the remaining failure to a graphical-interface font. The closing status line states that ten memory checks out of ten passed. These figures are reproduced as formulations of the report, each in the rubric in which it appears. The circuit described is the local MemorySystem; the demonstration entry point imports it together with the modules of the cognitive core.

---

""",
    "chinchilla_agent_spec.md": """<!-- bilingual-abstract -->

**[Русский](#ru) · [English](#en)**

<a id="ru"></a>

## Аннотация

Документ задаёт техническую спецификацию версии 1.0 целевого когнитивного агента «шиншилла», построенного на архитектуре NOWA. Фиксируются репертуар из семидесяти четырёх действий с этологической группировкой, четырнадцать типов поведенческих цепочек, восемнадцать именованных зон клетки и трёхслойная команда визуализации, различающая действие, позу и микродвижение. Динамика организма выводится из пяти накопительных драйвов и системы энергии, восьмимерного аффективного вектора с заданными антагонистическими парами осей, пяти нейромодуляторов и конкуренции каналов базальных ганглиев с итоговым выбором через таламический вентиль, температура которого зависит от норадреналина.

Спецификация отдельно определяет эпизодическую память гиппокампа, образование корковых паттернов и обновление памяти цепочек исключительно в фазе сна, а также изолированное обучение временных различий по правилу TD(0), читающее скалярную награду и слепок состояния. Заданы жёсткие инварианты с отказом при нарушении, мягкие ограничения, регистрируемые в журнале отказов, и количественные пределы доли мнемического импульса, числа внутренних циклов и речевых событий. Минимальный снимок для восстановления включает драйвы, энергию, аффект, нейромодуляторы, гиппокамп, кору, память цепочек, слой ценности и каналы базальных ганглиев.

Сценарии TC-01–TC-35 сформулированы как ожидаемые реакции на заданные начальные условия: рефлексы потребностей, развёртывание цепочек, аффективные переходы, соблюдение ограничений, патологии благополучия, научение и контракт вывода pygame. Эти сценарии задают приёмочные условия спецификации. Документ описывает целевую архитектуру организма. Точка входа демонстрации импортирует соответствующие модули ядра и одновременно сохраняет локальные SchedulingSystem и MemorySystem.

<a id="en"></a>

## Abstract

The document sets out the version 1.0 technical specification of the target cognitive agent, the chinchilla, built on the NOWA architecture. It fixes a repertoire of seventy-four actions with an ethological grouping, fourteen types of behavioural chain, eighteen named cage zones, and a three-layer visualisation command distinguishing action, posture, and micromovement. The dynamics of the organism are derived from five accumulating drives and an energy system, an eight-dimensional affective vector with stated antagonistic axis pairs, five neuromodulators, and competition among basal-ganglia channels with final selection through a thalamic gate whose temperature depends on norepinephrine.

The specification separately defines hippocampal episodic memory, the formation of cortical patterns and the updating of chain memory exclusively in the sleep phase, and isolated temporal-difference learning under the TD(0) rule, which reads a scalar reward and a state snapshot. Hard invariants that fail on violation, soft constraints recorded in a failure log, and quantitative limits on the share of mnemonic impulse, the number of internal cycles, and speech events are stated. The minimal snapshot for restoration includes drives, energy, affect, neuromodulators, hippocampus, cortex, chain memory, the value layer, and basal-ganglia channels.

Scenarios TC-01 through TC-35 are formulated as expected responses to stated initial conditions: need reflexes, unfolding of chains, affective transitions, observance of constraints, wellbeing pathologies, learning, and the pygame output contract. These scenarios state the acceptance conditions of the specification. The document describes the target architecture of the organism. The demonstration entry point imports the corresponding core modules and at the same time retains the local SchedulingSystem and MemorySystem.

---

""",
}


def main() -> None:
    modified = []
    for name, abstract in ABSTRACTS.items():
        path = DOCS / name
        if not path.is_file():
            print(f"MISSING {name}")
            continue
        raw = path.read_bytes()
        decoded = raw.decode("utf-8")
        if "<!-- bilingual-abstract -->" in decoded:
            print(f"SKIP already marked {name}")
            continue
        nl = "\r\n" if b"\r\n" in raw else "\n"
        prefix = abstract.replace("\n", nl)
        if not prefix.endswith(nl + nl) and prefix.endswith("---" + nl):
            prefix += nl
        prefix_bytes = prefix.encode("utf-8")
        path.write_bytes(prefix_bytes + raw)
        written = path.read_bytes()
        if written[: len(prefix_bytes)] != prefix_bytes or written[len(prefix_bytes) :] != raw:
            raise SystemExit(f"BODY MISMATCH {name}")
        if written.count(b"<!-- bilingual-abstract -->") != 1:
            raise SystemExit(f"MARKER COUNT {name}")
        modified.append(name)
        print(f"OK {name} prefix={len(prefix_bytes)} original={len(raw)}")
    summary = DOCS / "PROJECT_COMPLETE_SUMMARY.md"
    summary_text = summary.read_text(encoding="utf-8")
    if "<!-- bilingual-abstract -->" in summary_text:
        raise SystemExit("SUMMARY WAS MODIFIED")
    print("MODIFIED")
    for name in modified:
        print(name)


if __name__ == "__main__":
    main()
