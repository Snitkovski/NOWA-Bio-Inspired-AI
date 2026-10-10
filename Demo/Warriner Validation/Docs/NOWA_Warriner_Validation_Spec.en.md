# NOWA × Warriner Validation Demo — Technical Specification

Russian version: [NOWA_Warriner_Validation_Spec.ru.md](NOWA_Warriner_Validation_Spec.ru.md)

**Status.** Normative specification. Scientific account of the platform: [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md).

The document specifies the original technical contract of lexical validation. The stimulus is delivered through prior initialisation of `NOWAHippocampus` with affectively coloured episodes from the Warriner et al. (2013) corpus; the target pipeline remains hippocampus — cortical pressure — basal ganglia — affective space. The association measure is Spearman rank correlation between the colony’s mean valence shift and the `V.Mean.Sum` ratings.

The modules `hippocampus_seeder.py`, `word_stimulus_encoder.py` (modes `lexical`, `sbert_neighbors`, `direct_vad`), `nowa_colony.py`, `warriner_validator.py`, a Streamlit interface and a CLI are specified. Interpretation thresholds for ρ, the requirement that seed and test corpora be disjoint, the implementation order, and the checklist before publication of results are fixed.

---

**Version:** 1.0  
**Status:** Ready for implementation  
**Aim:** Obtain a Spearman ρ between the mean valence shift of a NOWA colony and the human ratings `V.Mean.Sum` from Warriner et al. (2013)

---

## 1. Conceptual model

### Principal architectural decision

**Use NOWAHippocampus with prior initialisation of episodic memory**, rather than bypassing the hippocampus by direct injection into AffectiveSpace.

**Rationale:**
- It is biologically plausible: a word stimulus activates associative memory that already contains emotional traces
- It does not violate the architectural invariants of NOWA (the pipeline hippocampus → cortical pressure → basal ganglia → affective space remains intact)
- If `["happy"]` is presented to an empty hippocampus, there is no activation and ρ ≈ 0. The remedy is to fill the hippocampus with affectively coloured episodes before the stimulus is run

### Mechanism

```
Warriner CSV (13 915 words with V/A/D)
    ↓ sample_words(n=300, stratified)
    ↓
[INITIALISATION] HippocampusSeeder
    ├── Warriner → seed_experiences (affectively coloured episodes)
    ├── Each agent receives N_SEED episodes from Warriner
    └── The episodes cover the whole V/A/D range (low/mid/high)
    ↓
WordStimulusEncoder
    ├── word → context_events: List[str]  (NOWA format)
    ├── Mode A: ["word:happy", "valence:positive", "arousal:high"]
    └── Mode B: sentence-BERT → nearest Warriner neighbors → tokens
    ↓
NOWAColony.run_stimulus(context_events)
    ├── hippocampus.activate(context_events) → active_experiences
    ├── selector.compute_pressures(active_experiences, ...) → pressure_vector
    ├── agent.step(context_events) × N_TICKS
    └── measure: affective_space.axes delta
    ↓
SpearmanCorrelation(nowa_valence_shifts, warriner_V)
    ↓
ValidationReport + Streamlit Dashboard
```

---

## 2. Thresholds and success criteria

| ρ (Spearman, valence) | Interpretation | Action |
|---|---|---|
| ≥ 0.6 | Strong signal | Proceed to EmoBank |
| 0.4–0.6 | Proof of life | Optimise the encoder |
| 0.2–0.4 | Weak signal | Check the seed strategy |
| < 0.2 | No signal | Reconsider the context_event format |

---

## 3. New modules (files to be created)

```
nowa_validation/
├── hippocampus_seeder.py      # Memory initialisation from Warriner
├── word_stimulus_encoder.py   # word → context_events: List[str]
├── nowa_colony.py             # Colony management and the stimulus run
├── warriner_validator.py      # Orchestrator and correlations
├── demo_app.py                # Streamlit UI
├── run_quick.py               # CLI launch without a UI
├── data/
│   └── Ratings_Warriner_et_al.csv   # download from XANEW
└── requirements.txt
```

