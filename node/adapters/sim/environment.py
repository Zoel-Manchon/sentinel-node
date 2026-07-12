"""Simulated 'space' shared by every sim adapter — a monitored indoor room.

One coherent state instead of independent RNGs:
- an occupancy schedule (people arrive/leave over the day) drives EVERYTHING:
  presence radar, CO2/VOC rising with people, sound events more likely when
  occupied, camera person-count.
- air quality (VOC resistance, IAQ) degrades with occupancy and recovers when
  empty (ventilation).
- rare anomaly events (glass break, loud bang) can be scripted for demos.

So a 'busy room' looks busy on every channel at once — exactly what sells a
multi-sensor dashboard.
"""

import math
import random

SECONDS_PER_DAY = 86400


class SpaceWorld:
    def __init__(self, clock, seed: int = None):
        self._clock = clock
        self._rng = random.Random(seed)
        self._voc_baseline = 50_000.0    # ohms, clean air (higher = cleaner)
        self._last_step = None
        self._anomaly_until = 0
        self._anomaly_label = None

    def _seconds_of_day(self, ts: int) -> int:
        return ts % SECONDS_PER_DAY

    def occupancy(self) -> int:
        """Expected number of people right now (0..~4), schedule-driven.

        Busy 9-13h and 15-19h, empty at night, lunch dip. Smooth-ish with noise.
        """
        s = self._seconds_of_day(self._clock.now())
        h = s / 3600.0
        morning = math.exp(-((h - 11) ** 2) / 6.0)
        afternoon = math.exp(-((h - 17) ** 2) / 6.0)
        curve = 4.0 * max(morning, afternoon)
        if 13 <= h < 15:            # lunch: mostly empty
            curve *= 0.3
        if h < 7 or h >= 21:        # night: hard zero, no spurious noise
            return 0
        n = int(round(curve + self._rng.gauss(0, 0.4)))
        return max(0, min(5, n))

    def is_occupied(self) -> bool:
        return self.occupancy() > 0

    def presence_distance_m(self) -> float:
        """Distance to nearest target (LD2410 gate). 0 = no target."""
        if not self.is_occupied():
            return 0.0
        return round(self._rng.uniform(0.75, 5.0), 2)

    def _step(self):
        ts = self._clock.now()
        if self._last_step == ts:
            return
        self._last_step = ts
        occ = self.occupancy()
        # VOC resistance drops (air worsens) with people, recovers when empty.
        target = self._voc_baseline * (1.0 - 0.12 * occ)
        self._voc_baseline += (target - self._voc_baseline) * 0.02
        self._voc_baseline = max(8_000.0, min(60_000.0, self._voc_baseline))

    def temperature_c(self) -> float:
        self._step()
        s = self._seconds_of_day(self._clock.now())
        phase = 2 * math.pi * (s - 5 * 3600) / SECONDS_PER_DAY
        diurnal = -math.cos(phase) * 3.0
        occ_heat = 0.4 * self.occupancy()
        return 21.0 + diurnal + occ_heat + self._rng.gauss(0, 0.1)

    def humidity_pct(self) -> float:
        self._step()
        return min(70.0, max(30.0, 45.0 + 2.0 * self.occupancy() + self._rng.gauss(0, 1.0)))

    def pressure_hpa(self) -> float:
        return 1013.0 + self._rng.gauss(0, 0.4)

    def gas_resistance_ohm(self) -> float:
        self._step()
        return max(5_000.0, self._voc_baseline + self._rng.gauss(0, 800))

    def iaq(self) -> float:
        """0 (excellent) .. 500 (hazardous). Inverse of gas resistance."""
        r = self.gas_resistance_ohm()
        iaq = (60_000.0 - r) / 60_000.0 * 300.0
        return max(0.0, min(500.0, iaq + self._rng.gauss(0, 5)))

    def sound_level_dbfs(self) -> float:
        """Ambient loudness, -60 (silent) .. 0 (max). Louder when occupied."""
        base = -55.0 + 8.0 * self.occupancy()
        if self._clock.now() < self._anomaly_until:
            base = -8.0
        return min(0.0, base + self._rng.gauss(0, 2.0))

    def sound_event(self):
        """Return (label, confidence) for the acoustic classifier."""
        ts = self._clock.now()
        if ts < self._anomaly_until and self._anomaly_label:
            return (self._anomaly_label, self._rng.uniform(0.80, 0.97))
        if self.is_occupied() and self._rng.random() < 0.15:
            return (self._rng.choice(["speech", "footsteps", "door"]),
                    self._rng.uniform(0.6, 0.9))
        return ("quiet", self._rng.uniform(0.7, 0.95))

    # -- demo hooks ----------------------------------------------------------

    def force_anomaly(self, label: str = "glass_break", duration_s: int = 20):
        self._anomaly_label = label
        self._anomaly_until = self._clock.now() + duration_s
