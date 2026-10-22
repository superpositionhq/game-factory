"""Probe checks: what the checker asks the TaskProbe plugin to measure during a play, how it reduces what came back to
one number, and the parts it computes itself (the colour pipeline, the headless editor pass over the project). Nothing
here runs Unreal: check.py plays the game and runs the editor (unreal.py) and hands the results here. Measures are dicts
with their defaults filled in (tasks.measure).

- `plan(task)`: each play's plugin queries (game-probe-queries/1), every runtime measure of the task's probes merged
  per play under stable ids (a query's id is the hash of what it selects, its fields the union of what the probes read).
- `measured(measure, probe, log)`: one number from a play's probe.json (`measures`, and the `track` and `camera` rows
  for the pawn's and the camera's own fields) or its log, following window/at/of/agg/match, and why there is none.
- `colour(settings)`: a neutral grey (0.18) through the grading settings and the key light's colour.
- `editor_script(items, nonce)` / `editor_results(output, file, nonce)` / `reduce_asset(measure, result)`: the editor
  pass, one Python script for the `unreal` module evaluating every `asset` measure of a side."""

import hashlib
import json
import math
import re

from . import tasks

QUERIES_FORMAT = "game-probe-queries/1"
EVERY = 0.5  # seconds between samples
NEAR = 0.26  # a sample within this many seconds of a time is the sample at that time
EDITOR_FILE = "Saved/TaskProbe/probes_editor.json"  # the editor pass's result, beside its printed line
MARKER = "TASK_PROBES"
GREY = 0.18
LUMA = (0.2126, 0.7152, 0.0722)  # Rec. 709 / sRGB linear


def _hash(data, n=10):
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()[:n]


def probes(task):
    """The task's probe checks, in order (tasks.check form)."""
    return [c for _, c in tasks.checks(task) if c["kind"] == "probe"]


# -- (a) the plugin's queries -------------------------------------------------------------------------------------------


def needs(measure):
    """The plugin queries a runtime measure needs, without ids: [{kind, ..., fields}] (none for the pawn's and the
    camera's own fields, read from the track and camera rows, nor for the log)."""
    probe, field = measure["probe"], measure.get("field")
    if probe == "pawn":
        to = measure.get("to")
        if field == "dist" and to is not None and "actor" in to:
            return [{"kind": "actors", "select": to["actor"], "fields": ["x", "y", "z"]}]
        return []
    if probe == "camera":
        return [{"kind": "camera", "fields": [field]}] if field in ("occluded", "pawn_on_screen") else []
    if probe in ("actors", "widgets", "components"):
        return [{"kind": probe, "select": measure["select"], "fields": [] if field == "count" else [field]}]
    if probe == "light":
        return [{"kind": "light", "point": measure["point"]}]
    if probe == "grading":  # a post: field is asked for by name; the colour pipeline's settings always come
        return [{"kind": "grading", "fields": [field] if field.startswith("post:") else []}]
    if probe == "spawns":
        return [{"kind": "spawns", "class": measure["class"]}]
    return []  # log


def query_id(query):
    """A query's stable id: the hash of what it measures (its fields left out, so probes reading other fields of one
    selection share it)."""
    return "q" + _hash({k: v for k, v in query.items() if k != "fields"})


def plan(task):
    """{play name: [query, ...]} for every play a runtime probe of `task` names ("look", "drive", a task play), each
    query with its id, sorted by id; a play whose probes need no query (the track, the log) maps to []."""
    out = {}
    for check in probes(task):
        if check["measure"]["probe"] not in tasks.RUNTIME:
            continue
        merged = out.setdefault(tasks.play_name(check), {})
        for query in needs(check["measure"]):
            qid = query_id(query)
            found = merged.setdefault(qid, {"id": qid, **{k: v for k, v in query.items() if k != "fields"}})
            if "fields" in query:
                found["fields"] = sorted(set(found.get("fields", [])) | set(query["fields"]))
    return {name: [merged[q] for q in sorted(merged)] for name, merged in out.items()}


