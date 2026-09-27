"""Build a static interactive practice artifact from local PDF candidates.

This owner-facing preview contains answer keys client-side; it is not the private
student grading endpoint. No app/database imports, credentials or network calls.
"""
import argparse
import json
from pathlib import Path
import shutil


def build(candidates, destination):
    data = json.loads(candidates.read_text(encoding='utf-8'))
    questions = data['candidates']
    if not 1 <= len(questions) <= 100 or data.get('rejected'):
        raise ValueError('Use 1–100 extracted questions without rejected pages.')
    for q in questions:
        if not 2 <= len(q['choices']) <= 6 or type(q['answer']) is not int or not 0 <= q['answer'] < len(q['choices']):
            raise ValueError('Invalid choices or answer key.')
    source = Path(__file__).parent / 'practice_preview'
    payload = json.dumps(dict(questions=questions, source_sha256=data['source_sha256']), ensure_ascii=True)
    payload = payload.replace('&','\\u0026').replace('<','\\u003c').replace('>','\\u003e')
    html = (source/'practice.html').read_text(encoding='utf-8').replace('__QUESTION_DATA__', payload)
    destination.mkdir(parents=True, exist_ok=True)
    (destination/'practice.html').write_text(html, encoding='utf-8')
    for name in ('practice.css','practice.js'):
        shutil.copyfile(source/name, destination/name)
    print(f'Built interactive preview with {len(questions)} questions.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidates', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    build(args.candidates, args.output)