---

## 4. Module `hippocampus_seeder.py`

### Purpose

Fills the `NOWAHippocampus` of each agent with affectively coloured episodes before the stimulus is run. This is the agent’s “long-term semantic memory” of what words can mean emotionally.

### Structure of a seed episode

Each seed episode is an `Experience` in the hippocampus, created from a Warriner row:

```
word: "happy"
V.Mean.Sum: 8.21  →  valence: +0.821 (normalized)
A.Mean.Sum: 6.11  →  arousal: 0.639
D.Mean.Sum: 7.34  →  dominance: 0.793

→ Path with events:
  Event("word:happy",        EventType.CONTEXT)
  Event("valence:positive",  EventType.CONTEXT)
  Event("arousal:high",      EventType.CONTEXT)
  Event("dominance:high",    EventType.CONTEXT)

→ consequence: Event("affect_positive", EventType.CONSEQUENCE)
→ intensity: abs(valence) = 0.821
→ reward: valence = +0.821
```

### Coverage strategy

The seed corpus must cover the whole valence range evenly; otherwise the hippocampus is biased:

```
N_SEED_PER_AGENT = 500  # minimum for a meaningful activation
Stratification:
  - 100 words from the lower quartile of V (negative: "murder", "cancer", "torture")
  - 300 words from the middle range of V (neutral/mixed)
  - 100 words from the upper quartile of V (positive: "happy", "love", "victory")
```

### Interface

```python
class HippocampusSeeder:
    def __init__(
        self,
        warriner_df: pd.DataFrame,
        n_seed: int = 500,
        seed_strategy: Literal['stratified', 'random', 'full'] = 'stratified',
        rng: random.Random = None,
    )

    def build_seed_corpus(self) -> List[dict]:
        """
        Returns the list of seed records.
        Each record: {'word': str, 'v': float, 'a': float, 'd': float}
        Normalised values: v ∈ [-1,+1], a ∈ [0,1], d ∈ [0,1]
        """

    def seed_agent(self, agent: Any) -> int:
        """
        Fills the agent's hippocampus with seed episodes.
        Returns the number of episodes added.
        
        For each seed word:
        1. Create a Path with context_events (see the format below)
        2. Create a consequence Event from the sign of valence
        3. Call hippocampus.store(path, consequence, intensity, reward)
        4. If the word is frequent (|v| > 0.7): call hippocampus.reinforce()
        """

    def seed_colony(self, agents: List[Any]) -> Dict[str, int]:
        """
        Fills the whole colony. Each agent receives the same corpus
        (but in a different order, so that activation varies).
        Returns {agent_id: n_episodes_added}
        """
```

### Format of context_events for a seed episode

```python
def _word_to_events(word: str, v: float, a: float, d: float) -> List[str]:
    """
    Converts a word plus VAD into a list of event tokens for a Path.
    
    Obligatory tokens:
    - f"word:{word}"                    # lexical identity
    
    Valence tokens (by threshold):
    - "valence:very_positive"  if v > 0.6
    - "valence:positive"       if 0.2 < v <= 0.6
    - "valence:neutral"        if -0.2 <= v <= 0.2
    - "valence:negative"       if -0.6 <= v < -0.2
    - "valence:very_negative"  if v < -0.6
    
    Arousal tokens:
    - "arousal:high"           if a > 0.6
    - "arousal:medium"         if 0.4 <= a <= 0.6
    - "arousal:low"            if a < 0.4
    
    Dominance tokens:
    - "dominance:high"         if d > 0.6
    - "dominance:low"          if d < 0.4
    
    Categorical (NRC-style, optional if nrclex is available):
    - "emotion:joy", "emotion:fear", etc.
    """
```

### Intensity and reward parameters

