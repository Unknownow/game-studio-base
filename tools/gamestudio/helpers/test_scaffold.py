"""Create the files /test-setup scaffolds for one engine, never overwriting one that exists."""
import datetime
import os
import re
import sys

from .. import config as cfgmod
from .. import engines
from . import _util

HELP = """Usage: python tools/studio.py test-scaffold ENGINE [--dry-run | --list] [--root DIR] [--date YYYY-MM-DD]
Creates the files /test-setup scaffolds for one engine, never overwriting one that exists, and prints per
path whether it was created, already there or skipped. Observations, not a verdict.
  ENGINE          an engine name (the engine.name value); its engine plugin supplies the engine files
  --dry-run       print what would be created (WOULD_CREATE), write nothing
  --list          print the project-relative paths this engine's scaffold creates, one per line and nothing
                  else, whatever already exists
  --date D        the setup date for the README (default: today)
Files, in this order: tests/README.md, production/qa/evidence/.gitkeep, the plugin's scaffold_files(), then
tests/smoke/critical-paths.md. The plugin returns a mapping of project-relative path to file text.
With no plugin for ENGINE, or a plugin with no scaffold_files, exit 2.
Output: TSV.
  engine <name>, mode write|dry-run, then per path
  CREATED <path> | WOULD_CREATE <path> | EXISTS <path> | FAILED <path> <reason>
  then created (or would_create) <n>, exists <n> (and failed <n> when above 0)
EXISTS means the path was there (a file, a folder or a link) and was not touched.
Exit codes: 0 every path created or already there; 1 the root cannot be read; 2 usage error, or no scaffold
for the engine; 4 a file or folder could not be created (FAILED). Never prompts."""

README = """# Test Infrastructure

**Engine**: {engine} {version}
**CI**: `.github/workflows/tests.yml`
**Setup date**: {date}

## Directory Layout

```
tests/
  smoke/          # Critical path test list for /smoke-check gate
```

Unit and integration tests live in the engine's test root (`tests_root` in `engine.toml`, default `tests/`).

```
production/qa/
  evidence/       # Screenshot logs and manual test sign-off records
```

> **Manual evidence lives under `production/qa/evidence/`, not `tests/`** — that is where every consumer reads it.

## Running Tests

Run `python tools/studio.py test-run`. It uses the engine plugin's command, else `testing.command` in `project.toml`.

## Test Naming

Follow the engine's test naming convention (`rules/test-standards.md`): names say the scenario and the expected result.

## Story Type → Test Evidence

| Story Type | Required Evidence | Location |
|---|---|---|
| Logic | Automated unit test | the engine's test root |
| Integration | Integration test or documented playtest | the engine's test root, or `production/qa/evidence/` |
| Visual/Feel | Screenshot and sign-off | `production/qa/evidence/` |
| UI | Manual walkthrough or interaction test | `production/qa/evidence/` |
| Config/Data | Smoke check pass | `production/qa/smoke-*.md` |
"""

SMOKE = """# Smoke Test: Critical Paths

**Purpose**: Run these 10-15 checks in under 15 minutes before any QA hand-off.
**Run via**: `/smoke-check` (which reads this file)
**Update**: Add new entries when new core systems are implemented.

## Core Stability (always run)

1. Game launches to main menu without crash
2. New game / session can be started from the main menu
3. Main menu responds to all inputs without freezing

## Core Mechanic (update per sprint)

<!-- Add the primary mechanic for each sprint here as it is implemented -->
4. [Primary mechanic — update when first core system is implemented]

## Data Integrity

5. Save game completes without error (once save system is implemented)
6. Load game restores correct state (once load system is implemented)

## Performance

7. No visible frame rate drops on target hardware (60fps target)
8. No memory growth over 5 minutes of play (once core loop is implemented)
"""


def main(root, argv):
    r, rest = _util.split_root(argv)
    if r:
        root = os.path.abspath(r)
    engine, mode, date = "", "write", ""
    i = 0
    while i < len(rest):
        a = rest[i]
        if a in ("-h", "--help"):
            print(HELP)
            return 0
        if a in ("--dry-run", "--list"):
            mode = a[2:]
        elif a == "--date":
            if i + 1 >= len(rest):
                return _util.usage_error("test-scaffold", "--date needs a date")
            i += 1
            date = rest[i]
        elif a.startswith("--date="):
            date = a[7:]
        elif a.startswith("-") and len(a) > 1:
            return _util.usage_error("test-scaffold", "unknown argument: %s" % a)
        elif not engine:
            engine = a
        else:
            return _util.usage_error("test-scaffold", "one engine only")
        i += 1
    if not engine:
        return _util.usage_error("test-scaffold", "no engine given")
    if date and not re.match(r"^\d{4}-\d{2}-\d{2}$", date):
        return _util.usage_error("test-scaffold", "--date must be YYYY-MM-DD, got %s" % date)
    if not os.path.isdir(root):
        sys.stderr.write("test-scaffold: cannot read root %s\n" % root)
        return 1
    plugin = engines.load_by_name(engine)
    if plugin is None or not hasattr(plugin, "scaffold_files"):
        sys.stderr.write("studio: no test scaffold for engine %s\n" % engine)
        return 2
    cfg = cfgmod.load(root)
    ctx = engines.Ctx(root, cfg)
    extra = plugin.scaffold_files(ctx) or {}
    if not isinstance(extra, dict):
        extra = dict(extra)
    version = cfg.value("engine.version") or ""
    files = [("tests/README.md", README.format(engine=engine, version=version, date=date or datetime.date.today().isoformat())),
             ("production/qa/evidence/.gitkeep", "")]
    files.extend(extra.items())
    files.append(("tests/smoke/critical-paths.md", SMOKE))
    if mode == "list":
        for p, _ in files:
            print(p)
        return 0
    print("engine\t%s" % engine)
    print("mode\t%s" % ("dry-run" if mode == "dry-run" else "write"))
    created = exists = failed = 0
    for rel, text in files:
        full = os.path.join(root, rel)
        if os.path.lexists(full):
            exists += 1
            print("EXISTS\t%s" % rel)
            continue
        if mode == "dry-run":
            created += 1
            print("WOULD_CREATE\t%s" % rel)
            continue
        try:
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, "x", encoding="utf-8", newline="\n") as fh:
                fh.write(text)
            created += 1
            print("CREATED\t%s" % rel)
        except FileExistsError:
            exists += 1
            print("EXISTS\t%s" % rel)
        except OSError as e:
            failed += 1
            print("FAILED\t%s\t%s" % (rel, str(e).replace("\t", " ")))
    print("%s\t%d" % ("would_create" if mode == "dry-run" else "created", created))
    print("exists\t%d" % exists)
    if failed:
        print("failed\t%d" % failed)
        return 4
    return 0
