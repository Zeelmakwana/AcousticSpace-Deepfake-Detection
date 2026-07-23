"""
AcousticSpace — In-Process Metrics Registry
============================================
Thread-safe, zero-dependency metrics store for production monitoring.

Design
------
- Pure Python — no Prometheus client library required.  The ``GET /metrics``
  endpoint exposes both a JSON representation (default) and a plain-text
  Prometheus-compatible format (``?format=prometheus``).
- All counters, histograms, and gauges are stored as module-level singletons
  so they survive across requests within the same process.
- Thread safety is achieved via ``threading.Lock`` on each metric object.
- The registry is intentionally lightweight — it tracks only the metrics
  that matter for AcousticSpace production operations.

Metric catalogue
----------------
Counters  (monotonically increasing)
  requests_total          — HTTP requests received, labelled by method+path+status
  analyses_total          — Audio analysis jobs, labelled by prediction+mode
  auth_events_total       — Auth events, labelled by event type + outcome
  errors_total            — Unhandled / 5xx errors

Histograms (distribution of observed values)
  request_duration_ms     — Wall-clock time per HTTP request (milliseconds)
  analysis_duration_sec   — End-to-end analysis pipeline time (seconds)
  file_size_bytes         — Uploaded audio file size (bytes)

Gauges (current point-in-time value)
  analyses_in_flight      — Analyses currently being processed
  db_analyses_stored      — Total rows in analysis_history (refreshed on demand)
  process_start_time_sec  — Unix epoch when the process started (set once)

Public API
----------
  REGISTRY : MetricsRegistry  — the singleton registry
  record_request(method, path, status, duration_ms)
  record_analysis(prediction, mode, duration_sec, file_size_bytes)
  record_auth_event(event, outcome)
  record_error()
  set_db_count(n)
  inc_in_flight() / dec_in_flight()
"""

from __future__ import annotations

import math
import threading
import time
from collections import defaultdict
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Primitive metric types
# ---------------------------------------------------------------------------

class Counter:
    """Monotonically increasing integer counter, optionally labelled."""

    def __init__(self, name: str, description: str) -> None:
        self.name        = name
        self.description = description
        self._lock       = threading.Lock()
        self._values: Dict[str, int] = defaultdict(int)

    def inc(self, labels: str = "", amount: int = 1) -> None:
        with self._lock:
            self._values[labels] += amount

    def get(self) -> Dict[str, int]:
        with self._lock:
            return dict(self._values)

    def total(self) -> int:
        with self._lock:
            return sum(self._values.values())


class Gauge:
    """Signed floating-point value that can go up or down."""

    def __init__(self, name: str, description: str, initial: float = 0.0) -> None:
        self.name        = name
        self.description = description
        self._lock       = threading.Lock()
        self._value      = initial

    def set(self, v: float) -> None:
        with self._lock:
            self._value = v

    def inc(self, amount: float = 1.0) -> None:
        with self._lock:
            self._value += amount

    def dec(self, amount: float = 1.0) -> None:
        with self._lock:
            self._value -= amount

    def get(self) -> float:
        with self._lock:
            return self._value


class Histogram:
    """
    Records a distribution of observed values.

    Computes: count, sum, min, max, mean, p50, p90, p95, p99 on demand.
    Stores up to ``_MAX_SAMPLES`` raw values (ring-buffer — older values
    are discarded when the buffer is full).
    """

    _MAX_SAMPLES = 10_000

    def __init__(self, name: str, description: str) -> None:
        self.name        = name
        self.description = description
        self._lock       = threading.Lock()
        self._samples: List[float] = []
        self._count      = 0
        self._sum        = 0.0
        self._min        = math.inf
        self._max        = -math.inf

    def observe(self, value: float) -> None:
        with self._lock:
            self._count += 1
            self._sum   += value
            if value < self._min:
                self._min = value
            if value > self._max:
                self._max = value
            # Ring-buffer: keep only the most recent _MAX_SAMPLES
            if len(self._samples) >= self._MAX_SAMPLES:
                self._samples.pop(0)
            self._samples.append(value)

    def stats(self) -> dict:
        with self._lock:
            if self._count == 0:
                return {
                    "count": 0, "sum": 0.0,
                    "min": None, "max": None, "mean": None,
                    "p50": None, "p90": None, "p95": None, "p99": None,
                }
            sorted_s = sorted(self._samples)
            n        = len(sorted_s)

            def percentile(p: float) -> float:
                idx = max(0, min(n - 1, int(math.ceil(p / 100.0 * n)) - 1))
                return round(sorted_s[idx], 4)

            return {
                "count": self._count,
                "sum":   round(self._sum, 4),
                "min":   round(self._min, 4),
                "max":   round(self._max, 4),
                "mean":  round(self._sum / self._count, 4),
                "p50":   percentile(50),
                "p90":   percentile(90),
                "p95":   percentile(95),
                "p99":   percentile(99),
            }


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

