"""Command line: python tools/studio.py <command>."""
import argparse
import importlib
import json
import os
import sys

from . import config as cfgmod
from .common import default_root, git

COMMANDS = [
    ("setup", "set the git hooks path, sync the Claude Code add-on, run engine setup"),
    ("status", "show project, stories, session, git, gaps and engine state"),
    ("config", "show resolved config, or write one value with --set key=value"),
    ("check", "run blocking checks and advice (use --staged before a commit)"),
    ("update", "copy template-owned files from a template checkout (--from DIR)"),
    ("upstream-diff", "map changes in the CCGS repo to this repo (read-only)"),
    ("claude-sync", "generate .claude/ skills, agents and settings from the portable files"),
    ("claude-hook", "Claude Code hook entry point (pre-bash)"),
]


def _helper_names():
    from . import helpers
    return helpers.NAMES


def _helper_summary(name):
    mod = importlib.import_module("gamestudio.helpers." + name.replace("-", "_"))
    doc = (mod.__doc__ or "").strip().splitlines()
    return doc[0] if doc else ""


def _out(text):
    if text:
        sys.stdout.write(text if text.endswith("\n") else text + "\n")


def _help():
    lines = ["usage: python tools/studio.py [--root DIR] <command> [args]", "", "commands:"]
    for name, desc in COMMANDS:
        lines.append("  %-22s %s" % (name, desc))
    lines.append("")
    lines.append("helper commands (used by skills; run \"<command> --help\" for its arguments):")
    for name in _helper_names():
        lines.append("  %-22s %s" % (name, _helper_summary(name)))
    return "\n".join(lines)


def _parser():
    p = argparse.ArgumentParser(prog="studio.py", add_help=False)
    sub = p.add_subparsers(dest="cmd")
    sub.add_parser("setup")
    sub.add_parser("status")
    c = sub.add_parser("config")
    c.add_argument("--keys")
    c.add_argument("--json", action="store_true")
    c.add_argument("--set")
    c.add_argument("--local", action="store_true")
    k = sub.add_parser("check")
    k.add_argument("--staged", action="store_true")
    k.add_argument("--all", action="store_true")
    u = sub.add_parser("update")
    u.add_argument("--from", dest="src", required=True)
    u.add_argument("--dry-run", action="store_true")
    u.add_argument("--delete", action="store_true")
    d = sub.add_parser("upstream-diff")
    d.add_argument("--clone", required=True)
    d.add_argument("--to")
    d.add_argument("--coverage", action="store_true")
    sub.add_parser("claude-sync")
    h = sub.add_parser("claude-hook")
    h.add_argument("event", choices=["pre-bash"])
    return p


def cmd_check(root, staged):
    from . import check as checkmod
    report = checkmod.run_check(root, staged=staged)
    _out("\n".join(report.lines()))
    return 1 if report.errors else 0


def cmd_setup(root):
    from . import claude_sync, engines
    code, _ = git(root, "config", "core.hooksPath", "hooks")
    if code != 0:
        sys.stderr.write("studio: could not set core.hooksPath (is this a git repository?)\n")
        return 2
    print("git hooks: core.hooksPath = hooks")
    code, lines = claude_sync.sync(root)
    _out("\n".join(lines))
    cfg = cfgmod.load(root)
    ctx = engines.Ctx(root, cfg)
    plugin = engines.load_plugin(ctx)
    msgs = engines.call(plugin, "setup", ctx)
    if msgs:
        _out("\n".join(msgs) if isinstance(msgs, list) else str(msgs))
    return code


def cmd_claude_hook(root):
    from . import check as checkmod
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        return 0
    command = (payload.get("tool_input") or {}).get("command", "")
    if "git commit" not in command:
        return 0
    report = checkmod.run_check(root, staged=True)
    if report.errors:
        sys.stderr.write("\n".join(report.lines()) + "\n")
        return 2
    return 0


def main(argv):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    argv = list(argv)
    root = default_root()
    if len(argv) >= 2 and argv[0] == "--root":
        root = os.path.abspath(argv[1])
        argv = argv[2:]
    if not argv or argv[0] in ("-h", "--help", "help"):
        _out(_help())
        return 0
    name = argv[0]
    if name in _helper_names():
        mod = importlib.import_module("gamestudio.helpers." + name.replace("-", "_"))
        return mod.main(root, argv[1:])
    if name not in [c for c, _ in COMMANDS]:
        sys.stderr.write("studio: unknown command %r (see --help)\n" % name)
        return 2
    args = _parser().parse_args(argv)
    if name == "setup":
        return cmd_setup(root)
    if name == "status":
        from . import status
        lines, ok = status.build(root)
        if not ok:
            sys.stderr.write("\n".join(lines) + "\n")
            return 2
        _out("\n".join(lines))
        return 0
    if name == "config":
        code, text = cfgmod.run(root, args)
        (sys.stderr if code == 2 else sys.stdout).write(text + "\n")
        return code
    if name == "check":
        return cmd_check(root, args.staged)
    if name == "update":
        from . import manifest
        code, lines = manifest.run(root, args.src, args.dry_run, args.delete)
        (sys.stderr if code == 2 else sys.stdout).write("\n".join(lines) + "\n" if lines else "")
        return code
    if name == "upstream-diff":
        from . import upstream
        code, lines = upstream.run(root, args.clone, args.to, args.coverage)
        (sys.stderr if code == 2 else sys.stdout).write("\n".join(lines) + "\n")
        return code
    if name == "claude-sync":
        from . import claude_sync
        code, lines = claude_sync.sync(root)
        _out("\n".join(lines))
        return code
    if name == "claude-hook":
        return cmd_claude_hook(root)
    return 2
