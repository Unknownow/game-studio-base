"""Observations about the roles and about every place a skill hands work to one."""
import os
import re
import sys
from itertools import combinations

from .. import frontmatter as fmmod
from . import _util

HELP = """Usage: python tools/studio.py agent-check [--agent <name>] [--skill <name>] [--root DIR]
Observations about the roles in roles/ and about every place a skill hands work to one. /skill-test reads
roles and skills as text and judges them; this finds the mechanical part: frontmatter that does not parse,
two descriptions close enough that the wrong role gets picked, a role body that tells it to ask the user, a
`can:` list the body contradicts. OBSERVATIONS, NEVER VERDICTS: it prints what it found, with denominators
first, and exits 0 once it has run.
  --agent <name>  one role: its block, the overlap pairs it is in, and the delegation blocks that name it
  --skill <name>  one skill: its delegation blocks only
Output:
  ROOT: <path>
  AGENTS: <n>  SKILLS: <n>  SKILL_FILES: <n>  DELEGATION_BLOCKS: <n>
  AGENT: <name> frontmatter=<ok|missing|unclosed|bad> tier=<v|unset> memory=<v|unset>
    description: <text>
    can: <list | unset>   skills: <list>
    NOTE: <kind> <detail>                  one line per observation
  OVERLAP: <a> <b> jaccard=<x> shared=<words>   (threshold printed first)
  DELEGATION: <skill> <file>:<line> "<heading>" agents=<names> lines=<n>
    markers: objective=<n> output=<n> sources=<n> boundaries=<n> recheck=<n>
NOTE kinds:
  frontmatter     frontmatter that does not parse; name missing or not the file name; no description
  preload-missing `skills:` lists a skill that does not exist, or one that sets disable-model-invocation
  asks-user       a body line that tells the role to ask the user or wait for approval; a role's questions
                  must come back in its report
  can-mismatch    `can:` lacks shell but the body names shell commands
  no-delegations  printed under DELEGATION when no block was found, so "none found" is never silent
Exit codes: 0 done; 1 no roles folder. Reads only."""

OVERLAP_THRESHOLD = 0.12
COMMON_SHARE = 0.25
STOPWORDS = set("""
about after also among and any are been before being between both but can could each
for from has have how into its like more most must not off one only other over own same
should such than that the their them then there these they this those through under use
used uses using via what when where which while who will with within without your
""".split())

ASKS_USER = re.compile(
    r"\bask(?:ing)? (?:the )?user\b"
    r"|\bask(?:ing)? (?:the user |them )?(?:clarifying |architecture |design |follow-up )?questions?\b"
    r"|\bMay I (?:write|create|edit|save|update|proceed|delete)\b"
    r"|\bwait(?:ing)? for (?:the user|approval|confirmation|their)\b"
    r"|\b(?:get|seek|obtain|request) (?:user |explicit )?(?:approval|sign-off|confirmation)\b"
    r"|\bconfirm with the user\b",
    re.IGNORECASE)
NO_TOOL = re.compile(r"\bno question tool\b|\bcannot ask the user\b|\bwhoever called you\b|\bdelegated role\b", re.I)
SHELL = re.compile(r"```(?:bash|sh|shell)\b|`(?:git|npm|bash|make|python|pytest|dotnet|cargo) [^`]+`")
CUE = re.compile(r"\bact as\b|\bhand (?:it|this|them|each|the [\w-]+) (?:\w+ )?to\b|\bdelegat|\bbrief\b|roles/[\w-]+\.md", re.I)
MARKERS = {
    "objective": re.compile(r"\bask (?:them|it|each)\b|\bto (?:review|check|write|design|draft|produce|validate|assess|evaluate|audit|analy[sz]e|create|implement|identify|find)\b|\bgoal\b|\bobjective\b", re.I),
    "output": re.compile(r"\breturn\b|\boutput\b|\breport\b|\bformat\b|\bwrite (?:your|the|its) [\w ]{0,20}to\b", re.I),
    "sources": re.compile(r"`[\w.-]+/[\w./*-]+`|\bread\b|\bpass\b|\binputs?\b|\bsources?\b", re.I),
    "boundaries": re.compile(r"\bdo not\b|\bdon't\b|\bnever\b|\bonly\b|\bmust not\b", re.I),
    "recheck": re.compile(r"\bre-?check|\bre-?verify|\bdouble-check|\bsecond opinion\b|\bverify (?:your|the|its) own\b", re.I),
}


def words(text):
    return {w for w in re.findall(r"[a-z]{4,}", text.lower()) if w not in STOPWORDS}


