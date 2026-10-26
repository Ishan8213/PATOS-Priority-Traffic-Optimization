from patos.graph import Signal
from patos.signals import GREEN, RED, phase_at, wait_s

SIG = Signal(cycle_s=60, ns_green_s=25, ew_green_s=25, offset_s=0)  # NS 0-25, EW 25-50, all-red 50-60


def test_phase_windows():
    assert phase_at(SIG, "NS", 10)[0] == GREEN
    assert phase_at(SIG, "NS", 30)[0] == RED
    assert phase_at(SIG, "EW", 30)[0] == GREEN
    assert phase_at(SIG, "EW", 55)[0] == RED  # all-red clearance
    assert phase_at(SIG, "NS", 55)[0] == RED


def test_green_remaining_reported():
    state, remaining = phase_at(SIG, "NS", 10)
    assert state == GREEN and remaining == 15


def test_no_wait_in_green():
    assert wait_s(SIG, "NS", 10) == 0.0


def test_wait_until_next_green_when_red():
    assert wait_s(SIG, "NS", 30) == 30  # next NS green at t=60
    assert wait_s(SIG, "EW", 5) == 20   # EW green starts at 25


def test_wait_across_cycle_boundary():
    assert wait_s(SIG, "EW", 55) == 30  # 5s of clearance + 25s of NS green
    assert wait_s(SIG, "NS", 55) == 5


def test_late_green_is_not_assumed_passable():
    assert wait_s(SIG, "NS", 24.0) == 36.0  # only 1s left < 2s minimum -> wait for next cycle
    assert wait_s(SIG, "NS", 22.0) == 0.0


def test_cycle_start_override():
    assert phase_at(SIG, "NS", 100, cycle_start=100)[0] == GREEN
    assert wait_s(SIG, "EW", 100, cycle_start=100) == 25


def test_periodicity_with_large_epoch():
    base = 1_800_000_000.0
    assert wait_s(SIG, "NS", base + 30, cycle_start=base) == 30
