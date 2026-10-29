"""Run the project's automated tests under a timeout and read the result with one exit-code ladder."""
import os
import re
import shlex
import subprocess
import sys
import tempfile

from .. import config as cfgmod
from .. import engines
from . import _util

HELP = """Usage: python tools/studio.py test-run [options]
Runs the project's automated tests the way /smoke-check Phase 2 does, under a timeout, and reads the
result with one exit-code ladder: the command, the timeout, the exit code, the zero-tests marker, the
counts, and the ladder row that matched. Observations, not a verdict: PASS, FAIL and NOT ASSESSED stay
with /smoke-check.
  --cmd COMMAND       the test command to run, instead of the engine plugin's or testing.command
  --timeout SECONDS   default 900
  --log FILE          keep the runner's output here (default: a temp file)
  --dry-run           print what would run; run nothing
  --root DIR          the project; defaults to the repo this script is in
The command comes from the engine plugin's test_command(), else `[testing] command` in project.toml (split
like a shell would). With neither, exit 2.
The ladder (one for every engine):
  exit 0, output shows tests ran, or its count is unknown   rule pass
  exit 0, no tests ran (empty output, or a zero-tests marker)   rule no-tests
  exit 1                                                    rule fail
  any other exit code                                       rule error
  the timeout reached                                       rule timeout
Output: TSV, in this order (a row that cannot apply is left out).
  engine <name|->
  command <testing.command|plugin|--cmd> <the command>
  timeout <seconds>
  ran <yes|no> <why not, or ->
  exit <code of the test command>
  timed_out <yes|no>
  zero_tests <yes|no|unknown> <the marker line, or ->
  tests total=<n> passed=<n> failed=<n>        or `-  not sourced`
  failed <a line naming a failing test>  (up to 10, then `failed_more <n>`)
  rule <id> <what that row of the ladder says>
  log <path>
Exit codes: 0 the helper finished (whatever the tests did: read the rows); 1 cannot read the root or write the
log; 2 usage error, or no test command; It runs the project's own test command and never edits project.toml."""

ZERO = [re.compile(r'testcasecount="0"'), re.compile(r"No test cases found", re.I),
        re.compile(r"No tests (were )?(found|run|ran|collected)", re.I), re.compile(r"\b0 tests?\b", re.I),
        re.compile(r"Ran 0 tests", re.I), re.compile(r"no automation tests matched", re.I)]
COUNTS = [re.compile(r'testcasecount="([0-9]+)"[^>]*?(?:passed="([0-9]+)")?[^>]*?(?:failed="([0-9]+)")?'),
          re.compile(r"Ran ([0-9]+) tests?"),
          re.compile(r"([0-9]+) passed(?:, ([0-9]+) failed)?")]
FAILLINE = re.compile(r"(^|[^A-Za-z0-9_])(FAILED|FAIL|Failed|failed:)([^A-Za-z0-9_]|$)")


def split_cmd(cmd):
    if os.name == "nt":
        out = []
        for tok in shlex.split(cmd, posix=False):
            if len(tok) >= 2 and tok[0] == tok[-1] and tok[0] in "\"'":
                tok = tok[1:-1]
            out.append(tok)
        return out
    return shlex.split(cmd)


def read_counts(text):
    m = re.search(r'<test-run[^>]*>', text)
    if m:
        tag = m.group(0)

        def a(n):
            x = re.search(n + r'="([0-9]+)"', tag)
            return int(x.group(1)) if x else None
        total = a("testcasecount") if a("testcasecount") is not None else a("total")
        if total is not None:
            return total, a("passed") or 0, a("failed") or 0
    m = re.search(r"Ran ([0-9]+) tests?", text)
    if m:
        total = int(m.group(1))
        f = re.search(r"failures=([0-9]+)", text)
        fe = int(f.group(1)) if f else 0
        e = re.search(r"errors=([0-9]+)", text)
        fe += int(e.group(1)) if e else 0
        return total, total - fe, fe
    m = re.search(r"([0-9]+) passed", text)
    if m:
        p = int(m.group(1))
        f = re.search(r"([0-9]+) failed", text)
        fi = int(f.group(1)) if f else 0
        return p + fi, p, fi
    return None