def query_file(queries, every=None):
    """The plugin's query file (-TaskProbeQueries) for one play's queries (sampled every `every` s, default 0.5), or
    None when it has none."""
    return {"format": QUERIES_FORMAT, "every": every or EVERY, "queries": queries} if queries else None


def task_plays(task):
    """{name: task play} of the task-defined plays its probes name."""
    return {c["play"]["name"]: c["play"] for c in probes(task) if isinstance(c["play"], dict)}


# -- (b) reducing samples to one number ---------------------------------------------------------------------------------


def number(value, match=None):
    """A measured value as a number: booleans 0/1, numbers as they are, a string 1/0 by `match` (None without one)."""
    if value is None:
        return None
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, int | float):
        return float(value) if math.isfinite(value) else None
    if isinstance(value, str):
        return None if match is None else (1.0 if re.search(match, value) else 0.0)
    return None


def combine(values, of):
    """One sample's rows (actors, widgets) combined by `of`; None values left out."""
    found = [v for v in values if v is not None]
    if of == "count":
        return float(sum(1 for v in found if v != 0))
    if of == "any":
        return 1.0 if any(v != 0 for v in found) else 0.0
    if of == "all":
        return 1.0 if found and all(v != 0 for v in found) else 0.0
    if of == "sum":
        return float(sum(found))
    if not found:
        return None
    if of == "min":
        return min(found)
    if of == "max":
        return max(found)
    if of == "mean":
        return sum(found) / len(found)
    if of == "first":
        return found[0]
    raise ValueError(f"no `of` {of}")


def aggregate(values, agg):
    """The picked samples' values reduced by `agg`; None when no sample has a value."""
    found = [v for v in values if v is not None]
    if not found:
        return None
    if agg == "min":
        return min(found)
    if agg == "max":
        return max(found)
    if agg == "mean":
        return sum(found) / len(found)
    if agg == "first":
        return found[0]
    if agg == "last":
        return found[-1]
    if agg == "delta":
        return found[-1] - found[0]
    if agg == "any":
        return 1.0 if any(v != 0 for v in found) else 0.0
    if agg == "all":
        return 1.0 if all(v != 0 for v in found) else 0.0
    if agg == "count":
        return float(sum(1 for v in found if v != 0))
    if agg == "sum":
        return float(sum(found))
    if agg == "range":
        return max(found) - min(found)
    if agg == "std":
        mean = sum(found) / len(found)
        return math.sqrt(sum((v - mean) ** 2 for v in found) / len(found))
    if agg == "changes":
        return float(sum(1 for a, b in zip(found, found[1:]) if not math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-9)))
    raise ValueError(f"no agg {agg}")


def normal(degrees):
    """An angle in (-180, 180]."""
    out = math.fmod(degrees, 360.0)
    out = out - 360.0 if out > 180.0 else out
    return out + 360.0 if out <= -180.0 else out


def angled(measure, value):
    """An angle field's value normalised; with `to_angle`, its shortest absolute distance to that angle (0-180); with
    `to_axis`, its shortest distance to that axis (0-90: a direction and its opposite are one axis). Other fields as
    they are."""
    to_angle, to_axis = measure.get("to_angle"), measure.get("to_axis")
    turn = to_angle if to_angle is not None else to_axis
    if value is None or not tasks.is_angle(measure["field"], turn):
        return value
    if to_axis is not None:
        apart = abs(normal(value - to_axis))
        return min(apart, 180.0 - apart)
    return abs(normal(value - to_angle)) if to_angle is not None else normal(value)


