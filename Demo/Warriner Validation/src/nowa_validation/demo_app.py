"""Streamlit dashboard for the NOWA x Warriner validation demo."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import sys
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from nowa_validation.nowa_colony import NOWAColony
from nowa_validation.ui_i18n import peek_lang, t
from nowa_validation.warriner_validator import ValidationResult, WarrinerValidator
from nowa_validation.word_stimulus_encoder import WordStimulusEncoder


def _result_table(result: ValidationResult) -> list[dict[str, Any]]:
    rows = []
    for word, human_v, nowa_v, human_a, nowa_a in zip(
        result.words,
        result.warriner_valence_norm,
        result.nowa_valence_shifts,
        result.warriner_arousal_norm,
        result.nowa_arousal_shifts,
    ):
        rows.append(
            {
                "word": word,
                "warriner_valence": human_v,
                "nowa_valence_shift": nowa_v,
                "valence_residual": nowa_v - human_v,
                "warriner_arousal": human_a,
                "nowa_arousal_shift": nowa_a,
            }
        )
    return rows


def main() -> None:
    try:
        import streamlit as st
    except Exception as exc:
        raise SystemExit("streamlit is not installed. Install requirements.txt to run the UI.") from exc

    if "ui_lang" not in st.session_state:
        st.session_state.ui_lang = peek_lang()
    lang = st.session_state.ui_lang

    def tr(key: str, **kwargs: Any) -> str:
        return t(key, lang, **kwargs)

    st.set_page_config(page_title=tr("page_title"), layout="wide")
    st.title(tr("title"))

    with st.sidebar:
        st.selectbox(tr("language"), ["en", "ru"], key="ui_lang")
        lang = st.session_state.ui_lang
        st.header(tr("sidebar_config"))
        default_csv = Path(__file__).resolve().parents[2] / "data" / "Ratings_Warriner_et_al.csv"
        csv_path = st.text_input(tr("csv_path"), str(default_csv))
        encoder_mode = st.selectbox(
            tr("encoder_mode"),
            ["lexical", "sbert_neighbors", "direct_vad"],
            index=1,
            key="encoder_mode_v2",
            help=tr("encoder_help"),
        )
        protocol = st.selectbox(
            tr("protocol"),
            ["heldout", "in_vocab"],
            key="validation_protocol_v1",
            help=tr("protocol_help"),
        )
        n_agents = st.slider(tr("colony_size"), 50, 500, 100, 10)
        n_words = st.slider(tr("words"), 50, 1000, 300, 50)
        ticks = st.slider(tr("ticks"), 5, 30, 20, 1)
        seed_size = st.slider(tr("seed_size"), 100, 2000, 500, 100)
        st.subheader(tr("signal_header"))
        affective_gain = st.slider(
            tr("affective_gain"),
            0.5,
            3.0,
            1.8,
            0.1,
            help=tr("affective_help"),
        )
        signal_ticks = st.slider(
            tr("signal_ticks"),
            1,
            10,
            3,
            1,
            help=tr("signal_ticks_help"),
        )
        memory_top_k = st.slider(
            tr("memory_topk"),
            1,
            10,
            3,
            1,
            help=tr("memory_topk_help"),
        )
        memory_min_activation = st.slider(
            tr("min_activation"),
            0.0,
            1.0,
            0.3,
            0.05,
            help=tr("min_activation_help"),
        )
        seed = st.number_input(tr("seed"), min_value=0, value=42, step=1)
        run_clicked = st.button(tr("run"), type="primary")

    if not run_clicked:
        st.info(tr("idle_info"))
        st.caption(tr("disclaimer"))
        return

    if encoder_mode == "lexical" and protocol == "heldout":
        st.warning(tr("lexical_warning"))
    if encoder_mode == "direct_vad":
        st.warning(tr("direct_vad_warning"))
    if protocol == "in_vocab":
        st.warning(tr("in_vocab_warning"))

    progress = st.progress(0.0)
    status = st.empty()

    def on_progress(index: int, total: int, word: str) -> None:
        progress.progress(index / max(1, total))
        status.write(tr("processing", index=index, total=total, word=word))

    colony = NOWAColony(
        n_agents=n_agents,
        ticks_per_stimulus=ticks,
        signal_ticks=signal_ticks,
        affective_gain=affective_gain,
        memory_top_k=memory_top_k,
        memory_min_activation=memory_min_activation,
        seed=int(seed),
    )
    encoder = WordStimulusEncoder(mode=encoder_mode)
    validator = WarrinerValidator(
        warriner_csv_path=csv_path,
        colony=colony,
        encoder=encoder,
        n_words=n_words,
        validation_protocol=protocol,
        seed=int(seed),
    )
    result = validator.run(seed_size=seed_size, progress_callback=on_progress)
    diagnostics = validator.diagnose_zero_activations(result)

    tabs = st.tabs(
        [
            tr("tab_main"),
            tr("tab_scatter"),
            tr("tab_archetype"),
            tr("tab_memory"),
            tr("tab_words"),
            tr("tab_neuro"),
        ]
    )

    with tabs[0]:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric(tr("spearman_v"), f"{result.spearman_rho_valence:.3f}")
        c2.metric(tr("pearson_v"), f"{result.pearson_r_valence:.3f}")
        c3.metric(tr("ccc_v"), f"{result.ccc_valence:.3f}")
        c4.metric(tr("spearman_a"), f"{result.spearman_rho_arousal:.3f}")
        st.write(result.summary())
        st.write(tr("backend", name=colony.backend_name))
        st.write(tr("protocol_line", protocol=protocol))
        st.metric(tr("sd_ratio"), f"{result.sd_ratio:.3f}")
        st.metric(tr("mean_memories"), f"{result.mean_activated_memories:.2f}")

    with tabs[1]:
        rows = _result_table(result)
        try:
            import plotly.express as px

            fig = px.scatter(
                rows,
                x="warriner_valence",
                y="nowa_valence_shift",
                hover_name="word",
                trendline="ols",
            )
            st.plotly_chart(fig, use_container_width=True)
        except Exception:
            st.dataframe(rows, use_container_width=True)

    with tabs[2]:
        st.bar_chart(result.archetype_correlations)
        st.json(result.archetype_n_agents)

    with tabs[3]:
        st.metric(tr("zero_ratio"), f"{result.zero_activation_ratio:.2%}")
        st.write(diagnostics["recommendation"])
        st.write(diagnostics["worst_words"])

    with tabs[4]:
        rows = _result_table(result)
        st.dataframe(rows, use_container_width=True)
        st.download_button(
            tr("download"),
            data=str(asdict(result)),
            file_name="nowa_warriner_validation.json",
        )

    with tabs[5]:
        st.metric(tr("spearman_da"), f"{result.spearman_rho_da_valence:.3f}")
        st.metric(tr("spearman_cort"), f"{result.spearman_rho_cortisol_valence:.3f}")
        nm_rows = [
            {
                "word": response.word,
                "da_delta": response.mean_da_delta,
                "ne_delta": response.mean_ne_delta,
                "cortisol_delta": response.mean_cortisol_delta,
            }
            for response in result.colony_responses
        ]
        st.dataframe(nm_rows, use_container_width=True)

    st.caption(
        tr(
            "caption",
            disclaimer=tr("disclaimer"),
            rho=result.spearman_rho_valence,
            n=result.n_words,
            encoder=result.encoder_mode,
        )
    )


if __name__ == "__main__":
    main()