class MetricsRegistry:
    """Holds all metric objects and exposes serialisation methods."""

    def __init__(self) -> None:
        # Counters
        self.requests_total       = Counter("requests_total",       "HTTP requests received")
        self.analyses_total       = Counter("analyses_total",       "Audio analysis jobs completed")
        self.auth_events_total    = Counter("auth_events_total",    "Authentication events")
        self.errors_total         = Counter("errors_total",         "Unhandled / 5xx errors")

        # Histograms
        self.request_duration_ms  = Histogram("request_duration_ms",  "HTTP request duration (ms)")
        self.analysis_duration_sec = Histogram("analysis_duration_sec", "Analysis pipeline duration (s)")
        self.file_size_bytes      = Histogram("file_size_bytes",      "Uploaded audio file size (bytes)")

        # Gauges
        self.analyses_in_flight   = Gauge("analyses_in_flight",   "Analyses currently in flight")
        self.db_analyses_stored   = Gauge("db_analyses_stored",   "Total rows in analysis_history")
        self.process_start_time   = Gauge(
            "process_start_time_sec",
            "Unix timestamp when the process started",
            initial=time.time(),
        )

    # ---- Serialisation -------------------------------------------------------

    def to_dict(self) -> dict:
        """Return all metrics as a JSON-serialisable dict."""
        return {
            "counters": {
                "requests_total":    self.requests_total.get(),
                "analyses_total":    self.analyses_total.get(),
                "auth_events_total": self.auth_events_total.get(),
                "errors_total":      self.errors_total.total(),
            },
            "histograms": {
                "request_duration_ms":   self.request_duration_ms.stats(),
                "analysis_duration_sec": self.analysis_duration_sec.stats(),
                "file_size_bytes":       self.file_size_bytes.stats(),
            },
            "gauges": {
                "analyses_in_flight": self.analyses_in_flight.get(),
                "db_analyses_stored": self.db_analyses_stored.get(),
                "process_uptime_sec": round(time.time() - self.process_start_time.get(), 2),
            },
        }

    def to_prometheus(self) -> str:
        """
        Render metrics as Prometheus text exposition format (version 0.0.4).
        Suitable for scraping by a Prometheus server or Grafana agent.
        """
        lines: list[str] = []

        def _counter(c: Counter) -> None:
            lines.append(f"# HELP {c.name} {c.description}")
            lines.append(f"# TYPE {c.name} counter")
            for label, val in c.get().items():
                lbl = f'{{{label}}}' if label else ""
                lines.append(f"{c.name}{lbl} {val}")

        def _gauge(g: Gauge) -> None:
            lines.append(f"# HELP {g.name} {g.description}")
            lines.append(f"# TYPE {g.name} gauge")
            lines.append(f"{g.name} {g.get()}")

        def _histogram(h: Histogram) -> None:
            s = h.stats()
            lines.append(f"# HELP {h.name} {h.description}")
            lines.append(f"# TYPE {h.name} summary")
            lines.append(f'{h.name}{{quantile="0.5"}} {s["p50"] or "NaN"}')
            lines.append(f'{h.name}{{quantile="0.9"}} {s["p90"] or "NaN"}')
            lines.append(f'{h.name}{{quantile="0.95"}} {s["p95"] or "NaN"}')
            lines.append(f'{h.name}{{quantile="0.99"}} {s["p99"] or "NaN"}')
            lines.append(f"{h.name}_sum {s['sum']}")
            lines.append(f"{h.name}_count {s['count']}")

        _counter(self.requests_total)
        _counter(self.analyses_total)
        _counter(self.auth_events_total)
        _counter(self.errors_total)
        _histogram(self.request_duration_ms)
        _histogram(self.analysis_duration_sec)
        _histogram(self.file_size_bytes)
        _gauge(self.analyses_in_flight)
        _gauge(self.db_analyses_stored)

        uptime_gauge = Gauge("process_uptime_sec", "Process uptime in seconds",
                             initial=round(time.time() - self.process_start_time.get(), 2))
        _gauge(uptime_gauge)

        return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Singleton registry
# ---------------------------------------------------------------------------
REGISTRY = MetricsRegistry()


# ---------------------------------------------------------------------------
# Convenience recording functions (called from middleware and route handlers)
# ---------------------------------------------------------------------------

def record_request(
    method: str,
    path: str,
    status: int,
    duration_ms: float,
) -> None:
    """Record a completed HTTP request."""
    # Normalise path — replace UUIDs and numeric IDs with placeholders
    # to avoid high-cardinality label explosion.
    import re
    norm_path = re.sub(
        r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
        ":id", path, flags=re.IGNORECASE
    )
    norm_path = re.sub(r"/\d+", "/:n", norm_path)

    label = f'method="{method}",path="{norm_path}",status="{status}"'
    REGISTRY.requests_total.inc(label)
    REGISTRY.request_duration_ms.observe(duration_ms)

    if status >= 500:
        REGISTRY.errors_total.inc()


def record_analysis(
    prediction: str,
    mode: str,
    duration_sec: float,
    file_bytes: Optional[int] = None,
) -> None:
    """Record a completed analysis job."""
    label = f'prediction="{prediction}",mode="{mode}"'
    REGISTRY.analyses_total.inc(label)
    REGISTRY.analysis_duration_sec.observe(duration_sec)
    if file_bytes is not None:
        REGISTRY.file_size_bytes.observe(float(file_bytes))


def record_auth_event(event: str, outcome: str) -> None:
    """Record an authentication event (login, register, refresh, etc.)."""
    label = f'event="{event}",outcome="{outcome}"'
    REGISTRY.auth_events_total.inc(label)


def inc_in_flight() -> None:
    REGISTRY.analyses_in_flight.inc()


def dec_in_flight() -> None:
    REGISTRY.analyses_in_flight.dec()


def set_db_count(n: int) -> None:
    REGISTRY.db_analyses_stored.set(float(n))