def pick(series, measure):
    """The samples [(t, value)] (in time order) that `window` or `at` picks; all of them by default."""
    series = sorted(series, key=lambda s: s[0])
    if measure.get("window") is not None:
        t0, t1 = measure["window"]
        return [s for s in series if t0 - 1e-6 <= s[0] <= t1 + 1e-6]
    at = measure.get("at")
    if at == "end":
        return series[-1:]
    if at is not None:
        picked = []
        for t in at:
            found = _nearest(series, t)
            if found is not None:
                picked.append(found)
        return picked
    return series


def _nearest(rows, t, key=lambda r: r[0]):
    best = min(rows, key=lambda r: abs(key(r) - t), default=None)
    return best if best is not None and abs(key(best) - t) <= NEAR else None


def _rows(probe, name, width):
    return [[float(v) for v in row] for row in (probe or {}).get(name) or []
            if isinstance(row, list) and len(row) == width and all(isinstance(v, int | float) for v in row)]


def _samples(probe, qid):
    found = ((probe or {}).get("measures") or {}).get(qid) or []
    return sorted((s for s in found if isinstance(s, dict) and isinstance(s.get("t"), int | float)),
                  key=lambda s: s["t"])


def _distance(a, b):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b, strict=True)))


def _forward(pitch, yaw):
    p, y = math.radians(pitch), math.radians(yaw)
    return [math.cos(p) * math.cos(y), math.cos(p) * math.sin(y), math.sin(p)]


def point_at(point, t, probe):
    """Where `point` (tasks.point form) is at play time `t` (cm), or None when the play didn't measure it then."""
    if "xyz" in point:
        return list(point["xyz"])
    if "pawn" in point:
        row = _nearest(_rows(probe, "track", 4), t)
        return None if row is None else [a + b for a, b in zip(row[1:4], point["offset"], strict=True)]
    if "camera" in point:
        row = _nearest(_rows(probe, "camera", 7), t)
        if row is None:
            return None
        ahead = _forward(row[4], row[5])
        return [c + point["forward"] * f for c, f in zip(row[1:4], ahead, strict=True)]
    query = {"kind": "actors", "select": point["actor"]}
    sample = _nearest(_samples(probe, query_id(query)), t, key=lambda s: s["t"])
    rows = (sample or {}).get("rows") or []
    first = rows[0] if rows and isinstance(rows[0], dict) else None
    xyz = [number(first.get(k)) for k in ("x", "y", "z")] if first else None
    if xyz is None or None in xyz:
        return None
    return [a + b for a, b in zip(xyz, point["offset"], strict=True)]


def series(measure, probe):
    """[(t, value or None)] of a runtime measure, one per sample of its play."""
    probe_kind, field = measure["probe"], measure["field"]
    if probe_kind == "pawn":
        track = _rows(probe, "track", 4)
        out = []
        for i, row in enumerate(track):
            t, here = row[0], row[1:4]
            if field in ("x", "y", "z"):
                value = here["xyz".index(field)]
            elif field == "speed":
                dt = t - track[i - 1][0] if i else 0.0
                value = _distance(here, track[i - 1][1:4]) / dt if i and dt > 0 else None
            elif field == "moved":
                value = _distance(here, track[0][1:4])
            else:  # dist
                there = point_at(measure["to"], t, probe)
                value = None if there is None else _distance(here, there)
            out.append((t, value))
        return out
    if probe_kind == "camera" and field not in ("occluded", "pawn_on_screen"):
        track, out = _rows(probe, "track", 4), []
        for row in _rows(probe, "camera", 7):
            t = row[0]
            if field in ("pitch", "yaw", "fov"):
                out.append((t, angled(measure, row[{"pitch": 4, "yaw": 5, "fov": 6}[field]])))
                continue
            pawn = _nearest(track, t)
            if pawn is None:
                out.append((t, None))
            elif field == "distance":
                out.append((t, _distance(row[1:4], pawn[1:4])))
            else:  # height
                out.append((t, row[3] - pawn[3]))
        return out
    (query,) = needs(measure)
    samples = _samples(probe, query_id(query))
    if probe_kind in ("actors", "widgets", "components"):
        out = []
        for s in samples:
            rows = [r for r in s.get("rows") or [] if isinstance(r, dict)]
            if field == "count":
                out.append((s["t"], float(len(rows))))
            else:
                out.append((s["t"], combine([angled(measure, number(r.get(field), measure.get("match")))
                                             for r in rows], measure["of"])))
        return out
    values = [(s["t"], s.get("value") if isinstance(s.get("value"), dict) else {}) for s in samples]
    if probe_kind in ("camera", "light"):
        return [(t, number(v.get(field))) for t, v in values]
    if probe_kind == "grading":
        if field.startswith("post:"):
            return [(t, number(v.get(field))) for t, v in values]
        return [(t, colour(v)[field]) for t, v in values]
    if probe_kind == "spawns":  # cumulative counts since the play started -> the count in each sample's interval
        out, before = [], 0.0
        for t, v in values:
            now = number(v.get(field))
            out.append((t, None if now is None else now - before))
            before = now if now is not None else before
        return out
    raise ValueError(f"no runtime probe {probe_kind}")


