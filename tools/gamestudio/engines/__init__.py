"""Engine plugin loader. A plugin is gamestudio/engines/<engine.name>.py; every function is optional."""
import importlib
import os

from .. import config as cfgmod
from ..common import walk

_HERE = os.path.dirname(os.path.abspath(__file__))


class Ctx(object):
    def __init__(self, root, cfg):
        self.root = root
        self.cfg = cfg
        self.engine_toml = cfg.engine_toml.get("engine", {}) if isinstance(cfg.engine_toml.get("engine"), dict) else {}

    def engine_name(self):
        v = self.cfg.value("engine.name")
        return str(v).lower() if v else ""


def load_by_name(name):
    name = (name or "").lower()
    if not name or not name.replace("_", "").isalnum():
        return None
    if not os.path.exists(os.path.join(_HERE, name + ".py")):
        return None
    return importlib.import_module("gamestudio.engines." + name)


def load_plugin(ctx):
    return load_by_name(ctx.engine_name())


def call(plugin, fn, ctx, *args, default=None):
    f = getattr(plugin, fn, None) if plugin else None
    if f is None:
        return default
    return f(ctx, *args)


def derive_code_root(root):
    """The single src/Source folder, or Assets when ProjectSettings/ProjectVersion.txt exists. None if zero or several."""
    top = os.listdir(root)
    present = [d for d in ("src", "Source") if d in top]
    if "Assets" in top and os.path.isfile(os.path.join(root, "ProjectSettings", "ProjectVersion.txt")):
        present.append("Assets")
    return present[0] if len(present) == 1 else None


def code_root(ctx, plugin=None):
    """Plugin, then engine.toml code_root, then an unambiguous src/Assets/Source folder. None if unresolved."""
    plugin = plugin if plugin is not None else load_plugin(ctx)
    v = call(plugin, "code_root", ctx)
    if v:
        return v
    v = ctx.engine_toml.get("code_root")
    if v:
        return v
    return derive_code_root(ctx.root)


def data_globs(ctx, plugin=None):
    plugin = plugin if plugin is not None else load_plugin(ctx)
    v = call(plugin, "data_globs", ctx)
    if v:
        return list(v)
    v = ctx.engine_toml.get("data_globs")
    return list(v) if v else []
