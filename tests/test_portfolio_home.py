"""The public portfolio homepage renders owner facts and figures derived from published results."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.database import make_engine
from app.main import create_app
from app.portfolio_content import TUTOR, portfolio_figures
from app.result_content import RESULTS


class PortfolioHomeTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.engine = make_engine(str(Path(directory.name) / "test.db"))
        self.addCleanup(self.engine.dispose)
        self.client = self.enterContext(TestClient(create_app(self.engine, session_secret="test-only-secret")))

    def test_figures_follow_the_published_results(self):
        figures = portfolio_figures()
        totals = sorted((row["ebrw"] + row["math"] for row in RESULTS), reverse=True)
        self.assertEqual(figures["count"], len(RESULTS))
        self.assertEqual([row["total"] for row in figures["ranked"]], totals)
        self.assertEqual(figures["best_total"], totals[0])
        self.assertEqual(figures["average"], f"{sum(totals) / len(totals):.1f}")
        self.assertEqual(figures["top_math_count"], sum(row["math"] == figures["top_math"] for row in RESULTS))
        self.assertTrue(all(row.get("quote") for row in figures["quoted"]))

    def test_homepage_shows_tutor_scores_and_every_result(self):
        page = self.client.get("/")
        self.assertEqual(page.status_code, 200)
        self.assertIn(f'<h1 id="pf-title"', page.text)
        self.assertIn(str(TUTOR["sat"]), page.text)
        self.assertIn(TUTOR["university"], page.text)
        for row in RESULTS:
            self.assertIn(f'href="/results#result-{row["id"]}"', page.text)
        reached = sum(row["ebrw"] + row["math"] >= 1350 for row in RESULTS)
        self.assertIn(f"<strong>{reached} of {len(RESULTS)}</strong> students reached 1350", page.text)
        self.assertNotIn("style=", page.text)
        self.assertNotIn("<script>", page.text)

    def test_contact_appears_only_when_configured(self):
        self.assertNotIn("t.me/", self.client.get("/").text)
        contact = {"label": "Message me on Telegram", "href": "https://t.me/example"}
        with patch.dict(TUTOR, contact=contact):
            page = self.client.get("/").text
        self.assertIn('href="https://t.me/example">Message me on Telegram', page)

    def test_page_assets_are_served_locally(self):
        page = self.client.get("/").text
        for path in ("/static/portfolio.css", "/static/portfolio.js", "/static/portfolio-flag.js",
                     "/static/fonts/big-shoulders-800-latin.woff2", "/static/portfolio/szeged-tisza.jpg"):
            self.assertIn(path, page)
            self.assertEqual(self.client.get(path).status_code, 200, path)


if __name__ == "__main__":
    unittest.main()