def default_agg(measure):
    return measure.get("agg") or ("sum" if measure["probe"] == "spawns" else "last")


def reduce(measure, probe, log=""):
    """A runtime measure of one play as one number, or None when the play measured nothing for it."""
    return measured(measure, probe, log)[0]


def ended(probe):
    """When a play's samples end (s): the probe's own seconds, else its last track or camera row."""
    found = [r[0] for r in _rows(probe, "track", 4) + _rows(probe, "camera", 7)]
    seconds = (probe or {}).get("seconds")
    if isinstance(seconds, int | float) and not isinstance(seconds, bool):
        return float(seconds)
    return max(found, default=0.0)


def measured(measure, probe, log=""):
    """(a runtime measure of one play as one number, or None; why none). A play that ended early (quit, crashed,
    never reached the window) has no samples there: "no samples in the window (the play ended at X s)"."""
    if measure["probe"] == "log":
        return float(sum(1 for line in (log or "").splitlines() if re.search(measure["pattern"], line))), None
    if probe is None:
        return None, "no samples in the window (the play wrote no probe file)"
    picked = pick(series(measure, probe), measure)
    if not picked:
        return None, f"no samples in the window (the play ended at {fmt(ended(probe))} s)"
    value = aggregate([v for _, v in picked], default_agg(measure))
    if value is not None:
        return value, None
    errors = [str(e) for e in (probe.get("query_errors") or []) if isinstance(e, str)]
    said = f"; the plugin said: {errors[0][:300]}" if errors else ""
    return None, f"no value in the window (nothing it selects was measured){said}"


# -- (c) the colour pipeline --------------------------------------------------------------------------------------------


def _mul(m, v):
    return [sum(m[i][j] * v[j] for j in range(3)) for i in range(3)]


def _matmul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


SRGB_TO_XYZ = [[0.4124564, 0.3575761, 0.1804375], [0.2126729, 0.7151522, 0.0721750],
               [0.0193339, 0.1191920, 0.9503041]]
XYZ_TO_SRGB = [[3.2404542, -1.5371385, -0.4985314], [-0.9692660, 1.8760108, 0.0415560],
               [0.0556434, -0.2040259, 1.0572252]]
BRADFORD = [[0.8951, 0.2664, -0.1614], [-0.7502, 1.7135, 0.0367], [0.0389, -0.0685, 1.0296]]
BRADFORD_INV = [[0.9869929, -0.1470543, 0.1599627], [0.4323053, 0.5183603, 0.0492912],
                [-0.0085287, 0.0400428, 0.9684867]]


