"""Bounded, read-only extractor for reviewed SQB Boundaries and Transitions layouts.

Use the project virtual environment (pypdf). Does not import the app, contact services,
execute PDF actions, write a database or publish questions. Unsupported pages
are quarantined for review instead of guessing structure.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

PROFILE = 'sqb-psat89-boundaries-v1'
# Visually reviewed 46x15 difficulty indicators from the supplied SQB export.
# Exact hashes, not size alone: an unknown content diagram must never be dropped.
DIFFICULTY_ICONS = {
    'f86aeca58e19f95fb3b34808c715429f79fd9620871edf5629589f9afd65dd95': 'medium',
    '0bdcb9ec61244c4489cfa38c4214a256592910ff4428bd455d7e35c9588a2baf': 'easy',
    '6ae14a4f1ebd3c65234d6ee58e0b7e7fdca2f0c7d305653342ce727a362f4474': 'hard',
}
LIGATURES = str.maketrans({'\ufb00':'ff', '\ufb01':'fi', '\ufb02':'fl',
    '\ufb03':'ffi', '\ufb04':'ffl', '\ufb05':'st', '\ufb06':'st', '\xa0':' '})
PROMPT = 'Which choice completes the text so that it conforms to the conventions of Standard English?'


def prose(value):
    # Reflow PDF line wraps; deliberately preserve punctuation and Unicode math.
    return ' '.join(value.split())


TRANSITIONS_PROFILE = 'sqb-psat10-transitions-v1'
TRANSITIONS_PROMPT = 'Which choice completes the text with the most logical transition?'


def parse_page(raw, page, profile=PROFILE):
    text = raw.translate(LIGATURES).replace('\r\n', '\n').strip()
    if len(text) > 50000:
        raise ValueError('Page text exceeds the supported profile limit.')
    transitions = profile == TRANSITIONS_PROFILE
    if profile not in (PROFILE, TRANSITIONS_PROFILE):
        raise ValueError('Unsupported extraction profile.')
    assessment_pattern = r'PSAT/NMSQT &\s+PSAT 10' if transitions else r'PSAT 8/9'
    domain_pattern = r'Expression of Ideas' if transitions else r'Standard English\s+Conventions'
    skill = 'Transitions' if transitions else 'Boundaries'
    prompt = TRANSITIONS_PROMPT if transitions else PROMPT
    match = re.fullmatch(
        r'Question ID (?P<id>[a-fA-F0-9]{8})\s+ID: (?P=id)\s+(?P<body>.*?)\s+'
        r'ID: (?P=id) Answer\s+Correct Answer:\s*(?P<answer>[A-D])\s+Rationale\s+'
        r'(?P<rationale>.*?)\s+Question Difficulty:\s*(?P<difficulty>Easy|Medium|Hard)\s+'
        r'Assessment\s+' + assessment_pattern + r'\s+Test\s+Reading and Writing\s+Domain\s+'
        + domain_pattern + r'\s+Skill\s+' + skill + r'\s+Difficulty', text, re.S)
    if not match:
        raise ValueError('Unsupported page structure, metadata or mismatched question IDs.')
    body = re.fullmatch(r'(?P<passage>.*?)\s+' + re.escape(prompt) +
        r'\s+A\. (?P<a>.*?)\nB\. (?P<b>.*?)\nC\. (?P<c>.*?)\nD\. (?P<d>.+)', match['body'], re.S)
    if not body:
        raise ValueError('Passage, prompt or four labelled choices could not be separated safely.')
    choices = [prose(body[label]) for label in 'abcd']
    if not prose(body['passage']) or not all(choices) or not prose(match['rationale']):
        raise ValueError('Required content is empty.')
    return dict(source_id=match['id'].lower(), page=page, assessment='PSAT/NMSQT & PSAT 10' if transitions else 'PSAT 8/9',
        section='Reading and Writing', domain='Expression of Ideas' if transitions else 'Standard English Conventions', skill=skill,
        difficulty=match['difficulty'].lower(), passage=prose(body['passage']), stem=prompt,
        choices=choices, answer=ord(match['answer'])-ord('A'), explanation=prose(match['rationale']),
        review_status='needs_review')


def extract(source, profile=PROFILE):
    from pypdf import PdfReader
    source = Path(source).resolve(strict=True)
    if source.stat().st_size > 10*1024*1024:
        raise ValueError('Use a PDF smaller than 10 MB for this rehearsal.')
    reader = PdfReader(source)
    if reader.is_encrypted or not 1 <= len(reader.pages) <= 100:
        raise ValueError('Use an unencrypted PDF with 1–100 pages.')
    try:
        from scripts.flexible_pdf import parse_questions, answer_key, parse_labelled_sqb
    except ModuleNotFoundError:
        from flexible_pdf import parse_questions, answer_key, parse_labelled_sqb
    candidates, rejected, seen = [], [], set()
    texts, keys, key_pages, numbered = {}, {}, set(), set()
    if profile == 'auto':
        for number, page in enumerate(reader.pages, 1):
            raw = (page.extract_text() or '').translate(LIGATURES).replace('\r\n','\n')
            if len(raw) > 50000:
                rejected.append(dict(page=number, reason='Page text exceeds supported limits.'))
                continue
            texts[number] = raw
            try:
                found = answer_key(raw)
                if found is not None:
                    if list(page.images): raise ValueError('Answer key contains images requiring review.')
                    if keys.keys() & found.keys(): raise ValueError('Repeated question number across answer keys.')
                    keys.update(found); key_pages.add(number)
            except ValueError as error:
                rejected.append(dict(page=number, reason=str(error)))
                key_pages.add(number)
    for number, page in enumerate(reader.pages, 1):
        try:
            if profile == 'auto' and (number in key_pages or number not in texts): continue
            raw = texts[number] if profile == 'auto' else page.extract_text() or ''
            if profile == 'auto':
                item = None
                for known in (PROFILE, TRANSITIONS_PROFILE):
                    try:
                        item = parse_page(raw, number, known)
                        break
                    except ValueError:
                        pass
                if item is None:
                    item = parse_labelled_sqb(raw, number)
                items = [item] if item is not None else parse_questions(raw, number, keys)
            else:
                items = [parse_page(raw, number, profile)]
            for image in page.images:
                if len(items) != 1 or DIFFICULTY_ICONS.get(hashlib.sha256(image.data).hexdigest()) != items[0]['difficulty']:
                    raise ValueError('Unknown image or difficulty mismatch; manual visual review is required.')
            for item in items:
                if item['source_id'] in seen:
                    raise ValueError('Duplicate source question ID in this document.')
                if item.get('source_number') in numbered:
                    raise ValueError('Repeated question number; answer-key matching is ambiguous.')
                seen.add(item['source_id'])
                if item.get('source_number'): numbered.add(item['source_number'])
                candidates.append(item)
        except Exception as error:
            rejected.append(dict(page=number, reason=str(error)))
    if set(keys) - numbered:
        rejected.append(dict(page=0, reason='Answer key has unmatched question numbers.'))
    return dict(profile=profile, source_name=source.name,
        source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(), pages=len(reader.pages),
        candidates=candidates, rejected=rejected, publication_allowed=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--profile', choices=('auto', PROFILE, TRANSITIONS_PROFILE), default='auto')
    args = parser.parse_args()
    result = extract(args.source, args.profile)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
    print(json.dumps(dict(pages=result['pages'], candidates=len(result['candidates']),
                         rejected=len(result['rejected']), output=str(args.output))))


if __name__ == '__main__':
    main()
