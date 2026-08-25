"""Human-readable pipeline progress + ETA."""

from __future__ import annotations

import time


def format_duration(seconds: float) -> str:
    """Format seconds as 3m12s / 1h05m."""
    total = max(0, int(round(seconds)))
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours}h{minutes:02d}m"
    if minutes:
        return f"{minutes}m{secs:02d}s"
    return f"{secs}s"


class ProgressTracker:
    """Rolling per-chapter ETA for BookProductionAgent events."""

    def __init__(self, total: int, default_chapter_sec: float = 8 * 60) -> None:
        self.total = max(0, total)
        self.done = 0
        self.failed = 0
        self.started_at = time.monotonic()
        self.durations: list[float] = []
        self.default_chapter_sec = default_chapter_sec
        self._chapter_started_at: float | None = None

    @property
    def remaining(self) -> int:
        return max(0, self.total - self.done)

    def average_chapter_sec(self) -> float:
        if self.durations:
            return sum(self.durations) / len(self.durations)
        return self.default_chapter_sec

    def eta_sec(self, remaining: int | None = None) -> float:
        left = self.remaining if remaining is None else remaining
        return self.average_chapter_sec() * left

    def start_chapter(self, index: int, title: str, extra: str = "") -> str:
        self._chapter_started_at = time.monotonic()
        elapsed = time.monotonic() - self.started_at
        left = max(0, self.total - index)
        suffix = f" {extra}" if extra else ""
        return (
            f"[{index + 1}/{self.total}] Starting: {title}.{suffix} "
            f"Elapsed {format_duration(elapsed)}. "
            f"ETA ~{format_duration(self.eta_sec(left))} "
            f"({left} left, ~{format_duration(self.average_chapter_sec())}/chapter)."
        )

    def finish_chapter(self, index: int, title: str, status: str) -> str:
        now = time.monotonic()
        if self._chapter_started_at is not None:
            elapsed_ch = now - self._chapter_started_at
            # Ignore sub-second timings (tests / cache hits) so ETA stays useful.
            if elapsed_ch >= 1.0:
                self.durations.append(elapsed_ch)
        self._chapter_started_at = None
        self.done += 1
        if status in {"failed", "error"}:
            self.failed += 1
        elapsed = now - self.started_at
        left = max(0, self.total - self.done)
        return (
            f"[{index + 1}/{self.total}] Finished: {title} ({status}). "
            f"Elapsed {format_duration(elapsed)}. "
            f"ETA ~{format_duration(self.eta_sec(left))} "
            f"({left} left, {self.failed} failed)."
        )

    def summary(self) -> str:
        elapsed = time.monotonic() - self.started_at
        return (
            f"Production done: {self.done}/{self.total} chapters "
            f"({self.failed} failed) in {format_duration(elapsed)}."
        )