def _planckian_uv(temp):
    u = (0.860117757 + 1.54118254e-4 * temp + 1.28641212e-7 * temp * temp) / \
        (1.0 + 8.42420235e-4 * temp + 7.08145163e-7 * temp * temp)
    v = (0.317398726 + 4.22806245e-5 * temp + 4.20481691e-8 * temp * temp) / \
        (1.0 - 2.89741816e-5 * temp + 1.61456053e-7 * temp * temp)
    return u, v


def _uv_xy(u, v):
    d = 2 * u - 8 * v + 4
    return 3 * u / d, 2 * v / d


def _daylight_xy(temp):
    temp *= 1.4388 / 1.438
    k = 1.0 / temp
    if temp <= 7000:
        x = 0.244063 + (0.09911e3 + (2.9678e6 - 4.6070e9 * k) * k) * k
    else:
        x = 0.237040 + (0.24748e3 + (1.9018e6 - 2.0064e9 * k) * k) * k
    return x, -3 * x * x + 2.87 * x - 0.275


def white_xy(temp, tint):
    """The white point of a white balance (temperature K, tint), as the engine's post-process shader computes it: the
    daylight locus (the Planckian below 4000 K), moved along the isotherm by the tint."""
    temp = min(max(float(temp), 1500.0), 15000.0)
    u, v = _planckian_uv(temp)
    base = _uv_xy(u, v)
    white = base if temp < 4000 else _daylight_xy(temp)
    ud = (-1.13758118e9 - 1.91615621e6 * temp - 1.53177 * temp * temp) / \
        (1.41213984e6 + 1189.62 * temp + temp * temp) ** 2
    vd = (1.97471536e9 - 705674.0 * temp - 308.607 * temp * temp) / (6.19363586e6 - 179.456 * temp + temp * temp) ** 2
    norm = math.hypot(ud, vd) or 1.0
    ud, vd = ud / norm, vd / norm
    moved = _uv_xy(u - vd * tint * 0.05, v + ud * tint * 0.05)
    return white[0] + moved[0] - base[0], white[1] + moved[1] - base[1]


def _xy_xyz(x, y):
    return [x / y, 1.0, (1 - x - y) / y]


def white_balance(temp, tint, kind="white_balance"):
    """The linear sRGB matrix of a white balance. Relative to the engine's neutral (6500 K, tint 0), so the default
    settings are exactly the identity. "white_balance" (the engine's default): a light of `temp` is made white, so a
    low temperature cools the image; "color_temperature" the other way."""
    src, dst = white_xy(temp, tint), white_xy(6500.0, 0.0)
    if kind == "color_temperature":
        src, dst = dst, src
    s, d = _mul(BRADFORD, _xy_xyz(*src)), _mul(BRADFORD, _xy_xyz(*dst))
    scale = [[d[0] / s[0], 0, 0], [0, d[1] / s[1], 0], [0, 0, d[2] / s[2]]]
    adapt = _matmul(BRADFORD_INV, _matmul(scale, BRADFORD))
    return _matmul(XYZ_TO_SRGB, _matmul(adapt, SRGB_TO_XYZ))


def _luma(rgb):
    return sum(a * b for a, b in zip(LUMA, rgb, strict=True))


def _vec4(settings, key, default):
    found = settings.get(key)
    if isinstance(found, list) and len(found) in (3, 4) and all(isinstance(v, int | float) for v in found):
        return [float(v) for v in found] + ([default] if len(found) == 3 else [])
    return [default] * 4


def _rgb(found):
    if isinstance(found, list) and len(found) >= 3 and all(isinstance(v, int | float) for v in found[:3]):
        return [max(0.0, float(v)) for v in found[:3]]
    return None


