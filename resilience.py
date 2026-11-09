"""
Unit 9 capstone (shape B): keep answering when signal one fails.

The GPT-2 detector is the one part of the pipeline that can fail in ways the
rest can't: the model files can be missing or corrupt, torch can raise on odd
input, and a busy laptop can make one call take far longer than usual. Before
unit 9, any of those turned into a 503 (or a request that just hung).

`run_model_signal` runs the detector with a time budget. It returns
(score, error, milliseconds). When score is None, the caller scores with the
two signals that still work and marks the result degraded.

Fault injection (testing only): when config.FAULT_INJECTION_ENABLED is on, a
request can send the header `X-Fault-Inject: detector_error` or
`detector_slow` to make the detector fail or stall on purpose. With the flag
off (the default), the header is ignored.
"""

import threading
import time

import config
import detector

# Stretch improvement 2 (unit 9): no fixed worker pool. The first capstone run
# used 4 pooled workers, and a timed-out call kept its worker for the whole
# stall (Python can't stop a running thread), so after a burst of stalls the
# healthy requests queued behind them and timed out too (criterion 5 missed).
# Now every call gets its own daemon thread, so a stuck call holds nothing a
# healthy call needs. To stop a truly hung detector from piling up threads
# forever, at most MAX_INFLIGHT calls may be running at once; past that the
# service answers degraded immediately instead of starting another.
MAX_INFLIGHT = 16
_inflight = 0
_lock = threading.Lock()


class InjectedFault(RuntimeError):
    """Raised on purpose by fault injection, so the log can tell it apart."""


def _work(text: str, fault: str | None) -> float:
    if fault == "detector_error":
        raise InjectedFault("injected fault: detector_error")
    if fault == "detector_slow":
        time.sleep(config.FAULT_SLOW_SECONDS)
    return detector.model_signal(text)


def inflight() -> int:
    with _lock:
        return _inflight


def run_model_signal(text: str, fault: str | None = None):
    """Return (score or None, error string or None, elapsed ms)."""
    global _inflight
    start = time.perf_counter()
    ms = lambda: round((time.perf_counter() - start) * 1000, 1)  # noqa: E731

    with _lock:
        if _inflight >= MAX_INFLIGHT:
            return None, f"detector_saturated: {_inflight} calls still running", ms()
        _inflight += 1

    box = {}
    done = threading.Event()

    def target():
        global _inflight
        try:
            box["score"] = _work(text, fault)
        except Exception as exc:  # any failure inside the model call
            box["error"] = exc
        finally:
            with _lock:
                _inflight -= 1
            done.set()

    threading.Thread(target=target, daemon=True, name="detector-call").start()
    if not done.wait(timeout=config.DETECTOR_TIMEOUT_SECONDS):
        # The thread keeps running in the background; its result is dropped.
        return None, f"detector_timeout: over {config.DETECTOR_TIMEOUT_SECONDS}s", ms()
    if "error" in box:
        exc = box["error"]
        return None, f"detector_error: {type(exc).__name__}: {exc}", ms()
    return box["score"], None, ms()


def requested_fault(headers) -> str | None:
    if not config.FAULT_INJECTION_ENABLED:
        return None
    fault = (headers.get("X-Fault-Inject") or "").strip()
    return fault if fault in ("detector_error", "detector_slow") else None


def warm_up() -> bool:
    """Load the model once at startup so the first real request isn't timed out."""
    try:
        detector.model_signal("This sentence is only here to load the model before the first request arrives.")
        return True
    except Exception:
        return False
