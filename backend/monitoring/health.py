"""
AcousticSpace — Deep Health Check
===================================
Provides ``get_health_report()`` — a comprehensive, non-blocking health
assessment of every runtime dependency.

Checks performed
----------------
api
  Always "ok" — if this function returns at all, the API process is alive.

database
  Opens a SQLAlchemy session and executes ``SELECT 1``.
  Reports row count of ``analysis_history`` as a metric.

disk
  Inspects the partition containing the working directory.
  Warns at < 500 MB free; critical at < 100 MB free.

memory
  Reads RSS and VMS of the current process via ``psutil``.
  Warns if RSS > 80 % of total system memory.

model
  Calls ``get_inference_engine().model_info()`` to report the active
  inference mode and whether a checkpoint was found.

uptime
  Wall-clock seconds since the process started (from ``metrics.REGISTRY``).

system
  OS, Python version, hostname, and CPU count for deployment traceability.

Overall status
--------------
"ok"       — all checks pass
"degraded" — one or more non-critical checks warn
"critical" — database unreachable or disk critically low

Public API
----------
  get_health_report(db_session) -> dict
    Returns a dict conforming to the ``DetailedHealthResponse`` schema used
    by ``GET /health/detailed``.

  get_liveness() -> dict
    Lightweight check used by the Docker HEALTHCHECK and ``GET /health``.
    Only verifies the process is alive and the DB connection is open.
"""

from __future__ import annotations

import logging
import os
import platform
import sys
import time
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("acousticspace.health")

# ---------------------------------------------------------------------------
# Individual checkers
# ---------------------------------------------------------------------------

def _check_api() -> dict:
    return {"status": "ok", "detail": "API process is responsive"}


def _check_database(db_session: Any) -> dict:
    """Run a SELECT 1 against the configured database."""
    try:
        from sqlalchemy import text
        db_session.execute(text("SELECT 1"))

        from models.analysis_history import AnalysisHistory
        count: int = db_session.query(AnalysisHistory).count()

        # Refresh the gauge in the metrics registry
        from monitoring.metrics import set_db_count
        set_db_count(count)

        return {
            "status": "ok",
            "detail": "Database connection healthy",
            "analyses_stored": count,
        }
    except Exception as exc:
        logger.error("Health check — database error: %s", exc)
        return {
            "status": "critical",
            "detail": f"Database unreachable: {type(exc).__name__}",
            "analyses_stored": None,
        }


def _check_disk() -> dict:
    """Check free disk space on the working-directory partition."""
    try:
        import shutil
        total, used, free = shutil.disk_usage(os.getcwd())
        free_mb  = free  // (1024 * 1024)
        total_mb = total // (1024 * 1024)
        used_pct = round(used / total * 100, 1) if total else 0.0

        if free_mb < 100:
            status = "critical"
            detail = f"Disk critically low: {free_mb} MB free"
        elif free_mb < 500:
            status = "degraded"
            detail = f"Disk space low: {free_mb} MB free"
        else:
            status = "ok"
            detail = f"{free_mb} MB free of {total_mb} MB total"

        return {
            "status":    status,
            "detail":    detail,
            "free_mb":   free_mb,
            "total_mb":  total_mb,
            "used_pct":  used_pct,
        }
    except Exception as exc:
        logger.warning("Health check — disk error: %s", exc)
        return {"status": "degraded", "detail": f"Disk check failed: {exc}"}


def _check_memory() -> dict:
    """Check process memory usage via psutil."""
    try:
        import psutil
        proc        = psutil.Process(os.getpid())
        mem_info    = proc.memory_info()
        sys_mem     = psutil.virtual_memory()

        rss_mb      = mem_info.rss // (1024 * 1024)
        vms_mb      = mem_info.vms // (1024 * 1024)
        sys_total_mb = sys_mem.total // (1024 * 1024)
        sys_avail_mb = sys_mem.available // (1024 * 1024)
        used_pct    = round(mem_info.rss / sys_mem.total * 100, 1) if sys_mem.total else 0.0

        status = "degraded" if used_pct > 80 else "ok"
        detail = (
            f"Process RSS {rss_mb} MB ({used_pct}% of system memory)"
            if status == "ok"
            else f"High RSS: {rss_mb} MB ({used_pct}% of system total)"
        )

        return {
            "status":         status,
            "detail":         detail,
            "rss_mb":         rss_mb,
            "vms_mb":         vms_mb,
            "sys_total_mb":   sys_total_mb,
            "sys_avail_mb":   sys_avail_mb,
            "process_used_pct": used_pct,
        }
    except ImportError:
        return {
            "status": "degraded",
            "detail": "psutil not installed — memory metrics unavailable",
        }
    except Exception as exc:
        logger.warning("Health check — memory error: %s", exc)
        return {"status": "degraded", "detail": f"Memory check failed: {exc}"}


def _check_model() -> dict:
    """Query the inference engine for its current mode and checkpoint state."""
    try:
        from services.inference import get_inference_engine
        info = get_inference_engine().model_info()
        return {
            "status":           "ok",
            "mode":             info.get("mode"),
            "checkpoint_found": info.get("checkpoint_found"),
            "device":           info.get("device"),
            "architecture":     info.get("architecture"),
        }
    except Exception as exc:
        logger.warning("Health check — model error: %s", exc)
        return {
            "status": "degraded",
            "detail": f"Inference engine unavailable: {type(exc).__name__}",
        }


def _check_uptime() -> dict:
    """Return process uptime derived from the metrics registry."""
    try:
        from monitoring.metrics import REGISTRY
        start = REGISTRY.process_start_time.get()
        uptime_sec = round(time.time() - start, 2)
        started_at = datetime.fromtimestamp(start, tz=timezone.utc).isoformat()
        return {
            "status":      "ok",
            "uptime_sec":  uptime_sec,
            "started_at":  started_at,
        }
    except Exception as exc:
        return {"status": "degraded", "detail": str(exc)}


def _check_system() -> dict:
    """Return static system information for deployment traceability."""
    import socket
    return {
        "status":         "ok",
        "os":             platform.system(),
        "os_version":     platform.version(),
        "python_version": sys.version.split()[0],
        "hostname":       socket.gethostname(),
        "cpu_count":      os.cpu_count(),
        "app_env":        os.getenv("APP_ENV", "development"),
        "app_version":    "1.0.0",
    }


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------

def get_health_report(db_session: Any) -> dict:
    """
    Run all health checks and return a unified report dict.

    Parameters
    ----------
    db_session : sqlalchemy.orm.Session
        An open SQLAlchemy session, injected by the route handler.

    Returns
    -------
    dict
        Conforms to DetailedHealthResponse.  Top-level ``status`` is the
        worst status across all individual checks.
    """
    checks = {
        "api":      _check_api(),
        "database": _check_database(db_session),
        "disk":     _check_disk(),
        "memory":   _check_memory(),
        "model":    _check_model(),
        "uptime":   _check_uptime(),
        "system":   _check_system(),
    }

    # Derive overall status: critical > degraded > ok
    statuses = [c.get("status", "ok") for c in checks.values()]
    if "critical" in statuses:
        overall = "critical"
    elif "degraded" in statuses:
        overall = "degraded"
    else:
        overall = "ok"

    return {
        "status":    overall,
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "checks":    checks,
    }


def get_liveness() -> dict:
    """
    Minimal liveness probe — used by Docker HEALTHCHECK and GET /health.
    Returns quickly without querying the database.
    """
    return {
        "status":    "ok",
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "service":   "AcousticSpace API",
        "version":   "1.0.0",
    }