def colour(settings):
    """A neutral grey (0.18) lit by the key light's colour (the sun's lit_color, else its colour, else the sky light's;
    its luminance taken out, so only its hue counts), through white balance and the global saturation, contrast, gamma,
    gain and offset (the engine's ColorCorrect, in linear sRGB): {grey, cast, warmth, tint, saturation, contrast}.
    `settings` is the plugin's grading value."""
    settings = settings if isinstance(settings, dict) else {}
    sun = settings.get("sun") if isinstance(settings.get("sun"), dict) else {}
    sky = settings.get("sky") if isinstance(settings.get("sky"), dict) else {}
    light = _rgb(sun.get("lit_color")) or _rgb(sun.get("color")) or _rgb(sky.get("color")) or [1.0, 1.0, 1.0]
    luma = _luma(light)
    rgb = [GREY * c / luma for c in light] if luma > 0 else [GREY] * 3
    temp = settings.get("white_temp", 6500.0)
    tint = settings.get("white_tint", 0.0)
    kind = settings.get("temperature_type", "white_balance")
    if isinstance(temp, int | float) and isinstance(tint, int | float):
        rgb = _mul(white_balance(temp, tint, kind), rgb)
    sat, con = _vec4(settings, "saturation", 1.0), _vec4(settings, "contrast", 1.0)
    gamma, gain = _vec4(settings, "gamma", 1.0), _vec4(settings, "gain", 1.0)
    offset = _vec4(settings, "offset", 0.0)
    luma = _luma(rgb)
    rgb = [max(0.0, luma + (c - luma) * sat[i] * sat[3]) for i, c in enumerate(rgb)]
    rgb = [(c / GREY) ** (con[i] * con[3]) * GREY for i, c in enumerate(rgb)]
    rgb = [c ** (1.0 / max(1e-6, gamma[i] * gamma[3])) for i, c in enumerate(rgb)]
    rgb = [max(0.0, c * gain[i] * gain[3] + offset[i] + offset[3]) for i, c in enumerate(rgb)]
    grey = _luma(rgb)
    over = grey if grey > 1e-9 else 1e-9
    return {"grey": grey, "cast": (max(rgb) - min(rgb)) / over, "warmth": (rgb[0] - rgb[2]) / over,
            "tint": (rgb[1] - (rgb[0] + rgb[2]) / 2) / over, "saturation": sum(sat[:3]) / 3 * sat[3],
            "contrast": sum(con[:3]) / 3 * con[3]}


# -- (d) the editor pass --------------------------------------------------------------------------------------------------


def _asset_json(measure):
    """An asset measure as the editor script reads it: its set fields only."""
    return {k: v for k, v in measure.items() if v is not None}


def editor_id(measure):
    return "a" + _hash(_asset_json(measure))


def editor_items(task):
    """[(id, measure as JSON)] of the task's asset measures, each once, by a stable id."""
    seen = {}
    for check in probes(task):
        if check["measure"]["probe"] == "asset":
            seen.setdefault(editor_id(check["measure"]), _asset_json(check["measure"]))
    return sorted(seen.items())


