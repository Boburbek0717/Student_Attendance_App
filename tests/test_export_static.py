"""The static export produces self-contained public pages with no root-relative links."""
from pathlib import Path
import re
import tempfile
import unittest

from scripts.export_static import APP_ORIGIN, export, rewrite


class StaticExportTests(unittest.TestCase):
    def test_export_writes_pages_and_their_assets(self):
        with tempfile.TemporaryDirectory() as directory:
            site = Path(directory) / 'site'
            export(site)
            home = (site / 'index.html').read_text(encoding='utf-8')
            self.assertIn('href="results.html#result-', home)
            self.assertIn(f'href="{APP_ORIGIN}/questions"', home)
            self.assertNotIn('testserver', home)
            for asset in re.findall(r'(?:href|src)="(static/[^"?]+)', home):
                self.assertTrue((site / asset).is_file(), asset)
            self.assertTrue((site / 'results.html').is_file())
            self.assertTrue((site / '.nojekyll').is_file())
            self.assertFalse((site / 'static' / 'vendor').exists())

    def test_unknown_root_link_fails_instead_of_breaking(self):
        with self.assertRaises(ValueError):
            rewrite('<a href="/teacher">Teacher</a>')


if __name__ == '__main__':
    unittest.main()