```python
intensity = abs(v)                    # [0, 1] — how "strong" the episode is
reward = v                            # [-1, +1] — valence directly
encoding_strength = abs(v) * 0.8 + 0.2  # minimum 0.2, so that the episode enters memory

# Consequence Event:
if v > 0.1:
    consequence = Event("positive_valence_outcome", EventType.CONSEQUENCE)
elif v < -0.1:
    consequence = Event("negative_valence_outcome", EventType.CONSEQUENCE)
else:
    consequence = Event("neutral_outcome", EventType.CONSEQUENCE)

# Reinforcement for strong episodes:
if abs(v) > 0.7:
    hippocampus.reinforce(path, consequence, intensity=intensity)
    # additional strengthening — the word "murder" or "love" must
    # leave a deeper trace
```

---

## 5. Module `word_stimulus_encoder.py`

### Purpose

Converts a test word (from Warriner) into `context_events: List[str]` — precisely the format accepted by `agent.step()` and `hippocampus.activate()`.

**Critically important:** test words must NOT contain valence tokens (`"valence:positive"`). Otherwise the correct episodes are activated trivially and the correlation is an artefact. The test input must be lexical only.

### Three modes

#### Mode A: `lexical` (recommended baseline)

```python
def encode_lexical(word: str) -> List[str]:
    """
    Lexical tokens only — no valence information.
    This is an honest test: does the agent know that "happy" is a positive word
    solely because "word:happy" is present in memory.
    
    Returns:
    - [f"word:{word}"]
    
    Optionally, if nrclex is available (this does not reveal VAD):
    - add discrete NRC emotions as further tokens
    - [f"word:{word}", "emotion:joy", "emotion:trust"]
    """
```

#### Mode B: `sbert_neighbors` (recommended advanced mode)

```python
def encode_sbert_neighbors(word: str, warriner_df: pd.DataFrame, k: int = 5) -> List[str]:
    """
    1. Obtain the SBERT embedding of the word
    2. Find the K nearest neighbours in Warriner by cosine similarity
       (from the seed corpus already loaded into the hippocampus)
    3. Add them as co-activation tokens
    
    Returns:
    - [f"word:{word}", f"word:{neighbor1}", f"word:{neighbor2}", ...]
    
    Logic: if "happy" is semantically close to "joyful" and "cheerful",
    and those words are already in the agent's memory, they help to activate
    the correct affective traces.
    
    IMPORTANT: neighbours are sought by lexical meaning (SBERT) only,
    and NOT by valence — otherwise the test is cheated.
    """
```

#### Mode C: `direct_vad` (baseline and debugging only)

```python
def encode_direct_vad(word: str, warriner_row: dict) -> List[str]:
    """
    FOR COMPARISON ONLY — it reveals VAD to the agent.
    If this mode yields a high ρ and 'lexical' yields a low ρ,
    the problem is the semantic coverage of the seed corpus.
    
    Do NOT use it for the real validation.
    """
```

### Interface

```python
class WordStimulusEncoder:
    def __init__(
        self,
        mode: Literal['lexical', 'sbert_neighbors', 'direct_vad'] = 'lexical',
        warriner_df: Optional[pd.DataFrame] = None,
        sbert_model=None,
        k_neighbors: int = 5,
    )

    def encode(
        self,
        word: str,
        warriner_row: Optional[dict] = None,
    ) -> List[str]:
        """Main entry point. Returns context_events: List[str]"""

    def encode_batch(
        self,
        words: List[str],
        warriner_rows: Optional[List[dict]] = None,
    ) -> List[List[str]]:
        """Batch encoding for efficiency."""
```

---

## 6. Module `nowa_colony.py`

### Purpose

Manages N NOWA agents, runs the stimulus through each of them, and aggregates the results.

### Data classes

