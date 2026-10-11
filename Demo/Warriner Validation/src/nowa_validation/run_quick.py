"""CLI runner for the NOWA x Warriner validation demo."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from nowa_validation.nowa_colony import NOWAColony
from nowa_validation.ui_i18n import peek_lang, t
from nowa_validation.warriner_validator import ValidationResult, WarrinerValidator
from nowa_validation.word_stimulus_encoder import WordStimulusEncoder


def _progress(index: int, total: int, word: str, lang: str) -> None:
    print(t("cli_progress", lang, index=index, total=total, word=word))


def _json_default(value: Any) -> Any:
    if hasattr(value, "__dict__"):
        return dict(value.__dict__)
    return str(value)


def main(argv: list[str] | None = None) -> int:
    lang = peek_lang(list(sys.argv[1:] if argv is None else argv))
    parser = argparse.ArgumentParser(description=t("cli_description", lang))
    parser.add_argument("--lang", choices=["en", "ru"], default=None, help="UI language (en or ru). Overrides NOWA_LANG.")
    parser.add_argument("--warriner", required=True, help="Path to Warriner CSV.")
    parser.add_argument("--words", type=int, default=300, help="Held-out words to test.")
    parser.add_argument("--agents", type=int, default=100, help="Colony size.")
    parser.add_argument("--seed-size", type=int, default=500, help="Seed episodes per agent.")
    parser.add_argument("--ticks", type=int, default=20, help="Ticks per stimulus.")
    parser.add_argument(
        "--affective-gain",
        type=float,
        default=1.8,
        help="Multiplier for affective_space inputs from memory signal.",
    )
    parser.add_argument(
        "--signal-ticks",
        type=int,
        default=3,
        help="Ticks where stimulus is actively injected.",
    )
    parser.add_argument(
        "--memory-top-k",
        type=int,
        default=3,
        help="Top-K activated episodes used for VAD signal.",
    )
    parser.add_argument(
        "--memory-min-activation",
        type=float,
        default=0.3,
        help="Min activation_energy threshold for episode inclusion.",
    )
    parser.add_argument(
        "--encoder",
        choices=["lexical", "sbert_neighbors", "direct_vad"],
        default="sbert_neighbors",
        help="Stimulus encoding mode.",
    )
    parser.add_argument(
        "--protocol",
        choices=["heldout", "in_vocab"],
        default="heldout",
        help="heldout for disjoint validation, in_vocab for a core smoke test.",
    )
    parser.add_argument("--seed", type=int, default=42, help="Deterministic random seed.")
    parser.add_argument("--output", default="", help="Optional JSON output path.")
    args = parser.parse_args(argv)
    if args.lang in ("en", "ru"):
        lang = args.lang

    print(t("cli_init", lang, n=args.agents))
    colony = NOWAColony(
        n_agents=args.agents,
        ticks_per_stimulus=args.ticks,
        signal_ticks=args.signal_ticks,
        affective_gain=args.affective_gain,
        memory_top_k=args.memory_top_k,
        memory_min_activation=args.memory_min_activation,
        seed=args.seed,
    )
    encoder = WordStimulusEncoder(mode=args.encoder)
    validator = WarrinerValidator(
        warriner_csv_path=args.warriner,
        colony=colony,
        encoder=encoder,
        n_words=args.words,
        validation_protocol=args.protocol,
        seed=args.seed,
    )

    print(t("cli_seed", lang, n=args.seed_size))
    result: ValidationResult = validator.run(
        seed_size=args.seed_size,
        progress_callback=lambda index, total, word: _progress(index, total, word, lang),
    )

    print()
    print(result.summary())
    print()
    print(t("cli_backend", lang, name=colony.backend_name))
    print(t("cli_protocol", lang, protocol=args.protocol))
    print(
        t(
            "cli_signal",
            lang,
            gain=colony.affective_gain,
            ticks=colony.signal_ticks,
            topk=colony.memory_top_k,
            threshold=colony.memory_min_activation,
        )
    )
    if result.archetype_correlations:
        print()
        print(t("cli_archetype", lang))
        for archetype, rho in sorted(result.archetype_correlations.items()):
            print(f"  {archetype:20s} rho = {rho:.3f}")

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(asdict(result), ensure_ascii=False, indent=2, default=_json_default),
            encoding="utf-8",
        )
        print()
        print(t("cli_output", lang, path=output_path))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