def main(root, argv):
    r, rest = _util.split_root(argv)
    if r:
        root = os.path.abspath(r)
    cmd_arg, timeout, log, dry = "", 900, "", False
    i = 0
    while i < len(rest):
        a = rest[i]
        if a in ("-h", "--help"):
            print(HELP)
            return 0
        if a == "--dry-run":
            dry = True
            i += 1
            continue
        if a in ("--cmd", "--timeout", "--log"):
            if i + 1 >= len(rest):
                return _util.usage_error("test-run", "%s needs a value" % a)
            v = rest[i + 1]
            if a == "--cmd":
                cmd_arg = v
            elif a == "--log":
                log = v
            else:
                if not re.match(r"^[0-9]+$", v) or int(v) <= 0:
                    return _util.usage_error("test-run", "--timeout is whole seconds above 0")
                timeout = int(v)
            i += 2
            continue
        return _util.usage_error("test-run", "unknown argument: %s" % a)
    if not os.path.isdir(root):
        sys.stderr.write("test-run: cannot read root %s\n" % root)
        return 1
    cfg = cfgmod.load(root)
    ctx = engines.Ctx(root, cfg)
    plugin = engines.load_plugin(ctx)
    ename = cfg.value("engine.name") or ""
    source, cmd = "", None
    if cmd_arg:
        source, cmd = "--cmd", split_cmd(cmd_arg)
    else:
        pc = engines.call(plugin, "test_command", ctx)
        if pc:
            source, cmd = "plugin", list(pc) if isinstance(pc, (list, tuple)) else split_cmd(str(pc))
        else:
            tc = cfg.value("testing.command")
            if tc:
                source, cmd = "testing.command", split_cmd(str(tc))
    if not cmd:
        sys.stderr.write("studio: no test command; set testing.command in project.toml or configure an engine\n")
        return 2
    _util.row("engine", ename or "-")
    _util.row("command", source, " ".join(cmd))
    _util.row("timeout", timeout)
    if dry:
        _util.row("ran", "no", "--dry-run")
        return 0
    if not log:
        fd, log = tempfile.mkstemp(prefix="test-run-", suffix=".log")
        os.close(fd)
    try:
        timed, code, out = False, None, ""
        try:
            p = subprocess.run(cmd, cwd=root, capture_output=True, text=True, errors="replace", timeout=timeout)
            code, out = p.returncode, (p.stdout or "") + (p.stderr or "")
        except subprocess.TimeoutExpired as e:
            timed = True
            out = ((e.stdout or b"").decode("utf-8", "replace") if isinstance(e.stdout, bytes) else (e.stdout or "")) + \
                  ((e.stderr or b"").decode("utf-8", "replace") if isinstance(e.stderr, bytes) else (e.stderr or ""))
        except OSError as e:
            _util.row("ran", "no", "the command could not start: %s" % e)
            _util.row("rule", "error", "the test command could not start")
            return 0
        with open(log, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(out)
    except OSError as e:
        sys.stderr.write("test-run: cannot write the log %s: %s\n" % (log, e))
        return 1
    out = out.replace("\r\n", "\n")
    _util.row("ran", "yes", "-")
    _util.row("exit", "-" if code is None else code)
    _util.row("timed_out", "yes" if timed else "no")
    zero, marker = "unknown", "-"
    counts = read_counts(out)
    if not out.strip():
        zero, marker = "yes", "no output"
    else:
        for rx in ZERO:
            m = rx.search(out)
            if m:
                zero = "yes"
                marker = next((ln for ln in out.split("\n") if rx.search(ln)), m.group(0)).strip()
                break
        if zero == "unknown" and counts is not None and counts[0] > 0:
            zero = "no"
    if zero == "unknown" and counts is not None and counts[0] == 0:
        zero = "yes"
    _util.row("zero_tests", zero, marker)
    if counts is not None:
        _util.row("tests", "total=%d passed=%d failed=%d" % counts)
    else:
        _util.row("tests", "-", "not sourced")
    fl = [ln.strip() for ln in out.split("\n") if FAILLINE.search(ln)]
    for ln in fl[:10]:
        _util.row("failed", ln)
    if len(fl) > 10:
        _util.row("failed_more", len(fl) - 10)
    if timed:
        _util.row("rule", "timeout", "the timeout was reached: the run never completed")
    elif code == 0:
        if zero == "yes":
            _util.row("rule", "no-tests", "exit 0 but no tests ran: not a pass")
        else:
            _util.row("rule", "pass", "exit 0 and tests ran or their count is unknown")
    elif code == 1:
        _util.row("rule", "fail", "exit 1: a test failed or the run failed")
    else:
        _util.row("rule", "error", "exit %s: not a result the ladder names" % code)
    _util.row("log", log)
    return 0