```python
@dataclass
class AgentResponse:
    agent_id: str
    archetype: str              # "explorer" | "passive" | "resource_pragmatist" | "anxious_loner"
    valence_before: float       # pleasure - pain before the stimulus
    valence_after: float        # pleasure - pain after N ticks
    valence_shift: float        # after - before
    arousal_shift: float
    da_delta: float             # dopamine delta
    ne_delta: float             # norepinephrine delta
    cortisol_delta: float
    serotonin_delta: float
    n_activated_memories: int   # how many episodes the stimulus activated
    stimulus_word: str
    raw_axes_before: dict
    raw_axes_after: dict


@dataclass
class ColonyResponse:
    word: str
    n_agents: int
    mean_valence_shift: float
    std_valence_shift: float    # IMPORTANT: check for collapse (SD << SD_human)
    mean_arousal_shift: float
    mean_da_delta: float
    mean_ne_delta: float
    mean_cortisol_delta: float
    mean_n_activated_memories: float
    per_archetype: Dict[str, float]     # archetype → mean valence shift
    agent_responses: List[AgentResponse]
    processing_time_s: float
```

### Initialisation of agents

```python
class NOWAColony:
    def __init__(
        self,
        n_agents: int = 100,
        ticks_per_stimulus: int = 10,
        seed: int = 42,
    )

    def initialize(
        self,
        warriner_df: pd.DataFrame,
        n_seed: int = 500,
        agent_factory=None,
    ) -> None:
        """
        1. Create N agents (through AgentFactory if it is available, otherwise directly)
        2. Apply genomic parameters (GenomeVector.random() for each)
        3. Assign archetypes from the genomic parameters
        4. Run HippocampusSeeder for each agent
        5. Record the baseline state (affective_space.axes snapshot)
        
        After initialize(), the agents are ready for run_stimulus().
        """
```

### Assignment of archetypes

The archetype is determined by two genomic parameters of the agent:

```
Axis X: nm_acc_k_cort (sensitivity to cortisol: 0.3..1.2)
Axis Y: dr_curiosity_baseline (baseline curiosity: 0.05..0.40)

Quadrants:
  low_cort  + high_curiosity  → "explorer"
  low_cort  + low_curiosity   → "passive"
  high_cort + high_curiosity  → "resource_pragmatist"
  high_cort + low_curiosity   → "anxious_loner"

Threshold: the median of the distribution over the colony (not a fixed constant)
```

### Running a stimulus

```python
def run_stimulus(self, context_events: List[str]) -> ColonyResponse:
    """
    For each agent:
    1. RESET: restore affective_space.axes from the baseline snapshot
       (do NOT recreate the agent — only the affective state)
    2. INJECT: call agent.step(context_events)
       - this activates hippocampus.activate(context_events)
       - obtains active_experiences
       - computes cortical pressure
       - passes through the basal ganglia to ThalamicGate
       - updates affective_space
    3. TICK: run a further (N_TICKS - 1) ticks with an empty context []
       (decay of the affective state, with no new stimulus)
    4. MEASURE: read affective_space.axes and compute the deltas
    5. NM: read the neuromodulator snapshot and compute the deltas
    
    IMPORTANT: do NOT call sleep() between stimuli — waking ticks only
    IMPORTANT: do NOT update ValueLayer during the run (reward=0 for ticks 2..N)
    """
```

### Reset of affective state between stimuli

```python
def _reset_agent_affective_state(self, agent: Any) -> None:
    """
    Resets ONLY the agent's affective state to the baseline.
    Does NOT touch: hippocampus, cortex, neuromodulators, value_layer.
    
    Algorithm:
    1. Obtain baseline_snapshot from self._baseline_states[agent_id]
    2. For affective_space: overwrite axes from the snapshot
    3. For affect_state (legacy): overwrite valence/arousal/threat/curiosity
    4. Do NOT reset affective_background or affective_persistence —
       they model the long-term background, which must remain
    
    Rationale: between the words "happy" and "murder" the agent must
    have the same starting affective background. The long-term
    personality characteristics (the background field) remain.
    """
```

---