EDITOR_SCRIPT = r'''# The task checker's editor pass (game-factory docs/task-check.md): every asset measure of the project, as saved.
import fnmatch
import json
import math
import os
import re

import unreal

MEASURES = json.loads(%(measures)r)
NONCE = %(nonce)r
OUT = %(out)r
DEFAULT_MATERIALS = ("WorldGridMaterial", "DefaultMaterial", "DefaultLitMaterial", "DefaultDeferredDecalMaterial")
CLASSES = {}


def snake(name):
    if re.match(r"^b[A-Z]", name):
        name = name[1:]
    return re.sub(r"(?<=[a-z0-9])([A-Z])", r"_\1", name).lower()


def read(obj, name):
    for candidate in (name, snake(name)):
        try:
            return obj.get_editor_property(candidate)
        except Exception:
            pass
    raise KeyError("no property " + name + " on " + type(obj).__name__)


def component(actor, name):
    for found in actor.get_components_by_class(unreal.ActorComponent):
        cls = found.get_class().get_name()
        if found.get_name() == name or cls in (name, name + "Component"):
            return found
    return None


def step(obj, part, actor=None):
    m = re.match(r"^(\w+)(?:\[(\d+)\])?$", part)
    name, index = m.group(1), m.group(2)
    try:
        value = read(obj, name)
    except KeyError:
        value = component(actor, name) if actor is not None else None
        if value is None:
            raise
    if index is not None:
        items = list(value) if value is not None else []
        value = items[int(index)] if int(index) < len(items) else None
    return value


def path_value(obj, path, actor=None):
    value = obj
    for i, part in enumerate(path.split(".")):
        if value is None:
            return None
        value = step(value, part, actor if i == 0 else None)
    return value


def plain(value):
    if value is None:
        return None
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, (int, float)):
        return float(value) if math.isfinite(value) else None
    if isinstance(value, unreal.EnumBase):
        return float(value.value)
    if isinstance(value, (str, unreal.Name, unreal.Text)):
        return str(value)
    if isinstance(value, unreal.Object):
        return 1.0
    return None


def resolve(name):
    if name not in CLASSES:
        found = None
        native = getattr(unreal, name, None)
        if native is not None and hasattr(native, "static_class"):
            found = native.static_class()
        elif name.endswith("_C"):
            registry = unreal.AssetRegistryHelpers.get_asset_registry()
            for data in registry.get_assets_by_class(unreal.TopLevelAssetPath("/Script/Engine", "Blueprint"), True):
                if str(data.asset_name) == name[:-2]:
                    found = unreal.load_class(None, str(data.package_name) + "." + name)
                    break
        CLASSES[name] = found
    return CLASSES[name]


def selected(actor, select):
    if "class" in select:
        target = resolve(select["class"])
        own = actor.get_class()
        if own.get_name() != select["class"] and (target is None
                                                   or not unreal.MathLibrary.class_is_child_of(own, target)):
            return False
    if "tag" in select and not actor.actor_has_tag(select["tag"]):
        return False
    if "name" in select and not (fnmatch.fnmatchcase(actor.get_name(), select["name"])
                                 or fnmatch.fnmatchcase(actor.get_actor_label(), select["name"])):
        return False
    if "near" in select:
        here, there = actor.get_actor_location(), select["near"]["point"]["xyz"]
        if math.sqrt((here.x - there[0]) ** 2 + (here.y - there[1]) ** 2 + (here.z - there[2]) ** 2) \
                > select["near"]["radius"]:
            return False
    return True


def is_default(material):
    if material is None:
        return True
    base = material.get_base_material() if hasattr(material, "get_base_material") else material
    return base is None or (base.get_path_name().startswith("/Engine/") and base.get_name() in DEFAULT_MATERIALS)


def slots(found):
    return [found.get_material(i) for i in range(found.get_num_materials())]


def actor_rows(actor, field, match):
    label = actor.get_actor_label()
    meshes = list(actor.get_components_by_class(unreal.MeshComponent))
    if field == "count":
        return [{"name": label, "value": 1.0}]
    if field == "material_default":
        bad = any(not slots(m) or any(is_default(s) for s in slots(m)) for m in meshes)
        return [{"name": label, "value": 1.0 if bad else 0.0}]
    if field.startswith("material:"):
        prop, rows = field.split(":", 1)[1], []
        for m in meshes:
            for s in slots(m):
                value = None
                for owner in (s, s.get_base_material() if s is not None else None):
                    if owner is None:
                        continue
                    try:
                        value = plain(read(owner, prop))
                        break
                    except KeyError:
                        continue
                rows.append({"name": label + "/" + m.get_name(), "value": value})
        return rows
    if field == "mesh_collision":
        rows = []
        for m in actor.get_components_by_class(unreal.StaticMeshComponent):
            mesh = m.get_editor_property("static_mesh")
            has = False
            if mesh is not None:
                try:
                    count = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem).get_simple_collision_count(mesh)
                except Exception:
                    count = unreal.EditorStaticMeshLibrary.get_simple_collision_count(mesh)
                body = mesh.get_editor_property("body_setup")
                flag = body.get_editor_property("collision_trace_flag") if body is not None else None
                has = count > 0 or flag == unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE
            rows.append({"name": label + "/" + m.get_name(), "value": 1.0 if has else 0.0})
        return rows
    try:
        value = plain(path_value(actor, field[5:], actor))
    except (KeyError, IndexError):  # this actor hasn't the component or the property: no value
        value = None
    return [{"name": label, "value": value}]


def measure(m):
    if "asset" in m:
        asset = unreal.load_asset(m["asset"])
        if asset is None:
            return {"error": "no asset " + m["asset"]}
        return {"value": plain(path_value(asset, m["field"][5:]))}
    world = unreal.EditorLoadingAndSavingUtils.load_map(m["map"])
    if world is None:
        return {"error": "no map " + m["map"]}
    actors = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor)
    rows = []
    for actor in actors:
        if selected(actor, m["select"]):
            rows += actor_rows(actor, m["field"], m.get("match"))
    return {"rows": rows}


results = {}
for mid, m in MEASURES.items():
    try:
        results[mid] = measure(m)
    except Exception as e:
        results[mid] = {"error": (type(e).__name__ + ": " + str(e))[:300]}
line = json.dumps({"nonce": NONCE, "measures": results}, sort_keys=True)
try:
    os.makedirs(os.path.dirname(os.path.join(unreal.Paths.project_dir(), OUT)), exist_ok=True)
    with open(os.path.join(unreal.Paths.project_dir(), OUT), "w", encoding="utf-8") as f:
        f.write(line)
except Exception as e:
    unreal.log_warning("probes: couldn't write " + OUT + ": " + str(e))
print(%(marker)r + " " + line)
'''


