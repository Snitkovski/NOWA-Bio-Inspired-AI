# NOWA — a Neural Memory Agent with Automatic Training

Russian version: [README_AUTO_TRAINING.ru.md](README_AUTO_TRAINING.ru.md)

**Status (27 September 2026).** A core document. The current scientific exposition of the complex, in Russian and in English, is [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md). The text below retains the wording of its original drafting: a normative module contract or a laboratory record.

An intelligent agent with an integrated memory system and **automatic training of the action selector**.

## Quick Start

### Installation

```bash
# Clone the repository
git clone <repo>
cd NOWA_2

# Create a virtual environment
python -m venv .venv

# Activate the environment
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt
```

### Launching the GUI

```bash
python src/gui.py
```

## Principal Functions

### 1. **Loading experience from datasets**
- Press "Load dataset"
- Choose a JSON file of experiences
- The system adds them to memory automatically

### 2. **Automatic training** (new)
- Press "Auto-training"
- Set the parameters (epochs, learning rate)
- The system trains itself on the dataset
- Watch accuracy before and after

### 3. **Interactive dialogue**
- Write questions
- Give ratings
- The system learns from the ratings

### 4. **State inspector**
- View of every experience in memory
- Action statistics
- Selector weights

## How Does Automatic Training Work?

```
JSON dataset → load → train → accuracy improves
                         ↓
                   Each epoch:
                   1. Take an experience
                   2. The selector chooses an action
                   3. Compare it with the correct one
                   4. Give a reward or a penalty
                   5. Update the weights

Result: the system answers a wider range of questions correctly.
```

## Testing

```bash
# All tests (23)
pytest tests/ -v

# Trainer only
pytest tests/test_trainer.py -v

# Short traceback
pytest tests/ -v --tb=short

# Result: 23 passed
```

## Project Structure

```
NOWA_2/
├── src/
│   ├── agent.py              # Main agent
│   ├── hippocampus.py        # Episodic memory
│   ├── cortex.py             # Semantic memory
│   ├── selector.py           # Action selection
│   ├── trainer.py            # Automatic training
│   ├── loader.py             # Dataset loading
│   ├── gui.py                # GUI
│   └── ...
├── tests/
│   ├── test_agent.py
│   ├── test_selector.py
│   ├── test_hippocampus.py
│   ├── test_trainer.py       # Trainer tests
│   └── ...
├── datasets/
│   └── test.json             # Example dataset
├── LEARNING.md               # Detailed guide
├── CHANGELOG.md              # List of changes
└── examples_training.py      # Usage examples
```

## Usage Examples

### Example 1: simple training
```python
from trainer import SelectorTrainer
from loader import load_experiences_from_datasets_folder

# Load experiences
experiences = load_experiences_from_datasets_folder()

# Create the trainer
trainer = SelectorTrainer(selector, hippocampus, cortex)

# Train
history = trainer.train_full(experiences, epochs=5, learning_rate=0.5)

# Read the result
accuracy = trainer.get_accuracy(experiences)
print(f"Accuracy: {accuracy:.2%}")
```

### Example 2: detailed analysis
```python
# Results for each experience
results = trainer.get_detailed_results(experiences)

for result in results:
    print(f"Expected: {result['expected_action']}")
    print(f"Chosen: {result['chosen_action']}")
    print(f"Correct: {result['correct']}")
```

### Example 3: run all examples
```bash
python examples_training.py
```

## Results

**Before training:** every question may receive the same answer  
**After training:** the system answers different questions correctly

```
Question        Expected            Before  After
─────────────────────────────────────────────────
"who are you?"  ответить_кто_я      no      yes
"how are you?"  сказать_привет      no      yes
"help me"       отказаться          no      yes
─────────────────────────────────────────────────
Accuracy:                          33%     100%
```

## Training Parameters

| Parameter | Value | Description |
|----------|----------|---------|
| Epochs | 5-10 | Number of passes over the dataset |
| Learning rate | 0.1-1.0 | Learning speed (higher means faster) |
| Batch size | - | One experience at a time (can be improved) |

**Recommendations:**
- Small datasets: 5-10 epochs, learning rate 0.5
- Large datasets: 20 or more epochs, learning rate 0.1

## Troubleshooting

### Problem: accuracy does not improve
- Confirm that the dataset is loaded
- Try raising the learning rate to 0.7-1.0
- Increase the number of epochs to 10-20

### Problem: the system gives only one answer
- This is expected before training
- Press "Auto-training" to train
- Or give different ratings by hand

### Problem: memory is full
- Save the state (the "Save" button)
- Restart the application
- Load the save

## Documentation

- **LEARNING.md** — a detailed account of the architecture
- **CHANGELOG.md** — the list of all changes
- Comments in the code

## Code Quality

- **23 tests** — all passed
- **Coverage** — all principal components
- **Documentation** — in the code and in the files
- **Examples** — 4 complete examples

## Statistics

- **Python files:** 15+
- **Lines of code:** ~2000
- **Tests:** 23
- **Documentation:** complete

## Capabilities

- Loading experience from JSON datasets
- Automatic training of the selector
- Interactive dialogue with ratings
- Saving and loading state
- Memory inspector
- Full test coverage
- Usage examples

## Possible Improvements

- [ ] Visualization of accuracy graphs
- [ ] Batch processing of data
- [ ] Cross-validation
- [ ] Adaptive learning rate
- [ ] Export of results to CSV

## License

PolyForm Strict License 1.0.0 — see [LICENSE](../LICENSE) in the repository root.

## Author

NOWA Project  
January 2026

---

**Ready for use.**