## 7. Module `warriner_validator.py`

### Loading and sampling

```python
class WarrinerValidator:
    def __init__(
        self,
        warriner_csv_path: str,
        colony: NOWAColony,
        encoder: WordStimulusEncoder,
        n_words: int = 300,
        stratify_bins: bool = True,
        test_split_ratio: float = 0.2,  # 20% held-out test set
        seed: int = 42,
    )

    def load_warriner(self) -> pd.DataFrame:
        """
        Loads the CSV. Expected columns:
        - 'Word' (or 'word', 'lemma')
        - 'V.Mean.Sum' (or 'valence', 'V')
        - 'A.Mean.Sum' (or 'arousal', 'A')
        - 'D.Mean.Sum' (or 'dominance', 'D')
        
        Normalisation:
        - V: (v - 5.0) / 4.0  → [-1, +1]
        - A: (a - 1.0) / 8.0  → [0, 1]
        - D: (d - 1.0) / 8.0  → [0, 1]
        """

    def sample_words(self) -> Tuple[List[dict], List[dict]]:
        """
        Stratified sample.
        
        The document recommends: 50 low-V, 200 mid-V, 50 high-V
        for n_words=300.
        
        Returns (calibration_rows, test_rows).
        calibration_rows are used by HippocampusSeeder for the seed.
        test_rows are the words for validation (they must NOT intersect the seed).
        
        IMPORTANT: the seed corpus and the test corpus must be disjoint.
        Otherwise the agent "saw" the word at initialisation, and the correlation is trivial.
        """
```

### Train/test split

```
Warriner (13 915 words)
    ↓ stratified split
    ├── seed_corpus (80% = ~11 132 words)  → HippocampusSeeder
    │   The agent knows these words "from birth"
    └── test_corpus (20% = ~2 783 words)  → Validation
        The agent has never seen these words directly.
        The test checks generalisation through semantic similarity.

From test_corpus, sample n_words=300 (stratified).
```

### Computation of correlations

```python
@dataclass
class ValidationResult:
    n_words: int
    encoder_mode: str
    
    # Principal metrics (valence)
    spearman_rho_valence: float
    spearman_p_valence: float
    pearson_r_valence: float
    ccc_valence: float          # Concordance Correlation Coefficient
    
    # Arousal
    spearman_rho_arousal: float
    spearman_p_arousal: float
    
    # Per archetype
    archetype_correlations: Dict[str, float]   # archetype → ρ
    archetype_n_agents: Dict[str, int]          # archetype → count
    
    # Variance check (anti-collapse)
    sd_nowa_valence: float
    sd_human_valence: float
    sd_ratio: float             # must be > 0.1, otherwise collapse
    
    # Memory activation statistics
    mean_activated_memories: float   # mean number of activated episodes
    zero_activation_ratio: float     # share of words with zero memory activation
    
    # Raw data for plotting
    words: List[str]
    warriner_valence_norm: List[float]
    nowa_valence_shifts: List[float]
    warriner_arousal_norm: List[float]
    nowa_arousal_shifts: List[float]
    colony_responses: List[ColonyResponse]
    
    def summary(self) -> str:
        """Human-readable summary with an interpretation."""


def compute_ccc(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """
    Concordance Correlation Coefficient.
    CCC = 2 * cov(x,y) / (var(x) + var(y) + (mean_x - mean_y)^2)
    It accounts for both the correlation and the shift of the mean.
    CCC > 0.3 for arousal is the state-of-the-art level (according to the document).
    """
```

### Diagnosis of zero activations

```python
def diagnose_zero_activations(
    self,
    result: ValidationResult,
    threshold: float = 0.3,
) -> dict:
    """
    If zero_activation_ratio > threshold:
    - The seed corpus does not cover the test words semantically
    - n_seed must be increased, or the encoder switched to sbert_neighbors
    
    Returns a diagnostic report:
    {
        'zero_activation_ratio': float,
        'worst_words': List[str],  # words with the least activation
        'recommendation': str,
    }
    """
```

