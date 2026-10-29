"""The measurements /asset-audit takes by hand: names, PNG dimensions, sizes, audio sample rates."""
import os
import re
import shutil
import struct
import subprocess
import sys

from .. import config as cfgmod
from . import _util

HELP = """Usage: python tools/studio.py asset-scan [--root DIR] [--engine unity|none] [--category C]
         [--budget KEY=SIZE ...] [--max-dim N] [--sample-rates LIST] [--name-regex ERE] [--files]
The measurements /asset-audit takes by hand: asset names against the naming rule, PNG power-of-two
dimensions, file sizes against the budgets you pass, and audio sample rates where `file` reports one.
Observations, not a verdict. A check that did not run says so in a `check` row and its hits are `-`,
never 0: a scan that measured nothing is not a scan that found nothing.
  --engine E          unity or none (default: engine.name from project.toml; anything but unity uses
                      the neutral Assets/ layout)
  --category C        keep one category: in the neutral layout a folder of Assets/ (art, audio, vfx,
                      shaders or data); on unity the first folder under Assets/ (any case)
  --budget KEY=SIZE   a size budget in bytes, or with a K (1024) or M (1048576) suffix. KEY is `all`, a
                      type (texture, audio, data, other) or a file extension; the most specific wins:
                      extension, then type, then all. A key given twice is an error.
  --max-dim N         a texture whose width or height is above N pixels
  --sample-rates L    comma-separated Hz values audio may have (44100,48000)
  --name-regex ERE    the art bible's naming rule: replaces the built-in rule, and is the only rule on
                      unity; matched against the file name with its extension
  --files             one FILE row per scanned file
What is scanned: neutral layout: Assets/art, Assets/audio, Assets/vfx, Assets/shaders, Assets/data (other
folders are counted as outside_scope). Unity: Assets/, leaving out scripts (.cs, .asmdef) and .meta files.
.gitkeep placeholders are left out everywhere; each left-out kind is counted in an `excluded` row.
Naming (neutral layout): lowercase letters, digits and _ in the name, a-z 0-9 in the extension, one dot.
Textures: PNG width and height are read from the IHDR header. Orphans and missing assets are not checked:
this layout defines no reference syntax.
Output: TSV, in this order: engine, root, category_filter, scanned, outside_scope, excluded, category,
check rows, hits rows, then NAMING / POT / SIZE / DIM / RATE / NOTREAD / FILE rows in path order.
Exit codes: 0 scanned; 1 the root cannot be read; 2 usage error; 4 the asset root is absent. Reads only."""

TEXTURE = {"png", "jpg", "jpeg", "webp", "tga", "bmp", "exr", "hdr", "dds", "ktx", "ktx2"}
AUDIO = {"ogg", "wav", "mp3", "flac", "opus", "m4a", "aac", "aif", "aiff"}
DATA = {"json", "yaml", "yml"}
NEUTRAL_CATS = ["art", "audio", "vfx", "shaders", "data"]


def ftype(ext):
    if ext in TEXTURE:
        return "texture"
    if ext in AUDIO:
        return "audio"
    if ext in DATA:
        return "data"
    return "other"


def pot(n):
    if n < 1:
        return False
    while n > 1:
        if n % 2:
            return False
        n //= 2
    return True


def name_breaks(base):
    p = base.rfind(".")
    stem, ex = (base, "") if p < 0 else (base[:p], base[p + 1:])
    out = []

    def add(k):
        if k not in out:
            out.append(k)

    def cls(c):
        if c.isupper():
            return "uppercase"
        return {" ": "space", "-": "hyphen", ".": "dot"}.get(c, "other")
    for c in stem:
        if not re.match(r"[a-z0-9_]", c):
            add(cls(c))
    for c in ex:
        if not re.match(r"[a-z0-9]", c):
            add(cls(c))
    return ",".join(out)


def rate_of(desc):
    m = re.search(r"([0-9]+) Hz", desc)
    if m:
        return int(m.group(1))
    m = re.search(r"([0-9]+(?:\.[0-9]+)?) kHz", desc)
    if m:
        return int(float(m.group(1)) * 1000 + 0.5)
    return None


