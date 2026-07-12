"""Duty-cycle scheduler.

On real hardware the loop body ends in machine.deepsleep(); here the ClockPort
abstracts sleeping so the same scheduler runs the desktop simulation
(accelerated) and, later, the ESP32 firmware.
"""


class DutyCycleScheduler:
    def __init__(self, publish_use_case, clock, interval_seconds: int = 300):
        if interval_seconds <= 0:
            raise ValueError("interval must be > 0")
        self._publish = publish_use_case
        self._clock = clock
        self.interval_seconds = interval_seconds

    def run_once(self):
        """One wake cycle. Returns the frame that was published."""
        return self._publish.execute()

    def run(self, cycles: int = 0, on_frame=None, on_error=None):
        """Run `cycles` iterations (0 = forever).

        `on_frame(frame)` / `on_error(exc)` are optional observation hooks —
        the application layer stays print()-free.
        """
        done = 0
        while cycles == 0 or done < cycles:
            try:
                frame = self.run_once()
                if on_frame:
                    on_frame(frame)
            except Exception as exc:  # noqa: BLE001 — field device must not die
                if on_error:
                    on_error(exc)
            done += 1
            if cycles == 0 or done < cycles:
                self._clock.sleep(self.interval_seconds)
        return done
