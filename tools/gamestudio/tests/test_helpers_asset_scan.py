import struct
import unittest

from ._util import RepoCase


def png(w, h):
    return b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR" + struct.pack(">II", w, h) + b"\x08\x06\x00\x00\x00"


class AssetScanTest(RepoCase):
    def test_neutral_layout(self):
        self.add({"assets/art/Hero Sprite.png": png(100, 64), "assets/art/ok_tile.png": png(64, 64),
                  "assets/data/items.json": "{}", "assets/other/skip.txt": "x", "assets/art/.gitkeep": ""})
        code, out, _ = self.run_cli("asset-scan", "--max-dim", "80", "--budget", "png=1K", "--files")
        self.assertEqual(code, 0)
        lines = out.splitlines()
        self.assertEqual(lines[0], "engine\tnone\tdefault")
        self.assertIn("root\tassets\tpresent", lines)
        self.assertIn("scanned\t3", lines)
        self.assertIn("outside_scope\t1\tfiles under assets/ outside art, audio, vfx, shaders and data", lines)
        self.assertIn("excluded\t.gitkeep\t1", lines)
        self.assertIn("check\tnaming\tran\tlowercase_underscore", lines)
        self.assertIn("hits\tnaming\t1", lines)
        self.assertIn("hits\tpot\t1", lines)
        self.assertIn("hits\tdim\t1", lines)
        self.assertIn("NAMING\tassets/art/Hero Sprite.png\tlowercase_underscore\tuppercase,space", lines)
        self.assertIn("POT\tassets/art/Hero Sprite.png\t100x64\twidth", lines)
        self.assertIn("hits\torphan\t-", lines)
        self.assertTrue(any(l.startswith("FILE\tassets/art/ok_tile.png\tart\ttexture\t") for l in lines))

    def test_unity_layout_uses_assets_root(self):
        self.add({"Assets/Art/Tile.png": png(64, 64), "Assets/Art/Tile.png.meta": "x", "Assets/Scripts/A.cs": "x"})
        code, out, _ = self.run_cli("asset-scan", "--engine", "unity")
        self.assertEqual(code, 0)
        self.assertIn("engine\tunity\tflag", out)
        self.assertIn("scanned\t1", out)
        self.assertIn("excluded\t.meta\t1", out)
        self.assertIn("excluded\t.cs\t1", out)
        self.assertIn("check\tnaming\tnot_run\tno naming rule for unity", out)

    def test_unsupported_engine_and_absent_root(self):
        code, _, err = self.run_cli("asset-scan", "--engine", "godot")
        self.assertEqual(code, 2)
        self.assertIn("engine godot is not supported; use unity or none", err)
        code, out, _ = self.run_cli("asset-scan")
        self.assertEqual(code, 4)
        self.assertIn("root\tassets\tabsent", out)
