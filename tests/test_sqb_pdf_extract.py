import unittest
import json
from pathlib import Path
import tempfile
from scripts.extract_sqb_pdf import parse_page, PROMPT


def page_text(identifier='abcdef12'):
    return f'''Question ID {identifier}
ID: {identifier}
A fictional writer finished a story ______ revised it.
{PROMPT}
A. and
B. , and
C. ; and
D. . and
ID: {identifier} Answer
Correct Answer:B
Rationale
Fictional explanation with a \ufb01 ligature.
Question Difficulty:Easy
Assessment
PSAT 8/9
Test
Reading and Writing
Domain
Standard English
Conventions
Skill
Boundaries
Difficulty
'''


class SqbExtractionTests(unittest.TestCase):
    def test_preserves_choices_punctuation_classification_and_answer(self):
        result = parse_page(page_text(), 3)
        self.assertEqual(result['choices'], ['and', ', and', '; and', '. and'])
        self.assertEqual(result['answer'], 1)
        self.assertEqual(result['assessment'], 'PSAT 8/9')
        self.assertEqual(result['page'], 3)
        self.assertIn('fi ligature', result['explanation'])
        self.assertEqual(result['review_status'], 'needs_review')

    def test_unknown_or_ambiguous_structure_is_rejected(self):
        for modified in [page_text().replace('Correct Answer:B','Correct Answer:E'),
                         page_text().replace('ID: abcdef12 Answer','ID: 12345678 Answer'),
                         page_text().replace('PSAT 8/9','SAT'),
                         page_text().replace('C. ; and\n',''), '']:
            with self.assertRaises(ValueError): parse_page(modified, 1)

    def test_multiline_choices_reflow_without_rewriting_punctuation(self):
        result = parse_page(page_text().replace('B. , and', 'B. writer,\n and editor'), 1)
        self.assertEqual(result['choices'][1], 'writer, and editor')

    def test_disposable_rehearsal_import_and_recovery(self):
        from scripts.extract_sqb_pdf import PROFILE
        from scripts.rehearse_question_import import rehearse
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'candidate.json'
            source.write_text(json.dumps(dict(profile=PROFILE, rejected=[], publication_allowed=False,
                source_name='Fictional.pdf', source_sha256='a'*64,
                candidates=[parse_page(page_text(),1)])), encoding='utf-8')
            report = rehearse(source, root / 'review')
            self.assertEqual(report['imported_drafts'], 1)
            self.assertEqual(report['published'], 0)
            self.assertFalse(report['live_database_used'])
            self.assertTrue(report['test_database_removed'])
            self.assertEqual(report['restored_sessions_revoked'], 1)
            self.assertIn('Correct answer: B', (root/'review/review.html').read_text(encoding='utf-8'))
            with self.assertRaises(FileExistsError): rehearse(source, root/'review')
