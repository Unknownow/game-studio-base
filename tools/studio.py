#!/usr/bin/env python3
# Entry point. The version guard below must stay valid Python 2/3-era syntax so
# an old interpreter reaches it and prints the message instead of a SyntaxError.
import sys

if sys.version_info < (3, 11):
    sys.stderr.write(
        "studio: Python 3.11+ is required (running %d.%d.%d at %s). "
        "Install it from python.org; the Windows Store \"python\" alias is not Python.\n"
        % (sys.version_info[0], sys.version_info[1], sys.version_info[2], sys.executable)
    )
    sys.exit(2)

import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gamestudio.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
