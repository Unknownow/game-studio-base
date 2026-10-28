"""Edit one scalar in a TOML file in place, keeping comments and order."""
import re

_SIMPLE = re.compile(r"^(\"(?:[^\"\\]|\\.)*\"|'[^']*'|[^#\s]+)\s*(#.*)?$")


class TomlEditError(Exception):
    pass


def format_value(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return '"' + escaped + '"'
    raise TomlEditError("edit project.toml by hand: only scalar values can be written")


def _header(table):
    return re.compile(r"^\s*\[\s*" + re.escape(table) + r"\s*\]\s*(#.*)?$")


_ANY_HEADER = re.compile(r"^\s*\[")


def set_value(text, path, value):
    """Return text with `path` ("table.key" or "a.b.key") set to the scalar `value`."""
    rendered = format_value(value)
    parts = path.split(".")
    key = parts[-1]
    table = ".".join(parts[:-1])
    nl = "\r\n" if "\r\n" in text else "\n"
    lines = text.split(nl) if text else []
    if table:
        start = None
        for i, line in enumerate(lines):
            if _header(table).match(line):
                start = i + 1
                break
        if start is None:
            body = list(lines)
            while body and body[-1].strip() == "":
                body.pop()
            if body:
                body.append("")
            body.append("[" + table + "]")
            body.append(key + " = " + rendered)
            return nl.join(body) + nl
    else:
        start = 0
    end = len(lines)
    for i in range(start, len(lines)):
        if _ANY_HEADER.match(lines[i]):
            end = i
            break
    key_re = re.compile(r"^(\s*" + re.escape(key) + r"\s*=\s*)(.*)$")
    for i in range(start, end):
        m = key_re.match(lines[i])
        if m:
            rest = m.group(2)
            sm = _SIMPLE.match(rest)
            if not sm or rest.startswith(("[", "{", '"""', "'''")):
                raise TomlEditError("edit project.toml by hand: `" + path + "` is not a simple scalar")
            comment = sm.group(2)
            lines[i] = m.group(1) + rendered + ("  " + comment if comment else "")
            return nl.join(lines)
    insert_at = end
    while insert_at > start and lines[insert_at - 1].strip() == "":
        insert_at -= 1
    lines.insert(insert_at, key + " = " + rendered)
    out = nl.join(lines)
    if not out.endswith(nl):
        out += nl
    return out
