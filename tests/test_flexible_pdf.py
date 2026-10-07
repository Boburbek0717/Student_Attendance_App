import unittest
from scripts.flexible_pdf import parse_questions, answer_key

HEADER='Assessment: SAT\nSection: Math\nDomain: Algebra\nCategory: Linear equations\nDifficulty: Medium\n'
QUESTION='Question 1\nSolve x + 2 = 5.\n(A) 1\n(B) 2\n(C) 3\n(D) 4\n'

class FlexiblePdfTests(unittest.TestCase):
    def test_separate_key_and_new_category(self):
        items=parse_questions(HEADER+QUESTION,1,answer_key('Answer Key\n1. C'))
        self.assertEqual(items[0]['answer'],2)
        self.assertEqual(items[0]['difficulty'],'medium')
        self.assertEqual(items[0]['skill'],'Linear equations')
        self.assertEqual(items[0]['section'],'Math')

    def test_multiple_questions_and_option_styles(self):
        raw=HEADER+QUESTION+'Answer: C\n'+QUESTION.replace('Question 1','2.').replace('(A)','A.').replace('(B)','B)').replace('(C)','C.').replace('(D)','D)').replace('x + 2','x + 3')+'Correct Answer: B\nExplanation: Subtract three.'
        items=parse_questions(raw,1)
        self.assertEqual(len(items),2)
        self.assertEqual(items[1]['explanation'],'Subtract three.')
        self.assertEqual(items[1]['choices'],['1','2','3','4'])

    def test_missing_conflicting_and_extra_choices_rejected(self):
        for raw in (HEADER+QUESTION, (HEADER+QUESTION+'Answer: A').replace('Difficulty: Medium\n',''),
                    HEADER+QUESTION+'Answer: A\nAnswer: C',HEADER+QUESTION.replace('(C) 3\n','')+'Answer: C'):
            with self.assertRaises(ValueError):parse_questions(raw,1)
        with self.assertRaises(ValueError):parse_questions(HEADER+QUESTION+'Answer: A',1,{'1':2})
        with self.assertRaises(ValueError):answer_key('Answers\n1. A\n1. B')

    def test_prompt_passage_and_difficulty_label_not_question_marker(self):
        raw=(HEADER+QUESTION+'Answer: C').replace('Difficulty: Medium','Question Difficulty: Hard').replace('Solve x + 2 = 5.','Passage: An original fictional passage.\nPrompt: Which statement is true?')
        item=parse_questions(raw,1)[0]
        self.assertEqual(item['passage'],'An original fictional passage.')
        self.assertEqual(item['stem'],'Which statement is true?')
        self.assertEqual(item['difficulty'],'hard')

    def test_document_two_pass_keys_and_unknown_images(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from types import SimpleNamespace
        from unittest.mock import patch
        from scripts.extract_sqb_pdf import extract
        pages=[SimpleNamespace(extract_text=lambda:HEADER+QUESTION,images=[]),
               SimpleNamespace(extract_text=lambda:'Answer Key\n1. C',images=[])]
        with TemporaryDirectory() as directory:
            path=Path(directory)/'fictional.pdf';path.write_bytes(b'%PDF-fictional')
            with patch('pypdf.PdfReader',return_value=SimpleNamespace(is_encrypted=False,pages=pages)):
                result=extract(path,'auto')
                self.assertEqual(len(result['candidates']),1)
                self.assertEqual(result['rejected'],[])
                pages[0].images=[SimpleNamespace(data=b'unknown diagram')]
                result=extract(path,'auto')
                self.assertEqual(result['candidates'],[])
                self.assertTrue(result['rejected'])

    def test_fifth_choice_is_not_silently_folded_into_fourth(self):
        with self.assertRaises(ValueError):parse_questions(HEADER+QUESTION+'E. 5\nAnswer: C',1)

    def test_real_pdf_worker_extracts_numbered_sheet_and_separate_key(self):
        from io import BytesIO
        from pypdf import PdfWriter
        from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
        from app.question_bank.pdf_import import parse_pdf, ReviewStore
        writer=PdfWriter()
        for text in (HEADER+QUESTION, 'Answer Key\n1. C'):
            page=writer.add_blank_page(width=612,height=792)
            font=DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')})
            page[NameObject('/Resources')]=DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):writer._add_object(font)})})
            lines=['BT /F1 12 Tf 40 750 Td 16 TL']
            for line in text.splitlines():
                escaped=line.replace('\\','\\\\').replace('(','\\(').replace(')','\\)')
                lines.append('('+escaped+') Tj T*')
            lines.append('ET')
            stream=DecodedStreamObject();stream.set_data('\n'.join(lines).encode())
            page[NameObject('/Contents')]=writer._add_object(stream)
        output=BytesIO();writer.write(output)
        result=parse_pdf(output.getvalue(),ReviewStore())
        self.assertEqual(result['rejected'],[])
        self.assertEqual(len(result['candidates']),1)
        self.assertEqual(result['candidates'][0]['answer'],2)

    def test_new_sqb_assessment_and_skill_need_no_profile(self):
        from scripts.flexible_pdf import parse_labelled_sqb
        from test_sqb_pdf_extract import page_text
        item=parse_labelled_sqb(page_text().replace('PSAT 8/9','SAT').replace('Boundaries','Form, Structure, and Sense'),1)
        self.assertEqual(item['skill'],'Form, Structure, and Sense')
        self.assertEqual(item['assessment'],'SAT')
        self.assertEqual(item['source_id'],'abcdef12')
        self.assertEqual(item['answer'],1)