def png_dims(path):
    """(w, h) or a reason string."""
    try:
        with open(path, "rb") as fh:
            b = fh.read(24)
    except OSError:
        return "too short to hold a PNG header"
    if len(b) < 24:
        return "too short to hold a PNG header"
    if b[:8] != b"\x89PNG\r\n\x1a\n":
        return "no PNG signature"
    if b[12:16] != b"IHDR":
        return "no IHDR chunk after the signature"
    return struct.unpack(">II", b[16:24])


def parse_budget(spec, seen):
    if "=" not in spec:
        raise ValueError("--budget takes KEY=SIZE, got %s" % spec)
    k, v = spec.split("=", 1)
    if not k or not v:
        raise ValueError("--budget takes KEY=SIZE, got %s" % spec)
    if not re.match(r"^[A-Za-z0-9]+$", k):
        raise ValueError("--budget key must be letters and digits, got %s" % k)
    if not re.match(r"^[0-9]+[KkMm]?$", v):
        raise ValueError("--budget size is a number of bytes with an optional K or M, got %s" % v)
    n = int(re.sub(r"[KkMm]$", "", v))
    if v[-1] in "Kk":
        n *= 1024
    elif v[-1] in "Mm":
        n *= 1048576
    kl = k.lower()
    can = "all" if kl == "all" else ("type:" + kl if kl in ("texture", "audio", "data", "other") else "ext:" + kl)
    if can in seen:
        raise ValueError("--budget key %s given twice" % k)
    seen[can] = n
    return can


