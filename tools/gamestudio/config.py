"""Config resolution: project.local.toml -> project.toml -> engine.toml -> rigor -> default."""
import json
import os
import tomllib

from . import toml_edit

RIGOR_TABLE = {
    "minimal": {"workflow": "minimal", "docs.density": "terse", "qa.level": "minimal",
                "story_granularity": "coarse", "review_mode": "solo", "team.size": "individual"},
    "standard": {"workflow": "standard", "docs.density": "balanced", "qa.level": "standard",
                 "story_granularity": "balanced", "review_mode": "lean", "team.size": "individual"},
    "full": {"workflow": "full", "docs.density": "thorough", "qa.level": "full",
             "story_granularity": "fine", "review_mode": "full", "team.size": "studio"},
}

STAGES = ["Concept", "Systems Design", "Technical Setup", "Pre-Production", "Production", "Polish", "Release"]
TIERS = ["minimal", "standard", "full"]

# file path -> allowed values (compared as lowercase-free exact strings; booleans as "true"/"false")
ENUMS = {
    "modes.review_mode": ["full", "lean", "solo"],
    "modes.rigor": TIERS,
    "modes.workflow": TIERS,
    "modes.automation": ["collaborative", "guided", "autonomous"],
    "modes.story_granularity": ["coarse", "balanced", "fine"],
    "docs.density": ["terse", "balanced", "thorough"],
    "qa.level": TIERS,
    "team.size": ["individual", "small", "studio"],
    "performance.enforce": ["warn", "block", "off"],
    "platform.cert_tier": ["none", "itch", "steam", "console"],
    "accessibility.target": ["none", "standard", "aaa"],
    "project.stage": STAGES,
    "testing.strict.logic": ["true", "false"],
    "testing.strict.integration": ["true", "false"],
    "testing.strict.visual": ["true", "false"],
    "testing.strict.ui": ["true", "false"],
    "testing.strict.config": ["true", "false"],
    "features.session_state": ["on", "off"],
    "features.read_guard": ["on", "off", "true", "false"],
    "platform.online": ["true", "false"],
    "workflow_overrides.edge_cases": ["true", "false"],
    "workflow_overrides.tuning_knobs": ["true", "false"],
    "workflow_overrides.art_bible_strict": ["true", "false"],
    "updates.check": ["true", "false"],
    "claude.sync": ["true", "false"],
}

# table -> allowed keys. A dict value means a nested table of keys; None means free-form.
SCHEMA = {
    "framework": ["source", "version"],
    "project": ["name", "stage", "genre", "kind", "version"],
    "modes": ["rigor", "review_mode", "workflow", "automation", "automation_always_ask", "story_granularity"],
    "workflow_overrides": ["edge_cases", "tuning_knobs", "art_bible_strict", {"system_overrides": None}],
    "engine": ["name", "version", "language", "editor_path"],
    "performance": ["enforce", "target_framerate", "frame_budget_ms", "draw_call_limit", "memory_ceiling_mb"],
    "testing": ["command", {"strict": ["logic", "integration", "visual", "ui", "config"]}],
    "docs": ["density"],
    "qa": ["level"],
    "team": ["size"],
    "claude": ["sync"],
    "platform": ["online", "cert_tier"],
    "accessibility": ["target"],
    "features": ["session_state", "read_guard"],
    "updates": ["check"],
}

