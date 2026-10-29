"""The facts a static skill check reads off a skill by eye: frontmatter keys, phases, verdicts, hooks."""
import os
import re
import sys

from .. import frontmatter as fm
from . import _util

HELP = """Usage: python tools/studio.py skill-lint <name>|all [--root DIR]
The facts a static skill check reads off a skill by eye: which frontmatter keys are there, how many phase
headings, which verdict words, whether it asks before writing, how it ends, whether its engine hook lines
are well formed, and what its argument hint says. Checks 1-7 of /skill-test static.
OBSERVATIONS, NEVER VERDICTS: nothing here is a PASS, WARN or FAIL. The one verdict the skill reports
(COMPLIANT, WARNINGS, NON-COMPLIANT, NOT ASSESSED) stays with /skill-test.
  <name>      one skill, the folder name under .agents/skills/
  all         every folder under .agents/skills/
Output: TSV. First `skills <n> .agents/skills`, then for each skill
  skill   <name>  files=<SKILL.md + references read>  lines=<n>
  check1  <name>  frontmatter=<ok|missing|unclosed|bad@LINE>  missing=<list|->  unknown=<list|->  name=<match|mismatch:<v>|absent>
  check2  <name>  phases=<distinct numbered phase headings>  h2=<distinct ## headings>  h2_total=<all of them>
  check3  <name>  verdicts=<WORD:count,...|->  assessment_words=<in the description|->
  check4  <name>  may_i_write=<n>  before_writing=<n>  approval=<n>  ask_write_lines=<n>  writes=<lines naming write, edit or create>
  check5  <name>  last_section=<heading|->  skills_named=<in that section|->  next_phrases=<whole skill>/<last section>
  check6  <name>  hooks=<engine hook lines>  malformed=<n>
  check7  <name>  hint=<text|empty|absent>  args_section=<first Arguments/Parse heading@line|->
and last `checked <N> of <M>`. A folder with no SKILL.md prints `NOT_READ <name> <reason>` and is not counted
as read. Allowed top-level keys: name, description, license, compatibility, metadata,
disable-model-invocation; the hint is `metadata.argument-hint`. A numbered phase is `## Phase N...` or `## N.`.
Exit codes: 0 done; 1 cannot read the root or find .agents/skills; 2 usage error; 3 no such skill. Reads only."""

ALLOWED = {"name", "description", "license", "compatibility", "metadata", "disable-model-invocation"}
VERDICTS = ("PASS FAIL CONCERNS APPROVED BLOCKED COMPLETE READY COMPLIANT NON-COMPLIANT PROCEED PIVOT KILL GO NO-GO "
            "CRITICAL HIGH MEDIUM LOW").split()
ASSESS = "review audit check gate ready readiness validate assess".split()
HOOK_LINE = re.compile(r"Engine step `hook:\s*([^`]*)`")
HOOK_ID = re.compile(r"^[a-z0-9-]+/[a-z0-9-]+$")


def cnt(s, w):
    return len(re.findall(r"(?<![A-Za-z0-9_-])" + re.escape(w) + r"(?![A-Za-z0-9_-])", s))


def occ(s, p):
    return s.count(p)


