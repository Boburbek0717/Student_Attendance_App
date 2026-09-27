"""Import reviewed PDF candidates through teacher HTTP routes in a disposable DB.

Never accepts a database destination. Emits a local review artifact and reconciliation
report; no publishing, real accounts, external storage or production database access.
"""
import argparse
from collections import Counter
from html import escape
import json
from pathlib import Path
import re
import secrets
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.isolated import isolated_imports
from scripts.extract_sqb_pdf import PROFILE


def rehearse(candidate_file, output):
    if candidate_file.stat().st_size > 2*1024*1024:
        raise ValueError('Candidate file exceeds rehearsal limit.')
    data = json.loads(candidate_file.read_text(encoding='utf-8'))
    if data.get('profile') != PROFILE or data.get('rejected') or data.get('publication_allowed') is not False:
        raise ValueError('Resolve extraction errors before this rehearsal; publication must remain disabled.')
    candidates = data['candidates']
    if not 1 <= len(candidates) <= 100 or len({q['source_id'] for q in candidates}) != len(candidates):
        raise ValueError('Expected 1–100 candidates with unique source IDs.')
    if any((q['assessment'], q['section'], q['domain'], q['skill']) !=
           ('PSAT 8/9', 'Reading and Writing', 'Standard English Conventions', 'Boundaries') for q in candidates):
        raise ValueError('Unexpected assessment or taxonomy. Do not silently relabel questions.')
    # Exclusive output creation avoids replacing a prior review or other local work.
    output.mkdir(parents=True, exist_ok=False)
    with tempfile.TemporaryDirectory(prefix='sat-pdf-rehearsal-') as temporary, isolated_imports():
        from fastapi.testclient import TestClient
        from sqlalchemy import select, func
        from sqlalchemy.orm import Session
        from app.database import make_engine
        from app.main import create_app
        from app.create_user import create_user
        from app.question_bank.models import Bank, Section, Domain, Skill, Question, Revision, Choice, AnswerKey, Source
        from scripts.backup import backup, restore, inspect_database
        engine = make_engine(str(Path(temporary) / 'fictional.db'))
        password = secrets.token_urlsafe(30)
        records, cards = [], []
        try:
            with TestClient(create_app(engine, secrets.token_urlsafe(32))) as client:
                with Session(engine) as db:
                    create_user(db, 'pdfreview', 'Import rehearsal teacher', password, 'teacher')
                    # Separate assessment taxonomy, never masquerading as SAT.
                    bank = Bank(code='psat89', name='PSAT 8/9'); db.add(bank); db.flush()
                    section = Section(bank_id=bank.id, code='reading-writing', name='Reading and Writing'); db.add(section); db.flush()
                    domain = Domain(section_id=section.id, code='standard-conventions', name='Standard English Conventions'); db.add(domain); db.flush()
                    skill = Skill(domain_id=domain.id, code='boundaries', name='Boundaries'); db.add(skill); db.commit()
                    skill_id = skill.id
                def token(page):
                    return re.search(r'name="csrf" value="([^"]+)"', page.text).group(1)
                login = client.post('/login', data=dict(username='pdfreview', password=password,
                    csrf=token(client.get('/login'))), follow_redirects=False)
                if login.status_code != 303: raise RuntimeError('Fictional login failed.')
                csrf = token(client.get('/teacher/questions/new'))
                for candidate in candidates:
                    values = dict(skill_id=str(skill_id), difficulty=candidate['difficulty'],
                        stem=candidate['stem'], passage=candidate['passage'], explanation=candidate['explanation'],
                        answer=str(candidate['answer']), source_name=data['source_name'],
                        rights_note='User-supplied PDF. Isolated import rehearsal only; publication permission not recorded.',
                        source_reference=f"PSAT 8/9 | ID {candidate['source_id']} | PDF page {candidate['page']}", csrf=csrf)
                    values.update({f'choice_{i}':text for i,text in enumerate(candidate['choices'])})
                    response = client.post('/teacher/questions/new', data=values, follow_redirects=False)
                    if response.status_code != 303:
                        raise RuntimeError(f"Draft import rejected on page {candidate['page']} (HTTP {response.status_code}).")
                    question_id = int(response.headers['location'].split('/')[3])
                    with Session(engine) as db:
                        question = db.get(Question, question_id)
                        revision = db.get(Revision, question.current_revision_id)
                        choices = db.scalars(select(Choice).where(Choice.revision_id == revision.id).order_by(Choice.position)).all()
                        key = db.get(AnswerKey, revision.id)
                        source = db.get(Source, revision.source_id)
                        if question.status != 'draft' or question.published_revision_id is not None:
                            raise RuntimeError('Import unexpectedly published content.')
                        if [c.text for c in choices] != candidate['choices'] or key.choice_id != choices[candidate['answer']].id:
                            raise RuntimeError('Stored choices or answer do not reconcile.')
                        if any(getattr(revision,k) != candidate[k] for k in ('stem','passage','explanation','difficulty')):
                            raise RuntimeError('Stored question content does not reconcile.')
                        if source.name != data['source_name'] or source.rights_note != values['rights_note']:
                            raise RuntimeError('Source provenance does not reconcile.')
                        if revision.skill_id != skill_id or revision.source_reference != values['source_reference']:
                            raise RuntimeError('Source or classification does not reconcile.')
                    preview = client.get(f'/teacher/questions/{question_id}/preview')
                    if preview.status_code != 200: raise RuntimeError('Preview failed.')
                    records.append(dict(page=candidate['page'], source_id=candidate['source_id'], draft_id=question_id, reconciled=True))
                    options = ''.join(f'<li><strong>{chr(65+i)}</strong> {escape(text)}</li>' for i,text in enumerate(candidate['choices']))
                    cards.append(f'''<article id="page-{candidate['page']}"><h2>Page {candidate['page']} · {escape(candidate['source_id'])} · {escape(candidate['difficulty'].title())}</h2>
<div class="split"><p>{escape(candidate['passage'])}</p><div><p>{escape(candidate['stem'])}</p><ol>{options}</ol></div></div>
<details><summary>Review answer and explanation</summary><p><strong>Correct answer: {chr(65+candidate['answer'])}</strong></p><p>{escape(candidate['explanation'])}</p></details></article>''')
                with Session(engine) as db:
                    count = db.scalar(select(func.count()).select_from(Question))
                    if count != len(candidates): raise RuntimeError('Draft count mismatch.')
                before = inspect_database(Path(temporary) / 'fictional.db')
                bundle = backup(Path(temporary) / 'fictional.db', Path(temporary) / 'backups')['bundle']
                recovery = restore(bundle, Path(temporary) / 'restored.db')
                after = inspect_database(Path(temporary) / 'restored.db')
                if before['fingerprints'] != after['fingerprints']: raise RuntimeError('Recovery mismatch.')
        finally:
            engine.dispose()
    report = dict(profile=PROFILE, source_sha256=data['source_sha256'], assessment='PSAT 8/9',
        imported_drafts=len(records), difficulties=dict(Counter(q['difficulty'] for q in candidates)),
        records=records, recovery_seconds=recovery['recovery_seconds'], restored_sessions_revoked=recovery['revoked_sessions'],
        live_database_used=False, published=0, test_database_removed=True, human_review='pending')
    (output / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    html = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>SAT Factory · PDF import review</title>
<style>body{font:16px/1.7 system-ui,sans-serif;color:#272c26;background:#f3f2e9;margin:0;padding:24px}main{max-width:1120px;margin:auto}h1{line-height:1.2}article{background:white;border:1px solid #d4d8cb;border-radius:6px;padding:28px;margin:24px 0}h2{font-size:18px}.split{display:grid;grid-template-columns:1fr 1fr;gap:32px}.split>p{font:18px/1.8 Georgia,serif}ol{list-style:none;padding:0}li{border:1px solid #92998b;border-radius:5px;padding:12px;margin:12px 0}li strong{margin-right:12px}summary{cursor:pointer;font-weight:600}details{border-top:1px solid #d4d8cb;padding-top:20px}p{overflow-wrap:anywhere}a{color:inherit}@media(max-width:700px){body{padding:12px}article{padding:20px}.split{grid-template-columns:1fr;gap:8px}}</style>
<main><h1>PDF import review</h1><p>PSAT 8/9 · Reading and Writing · Standard English Conventions · Boundaries</p><p>30 candidate drafts tested in a disposable database. Nothing was added to the working database or published. Review content against the original PDF before a real import.</p>'''
    html = html.replace('30 candidate', f'{len(records)} candidate')
    (output / 'review.html').write_text(html + ''.join(cards) + '</main></html>', encoding='utf-8')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidates', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    report = rehearse(args.candidates, args.output)
    print(json.dumps({key:report[key] for key in ('imported_drafts','difficulties','published','live_database_used','recovery_seconds')}))


if __name__ == '__main__':
    main()