def editor_script(items, nonce):
    """The editor pass's Python script for `items` ([(id, measure JSON)]): evaluates each with the `unreal` module and
    writes {"nonce", "measures": {id: {"value"} | {"rows": [{name, value}]} | {"error"}}} to EDITOR_FILE in the project
    and as one line, after MARKER, to its output. `nonce` (the checker's, unknown to the project) marks the real one."""
    return EDITOR_SCRIPT % {"measures": json.dumps(dict(items), sort_keys=True), "nonce": nonce, "out": EDITOR_FILE,
                            "marker": MARKER}


def editor_results(output, file=None, nonce=None):
    """{id: result} from the editor pass: its file's contents (bytes) when it wrote one, else the last MARKER line of
    its output, whichever carries `nonce`; None when neither does."""
    candidates = []
    if file is not None:
        candidates.append(file.decode("utf-8", errors="replace") if isinstance(file, bytes) else file)
    for line in reversed((output or "").splitlines()):
        at = line.find(MARKER + " ")
        if at >= 0:
            candidates.append(line[at + len(MARKER) + 1:])
    for text in candidates:
        try:
            found = json.loads(text)
        except ValueError:
            continue
        if isinstance(found, dict) and found.get("nonce") == nonce and isinstance(found.get("measures"), dict):
            return found["measures"]
    return None


def reduce_asset(measure, result):
    """(number or None, why none) of an asset measure from its editor result."""
    if not isinstance(result, dict):
        return None, "the editor pass gave nothing for it"
    if "error" in result:
        return None, f"the editor couldn't measure it: {str(result['error'])[:200]}"
    if measure.get("asset") is not None:
        value = angled(measure, number(result.get("value"), measure.get("match")))
        return value, None if value is not None else "the property has no number"
    rows = [r for r in result.get("rows") or [] if isinstance(r, dict)]
    if measure["field"] == "count":
        return float(len(rows)), None
    value = combine([angled(measure, number(r.get("value"), measure.get("match"))) for r in rows], measure["of"])
    return value, None if value is not None else "no selected actor has a value"


def fmt(value):
    return "nothing" if value is None else f"{value:.6g}"
