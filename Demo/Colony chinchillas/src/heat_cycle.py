"""Female reproductive cycle model."""

from __future__ import annotations

from dataclasses import dataclass, field

from config_colony import ESTRUS_DURATION_S, HEAT_CYCLE_LENGTH_S


@dataclass(slots=True)
class HeatCycle:
    """Simplified estrous cycle used by female agents."""

    value: float = 0.0
    phase: str = "anestrus"
    cycle_length_s: float = HEAT_CYCLE_LENGTH_S
    estrus_duration: float = ESTRUS_DURATION_S
    _elapsed: float = field(default=0.0, repr=False)

    def update(self, dt: float) -> None:
        """Advance cycle state."""
        self._elapsed = (self._elapsed + dt) % self.cycle_length_s
        estrus_start = self.cycle_length_s - self.estrus_duration
        proestrus_start = max(0.0, estrus_start - self.estrus_duration)

        if self._elapsed < proestrus_start:
            self.phase = "anestrus"
            self.value = 0.2 * (self._elapsed / max(proestrus_start, 1.0))
        elif self._elapsed < estrus_start:
            self.phase = "proestrus"
            progress = (self._elapsed - proestrus_start) / max(
                estrus_start - proestrus_start, 1.0
            )
            self.value = 0.3 + 0.35 * progress
        else:
            self.phase = "estrus"
            progress = (self._elapsed - estrus_start) / max(self.estrus_duration, 1.0)
            self.value = 0.75 + 0.25 * progress

    def urgency(self) -> float:
        """Urgency is high in estrus, low otherwise."""
        if self.phase == "estrus":
            return min(1.0, self.value + 0.1)
        if self.phase == "proestrus":
            return 0.4 + self.value * 0.2
        return self.value * 0.2

    def apply_mating(self) -> None:
        """Reset cycle after successful mating."""
        self._elapsed = 0.0
        self.phase = "metestrus"
        self.value = 0.1
