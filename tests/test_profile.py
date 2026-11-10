from html.parser import HTMLParser
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


class ImageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.images = []

    def handle_starttag(self, tag, attrs):
        if tag in {"img", "source"}:
            attributes = dict(attrs)
            self.images.append((tag, attributes))


class ProfileTests(unittest.TestCase):
    def test_profile_images_use_existing_local_assets(self):
        parser = ImageParser()
        parser.feed((ROOT / "README.md").read_text(encoding="utf-8"))
        self.assertTrue(parser.images)
        for tag, attributes in parser.images:
            path = attributes["srcset" if tag == "source" else "src"]
            with self.subTest(path=path):
                self.assertTrue(path.startswith("./assets/"))
                self.assertTrue((ROOT / path).is_file())
                if tag == "img":
                    self.assertTrue(attributes.get("alt"))
        banner = next(
            attributes
            for tag, attributes in parser.images
            if attributes.get("src") == "./assets/devrel-banner.svg"
        )
        self.assertIn("ZeCloud", banner["alt"])

    def test_banner_is_a_standalone_svg(self):
        root = ET.parse(ROOT / "assets" / "devrel-banner.svg").getroot()
        self.assertEqual(root.attrib["viewBox"], "0 0 960 196")
        for element in root.iter():
            with self.subTest(tag=element.tag):
                self.assertIn(
                    element.tag.rsplit("}", 1)[-1],
                    {"svg", "title", "rect", "path", "text", "g", "circle"},
                )
                self.assertFalse(any(key.rsplit("}", 1)[-1] == "href" for key in element.attrib))


if __name__ == "__main__":
    unittest.main()
