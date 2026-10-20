"""The task check's rules: a probe's threshold and whether a value passes it, and whether a task is VALID.

Thresholds (a probe's `expect`):
- a literal (`value`): as written;
- calibrated (`calibrate: f`): s + f * (r - s) from the start's value s and the reference's r, both measured by this
  check. A start that measured nothing anchors on the reference alone: r moved MARGIN of |r| toward the start's side
  (below r for > and >=, above it for < and <=). A reference that measured nothing, or a start and reference that
  measure the same, leave no threshold: the probe fails as uncalibrated;
- relative to the start (`start_times: f`, `start_plus: d`): s * f or s + d; a start that measured nothing leaves no
  threshold.

A task is VALID when
- the start builds, unless the task says it doesn't (a build check's `fails_at_start`: making it build is the task):
  then the start must not build, and that is the start failing the task (it is never played);
- with a reference: the reference builds and boots and passes every required probe; its other checks (log_absent,
  file_exists, probes that aren't required) are notes, never decisive; the start fails at least one required probe
  outside still_works (or doesn't build by design);
- without a reference: the start fails at least one required probe outside still_works (or doesn't build by design);
- either way, every required probe of the task's `still_works` milestone already passes at the start: what still works
  must hold there, or the probe is broken and would fail every correct solution. A still-works probe the start
  measured nothing for (its play crashed: the task's own bug) is no sign of a broken probe.
Judges (judge, code_judge, actions_judge) never take part, and neither do trace probes or packaging."""

import math

from . import probes, tasks

MARGIN = 0.25  # a calibrated threshold whose start measured nothing: the reference's value, this share toward the start


class Uncalibrated(Exception):
    """A probe whose threshold can't be made (a start and reference measuring the same; a side that must be measured
    measuring nothing): the task can't be graded by it. `start`, `fix`: what each side measured."""

    def __init__(self, message, start=None, fix=None):
        super().__init__(message)
        self.start, self.fix = start, fix


def threshold(expect, start=None, fix=None):
    """A probe's threshold from its expect: the literal, s + f * (r - s), s * f or s + d."""
    if "value" in expect:
        return float(expect["value"])
    if "calibrate" in expect:
        if start is None:
            return fix - MARGIN * abs(fix) if expect["op"] in (">", ">=") else fix + MARGIN * abs(fix)
        return start + expect["calibrate"] * (fix - start)
    if "start_times" in expect:
        return start * expect["start_times"]
    return start + expect["start_plus"]


def same(a, b):
    """Whether a start and a reference measure the same (within 1e-6 relative): nothing to calibrate between them."""
    return math.isclose(a, b, rel_tol=1e-6, abs_tol=1e-9)


def passes(value, op, limit):
    if op in ("==", "!="):
        equal = math.isclose(value, limit, rel_tol=1e-9, abs_tol=1e-9)
        return equal if op == "==" else not equal
    return {">": value > limit, ">=": value >= limit, "<": value < limit, "<=": value <= limit}[op]


def make_threshold(check, start_value, fix_value):
    """(threshold, start value, fix value) of probe `check` from its sides' measures (each `(value, why)` or a callable
    giving it, called only when the threshold needs that side). Raises Uncalibrated."""
    expect, relative = check["expect"], tasks.relative(check)
    if relative is None:
        return float(expect["value"]), None, None
    start, why = start_value() if callable(start_value) else start_value
    if start is None and relative == "start":
        raise Uncalibrated(f"{check['name']}: the start measured nothing ({why}), and the threshold is relative to it",
                           start)
    fix = None
    if relative == "calibrate":
        fix, why = fix_value() if callable(fix_value) else fix_value
        if fix is None:
            raise Uncalibrated(f"{check['name']}: the reference measured nothing ({why})", start, fix)
        if start is not None and same(start, fix):
            raise Uncalibrated(f"{check['name']}: the start and the reference both measure {probes.fmt(start)}, so "
                               "there is no threshold between them", start, fix)
    return threshold(expect, start, fix), start, fix


def describe(check, value, limit, start, fix, why=None):
    """A probe's detail: "<describe> | measured X, threshold OP Y (start S, fix R): why none"."""
    detail = f"{check['describe']} | measured {probes.fmt(value)}, threshold {check['expect']['op']} {probes.fmt(limit)}"
    if fix is not None:
        detail += f" (start {probes.fmt(start)}, fix {probes.fmt(fix)})"
    elif start is not None:
        detail += f" (start {probes.fmt(start)})"
    return detail + (f": {why}" if why else "")


def verdict(task, reference, start):
    """(valid, why, notes) from the reference's and the start's check rows ({"checks": [{name, kind, passed,
    detail}]}). `reference` None: a start-only check."""
    why, notes = [], []
    required = tasks.gating(task)
    still = tasks.still_works(task)
    build = tasks.fails_at_start(task)
    broken = [c for c in start["checks"] if build is not None and c["name"] == build["name"]
              and not str(c["detail"]).startswith("not asked")]
    if any(c["passed"] for c in broken):
        why.append(f"start builds, though {build['name']} says it doesn't (fails_at_start)")
    for c in start["checks"]:
        detail = str(c["detail"])
        if c["name"] in still and not c["passed"] and not detail.startswith("not asked") \
                and "measured nothing" not in detail:  # a crash the task fixes leaves nothing to measure
            why.append(f"start fails still-works {c['name']}: {detail[:160]}")
    if reference is not None:
        for c in reference["checks"]:
            if c["passed"]:
                continue
            if c["kind"] in ("build", "boot") or c["name"] in required:
                why.append(f"reference fails {c['name']}: {str(c['detail'])[:160]}")
            else:
                notes.append(f"reference fails {c['name']} ({c['kind']}): {str(c['detail'])[:160]}")
    if reference is None and broken:  # a start-only check's gate: the start doesn't build by design
        return not why, why, notes
    gates = [c for c in start["checks"] if c["name"] in required and c["name"] not in still] + broken
    if not gates:
        why.append("no required probe outside still_works to check the start with")
    elif all(c["passed"] for c in gates):
        why.append("start already passes every required probe")
    return not why, why, notes
