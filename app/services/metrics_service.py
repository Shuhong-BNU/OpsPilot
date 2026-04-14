"""轻量指标采集服务."""

from __future__ import annotations

from collections import defaultdict
from threading import Lock


class MetricsService:
    """记录请求量、耗时和工具成功率等指标."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._counters: dict[str, int] = defaultdict(int)
        self._timings: dict[str, list[int]] = defaultdict(list)

    def increment(self, name: str, value: int = 1) -> None:
        with self._lock:
            self._counters[name] += value

    def observe(self, name: str, value_ms: int) -> None:
        with self._lock:
            self._timings[name].append(value_ms)

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            averages = {
                name: (sum(values) / len(values) if values else 0)
                for name, values in self._timings.items()
            }
            return {
                "counters": dict(self._counters),
                "avg_latency_ms": averages,
            }

    def render_prometheus(self) -> str:
        data = self.snapshot()
        lines: list[str] = []
        counters = data["counters"]  # type: ignore[assignment]
        averages = data["avg_latency_ms"]  # type: ignore[assignment]
        for key, value in counters.items():
            lines.append(f"opspilot_{key} {value}")
        for key, value in averages.items():
            lines.append(f"opspilot_{key}_avg_ms {value:.2f}")
        return "\n".join(lines) + "\n"


metrics_service = MetricsService()
