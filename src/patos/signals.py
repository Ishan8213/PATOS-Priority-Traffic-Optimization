"""Fixed-time two-phase signal model.

Phase layout inside one cycle, with x = seconds since cycle start:
  [0, ns_green)                       -> north-south green
  [ns_green, ns_green + ew_green)     -> east-west green
  remainder                           -> all red (clearance)
A vehicle that would reach the stop line with less than MIN_GREEN_REMAINING_S
of green left is treated as having to wait for the next green: the planner
never assumes a vehicle squeezes through the end of a green phase.
"""
from __future__ import annotations

from .graph import Signal

GREEN = "GREEN"
RED = "RED"
MIN_GREEN_REMAINING_S = 2.0


def _window(signal: Signal, axis: str) -> tuple[float, float]:
    if axis == "NS":
        return 0.0, signal.ns_green_s
    if axis == "EW":
        return signal.ns_green_s, signal.ns_green_s + signal.ew_green_s
    raise ValueError(f"invalid axis {axis!r}")


def phase_at(signal: Signal, axis: str, t: float, cycle_start: float | None = None) -> tuple[str, float]:
    """Return (GREEN|RED, seconds of green remaining) for an approach axis at epoch time t."""
    cs = signal.offset_s if cycle_start is None else cycle_start
    x = (t - cs) % signal.cycle_s
    start, end = _window(signal, axis)
    if start <= x < end:
        return GREEN, end - x
    return RED, 0.0


def wait_s(
    signal: Signal,
    axis: str,
    t: float,
    cycle_start: float | None = None,
    min_green_remaining_s: float = MIN_GREEN_REMAINING_S,
) -> float:
    """Seconds a vehicle arriving at time t must wait before it may proceed legally."""
    cs = signal.offset_s if cycle_start is None else cycle_start
    x = (t - cs) % signal.cycle_s
    start, end = _window(signal, axis)
    if start <= x < end and (end - x) >= min_green_remaining_s:
        return 0.0
    if x < start:
        return start - x
    return signal.cycle_s - x + start