# display name -> file path
KEYS = [
    ("rigor", "modes.rigor"),
    ("review_mode", "modes.review_mode"),
    ("automation", "modes.automation"),
    ("automation_always_ask", "modes.automation_always_ask"),
    ("workflow", "modes.workflow"),
    ("docs.density", "docs.density"),
    ("qa.level", "qa.level"),
    ("story_granularity", "modes.story_granularity"),
    ("team.size", "team.size"),
    ("project.name", "project.name"),
    ("project.stage", "project.stage"),
    ("engine.name", "engine.name"),
    ("engine.version", "engine.version"),
    ("engine.editor_path", "engine.editor_path"),
    ("performance.enforce", "performance.enforce"),
    ("testing.command", "testing.command"),
    ("testing.strict.logic", "testing.strict.logic"),
    ("testing.strict.integration", "testing.strict.integration"),
    ("testing.strict.visual", "testing.strict.visual"),
    ("testing.strict.ui", "testing.strict.ui"),
    ("testing.strict.config", "testing.strict.config"),
    ("claude.sync", "claude.sync"),
]
DISPLAY_TO_PATH = dict(KEYS)
PATH_TO_DISPLAY = {p: d for d, p in KEYS}
FRONTED = {"review_mode", "workflow", "docs.density", "qa.level", "story_granularity", "team.size"}
DEFAULTS = {
    "modes.rigor": "minimal",
    "modes.automation": "collaborative",
    "modes.automation_always_ask": ["scope_changes", "file_deletions", "schema_changes"],
    "project.stage": "Concept",
    "performance.enforce": "warn",
    "claude.sync": True,
}


def known_paths():
    paths = {"schema_version"}
    for table, keys in SCHEMA.items():
        for k in keys:
            if isinstance(k, dict):
                for sub, subkeys in k.items():
                    paths.add(table + "." + sub)
                    for s in subkeys or []:
                        paths.add(table + "." + sub + "." + s)
            else:
                paths.add(table + "." + k)
    return paths


def normalize_key(name):
    """Accept a display name or a file path; return the file path."""
    if name in DISPLAY_TO_PATH:
        return DISPLAY_TO_PATH[name]
    return name


def load_toml(path):
    """Return (data, error). Absent file gives ({}, None) with exists False via os.path."""
    try:
        with open(path, "rb") as fh:
            return tomllib.load(fh), None
    except FileNotFoundError:
        return None, None
    except (tomllib.TOMLDecodeError, UnicodeDecodeError) as exc:
        return None, str(exc)


def lookup(data, path):
    cur = data
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def _is_unset(v):
    return v is None or (isinstance(v, str) and v.strip() == "")