def listed(v):
    if isinstance(v, list):
        return [str(x) for x in v]
    return [str(v)] if v not in (None, "") else []


def main(root, argv):
    r, rest = _util.split_root(argv)
    if r:
        root = os.path.abspath(r)
    agent_filter = skill_filter = ""
    i = 0
    while i < len(rest):
        a = rest[i]
        if a in ("-h", "--help"):
            print(HELP)
            return 0
        if a in ("--agent", "--skill"):
            if i + 1 >= len(rest):
                sys.stderr.write("agent-check: %s needs a value\n" % a)
                return 2
            if a == "--agent":
                agent_filter = rest[i + 1]
            else:
                skill_filter = rest[i + 1]
            i += 2
            continue
        if a.startswith("--agent="):
            agent_filter = a[8:]
        elif a.startswith("--skill="):
            skill_filter = a[8:]
        else:
            root = os.path.abspath(a)
        i += 1
    role_dir = os.path.join(root, "roles")
    skill_dir = os.path.join(root, ".agents", "skills")
    if not os.path.isdir(role_dir):
        sys.stderr.write("agent-check: no roles folder under %s\n" % root)
        return 1
    agents = {n[:-3]: os.path.join(role_dir, n) for n in sorted(os.listdir(role_dir)) if n.endswith(".md") and n != "README.md"}
    skills, skill_files = {}, []
    if os.path.isdir(skill_dir):
        for d in sorted(os.listdir(skill_dir)):
            if os.path.isfile(os.path.join(skill_dir, d, "SKILL.md")):
                skills[d] = os.path.join(skill_dir, d)
        for name, d in skills.items():
            for dp, _, files in os.walk(d):
                for f in sorted(files):
                    if f.endswith(".md"):
                        skill_files.append((name, os.path.join(dp, f)))

    def disabled(skill):
        d = skills.get(skill)
        if not d:
            return None
        try:
            data, _ = fmmod.parse(_util.read(os.path.join(d, "SKILL.md")))
        except fmmod.FrontmatterError:
            return False
        return bool(data and data.get("disable-model-invocation") in (True, "true"))

    records = {}
    for name, path in agents.items():
        text = _util.read(path)
        rec = {"status": "ok", "fm": {}, "notes": []}
        body_start = 0
        try:
            fl, _, first = fmmod.split(text)
            if fl is None:
                rec["status"] = "missing"
                rec["notes"].append("frontmatter no frontmatter block")
            else:
                body_start = first - 1
                try:
                    rec["fm"] = fmmod.parse_lines(fl, 2)
                except fmmod.FrontmatterError as e:
                    rec["status"] = "bad"
                    rec["notes"].append("frontmatter line %d: %s" % (e.line, e.message))
        except fmmod.FrontmatterError:
            rec["status"] = "unclosed"
            rec["notes"].append("frontmatter never closes with ---")
        fm = rec["fm"]
        if rec["status"] == "ok":
            if "name" not in fm:
                rec["notes"].append("frontmatter name missing")
            elif str(fm["name"]) != name:
                rec["notes"].append("frontmatter name %s is not the file name %s" % (fm["name"], name))
            if not str(fm.get("description", "")).strip():
                rec["notes"].append("frontmatter description missing or empty")
            for sk in listed(fm.get("skills")):
                off = disabled(sk)
                if off is None:
                    rec["notes"].append("preload-missing skills: lists %s, which is not a skill in .agents/skills/" % sk)
                elif off:
                    rec["notes"].append("preload-missing skills: lists %s, which sets disable-model-invocation: true" % sk)
        body = text.splitlines()[body_start:]
        can = listed(fm.get("can"))
        shell_seen = False
        for n, line in enumerate(body, start=body_start + 1):
            if ASKS_USER.search(line) and not NO_TOOL.search(line):
                rec["notes"].append("asks-user line %d: %s" % (n, line.strip()[:120]))
            if not shell_seen and rec["status"] == "ok" and can and "shell" not in can and SHELL.search(line):
                shell_seen = True
                rec["notes"].append("can-mismatch can: lacks shell but line %d names a shell command: %s" % (n, line.strip()[:100]))
        records[name] = rec

    desc_words = {n: words(str(r["fm"].get("description", ""))) for n, r in records.items()}
    df = {}
    for ws in desc_words.values():
        for w in ws:
            df[w] = df.get(w, 0) + 1
    limit = max(2, int(len(desc_words) * COMMON_SHARE))
    common = {w for w, c in df.items() if c > limit}
    distinct = {n: ws - common for n, ws in desc_words.items()}
    pairs = []
    for a, b in combinations(sorted(distinct), 2):
        union = distinct[a] | distinct[b]
        if not union:
            continue
        j = len(distinct[a] & distinct[b]) / len(union)
        if j >= OVERLAP_THRESHOLD:
            pairs.append((j, a, b, sorted(distinct[a] & distinct[b])))
    pairs.sort(key=lambda p: (-p[0], p[1], p[2]))

    weak = {n for n in agents if "-" not in n}

    def names_in(text):
        found = []
        for n in agents:
            if n in weak:
                pat = r"(?:`%s`|\*\*%s\*\*|roles/%s\.md)" % ((re.escape(n),) * 3)
            else:
                pat = r"(?<![\w-])%s(?![\w-])" % re.escape(n)
            if re.search(pat, text):
                found.append(n)
        return found

    blocks = []
    for sname, path in skill_files:
        lines = _util.read(path).splitlines()
        fenced, inside = [], False
        for l in lines:
            if l.lstrip().startswith("```"):
                inside = not inside
                fenced.append(True)
            else:
                fenced.append(inside)
        starts = [i for i, l in enumerate(lines) if not fenced[i] and re.match(r"^#{1,6}\s", l)] or [0]
        if starts[0] != 0:
            starts.insert(0, 0)
        for k, s in enumerate(starts):
            e = starts[k + 1] if k + 1 < len(starts) else len(lines)
            chunk = "\n".join(lines[s:e])
            prose = "\n".join(l for i, l in enumerate(lines[s:e], start=s) if not fenced[i])
            if not CUE.search(prose):
                continue
            named = names_in(prose)
            if not named:
                continue
            heading = lines[s].lstrip("#").strip() if re.match(r"^#{1,6}\s", lines[s]) else "(top of file)"
            marks = {k2: len(rx.findall(chunk)) for k2, rx in MARKERS.items()}
            rel = os.path.relpath(path, root).replace(os.sep, "/")
            blocks.append((sname, rel, s + 1, heading[:70], named, e - s, marks))

    show_agents = sorted(agents) if not agent_filter else [agent_filter]
    if skill_filter:
        show_agents = []
    show_blocks = [b for b in blocks if (not skill_filter or b[0] == skill_filter) and (not agent_filter or agent_filter in b[4])]
    print("ROOT: %s" % root)
    print("AGENTS: %d  SKILLS: %d  SKILL_FILES: %d  DELEGATION_BLOCKS: %d" % (len(agents), len(skills), len(skill_files), len(blocks)))
    if agent_filter and agent_filter not in agents:
        print("NOT FOUND: agent %s is not a file in roles/" % agent_filter)
        show_agents = []
    if skill_filter and skill_filter not in skills:
        print("NOT FOUND: skill %s is not a folder in .agents/skills/" % skill_filter)
    for name in show_agents:
        rec = records[name]
        fm = rec["fm"]
        print("AGENT: %s frontmatter=%s tier=%s memory=%s" % (name, rec["status"], fm.get("tier") or "unset",
                                                              str(fm.get("memory")).lower() if "memory" in fm else "unset"))
        print("  description: %s" % (str(fm.get("description", "")) or "(none)"))
        can = listed(fm.get("can"))
        print("  can: %s   skills: %s" % (", ".join(can) if can else "unset", ", ".join(listed(fm.get("skills"))) or "none"))
        for note in rec["notes"]:
            print("  NOTE: %s" % note)
    if not skill_filter:
        print("OVERLAP_THRESHOLD: jaccard >= %.2f over description words in at most %d of %d descriptions"
              % (OVERLAP_THRESHOLD, limit, len(desc_words)))
        shown = [p for p in pairs if not agent_filter or agent_filter in (p[1], p[2])]
        for j, a, b, shared in shown:
            print("OVERLAP: %s %s jaccard=%.2f shared=%s" % (a, b, j, ",".join(shared)))
        if not shown:
            print("OVERLAP: none at or above the threshold")
    for sname, rel, line, heading, named, n, marks in show_blocks:
        print('DELEGATION: %s %s:%d "%s" agents=%s lines=%d' % (sname, rel, line, heading, ",".join(named), n))
        print("  markers: " + " ".join("%s=%d" % kv for kv in marks.items()))
    if not show_blocks and (skill_filter or not agent_filter or agent_filter in agents):
        print("DELEGATION: no-delegations found in the files read")
    return 0
