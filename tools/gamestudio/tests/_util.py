"""Test helpers: temporary repos and CLI runs."""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

TOOLS = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STUDIO = os.path.join(TOOLS, "studio.py")
REPO = os.path.dirname(TOOLS)

BASE_TOML = 'schema_version = 1\n\n[modes]\nrigor = "minimal"\n'


def write_files(root, files):
    for rel, content in files.items():
        path = os.path.join(root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        mode = "wb" if isinstance(content, bytes) else "w"
        kwargs = {} if isinstance(content, bytes) else {"encoding": "utf-8", "newline": "\n"}
        with open(path, mode, **kwargs) as fh:
            fh.write(content)


def git(root, *args):
    return subprocess.run(["git", "-C", root] + list(args), capture_output=True, text=True, encoding="utf-8")


class RepoCase(unittest.TestCase):
    """Each test gets an empty directory; add files with self.add()."""

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="studio-test-")
        self.addCleanup(shutil.rmtree, self.root, True)

    def add(self, files):
        write_files(self.root, files)

    def with_toml(self, extra=None):
        files = {"project.toml": BASE_TOML}
        files.update(extra or {})
        self.add(files)

    def git_init(self):
        git(self.root, "init", "-q", "-b", "main")
        git(self.root, "config", "user.email", "t@example.com")
        git(self.root, "config", "user.name", "T")
        git(self.root, "config", "commit.gpgsign", "false")

    def run_cli(self, *args, stdin=None, root=None):
        r = subprocess.run([sys.executable, STUDIO, "--root", root or self.root] + list(args), input=stdin,
                           capture_output=True, text=True, encoding="utf-8")
        return r.returncode, r.stdout, r.stderr


STORY = """# Story 001: Thing

> **Epic**: core
> **Status**: {status}
> **Layer**: Core
> **Type**: {type}
> **Estimate**: S

## Context

**Requirement**: `TR-core-001`

## Acceptance Criteria

- [ ] one
- [ ] two

## Test Evidence

**Status**: [ ] Not yet created

## Dependencies

- Depends on: None
"""


def story(status="Ready", type="Logic"):
    return STORY.format(status=status, type=type)
