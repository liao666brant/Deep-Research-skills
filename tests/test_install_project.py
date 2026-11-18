import json
import subprocess
import tempfile
import unittest
from pathlib import Path


INSTALLER = Path(__file__).resolve().parents[1] / "scripts/install-project.py"


class ProjectInstallationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.project = Path(self.directory.name)

    def install(self, host, *, check=True):
        return subprocess.run(
            ["uv", "run", "--script", str(INSTALLER), host],
            cwd=self.project, check=check, capture_output=True, text=True,
        )

    def test_codex_preserves_existing_market_and_config(self):
        catalog = self.project / ".agents/plugins/marketplace.json"
        catalog.parent.mkdir(parents=True)
        original_plugin = {"name": "other", "source": {"source": "local", "path": "./other"}}
        catalog.write_text(json.dumps({"name": "team", "plugins": [original_plugin]}))
        config = self.project / ".codex/config.toml"
        config.parent.mkdir()
        config.write_text('model = "keep" # model\n\n[plugins."deep-research@team"]\nenabled = false # plugin\n')

        self.install("codex")
        entries = json.loads(catalog.read_text())["plugins"]
        self.assertEqual(entries[0], original_plugin)
        self.assertEqual(entries[1]["name"], "deep-research")
        self.assertEqual(entries[1]["source"]["path"], "./packages/codex")
        self.assertIn('model = "keep" # model', config.read_text())
        self.assertIn('[plugins."deep-research@team"]\nenabled = true # plugin', config.read_text())
        snapshot = (catalog.read_bytes(), config.read_bytes())
        self.install("codex")
        self.assertEqual((catalog.read_bytes(), config.read_bytes()), snapshot)

    def test_invalid_codex_config_does_not_create_a_market(self):
        config = self.project / ".codex/config.toml"
        config.parent.mkdir()
        config.write_text("invalid = [\n")
        result = self.install("codex", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("config.toml", result.stderr)
        self.assertFalse((self.project / ".agents/plugins/marketplace.json").exists())

    def test_codex_rejects_a_same_named_plugin_from_another_source(self):
        catalog = self.project / ".agents/plugins/marketplace.json"
        catalog.parent.mkdir(parents=True)
        config = self.project / ".codex/config.toml"
        config.parent.mkdir()
        config.write_text('model = "keep"\n')
        for source in (
            {"source": "local", "path": "./different-plugin"},
            {"source": "git-subdir", "url": "https://github.com/other/Deep-Research-skills.git", "path": "./packages/codex"},
            {"source": "git-subdir", "url": "https://github.com/liao666brant/Deep-Research-skills.git", "path": "./packages/other"},
        ):
            with self.subTest(source=source):
                entry = {"name": "deep-research", "source": source}
                catalog.write_text(json.dumps({"name": "team", "plugins": [entry]}))
                snapshot = (catalog.read_bytes(), config.read_bytes())
                result = self.install("codex", check=False)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("来源冲突", result.stderr)
                self.assertEqual((catalog.read_bytes(), config.read_bytes()), snapshot)

    def test_codex_keeps_the_existing_official_source_and_ref(self):
        catalog = self.project / ".agents/plugins/marketplace.json"
        catalog.parent.mkdir(parents=True)
        source = {
            "source": "git-subdir",
            "url": "https://github.com/liao666brant/Deep-Research-skills",
            "path": "packages/codex",
            "ref": "v1.0.0",
        }
        original = json.dumps({"name": "team", "plugins": [{"name": "deep-research", "source": source}]})
        catalog.write_text(original)

        self.install("codex")
        self.assertEqual(catalog.read_text(), original)
        self.assertIn('[plugins."deep-research@team"]\nenabled = true', (self.project / ".codex/config.toml").read_text())

    def test_opencode_merges_jsonc_and_keeps_comments(self):
        base = self.project / "opencode.json"
        base.write_text('{"model": "keep"}\n')
        config = self.project / ".opencode/opencode.jsonc"
        config.parent.mkdir()
        config.write_text('{\n  // heading\n  "plugins": ["other", /* plugin note */],\n}\n')

        self.install("opencode")
        updated = config.read_text()
        self.assertIn('"other", "github:liao666brant/Deep-Research-skills", /* plugin note */', updated)
        self.assertIn("// heading", updated)
        self.assertEqual(base.read_text(), '{"model": "keep"}\n')
        self.install("opencode")
        self.assertEqual(config.read_text(), updated)

    def test_opencode_leaves_an_existing_pinned_package(self):
        config = self.project / "opencode.jsonc"
        original = '{"plugins":[{"package":"github:liao666brant/Deep-Research-skills#v1", "options":{}}]}\n'
        config.write_text(original)
        self.install("opencode")
        self.assertEqual(config.read_text(), original)

    def test_opencode_adds_root_package_when_another_subdirectory_is_configured(self):
        config = self.project / "opencode.json"
        package = "github:liao666brant/Deep-Research-skills"
        other = f"{package}#master::path:packages/codex"
        config.write_text(json.dumps({"plugins": [other]}))

        self.install("opencode")
        self.assertEqual(json.loads(config.read_text())["plugins"], [other, package])

    def test_opencode_leaves_a_disabled_plugin_unchanged(self):
        config = self.project / "opencode.json"
        package = "github:liao666brant/Deep-Research-skills"
        for selector in ("-deep-research", "-*"):
            with self.subTest(selector=selector):
                original = json.dumps({"plugins": [package, selector]})
                config.write_text(original)
                result = self.install("opencode", check=False)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(f"{selector} 停用了 deep-research", result.stderr)
                self.assertEqual(config.read_text(), original)

    def test_opencode_checks_plugin_controls_in_project_precedence_order(self):
        base = self.project / "opencode.json"
        base.write_text('{"plugins": ["github:liao666brant/Deep-Research-skills"]}')
        config = self.project / ".opencode/opencode.jsonc"
        config.parent.mkdir()
        config.write_text('{"plugins": ["-deep-research"]}')
        result = self.install("opencode", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(".opencode/opencode.jsonc", result.stderr)

        enabled = '{"plugins": ["-deep-research", "deep-research"]}'
        config.write_text(enabled)
        self.install("opencode")
        self.assertEqual(config.read_text(), enabled)

    def test_invalid_opencode_config_is_unchanged(self):
        config = self.project / "opencode.jsonc"
        original = '{"plugins": ['
        config.write_text(original)
        result = self.install("opencode", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("opencode.jsonc", result.stderr)
        self.assertEqual(config.read_text(), original)


if __name__ == "__main__":
    unittest.main()
