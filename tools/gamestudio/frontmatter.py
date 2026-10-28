"""Parse the small YAML subset used in skill, role and rule frontmatter."""
import re


class FrontmatterError(Exception):
    def __init__(self, line, message):
        Exception.__init__(self, message)
        self.line = line
        self.message = message


def split(text):
    """Return (frontmatter_lines, body, first_body_line) or (None, text, 1) when absent."""
    text = text.lstrip("\ufeff")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, text, 1
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return lines[1:i], "\n".join(lines[i + 1:]), i + 2
    raise FrontmatterError(1, "frontmatter is not closed with ---")


def _strip_comment(raw):
    out = []
    quote = None
    i = 0
    while i < len(raw):
        c = raw[i]
        if quote:
            out.append(c)
            if c == "\\" and quote == '"' and i + 1 < len(raw):
                out.append(raw[i + 1])
                i += 1
            elif c == quote:
                quote = None
        elif c in "\"'" and (i == 0 or raw[i - 1] in " [,:"):
            quote = c
            out.append(c)
        elif c == "#" and (i == 0 or raw[i - 1] in " \t"):
            break
        else:
            out.append(c)
        i += 1
    return "".join(out).strip()


def _unquote(tok, line):
    if tok.startswith('"'):
        if len(tok) < 2 or not tok.endswith('"'):
            raise FrontmatterError(line, "unterminated string")
        inner = tok[1:-1]
        return re.sub(r"\\(.)", lambda m: {"n": "\n", "t": "\t"}.get(m.group(1), m.group(1)), inner)
    if tok.startswith("'"):
        if len(tok) < 2 or not tok.endswith("'"):
            raise FrontmatterError(line, "unterminated string")
        return tok[1:-1]
    return tok


def _scalar(tok, line):
    tok = tok.strip()
    if tok[:1] in ("|", ">") or tok[:1] in ("&", "*", "!") or tok.startswith("{"):
        raise FrontmatterError(line, "unsupported YAML construct")
    if tok[:1] in "\"'":
        return _unquote(tok, line)
    if tok == "true":
        return True
    if tok == "false":
        return False
    return tok


def _split_list(inner, line):
    items = []
    cur = []
    quote = None
    i = 0
    while i < len(inner):
        c = inner[i]
        if quote:
            cur.append(c)
            if c == "\\" and quote == '"' and i + 1 < len(inner):
                cur.append(inner[i + 1])
                i += 1
            elif c == quote:
                quote = None
        elif c in "\"'":
            quote = c
            cur.append(c)
        elif c == ",":
            items.append("".join(cur))
            cur = []
        else:
            cur.append(c)
        i += 1
    if quote:
        raise FrontmatterError(line, "unterminated string")
    last = "".join(cur)
    if last.strip() or items:
        items.append(last)
    return [_scalar(x, line) for x in items if x.strip()]


def _value(raw, line):
    raw = _strip_comment(raw)
    if raw.startswith("["):
        if not raw.endswith("]"):
            raise FrontmatterError(line, "list is not closed on the same line")
        return _split_list(raw[1:-1], line)
    return _scalar(raw, line)


_KEY = re.compile(r"^(\s*)([A-Za-z0-9_.-]+):(?:\s+(.*)|\s*)$")


def parse_lines(fm_lines, first_line=2):
    """Parse frontmatter lines. Raises FrontmatterError with the file line number."""
    data = {}
    parent = None
    for offset, raw in enumerate(fm_lines):
        n = first_line + offset
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if "\t" in raw[: len(raw) - len(raw.lstrip())]:
            raise FrontmatterError(n, "tab indentation")
        m = _KEY.match(raw)
        if not m:
            raise FrontmatterError(n, "unsupported line")
        indent, key, rest = len(m.group(1)), m.group(2), m.group(3)
        if indent == 0:
            if rest is None or not _strip_comment(rest):
                data[key] = ""
                parent = key
            else:
                data[key] = _value(rest, n)
                parent = None
        else:
            if parent is None:
                raise FrontmatterError(n, "unexpected indentation")
            if not isinstance(data[parent], dict):
                data[parent] = {}
            if rest is None or not _strip_comment(rest):
                raise FrontmatterError(n, "only one nesting level is supported")
            data[parent][key] = _value(rest, n)
    return data


def parse(text):
    """Return (data or None, body). None means no frontmatter."""
    fm, body, first = split(text)
    if fm is None:
        return None, text
    return parse_lines(fm, 2), body