def lint_skill(skill_dir, names):
    """Return the facts for one skill as a dict, or {"error": reason} when SKILL.md cannot be read."""
    path = os.path.join(skill_dir, "SKILL.md")
    if not os.path.isfile(path):
        return {"error": "no SKILL.md"}
    files = [path]
    refs = os.path.join(skill_dir, "references")
    if os.path.isdir(refs):
        files += [os.path.join(refs, n) for n in sorted(os.listdir(refs)) if n.endswith(".md") and os.path.isfile(os.path.join(refs, n))]
    f = {"files": 0, "lines": 0, "state": "missing", "data": {}, "h2seen": set(), "phseen": set(), "h2total": 0,
         "vcount": {}, "may": 0, "bef": 0, "apr": 0, "askw": 0, "writes": 0, "nextall": 0, "nextlast": 0, "lastsec": "",
         "lastskills": "", "argsh": "", "argsat": 0, "hooks": 0, "malformed": 0}
    for pth in files:
        try:
            text = _util.read(pth)
        except OSError:
            return {"error": "cannot read " + pth}
        is_skill = pth == path
        lines = text.split("\n")
        if lines and lines[-1] == "":
            lines.pop()
        f["files"] += 1
        f["lines"] += len(lines)
        body_start = 0
        if is_skill:
            try:
                fl, _, first = fm.split(text)
                if fl is None:
                    f["state"] = "missing"
                else:
                    f["state"] = "ok"
                    try:
                        f["data"] = fm.parse_lines(fl, 2)
                    except fm.FrontmatterError as e:
                        f["state"] = "bad@%d" % e.line
                    body_start = first - 1
            except fm.FrontmatterError:
                f["state"] = "unclosed"
        infence = False
        nextsec = 0
        secskills = ""
        for n, l in enumerate(lines):
            l = l.rstrip("\r")
            for w in VERDICTS:
                if re.search(r"[A-Z][A-Z]", l):
                    f["vcount"][w] = f["vcount"].get(w, 0) + cnt(l, w)
            if is_skill and n < body_start:
                continue
            if re.match(r"^[ \t]*(```|~~~)", l):
                infence = not infence
            ll = l.lower()
            f["may"] += occ(ll, "may i write")
            f["bef"] += occ(ll, "before writing")
            f["apr"] += occ(ll, "approval")
            if re.search(r"(^|[^a-z])ask", ll) and re.search(r"(^|[^a-z])writ", ll):
                f["askw"] += 1
            if re.search(r"(^|[^a-z])(write|edit|create)([^a-z]|$)", ll):
                f["writes"] += 1
            p = sum(occ(ll, x) for x in ("next step", "recommended next", "follow-up", "follow up", "after this"))
            f["nextall"] += p
            if is_skill:
                nextsec += p
            for m in HOOK_LINE.finditer(l):
                f["hooks"] += 1
                hid = m.group(1).strip()
                if not HOOK_ID.match(hid) or ("## hook: " + hid) not in l:
                    f["malformed"] += 1
            if not infence and l.startswith("## "):
                h = l[3:].strip()
                f["h2total"] += 1
                f["h2seen"].add(h)
                if re.match(r"^Phase [0-9]", h) or re.match(r"^[0-9]+\.", h):
                    f["phseen"].add(h)
                if is_skill:
                    f["lastsec"], nextsec, secskills = h, p, ""
                    if not f["argsh"] and re.search(r"(Argument|argument|Parse)", h):
                        f["argsh"], f["argsat"] = h, n + 1
            if is_skill and f["lastsec"]:
                for m in re.finditer(r"(?<![A-Za-z0-9_/.~-])/([a-z][a-z0-9-]*)", l):
                    nm = m.group(1)
                    if nm in names and nm not in secskills.split(","):
                        secskills = (secskills + "," if secskills else "") + nm
                f["lastskills"], f["nextlast"] = secskills, nextsec
    return f


