import json
from pathlib import Path
import tempfile
import unittest
from scripts.build_practice_preview import build


class PracticeArtifactTests(unittest.TestCase):
    def test_embedded_question_text_cannot_escape_json_script(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root/'questions.json'
            source.write_text(json.dumps(dict(source_sha256='fictional', rejected=[], candidates=[dict(
                choices=['</script><script>alert(1)</script>', 'safe'], answer=1)])), encoding='utf-8')
            build(source, root/'preview')
            html = (root/'preview/practice.html').read_text(encoding='utf-8')
            self.assertNotIn('</script><script>alert', html)
            self.assertIn('\\u003c/script\\u003e', html)
            self.assertTrue((root/'preview/practice.js').exists())
