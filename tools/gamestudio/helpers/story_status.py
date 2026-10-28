"""The story files' Status lines, in the order the minimal route takes them."""
import re

from . import _util

HELP = """Usage: python tools/studio.py story-status
One line per unfinished story, file-name (build) order within a group:
  IN_REVIEW    <path>
  IN_PROGRESS  <path>
  TODO         <path>  (Ready | Not Started)
  BLOCKED      <path>  (<status as written>)
  OTHER        <path>  (<status as written>)
  NO_STATUS    <path>
  COMPLETE     <done> of <total>
or STORIES      none when there are no story files. Observations only: no line says "next"."""


def main(root, argv):
    if argv and argv[0] in ("-h", "--help"):
        print(HELP)
        return 0
    files = _util.story_files(root)
    if not files:
        print("STORIES      none")
        return 0
    rev, prog, todo, blk, other = [], [], [], [], []
    done = 0
    import os
    for f in sorted(files):
        st = _util.story_status_of(_util.read(os.path.join(root, f)))
        if st is None:
            other.append("NO_STATUS    " + f)
            continue
        s = st.lower()
        if _util.is_done(st):
            done += 1
        elif re.match(r"^in progress([^a-z]|$)", s):
            prog.append("IN_PROGRESS  " + f)
        elif re.match(r"^in review([^a-z]|$)", s):
            rev.append("IN_REVIEW    " + f)
        elif re.match(r"^(ready|not started)([^a-z]|$)", s):
            todo.append("TODO         %s  (%s)" % (f, st))
        elif re.match(r"^blocked([^a-z]|$)", s):
            blk.append("BLOCKED      %s  (%s)" % (f, st))
        else:
            other.append("OTHER        %s  (%s)" % (f, st))
    for line in rev + prog + todo + blk + other:
        print(line)
    print("COMPLETE     %d of %d" % (done, len(files)))
    return 0
