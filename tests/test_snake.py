import datetime as dt
import importlib.util
import json
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("snake", ROOT / "scripts/update-snake.py")
snake = importlib.util.module_from_spec(spec)
spec.loader.exec_module(snake)
SNAPSHOT = json.loads((ROOT / "assets/contributions.json").read_text())


class SnakeTests(unittest.TestCase):
    def test_valid_snapshot(self):
        self.assertEqual(snake.validate_snapshot(SNAPSHOT), SNAPSHOT)

    def test_snapshot_rejects_bad_owner_and_levels(self):
        for snapshot in [
            {**SNAPSHOT, "username": "other"},
            {**SNAPSHOT, "days": [{**day, "level": 9} for day in SNAPSHOT["days"]]},
            {**SNAPSHOT, "days": SNAPSHOT["days"][:-10]},
            {**SNAPSHOT, "days": list(reversed(SNAPSHOT["days"]))},
        ]:
            with self.subTest(snapshot=snapshot["username"]), self.assertRaises(ValueError):
                snake.validate_snapshot(snapshot)

    def test_bad_network_responses_rejected(self):
        for html in ["<p>Sign in</p>", '<td data-date="2026-10-29" data-level="5">']:
            with self.assertRaises(ValueError):
                snake.build_snapshot(html)

    def test_stale_response_rejected(self):
        html = "".join(f'<td data-date="{day["date"]}" data-level="{day["level"]}">' for day in SNAPSHOT["days"])
        later = dt.datetime.fromisoformat(SNAPSHOT["generatedAt"]) + dt.timedelta(days=10)
        with self.assertRaises(ValueError):
            snake.build_snapshot(html, later)

    def test_svg_is_safe_and_has_accessible_description(self):
        for animated in [True, False]:
            svg = snake.render_svg(SNAPSHOT, animated)
            root = ET.fromstring(svg)
            tags = {node.tag.rsplit("}", 1)[-1] for node in root.iter()}
            self.assertTrue(tags <= {"svg", "title", "desc", "rect", "style", "text"})
            self.assertEqual(root.attrib["role"], "img")
            self.assertIn("aria-labelledby", root.attrib)
            self.assertEqual(svg.count('id="day-'), 364)
            self.assertNotIn("href=", svg)
            self.assertEqual("@keyframes snake-" in svg, animated)
            self.assertEqual("prefers-reduced-motion" in svg, animated)

    def test_committed_previews_are_reproducible(self):
        for name, animated in [("github-contribution-snake.svg", True), ("contributions-static.svg", False)]:
            self.assertEqual((ROOT / "assets" / name).read_text(), snake.render_svg(SNAPSHOT, animated))


if __name__ == "__main__":
    unittest.main()
