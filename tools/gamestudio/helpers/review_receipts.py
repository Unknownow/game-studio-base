"""Content-hash change detection for review skills (stamp files, compare against a receipt)."""
import hashlib
import os
import sys

HELP = """Usage:
  python tools/studio.py review-receipts hash <file> [<file>...]
      One stamp line per file: Reviewed-Content-Hash: <path> <hash>
      Paths use forward slashes. An absent literal path is left out with a note on stderr;
      a glob that matched nothing, or a file that cannot be hashed, exits 2.
  python tools/studio.py review-receipts check <receipt-file> [<file>...]
      RECEIPT: <receipt-file> (or RECEIPT: NONE), then per path (the files named, then every
      other path the receipt stamps):
        UNCHANGED / CHANGED / NEW / GONE: <path>, UNRESOLVED: <pattern> for an unexpanded glob.
      The LATEST stamp for a path wins. Observations only: the skill decides what they mean.
      An absent literal path the receipt never stamped is silent on purpose (an optional input).
  python tools/studio.py review-receipts sections-hash <file>
      Per `## ` section (plus __preamble__): Reviewed-Section-Hash: <path>#<heading> <hash>
  python tools/studio.py review-receipts sections-check <receipt-file> <file>
      SECTIONS: NONE (when no stamps), then SECTION-UNCHANGED / SECTION-CHANGED / SECTION-NEW per
      current section, then SECTION-REMOVED for stored sections that no longer exist.
Hashes are git blob hashes (the same as `git hash-object`)."""


def _blob(data):
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def _hash_file(path):
    try:
        with open(path, "rb") as fh:
            return _blob(fh.read())
    except OSError:
        return ""


def _norm(p):
    return p.replace("\\", "/")


def _is_glob(p):
    return any(c in p for c in "*?[")


def _spans(path):
    with open(path, "rb") as fh:
        lines = fh.read().split(b"\n")
    if lines and lines[-1] == b"":
        lines = lines[:-1]
    n = len(lines)
    spans = []
    pre, start, head, seen = True, 0, "", {}
    for i, l in enumerate(lines, 1):
        if l.startswith(b"## "):
            if pre and i > 1:
                spans.append((1, i - 1, "__preamble__"))
            pre = False
            if start:
                spans.append((start, i - 1, head))
            start = i
            head = l[3:].decode("utf-8", "replace").rstrip("\r")
            seen[head] = seen.get(head, 0) + 1
            if seen[head] > 1:
                head = "%s #%d" % (head, seen[head])
    if pre and n > 0:
        spans.append((1, n, "__preamble__"))
    if start:
        spans.append((start, n, head))
    return lines, spans


def _section_hash(lines, s, e):
    data = b"".join(l + b"\n" for l in lines[s - 1:e])
    return _blob(data)


def _latest(receipt_text, prefix):
    """Latest value stamped for key prefix 'Reviewed-...: <key> '."""
    val = None
    for line in receipt_text.split("\n"):
        line = line.rstrip("\r")
        if prefix in line:
            val = line.rsplit(" ", 1)[-1]
    return val


def _stamped_paths(text):
    out = []
    for line in text.split("\n"):
        line = line.rstrip("\r")
        k = "Reviewed-Content-Hash: "
        if k in line:
            rest = line.split(k, 1)[1]
            if " " in rest:
                p = rest.rsplit(" ", 1)[0]
                if p not in out:
                    out.append(p)
    return out


def main(root, argv):
    if not argv or argv[0] in ("-h", "--help"):
        if not argv:
            sys.stderr.write("review-receipts: no mode (hash, check, sections-hash, sections-check)\n")
            return 2
        print(HELP)
        return 0
    mode, args = argv[0], argv[1:]
    if mode == "hash":
        if not args:
            sys.stderr.write("review-receipts: hash mode needs at least one file\n")
            return 2
        rc = 0
        for f in args:
            if not os.path.isfile(f):
                if _is_glob(f):
                    sys.stderr.write("review-receipts: matched no file: %s\n" % f)
                    rc = 2
                else:
                    sys.stderr.write("review-receipts: not stamped, no such file: %s\n" % f)
                continue
            h = _hash_file(f)
            if not h:
                sys.stderr.write("review-receipts: could not hash: %s\n" % f)
                rc = 2
                continue
            print("Reviewed-Content-Hash: %s %s" % (_norm(f), h))
        return rc
    if mode == "check":
        if not args:
            sys.stderr.write("review-receipts: check mode needs a receipt file\n")
            return 2
        receipt, files = args[0], args[1:]
        if not os.path.isfile(receipt) or os.path.getsize(receipt) == 0:
            print("RECEIPT: NONE")
            for f in files:
                if not os.path.isfile(f):
                    if _is_glob(f):
                        print("UNRESOLVED: " + _norm(f))
                    continue
                print("NEW: " + _norm(f))
            return 0
        with open(receipt, "r", encoding="utf-8", errors="replace", newline="") as fh:
            text = fh.read()
        print("RECEIPT: " + _norm(receipt))
        stamped = _stamped_paths(text)
        reported = set()

        def compare(f, p):
            stored = _latest(text, "Reviewed-Content-Hash: %s " % p)
            if stored is None:
                print("NEW: " + p)
            elif _hash_file(f) == stored:
                print("UNCHANGED: " + p)
            else:
                print("CHANGED: " + p)

        for f in files:
            p = _norm(f)
            if not os.path.isfile(f):
                if _is_glob(f):
                    print("UNRESOLVED: " + p)
                elif p in stamped:
                    print("GONE: " + p)
                    reported.add(p)
                continue
            if p in reported:
                continue
            reported.add(p)
            compare(f, p)
        for p in stamped:
            if p in reported:
                continue
            reported.add(p)
            if os.path.isfile(p):
                compare(p, p)
            else:
                print("GONE: " + p)
        return 0
    if mode == "sections-hash":
        if not args or not os.path.isfile(args[0]):
            sys.stderr.write("review-receipts: sections-hash needs an existing file\n")
            return 2
        lines, spans = _spans(args[0])
        for s, e, h in spans:
            print("Reviewed-Section-Hash: %s#%s %s" % (_norm(args[0]), h, _section_hash(lines, s, e)))
        return 0
    if mode == "sections-check":
        if len(args) < 2 or not os.path.isfile(args[1]):
            sys.stderr.write("review-receipts: sections-check needs a receipt file and an existing file\n")
            return 2
        receipt, f = args[0], args[1]
        p = _norm(f)
        text = ""
        if os.path.isfile(receipt):
            with open(receipt, "r", encoding="utf-8", errors="replace", newline="") as fh:
                text = fh.read()
        stored = {}
        key = "Reviewed-Section-Hash: %s#" % p
        for line in text.split("\n"):
            line = line.rstrip("\r")
            if key in line:
                rest = line.split(key, 1)[1]
                if " " in rest:
                    h, v = rest.rsplit(" ", 1)
                    stored[h] = v
        lines, spans = _spans(f)
        if not stored:
            print("SECTIONS: NONE")
        current = []
        for s, e, h in spans:
            current.append(h)
            cur = _section_hash(lines, s, e)
            if h not in stored:
                print("SECTION-NEW: " + h)
            elif stored[h] == cur:
                print("SECTION-UNCHANGED: " + h)
            else:
                print("SECTION-CHANGED: " + h)
        for h in stored:
            if h not in current:
                print("SECTION-REMOVED: " + h)
        return 0
    sys.stderr.write("review-receipts: unknown mode %r (try --help)\n" % mode)
    return 2
