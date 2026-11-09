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

import concurrent.futures
import time

import config
import detector

# A few workers, so one stuck in a slow call never blocks the next request.
_POOL = concurrent.futures.ThreadPoolExecutor(max_workers=4, thread_name_prefix="detector")


class InjectedFault(RuntimeError):
    """Raised on purpose by fault injection, so the log can tell it apart."""


def _work(text: str, fault: str | None) -> float:
    if fault == "detector_error":
        raise InjectedFault("injected fault: detector_error")
    if fault == "detector_slow":
        time.sleep(config.FAULT_SLOW_SECONDS)
    return detector.model_signal(text)


def run_model_signal(text: str, fault: str | None = None):
    """Return (score or None, error string or None, elapsed ms)."""
    start = time.perf_counter()
    future = _POOL.submit(_work, text, fault)
    try:
        score = future.result(timeout=config.DETECTOR_TIMEOUT_SECONDS)
        return score, None, round((time.perf_counter() - start) * 1000, 1)
    except concurrent.futures.TimeoutError:
        # The worker keeps running in the background; its result is dropped.
        return None, f"detector_timeout: over {config.DETECTOR_TIMEOUT_SECONDS}s", round((time.perf_counter() - start) * 1000, 1)
    except Exception as exc:  # any failure inside the model call
        return None, f"detector_error: {type(exc).__name__}: {exc}", round((time.perf_counter() - start) * 1000, 1)


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
