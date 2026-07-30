from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).parent
WEB = ROOT / "web"


class WebReleaseTests(unittest.TestCase):
    def test_index_references_only_existing_local_runtime_assets(self) -> None:
        index = (WEB / "index.html").read_text(encoding="utf-8")
        local_assets = re.findall(r'(?:href|src)="([^"]+)"', index)
        expected = {"styles.css", "app.js", "favicon.svg"}
        self.assertTrue(expected <= set(local_assets))
        for asset in local_assets:
            if asset.startswith(("http://", "https://", "#")):
                continue
            self.assertTrue((WEB / asset).is_file(), asset)

    def test_browser_core_is_dependency_free_and_exposes_shanten_api(self) -> None:
        core = (WEB / "mahjong-core.mjs").read_text(encoding="utf-8")
        app = (WEB / "app.js").read_text(encoding="utf-8")
        self.assertNotIn("from \"http", core)
        self.assertIn("export function calculateShanten", core)
        self.assertIn("export function effectiveTiles", core)
        self.assertIn('from "./mahjong-core.mjs"', app)

    def test_pages_workflow_deploys_the_web_directory(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "pages.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("actions/configure-pages@v5", workflow)
        self.assertIn("actions/upload-pages-artifact@v4", workflow)
        self.assertIn("actions/deploy-pages@v4", workflow)
        self.assertIn("node web/test-core.mjs", workflow)
        self.assertRegex(workflow, r"path:\s*web")

    def test_public_entry_links_and_language_catalog_are_present(self) -> None:
        index = (WEB / "index.html").read_text(encoding="utf-8")
        app = (WEB / "app.js").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        pages_url = "https://Y36366363.github.io/Mahjong_card_reader/"
        self.assertIn(f"({pages_url}#settings-panel)", readme)
        self.assertIn('href="#settings-panel"', index)
        self.assertIn('value="en"', index)
        self.assertIn('value="ja"', index)
        self.assertIn("function applyLanguage", app)
        self.assertIn("currentLanguage === \"en\"", app)
        self.assertIn("currentLanguage === \"ja\"", app)


if __name__ == "__main__":
    unittest.main()