def main(root, argv):
    r, rest = _util.split_root(argv)
    if r:
        root = os.path.abspath(r)
    engine_arg, catf, budgets, bflags, maxdim, rates, namere, showfiles = "", "", {}, [], 0, "", "", False
    i = 0
    try:
        while i < len(rest):
            a = rest[i]
            if a in ("-h", "--help"):
                print(HELP)
                return 0
            if a == "--files":
                showfiles = True
                i += 1
                continue
            m = re.match(r"^(--[a-z-]+)=(.*)$", a)
            if m:
                flag, val, step = m.group(1), m.group(2), 1
            elif a in ("--engine", "--category", "--budget", "--max-dim", "--sample-rates", "--name-regex"):
                if i + 1 >= len(rest):
                    raise ValueError("%s needs a value" % a)
                flag, val, step = a, rest[i + 1], 2
            elif a.startswith("-"):
                raise ValueError("unknown argument: %s" % a)
            else:
                raise ValueError("unexpected argument: %s" % a)
            if flag == "--engine":
                engine_arg = val
            elif flag == "--category":
                catf = val.lower()
            elif flag == "--budget":
                parse_budget(val, budgets)
                bflags.append(val)
            elif flag == "--max-dim":
                if not re.match(r"^[0-9]+$", val):
                    raise ValueError("--max-dim takes a whole number of pixels")
                maxdim = int(val)
                if maxdim < 1:
                    raise ValueError("--max-dim takes a number above 0")
            elif flag == "--sample-rates":
                if not re.match(r"^[0-9]+(,[0-9]+)*$", val):
                    raise ValueError("--sample-rates takes comma-separated Hz values, got %s" % val)
                rates = val
            elif flag == "--name-regex":
                try:
                    re.compile(val)
                except re.error:
                    raise ValueError("--name-regex is not a valid regular expression: %s" % val)
                namere = val
            else:
                raise ValueError("unknown argument: %s" % flag)
            i += step
    except ValueError as e:
        sys.stderr.write("asset-scan: %s (try --help)\n" % e)
        return 2
    if not os.path.isdir(root):
        sys.stderr.write("asset-scan: cannot read root %s\n" % root)
        return 1
    if engine_arg:
        if engine_arg.lower() not in ("unity", "none"):
            sys.stderr.write("studio: engine %s is not supported; use unity or none\n" % engine_arg)
            return 2
        eng, esrc = engine_arg.lower(), "flag"
    else:
        cfg = cfgmod.load(root)
        val, src = cfg.get("engine.name")
        eng = "unity" if str(val or "").lower() == "unity" else "none"
        esrc = src if val else "default"
    if eng == "none" and catf and catf not in NEUTRAL_CATS:
        sys.stderr.write("asset-scan: --category takes art, audio, vfx, shaders or data, got %s (try --help)\n" % catf)
        return 2
    rootdir = "Assets"
    print("engine\t%s\t%s" % (eng, esrc))
    if rootdir not in os.listdir(root) or not os.path.isdir(os.path.join(root, rootdir)):
        print("root\t%s\tabsent" % rootdir)
        sys.stderr.write("asset-scan: %s/ does not exist; nothing was scanned\n" % rootdir)
        return 4
    print("root\t%s\tpresent" % rootdir)
    allf = []
    for dp, dn, fn in os.walk(os.path.join(root, rootdir)):
        for f in fn:
            allf.append(os.path.relpath(os.path.join(dp, f), root).replace(os.sep, "/"))
    allf.sort()
    excluded = {}
    kept, nout = [], 0
    for p in allf:
        parts = p.split("/")
        base = parts[-1]
        ext = base.rsplit(".", 1)[1].lower() if "." in base else ""
        reason = ""
        if base == ".gitkeep":
            reason = ".gitkeep"
        elif eng == "unity" and ext == "meta":
            reason = ".meta"
        elif eng == "unity" and ext == "cs":
            reason = ".cs"
        elif eng == "unity" and ext == "asmdef":
            reason = ".asmdef"
        if reason:
            excluded[reason] = excluded.get(reason, 0) + 1
            continue
        if eng == "none":
            s = parts[1] if len(parts) > 1 else ""
            if len(parts) < 3 or s not in NEUTRAL_CATS:
                nout += 1
                continue
            cat = s
        else:
            cat = parts[1] if len(parts) >= 3 else "-"
        if catf and cat.lower() != catf:
            continue
        kept.append((p, cat, base, ext))
    if catf:
        print("category_filter\t%s" % catf)
    print("scanned\t%d" % len(kept))
    if eng == "none":
        print("outside_scope\t%d\tfiles under Assets/ outside art, audio, vfx, shaders and data" % nout)
    for k in ([".gitkeep"] if eng == "none" else [".meta", ".cs", ".asmdef", ".gitkeep"]):
        print("excluded\t%s\t%d" % (k, excluded.get(k, 0)))
    catn = {}
    for _, cat, _, _ in kept:
        catn[cat] = catn.get(cat, 0) + 1
    for c in (NEUTRAL_CATS if eng == "none" else sorted(catn)):
        print("category\t%s\t%d" % (c, catn.get(c, 0)))
    nart = catn.get("art", 0)
    naud = catn.get("audio", 0)
    nodata = "no assets under %s" % rootdir if not kept else ""
    havefile = shutil.which("file") is not None
    hasb = bool(budgets)
    nra = len(rates.split(",")) if rates else 0
    allowed = {int(x) for x in rates.split(",")} if rates else set()
    if nodata:
        naming = ("not_run", nodata)
    elif namere:
        naming = ("ran", "name_regex " + namere)
    elif eng == "none":
        naming = ("ran", "lowercase_underscore")
    else:
        naming = ("not_run", "no naming rule for %s; pass the art bible's rule with --name-regex" % eng)
    potc = ("not_run", nodata) if nodata else ("ran", "PNG width and height from the IHDR bytes")
    if nodata:
        sizec = ("not_run", nodata)
    elif not hasb:
        sizec = ("not_run", "no --budget flag given")
    else:
        sizec = ("ran", " ".join(bflags))
    if nodata:
        dimc = ("not_run", nodata)
    elif not maxdim:
        dimc = ("not_run", "no --max-dim flag given")
    else:
        dimc = ("ran", "--max-dim %d" % maxdim)
    if nodata:
        ratec = ("not_run", nodata)
    elif not havefile:
        ratec = ("not_run", "file is not installed")
    else:
        ratec = ("ran", "file -b; allowed " + rates if nra else "file -b; no --sample-rates flag given, none compared")
    print("check\tnaming\t%s\t%s" % naming)
    if eng == "none":
        if nodata:
            print("check\tart_pattern\tnot_run\t%s\ncheck\taudio_pattern\tnot_run\t%s" % (nodata, nodata))
        else:
            print("check\tart_pattern\tnot_checkable\t%d files under Assets/art; the category and size values are not defined and the examples disagree" % nart)
            print("check\taudio_pattern\tnot_checkable\t%d files under Assets/audio; the category values are not defined and the name may hold any number of words" % naud)
    print("check\tpot\t%s\t%s" % potc)
    print("check\tsize\t%s\t%s" % sizec)
    print("check\tdim\t%s\t%s" % dimc)
    print("check\trate\t%s\t%s" % ratec)
    why = "no reference syntax is defined for this layout"
    print("check\torphans\tnot_run\t" + (nodata or why))
    print("check\tmissing\tnot_run\t" + (nodata or why))
    print("check\tdata\tnot_run\tJSON and YAML validity and schemas are not checked here")
    print("check\tformat\tnot_run\tfile formats are not checked here: the skill does not say how to tell a UI or 3D texture")
    print("check\tlast_modified\tnot_run\tnot read: file times are not stable across clones")
    rn, rp, rs, rd, rr, rnot, rf = [], [], [], [], [], [], []
    for p, cat, base, ext in kept:
        ty = ftype(ext)
        full = os.path.join(root, p)
        try:
            by = os.path.getsize(full)
        except OSError:
            by = -1
        dims, rate = "-", "-"
        if naming[0] == "ran":
            if namere:
                if not re.search(namere, base):
                    rn.append("NAMING\t%s\tname_regex\tdoes not match %s" % (p, namere))
            else:
                c = name_breaks(base)
                if c:
                    rn.append("NAMING\t%s\tlowercase_underscore\t%s" % (p, c))
        if ty == "texture":
            if ext != "png":
                rnot.append("NOTREAD\t%s\tdims\tonly PNG headers are read, not %s" % (p, ext))
            else:
                d = png_dims(full)
                if isinstance(d, str):
                    rnot.append("NOTREAD\t%s\tdims\t%s" % (p, d))
                else:
                    w, h = d
                    dims = "%dx%d" % (w, h)
                    if not pot(w) or not pot(h):
                        rp.append("POT\t%s\t%s\t%s" % (p, dims, "both" if not pot(w) and not pot(h) else ("width" if not pot(w) else "height")))
                    if maxdim and (w > maxdim or h > maxdim):
                        rd.append("DIM\t%s\t%s\t%d" % (p, dims, maxdim))
        if ty == "audio":
            if not havefile:
                rnot.append("NOTREAD\t%s\trate\tfile is not installed" % p)
            else:
                try:
                    desc = subprocess.run(["file", "-b", full], capture_output=True, text=True, errors="replace").stdout
                except OSError:
                    desc = ""
                rt = rate_of(desc)
                if rt is None:
                    rnot.append("NOTREAD\t%s\trate\tfile reports no sample rate" % p)
                else:
                    rate = str(rt)
                    if nra and rt not in allowed:
                        rr.append("RATE\t%s\t%d\t%s" % (p, rt, rates))
        if hasb and by >= 0:
            key = ""
            if "ext:" + ext in budgets:
                key = "ext:" + ext
            elif "type:" + ty in budgets:
                key = "type:" + ty
            elif "all" in budgets:
                key = "all"
            if key and by > budgets[key]:
                rs.append("SIZE\t%s\t%d\t%d\t%d\t%s" % (p, by, budgets[key], by - budgets[key], key))
        if showfiles:
            rf.append("FILE\t%s\t%s\t%s\t%s\t%s\t%s" % (p, cat, ty, by if by >= 0 else "-", dims, rate))
    print("hits\tnaming\t%s" % (len(rn) if naming[0] == "ran" else "-"))
    print("hits\tpot\t%s" % (len(rp) if potc[0] == "ran" else "-"))
    print("hits\tsize\t%s" % (len(rs) if sizec[0] == "ran" else "-"))
    print("hits\tdim\t%s" % (len(rd) if dimc[0] == "ran" else "-"))
    print("hits\trate\t%s" % (len(rr) if ratec[0] == "ran" and nra else "-"))
    print("hits\tnotread\t%s" % (len(rnot) if potc[0] == "ran" or ratec[0] == "ran" else "-"))
    print("hits\torphan\t-")
    print("hits\tmissing\t-")
    for group in (rn, rp, rs, rd, rr, rnot, rf):
        for ln in group:
            print(ln)
    return 0