def _enum_str(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    return str(v)


def _enum_bad(path, value):
    allowed = ENUMS.get(path)
    if path.startswith("workflow_overrides.system_overrides."):
        allowed = TIERS
    if allowed is None:
        return None
    if _enum_str(value) not in allowed:
        return "invalid value %r for %s (allowed: %s)" % (value, path, ", ".join(allowed))
    return None


def validate_data(data, label, require_version):
    """Return a list of problem strings for one parsed config file."""
    problems = []
    schema = SCHEMA
    if require_version and data.get("schema_version") != 1:
        problems.append("%s: schema_version must be 1" % label)
    elif "schema_version" in data and data["schema_version"] != 1:
        problems.append("%s: schema_version must be 1" % label)
    for top, val in data.items():
        if top == "schema_version":
            continue
        if top not in schema:
            problems.append("%s: unknown table or key `%s`" % (label, top))
            continue
        if not isinstance(val, dict):
            problems.append("%s: `%s` must be a table" % (label, top))
            continue
        allowed = schema[top]
        plain = [k for k in allowed if not isinstance(k, dict)]
        nested = {}
        for k in allowed:
            if isinstance(k, dict):
                nested.update(k)
        for key, v in val.items():
            if key in nested:
                if not isinstance(v, dict):
                    problems.append("%s: `%s.%s` must be a table" % (label, top, key))
                    continue
                sub = nested[key]
                for sk, sv in v.items():
                    if sub is not None and sk not in sub:
                        problems.append("%s: unknown key `%s.%s.%s`" % (label, top, key, sk))
                        continue
                    msg = _enum_bad("%s.%s.%s" % (top, key, sk), sv)
                    if msg:
                        problems.append("%s: %s" % (label, msg))
            elif key in plain:
                msg = None if _is_unset(v) else _enum_bad(top + "." + key, v)
                if msg:
                    problems.append("%s: %s" % (label, msg))
            else:
                problems.append("%s: unknown key `%s.%s`" % (label, top, key))
    return problems


class Config(object):
    def __init__(self, root):
        self.root = root
        self.local, self.local_err = load_toml(os.path.join(root, "project.local.toml"))
        self.project, self.project_err = load_toml(os.path.join(root, "project.toml"))
        self.engine_toml, self.engine_err = load_toml(os.path.join(root, "engine.toml"))
        self.local = self.local or {}
        self.project = self.project or {}
        self.engine_toml = self.engine_toml or {}
        self.notes = []

    def problems(self):
        out = []
        for label, err in (("project.toml", self.project_err), ("project.local.toml", self.local_err),
                           ("engine.toml", self.engine_err)):
            if err:
                out.append("%s: cannot parse: %s" % (label, err))
        if not os.path.exists(os.path.join(self.root, "project.toml")):
            out.append("project.toml: file is missing")
        elif not self.project_err:
            out.extend(validate_data(self.project, "project.toml", True))
        if not self.local_err and self.local:
            out.extend(validate_data(self.local, "project.local.toml", False))
        return out

    def _from_sources(self, path):
        defaults = self.engine_toml.get("defaults", {}) if isinstance(self.engine_toml.get("defaults"), dict) else {}
        for source, getter in (
            ("project.local.toml", lambda: lookup(self.local, path)),
            ("project.toml", lambda: lookup(self.project, path)),
            ("engine.toml", lambda: defaults.get(path)),
        ):
            v = getter()
            if _is_unset(v):
                continue
            if _enum_bad(path, v):
                self.notes.append("%s: %s ignored" % (source, _enum_bad(path, v)))
                continue
            return v, source
        return None, None

    def get(self, name):
        """Return (value, source). Value None means unset."""
        path = normalize_key(name)
        display = PATH_TO_DISPLAY.get(path, path)
        v, source = self._from_sources(path)
        if source:
            return v, source
        if display in FRONTED:
            rigor, _ = self.get("rigor")
            return RIGOR_TABLE[rigor][display], "rigor:" + rigor
        if path in DEFAULTS:
            return DEFAULTS[path], "default"
        return None, "default"

    def value(self, name):
        return self.get(name)[0]

    def system_overrides(self):
        so = lookup(self.project, "workflow_overrides.system_overrides")
        return so if isinstance(so, dict) else {}


def load(root):
    return Config(root)


def render_value(v):
    if v is None:
        return "unset"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, list):
        return ", ".join(str(x) for x in v)
    return str(v)


GATE_DEFAULTS = {"logic": "blocking", "integration": "blocking", "visual": "blocking", "ui": "blocking",
                 "config": "advisory"}
DERIVED = ["system_overrides", "gate_level", "engine_values", "perf_budgets", "review_gate"]


def derived_line(cfg, name):
    """Lines that answer a question skills would otherwise work out by hand. Printed only when named."""
    if name == "system_overrides":
        so = cfg.system_overrides()
        return "system_overrides: " + (" ".join("%s=%s" % kv for kv in so.items()) or "none")
    if name == "gate_level":
        parts = []
        for t, default in GATE_DEFAULTS.items():
            v, src = cfg.get("testing.strict." + t)
            if v is None:
                extra = "default; smoke-check: blocking" if t == "config" else "default"
                parts.append("%s=%s(%s)" % (t, default, extra))
            else:
                parts.append("%s=%s(%s)" % (t, "blocking" if v else "advisory", src))
        return "gate_level: " + " ".join(parts)
    if name == "engine_values":
        parts, srcs = [], set()
        for k in ("name", "version", "language"):
            v, src = cfg.get("engine." + k)
            parts.append("%s=%s%s" % (k, v if v else "unset", "(%s)" % src if v else ""))
        return "engine_values: " + " ".join(parts)
    if name == "perf_budgets":
        parts = []
        for k in ("target_framerate", "frame_budget_ms", "draw_call_limit", "memory_ceiling_mb"):
            v = lookup(cfg.project, "performance." + k)
            parts.append("%s=%s" % (k, v if v not in (None, "") else "unset"))
        return "perf_budgets: " + " ".join(parts) + " (project.toml)"
    if name == "review_gate":
        mode, src = cfg.get("review_mode")
        skill = "skip" if mode == "solo" else "skip" if mode == "lean" else "run"
        phase = "skip" if mode == "solo" else "run"
        return "review_gate: skill-gates=%s phase-gates=%s (review_mode %s, %s; a --review flag overrides)" % (skill, phase, mode, src)
    return None


