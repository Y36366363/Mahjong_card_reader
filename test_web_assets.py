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
        local_asset_paths = {asset.split("?", 1)[0] for asset in local_assets}
        self.assertTrue(expected <= local_asset_paths)
        for asset in local_assets:
            if asset.startswith(("http://", "https://", "#")):
                continue
            self.assertTrue((WEB / asset.split("?", 1)[0]).is_file(), asset)

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
        self.assertIn("function shareSettings", app)
        self.assertIn("#settings=", app)
        self.assertIn('id="share-settings-button"', index)
        for key in ("backgroundLabel", "backgroundAsset1", "backgroundUploaded", "backgroundHelp"):
            self.assertGreaterEqual(app.count(key), 3, key)
        self.assertIn('id="background-setting"', index)
        self.assertIn('id="background-file"', index)
        self.assertIn('id="analysis-status" class="status" data-i18n="waiting"', index)
        self.assertTrue((WEB / "assets" / "backgrounds" / "README.md").is_file())
        for number in (1, 2, 3):
            self.assertTrue((WEB / "assets" / "backgrounds" / f"background-{number}.jpg").is_file())
            self.assertTrue((WEB / "assets" / "backgrounds" / f"background-{number}.png").is_file())


if __name__ == "__main__":
    unittest.main()