---

## 8. Module `demo_app.py` — Streamlit UI

### Page structure

```
Streamlit App
├── Sidebar: Configuration
│   ├── Warriner CSV path
│   ├── Encoder mode (lexical | sbert_neighbors | direct_vad)
│   ├── Colony size (50..500, default 100)
│   ├── Words to test (50..1000, default 300)
│   ├── Ticks per stimulus (5..30, default 10)
│   ├── Seed size (100..2000, default 500)
│   └── [Run Validation]
│
└── Main area (Tabs)
    ├── Main Results
    │   ├── Metric cards: ρ(V), r(V), CCC(V), ρ(A)
    │   ├── Variance check: SD_NOWA vs SD_human
    │   ├── Memory activation: mean activated memories per word
    │   └── Signal badge: PROOF OF LIFE / WEAK / NO SIGNAL
    │
    ├── Scatter Plot
    │   ├── NOWA valence shift vs Warriner V (with trendline)
    │   ├── Hover: word name + both values
    │   └── Color: by archetype
    │
    ├── Per-Archetype Analysis
    │   ├── Bar chart: ρ per archetype
    │   ├── Distribution: valence shift histograms per archetype
    │   └── Key test: is anxious_loner more negative on neg-V words?
    │
    ├── Memory Diagnostics
    │   ├── Scatter: n_activated_memories vs |warriner_V|
    │   ├── Zero-activation words list
    │   └── Seed coverage visualization
    │
    ├── Word-Level Data
    │   ├── Sortable table: word, warriner_V, nowa_shift, residual
    │   ├── Top 20 outliers (worst predictions)
    │   └── Download CSV button
    │
    └── Neuromodulators
        ├── DA delta vs Warriner V scatter
        ├── NE delta vs Warriner A scatter
        └── Cortisol delta vs Warriner V (do negative words raise cortisol?)
```

### Principal visualisations

#### Anti-collapse check (obligatory to show the client)

```
SD check:
  SD(Human Warriner V) = X.XXX
  SD(NOWA valence shift) = X.XXX
  Ratio = X.XX  [green if > 0.1, red if < 0.05]

"If the ratio is below 0.1, the agents answer almost identically (collapse).
 The correlation may be an artefact rather than a real signal."
```

#### Per-archetype hypothesis test

```
H0: NOWA(anxious_loner | neg_V_words).valence_shift 
  = NOWA(explorer | neg_V_words).valence_shift

Test: a t-test between the two groups on the subset of neg-V words (V < -0.3)
Display: t-statistic, p-value, effect size Cohen's d

"If d > 0.5 and p < 0.05, the archetypes are biologically distinguishable."
```

### Footer disclaimer (obligatory on every page)

```
This report was generated by a computational simulation (NOWA synthetic 
respondent platform). It does NOT involve real human respondents. Findings are 
directional and intended to support hypothesis generation, creative triage, and 
pre-research exploration. They should NOT be used as the sole basis for 
high-stakes marketing decisions or substituted for human consumer research.

Validation correlation with Warriner et al. (2013) benchmark:
Spearman ρ = {result.spearman_rho_valence:.3f} (n={result.n_words} words, 
encoder={result.encoder_mode}).
```

---

## 9. CLI `run_quick.py`