def format_lines(cfg, names):
    lines = []
    for name in names:
        if name in DERIVED:
            lines.append(derived_line(cfg, name))
            continue
        v, src = cfg.get(name)
        lines.append("%s: %s (%s)" % (PATH_TO_DISPLAY.get(normalize_key(name), name), render_value(v), src))
    return lines


def _coerce(path, raw):
    if path in ENUMS and set(ENUMS[path]) >= {"true", "false"} and raw in ("true", "false"):
        return raw == "true"
    if path == "claude.sync":
        return raw == "true"
    if path in ("performance.target_framerate", "performance.draw_call_limit", "performance.memory_ceiling_mb"):
        try:
            return int(raw)
        except ValueError:
            pass
    if path == "performance.frame_budget_ms":
        try:
            return float(raw)
        except ValueError:
            pass
    return raw


def set_key(root, assignment, local=False):
    """Write one scalar. Returns (exit_code, message)."""
    if "=" not in assignment:
        return 2, "studio: --set expects key=value"
    name, raw = assignment.split("=", 1)
    path = normalize_key(name.strip())
    raw = raw.strip()
    if path == "modes.automation_always_ask":
        return 2, "studio: edit project.toml by hand: lists cannot be written with --set"
    ok = path in known_paths() or path.startswith("workflow_overrides.system_overrides.")
    if not ok:
        return 2, "studio: unknown config key `%s`" % path
    value = _coerce(path, raw)
    bad = _enum_bad(path, value)
    if bad:
        return 2, "studio: " + bad
    fname = os.path.join(root, "project.local.toml" if local else "project.toml")
    text = ""
    if os.path.exists(fname):
        with open(fname, "r", encoding="utf-8", newline="") as fh:
            text = fh.read()
    elif not local:
        text = "schema_version = 1\n"
    try:
        new = toml_edit.set_value(text, path, value)
    except toml_edit.TomlEditError as exc:
        return 2, "studio: " + str(exc)
    try:
        tomllib.loads(new)
    except tomllib.TOMLDecodeError as exc:
        return 2, "studio: refusing to write invalid TOML: %s" % exc
    with open(fname, "w", encoding="utf-8", newline="") as fh:
        fh.write(new)
    cfg = load(root)
    if path.startswith("workflow_overrides.system_overrides."):
        return 0, "%s = %s (%s)" % (path, raw, os.path.basename(fname))
    return 0, format_lines(cfg, [path])[0]


def run(root, args):
    """Implements the config command. Returns (exit_code, stdout)."""
    if args.set:
        code, msg = set_key(root, args.set, args.local)
        return code, msg
    cfg = load(root)
    if cfg.project_err or cfg.local_err:
        err = cfg.project_err or cfg.local_err
        return 2, "studio: config is unreadable: " + err
    names = [n.strip() for n in args.keys.split(",") if n.strip()] if args.keys else [d for d, _ in KEYS]
    if args.json:
        out = {}
        for n in names:
            if n in DERIVED:
                out[n] = {"value": derived_line(cfg, n).split(": ", 1)[1], "source": "derived"}
                continue
            v, s = cfg.get(n)
            out[PATH_TO_DISPLAY.get(normalize_key(n), n)] = {"value": v, "source": s}
        return 0, json.dumps(out, indent=2)
    lines = ["=== Resolved Config ==="] + format_lines(cfg, names)
    if not args.keys:
        lines.append(derived_line(cfg, "system_overrides"))
    if cfg.notes:
        lines.append("notes: " + "; ".join(cfg.notes))
    lines.append("=== end config ===")
    return 0, "\n".join(lines)
