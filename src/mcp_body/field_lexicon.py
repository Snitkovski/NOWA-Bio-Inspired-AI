"""Universal field-name lexicon — the only place where name magic is allowed.

Spec §6.3. A new MCP server that calls its fields ``unit_price`` /
``lead_time_days`` binds without a single line of role code. A server that
calls them ``cena`` / ``ref_key`` needs one YAML ``field_aliases`` entry, still
without code.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

ROLE_ID = "id"
ROLE_COST = "cost"
ROLE_TIME = "time"
ROLE_RELIABILITY = "reliability"
ROLE_QUANTITY = "quantity"
ROLE_STATUS = "status"

# Ambiguity is resolved by this order, which is why ``order_number`` is an id
# while ``total_amount`` is a cost and ``coverage_days`` is a time.
ROLE_PRIORITY: Tuple[str, ...] = (
    ROLE_COST,
    ROLE_TIME,
    ROLE_RELIABILITY,
    ROLE_QUANTITY,
    ROLE_STATUS,
    ROLE_ID,
)

# Patterns matched against a whole ``_``/``-``/case-split token. Short or
# common words live here so ``account_id`` is not a quantity ("count") and
# ``metadata`` is not a time ("eta").
ROLE_TOKENS: Dict[str, List[str]] = {
    ROLE_COST: ["price", "cost", "amount", "budget", "total", "fee", "sum"],
    ROLE_TIME: [
        "lead", "eta", "delay", "duration", "day", "days", "hour", "hours",
        "latency", "time",
    ],
    ROLE_RELIABILITY: ["reliability", "rating", "score", "trust", "otd"],
    ROLE_QUANTITY: ["qty", "quantity", "stock", "count", "volume", "coverage"],
    ROLE_STATUS: ["status", "state", "available", "active", "enabled"],
    ROLE_ID: ["id", "uuid", "guid", "code", "sku", "number", "ref"],
}

# Patterns matched anywhere in the lowercased name, for servers that do not
# separate words (``unitprice``). Spec §6.3 table.
ROLE_SUBSTRINGS: Dict[str, List[str]] = {
    ROLE_COST: ["price", "cost", "amount", "budget", "total", "fee"],
    ROLE_TIME: ["lead", "delay", "duration", "days", "hour", "latency"],
    ROLE_RELIABILITY: ["reliab", "rating", "score", "trust", "success_rate", "otd"],
    ROLE_QUANTITY: ["qty", "quantity", "stock", "volume", "coverage"],
    ROLE_STATUS: ["status", "state", "available", "active"],
    ROLE_ID: ["uuid", "guid"],
}


def tokenize(name: Any) -> Tuple[str, ...]:
    """Split ``supplierRefKey`` / ``supplier_ref_key`` into lowercase tokens."""
    text = str(name or "")
    tokens: List[str] = []
    current: List[str] = []
    previous_lower = False
    for char in text:
        if char.isalnum():
            if char.isupper() and previous_lower and current:
                tokens.append("".join(current))
                current = []
            current.append(char.lower())
            previous_lower = char.islower() or char.isdigit()
            continue
        if current:
            tokens.append("".join(current))
            current = []
        previous_lower = False
    if current:
        tokens.append("".join(current))
    return tuple(tokens)


@dataclass(frozen=True)
class FieldLexicon:
    """Immutable role table: role name → matching patterns."""

    tokens: Mapping[str, Tuple[str, ...]]
    substrings: Mapping[str, Tuple[str, ...]]
    aliases: Mapping[str, Tuple[str, ...]] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.aliases is None:
            object.__setattr__(self, "aliases", {})

    def roles(self) -> Tuple[str, ...]:
        known = set(self.tokens) | set(self.substrings) | set(self.aliases)
        ordered = [role for role in ROLE_PRIORITY if role in known]
        ordered.extend(sorted(known - set(ROLE_PRIORITY)))
        return tuple(ordered)

    def classify(self, name: Any) -> Optional[str]:
        """Return the field role for ``name``, or None when unknown."""
        lowered = str(name or "").strip().lower()
        if not lowered:
            return None
        name_tokens = set(tokenize(lowered))

        for role in self.roles():
            for alias in self.aliases.get(role, ()):
                if alias and (alias in lowered or alias in name_tokens):
                    return role
        for role in self.roles():
            if name_tokens & set(self.tokens.get(role, ())):
                return role
        for role in self.roles():
            if any(fragment in lowered for fragment in self.substrings.get(role, ())):
                return role
        return None


DEFAULT_LEXICON = FieldLexicon(
    tokens={role: tuple(values) for role, values in ROLE_TOKENS.items()},
    substrings={role: tuple(values) for role, values in ROLE_SUBSTRINGS.items()},
    aliases={},
)


def merge_aliases(
    base: Optional[FieldLexicon],
    yaml_aliases: Optional[Mapping[str, Iterable[str]]],
) -> FieldLexicon:
    """Merge role YAML ``field_aliases`` into a lexicon (per role, not in code).

    Aliases win over built-in patterns, so a server whose ``cena`` column must
    be treated as cost cannot be overruled by a coincidental substring.
    """
    lexicon = base or DEFAULT_LEXICON
    if not yaml_aliases:
        return lexicon
    merged: Dict[str, Tuple[str, ...]] = {
        role: tuple(values) for role, values in lexicon.aliases.items()
    }
    for role, values in dict(yaml_aliases).items():
        role_key = str(role).strip().lower()
        if not role_key:
            continue
        extra = [
            str(value).strip().lower()
            for value in (values or [])
            if str(value).strip()
        ]
        if not extra:
            continue
        merged[role_key] = tuple(dict.fromkeys(merged.get(role_key, ()) + tuple(extra)))
    return FieldLexicon(
        tokens=lexicon.tokens,
        substrings=lexicon.substrings,
        aliases=merged,
    )


def classify_field(
    name: str,
    aliases: Optional[Mapping[str, Iterable[str]]] = None,
) -> Optional[str]:
    """Classify one field name into a lexicon role, honouring YAML aliases."""
    return merge_aliases(DEFAULT_LEXICON, aliases).classify(name)
