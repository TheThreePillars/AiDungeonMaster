"""Performance timing utilities for latency measurement."""

import asyncio
import logging
import time
from contextlib import contextmanager, asynccontextmanager
from dataclasses import dataclass, field
from typing import Optional
from collections import deque
import statistics

logger = logging.getLogger(__name__)


@dataclass
class TimingMetric:
    """A single timing measurement."""
    stage: str
    duration_ms: float
    timestamp: float
    metadata: dict = field(default_factory=dict)


class LatencyTracker:
    """Tracks latency metrics across stages with rolling averages."""

    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        self._metrics: dict[str, deque[float]] = {}
        self._last_report: float = 0
        self._report_interval = 60.0  # Log summary every 60s

    def record(self, stage: str, duration_ms: float, **metadata):
        """Record a timing measurement."""
        if stage not in self._metrics:
            self._metrics[stage] = deque(maxlen=self.window_size)
        self._metrics[stage].append(duration_ms)

        # Log individual slow operations
        if duration_ms > 500:
            meta_str = f" {metadata}" if metadata else ""
            logger.warning(f"SLOW: {stage} took {duration_ms:.1f}ms{meta_str}")

        # Periodic summary
        now = time.monotonic()
        if now - self._last_report > self._report_interval:
            self._log_summary()
            self._last_report = now

    def get_stats(self, stage: str) -> dict:
        """Get statistics for a stage."""
        if stage not in self._metrics or not self._metrics[stage]:
            return {}
        data = list(self._metrics[stage])
        return {
            "count": len(data),
            "mean_ms": round(statistics.mean(data), 2),
            "median_ms": round(statistics.median(data), 2),
            "p95_ms": round(sorted(data)[int(len(data) * 0.95)] if len(data) >= 20 else max(data), 2),
            "max_ms": round(max(data), 2),
            "min_ms": round(min(data), 2),
        }

    def get_all_stats(self) -> dict:
        """Get statistics for all tracked stages."""
        return {stage: self.get_stats(stage) for stage in self._metrics}

    def _log_summary(self):
        """Log a summary of all tracked stages."""
        for stage, data in self._metrics.items():
            if data:
                stats = self.get_stats(stage)
                logger.info(
                    f"TIMING [{stage}]: mean={stats['mean_ms']:.1f}ms, "
                    f"p95={stats['p95_ms']:.1f}ms, n={stats['count']}"
                )


# Global tracker instance
_tracker: Optional[LatencyTracker] = None


def get_tracker() -> LatencyTracker:
    """Get or create the global latency tracker."""
    global _tracker
    if _tracker is None:
        _tracker = LatencyTracker()
    return _tracker


@contextmanager
def timed_sync(stage: str, **metadata):
    """Context manager for timing synchronous operations."""
    start = time.perf_counter()
    try:
        yield
    finally:
        duration_ms = (time.perf_counter() - start) * 1000
        get_tracker().record(stage, duration_ms, **metadata)


@asynccontextmanager
async def timed_async(stage: str, **metadata):
    """Context manager for timing async operations."""
    start = time.perf_counter()
    try:
        yield
    finally:
        duration_ms = (time.perf_counter() - start) * 1000
        get_tracker().record(stage, duration_ms, **metadata)


def record_timing(stage: str, duration_ms: float, **metadata):
    """Direct recording of a timing measurement."""
    get_tracker().record(stage, duration_ms, **metadata)