def rows_for(name, f):
    d = f["data"]
    meta = d.get("metadata") if isinstance(d.get("metadata"), dict) else {}
    desc = str(d.get("description", "")).lower()
    miss = [k for k in ("name", "description") if k not in d]
    unknown = [k for k in d if k not in ALLOWED]
    if "name" not in d:
        nm = "absent"
    elif str(d["name"]) == name:
        nm = "match"
    else:
        nm = "mismatch:" + str(d["name"])
    vs = ",".join("%s:%d" % (w, f["vcount"][w]) for w in VERDICTS if f["vcount"].get(w))
    aw = ",".join(w for w in ASSESS if cnt(desc, w))
    if "argument-hint" not in meta:
        hint = "absent"
    else:
        hint = str(meta["argument-hint"]).strip() or "empty"
    out = [("skill", name, "files=%d" % f["files"], "lines=%d" % f["lines"]),
           ("check1", name, "frontmatter=" + f["state"], "missing=" + (",".join(miss) or "-"),
            "unknown=" + (",".join(unknown) or "-"), "name=" + nm),
           ("check2", name, "phases=%d" % len(f["phseen"]), "h2=%d" % len(f["h2seen"]), "h2_total=%d" % f["h2total"]),
           ("check3", name, "verdicts=" + (vs or "-"), "assessment_words=" + (aw or "-")),
           ("check4", name, "may_i_write=%d" % f["may"], "before_writing=%d" % f["bef"], "approval=%d" % f["apr"],
            "ask_write_lines=%d" % f["askw"], "writes=%d" % f["writes"]),
           ("check5", name, "last_section=" + (f["lastsec"] or "-"), "skills_named=" + (f["lastskills"] or "-"),
            "next_phrases=%d/%d" % (f["nextall"], f["nextlast"])),
           ("check6", name, "hooks=%d" % f["hooks"], "malformed=%d" % f["malformed"]),
           ("check7", name, "hint=" + hint, "args_section=" + ("%s@%d" % (f["argsh"], f["argsat"]) if f["argsh"] else "-"))]
    return out


def advice(root, name):
    """(rule, message) pairs `check` shows as advice for one skill; never blocking."""
    base = os.path.join(root, ".agents", "skills")
    names = set(os.listdir(base)) if os.path.isdir(base) else set()
    f = lint_skill(os.path.join(base, name), names)
    if "error" in f:
        return []
    out = []
    steps = bool(re.search(r"^\s*1\.\s", _util.read(os.path.join(base, name, "SKILL.md")), re.M))
    if not steps and len(f["phseen"]) < 2:
        out.append(("no_steps", "no numbered steps or phase headings found"))
    if f["writes"] and not (f["may"] or f["bef"] or f["apr"] or f["askw"]):
        out.append(("no_ask_before_write", "writes files but has no ask-before-write language"))
    if not f["nextall"]:
        out.append(("no_next_step", "no next-step hand-off found"))
    if f["malformed"]:
        out.append(("bad_hook", "%d malformed engine hook line(s)" % f["malformed"]))
    return out


def main(root, argv):
    r, rest = _util.split_root(argv)
    if r:
        root = os.path.abspath(r)
    which = ""
    for a in rest:
        if a in ("-h", "--help"):
            print(HELP)
            return 0
        if a.startswith("-") and len(a) > 1:
            return _util.usage_error("skill-lint", "unknown argument: %s" % a)
        if which:
            return _util.usage_error("skill-lint", "one skill name or all")
        which = a
    if not which:
        return _util.usage_error("skill-lint", "no skill name given")
    if "/" in which or "\\" in which or which.startswith("."):
        return _util.usage_error("skill-lint", "'%s' is not a skill folder name" % which)
    if not os.path.isdir(root):
        sys.stderr.write("skill-lint: cannot read root %s\n" % root)
        return 1
    base = os.path.join(root, ".agents", "skills")
    if not os.path.isdir(base):
        sys.stderr.write("skill-lint: no .agents/skills folder under %s\n" % root)
        return 1
    names = sorted(n for n in os.listdir(base) if os.path.isdir(os.path.join(base, n)))
    if which == "all":
        todo = names
    else:
        if which not in names:
            sys.stderr.write("skill-lint: no skill folder .agents/skills/%s\n" % which)
            return 3
        todo = [which]
    print("skills\t%d\t.agents/skills" % len(todo))
    read = 0
    nameset = set(names)
    for n in todo:
        f = lint_skill(os.path.join(base, n), nameset)
        if "error" in f:
            print("NOT_READ\t%s\t%s" % (n, f["error"]))
            continue
        read += 1
        for row in rows_for(n, f):
            print("\t".join(row))
    print("checked\t%d of %d" % (read, len(todo)))
    return 0
