"""Teacher-reviewed PDF import. No writes until explicit confirmation."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
import threading
import time

from sqlalchemy import select
from app.database import write_transaction
from app.teacher import require_teacher
from app.question_bank.authoring import validate
from app.question_bank.models import Bank, Section, Domain, Skill, Question, Revision, Choice, AnswerKey, Source
from app.question_bank.publication import publish_revision

MAX_PDF = 10 * 1024 * 1024
ROOT = Path(__file__).resolve().parents[2]
TAXONOMY = {
    ('PSAT 8/9', 'Standard English Conventions', 'Boundaries'): ('psat89', 'standard-conventions', 'boundaries'),
    ('PSAT/NMSQT & PSAT 10', 'Expression of Ideas', 'Transitions'): ('psat10', 'expression-of-ideas', 'transitions'),
}


class ReviewStore:
    """Bounded ephemeral review cache; restart requires a new upload, never auto-import."""
    def __init__(self):
        self.lock = threading.RLock()
        self.parser = threading.Lock()
        self.entries = {}

    def prune(self):
        for key in list(self.entries):
            if self.entries[key]['expires'] <= time.monotonic():
                del self.entries[key]

    def put(self, owner, data):
        with self.lock:
            self.prune()
            if len(self.entries) >= 8:
                raise ValueError('Eight PDF reviews are already open. Try again after one expires (within 20 minutes).')
            token = secrets.token_urlsafe(32)
            self.entries[token] = dict(owner=owner, data=deepcopy(data), expires=time.monotonic()+1200, result=None)
            return token

    def get(self, token, owner):
        self.prune()
        entry = self.entries.get(token)
        if not entry or entry['owner'] != owner:
            raise ValueError('This PDF review expired or belongs to another login. Upload the PDF again.')
        return entry


def parse_pdf(payload, store):
    if not payload.startswith(b'%PDF-') or len(payload) > MAX_PDF:
        raise ValueError('Choose a PDF file no larger than 10 MB.')
    if not store.parser.acquire(blocking=False):
        raise ValueError('Another PDF is being checked. Please try again shortly.')
    try:
        with tempfile.TemporaryDirectory(prefix='sat-pdf-upload-') as folder:
            source, output = Path(folder)/'upload.pdf', Path(folder)/'review.json'
            source.write_bytes(payload)
            try:
                process = subprocess.run([sys.executable, str(ROOT/'scripts/pdf_import_worker.py'), str(source), str(output)],
                    stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    timeout=25, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            except subprocess.TimeoutExpired:
                raise ValueError('PDF processing took too long. Try a smaller supported PDF.') from None
            if process.returncode or not output.exists() or output.stat().st_size > 2*1024*1024:
                raise ValueError('This PDF could not be read. Use an unencrypted, text-based SQB answer PDF with up to 100 pages.')
            return json.loads(output.read_text(encoding='utf-8'))
    finally:
        store.parser.release()


def classification(item):
    key = (item['assessment'], item['domain'], item['skill'])
    if item['section'] != 'Reading and Writing' or key not in TAXONOMY:
        raise ValueError('Unsupported question category.')
    return TAXONOMY[key]


def values_for(item, skill_id, data):
    if len(item['choices']) != 4 or type(item['answer']) is not int or not 0 <= item['answer'] < 4:
        raise ValueError('Each question must have A–D and a correct answer.')
    return dict(stem=item['stem'], passage=item['passage'], explanation=item['explanation'],
        difficulty=item['difficulty'], skill_id=str(skill_id), answer=str(item['answer']),
        source_name=data['source_name'], rights_note='',
        source_reference=f"{item['assessment']} | ID {item['source_id']} | PDF page {item['page']} | SHA256 {data['source_sha256']}",
        **{f'choice_{i}':value for i,value in enumerate(item['choices'])})


def existing_question(db, item):
    matches = db.execute(select(Question, Revision).join(Revision, Question.current_revision_id == Revision.id)
        .where(Revision.source_reference.contains(f"{item['assessment']} | ID {item['source_id']} |", autoescape=True))).all()
    if not matches:
        return None
    if len(matches) != 1:
        raise ValueError(f"Page {item['page']}: multiple existing records use this source ID. Nothing was imported.")
    question, revision = matches[0]
    choices = db.scalars(select(Choice).where(Choice.revision_id == revision.id).order_by(Choice.position)).all()
    answer = db.get(AnswerKey, revision.id)
    taxonomy = db.execute(select(Bank.name, Domain.name, Skill.name).select_from(Skill)
        .join(Domain, Skill.domain_id == Domain.id).join(Section, Domain.section_id == Section.id)
        .join(Bank, Section.bank_id == Bank.id).where(Skill.id == revision.skill_id)).one()
    if (tuple(taxonomy) != (item['assessment'], item['domain'], item['skill'])
        or any(getattr(revision,k) != item[k] for k in ('stem','passage','explanation','difficulty'))
        or [c.text for c in choices] != item['choices'] or not answer
        or answer.choice_id != choices[item['answer']].id):
        raise ValueError(f"Page {item['page']}: this source ID already exists with different content. Nothing was imported; review the existing question.")
    return question


def inspect_review(db, data):
    problems = list(data['rejected'])
    rows = []
    for item in data['candidates']:
        try:
            classification(item)
            validate(values_for(item, 1, data))
            existing = existing_question(db, item)
            rows.append(dict(item=item, duplicate=existing is not None, existing_id=existing.id if existing else None))
        except ValueError as error:
            problems.append(dict(page=item['page'], reason=str(error)))
    return rows, problems


def ensure_category(db, item):
    bank_code, domain_code, skill_code = classification(item)
    bank = db.scalar(select(Bank).where(Bank.code == bank_code))
    if not bank:
        bank = Bank(code=bank_code, name=item['assessment']); db.add(bank); db.flush()
    section = db.scalar(select(Section).where(Section.bank_id == bank.id, Section.code == 'reading-writing'))
    if not section:
        section = Section(bank_id=bank.id, code='reading-writing', name=item['section']); db.add(section); db.flush()
    domain = db.scalar(select(Domain).where(Domain.section_id == section.id, Domain.code == domain_code))
    if not domain:
        domain = Domain(section_id=section.id, code=domain_code, name=item['domain']); db.add(domain); db.flush()
    skill = db.scalar(select(Skill).where(Skill.domain_id == domain.id, Skill.code == skill_code))
    if not skill:
        skill = Skill(domain_id=domain.id, code=skill_code, name=item['skill']); db.add(skill); db.flush()
    return skill.id


def commit_review(engine, request, store, token, mode):
    if mode not in ('draft', 'publish'):
        raise ValueError('Choose Import as drafts or Publish.')
    with store.lock, write_transaction(engine) as db:
        teacher = require_teacher(request, db)
        entry = store.get(token, (teacher.id, request.session.get('session_id')))
        if entry['result'] is not None:
            return entry['result']
        data = entry['data']
        rows, problems = inspect_review(db, data)
        if problems or not rows:
            raise ValueError('Resolve all flagged pages before importing. No questions were added.')
        created = skipped = 0
        for row in rows:
            item = row['item']
            if row['duplicate']:
                skipped += 1
                continue
            skill_id = ensure_category(db, item)
            clean = validate(values_for(item, skill_id, data))
            source = Source(name=clean['source_name'], rights_note='', created_by=teacher.id)
            db.add(source); db.flush()
            question = Question(created_by=teacher.id); db.add(question); db.flush()
            revision = Revision(question_id=question.id, number=1, skill_id=skill_id,
                difficulty=clean['difficulty'], stem=clean['stem'], passage=clean['passage'],
                explanation=clean['explanation'], source_id=source.id, source_reference=clean['source_reference'],
                content_hash=hashlib.sha256(json.dumps(clean, sort_keys=True).encode()).hexdigest(), created_by=teacher.id)
            db.add(revision); db.flush()
            for i, value in enumerate(item['choices']):
                choice = Choice(revision_id=revision.id, position=i, text=value); db.add(choice); db.flush()
                if i == item['answer']:
                    db.add(AnswerKey(revision_id=revision.id, choice_id=choice.id))
            db.flush(); revision.sealed = True; question.current_revision_id = revision.id; db.flush()
            if mode == 'publish':
                publish_revision(db, teacher.id, question.id, revision.id)
            created += 1
        # Record success only after the database commit succeeds.
        db.commit()
        entry['result'] = dict(created=created, skipped=skipped, mode=mode)
        return entry['result']