```
Usage:
  python run_quick.py \
    --warriner data/Ratings_Warriner_et_al.csv \
    --words 300 \
    --agents 100 \
    --seed-size 500 \
    --ticks 10 \
    --encoder lexical \
    --output results.json

Output (stdout):
  [Colony] Initializing 100 agents...
  [Seeder] Loading 500 seed episodes per agent...
  [Seeder] Seed coverage: low_V=100, mid_V=300, high_V=100
  [Validation] Processing word 1/300: abandon
  ...
  [Validation] Processing word 300/300: zest

  === NOWA × Warriner Validation ===
  Words tested: 300
  Encoder: lexical
  Seed size: 500

  VALENCE:
    Spearman ρ = 0.XXX  (p = X.XXXe-XX)
    Pearson  r = 0.XXX
    CCC        = 0.XXX
    PROOF OF LIFE  [or the corresponding status]

  AROUSAL:
    Spearman ρ = 0.XXX  (p = X.XXXe-XX)

  VARIANCE CHECK:
    SD(human)  = 0.XXX
    SD(NOWA)   = 0.XXX
    Ratio      = 0.XX  [OK / COLLAPSE WARNING]

  MEMORY DIAGNOSTICS:
    Mean activated memories per word: X.X
    Zero-activation words: XX (XX.X%)

  PER-ARCHETYPE correlations (valence):
    explorer:            ρ = 0.XXX
    passive:             ρ = 0.XXX
    resource_pragmatist: ρ = 0.XXX
    anxious_loner:       ρ = 0.XXX
```

---

## 10. `requirements.txt`

```
# Core
streamlit>=1.30
pandas>=2.0
numpy>=1.24
scipy>=1.10
plotly>=5.15
scikit-learn>=1.3

# NLP (for the encoder)
sentence-transformers>=2.2   # sbert_neighbors mode
nrclex>=3.0                  # lexical mode with NRC emotions

# Statistics
pingouin>=0.5                # CCC and ICC calculations

# Optional (for speed)
torch>=2.0                   # if SBERT is used
```

---

## 11. Implementation order

### Day 1 (4 hours)

1. `hippocampus_seeder.py` — basic version (stratified, lexical tokens)
2. `word_stimulus_encoder.py` — the `lexical` mode only
3. `nowa_colony.py` — initialisation, `run_stimulus()`, and reset
4. `run_quick.py` — CLI without a UI
5. A run of 300 words and 100 agents, yielding the first value of ρ

### Days 2–3

6. Outlier analysis: which words the model predicts worst
7. `word_stimulus_encoder.py` — the `sbert_neighbors` mode
8. Comparison: `lexical` versus `sbert_neighbors` versus `direct_vad`
9. Per-archetype diagnosis

### Days 4–5

10. `demo_app.py` — Streamlit UI
11. Per-archetype hypothesis test (t-test)
12. Memory-diagnostics tab
13. Export and the disclaimer footer

---

## 12. Critical checks before publication of results

- [ ] seed_corpus ∩ test_corpus = ∅ (no data leakage)
- [ ] SD(NOWA) / SD(human) > 0.1 (no collapse)
- [ ] zero_activation_ratio < 0.3 (the hippocampus activates)
- [ ] p-value < 0.01 at n=300 (statistical significance)
- [ ] The `direct_vad` baseline has been checked: if ρ_direct is much larger than ρ_lexical, a better encoder is required
- [ ] Per archetype: anxious_loner yields a more negative shift on neg-V words
- [ ] The disclaimer is present on every screen and in the CSV export

---

## 13. Expected results and risks

### Optimistic scenario (ρ ≥ 0.5)

The seed corpus gives sufficient coverage. SBERT neighbours strengthen activation of rare words. Archetypes show significantly different responses. The demonstration is ready for the first clients.

### Realistic scenario (ρ 0.3–0.5)

Weak words (abstract, rare, culturally specific) give zero activation. Remedy: increase the seed to 2000+ and add the `sbert_neighbors` encoder.

### Pessimistic scenario (ρ < 0.2)

The `context_events` format does not match the way the hippocampus indexes episodes. Diagnosis: inspect `NOWAHippocampus._build_query_signature()` — how it hashes `"word:happy"` compared with how the seed episodes are stored. Token normalisation (lowercase, stripping of spaces) may be required.

---

*The specification is ready to be handed to the implementing agent. Every dependency on existing NOWA modules is stated explicitly. The new modules do not modify existing code; they use only the public API.*
