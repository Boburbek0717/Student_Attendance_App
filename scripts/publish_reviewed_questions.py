"""Explicit operator publication of the owner-reviewed PSAT PDF batch.

No default database. Always backs up first, then upgrades and atomically imports
the batch. Does not read credentials, create users or authenticate as a student.
Use only after owner authorization; rehearse against a disposable DB first.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app.database import make_engine, initialize_database, write_transaction
from app.models import User
from app.question_bank.models import Bank, Section, Domain, Skill, Question, Revision, Choice, AnswerKey, Source
from app.question_bank.publication import publish_revision
from app.question_bank.authoring import validate
from sqlalchemy import select
from scripts.backup import backup

APPROVED_HASH='e386ca968c399da4df30a404ce3318126558ab2f0aa28921deba728524028aec'
APPROVED_BATCHES = {
    '96206f8c97dfcf0620ad0009e71764f8da16a552b965075e30a2b1ff9b4e09d3':
        (35, 'psat10', 'PSAT/NMSQT & PSAT 10', 'craft-and-structure', 'Craft and Structure', 'text-structure-and-purpose', 'Text Structure and Purpose'),
    APPROVED_HASH: (30, 'psat89', 'PSAT 8/9', 'standard-conventions', 'Standard English Conventions', 'boundaries', 'Boundaries'),
    '5be306b0b9b3dfb3dec9f8492b8d7fcb9574a8a30a8ead8c90fc1517fe6e4fd6':
        (33, 'psat10', 'PSAT/NMSQT & PSAT 10', 'expression-of-ideas', 'Expression of Ideas', 'transitions', 'Transitions'),
}


def publish_batch(database, candidates_path, teacher_username, backup_directory):
    database=Path(database).resolve(strict=True)
    data=json.loads(Path(candidates_path).read_text(encoding='utf-8'))
    candidates=data['candidates']
    batch = APPROVED_BATCHES.get(data.get('source_sha256'))
    if not batch or data.get('rejected') or len(candidates) != batch[0]:
        raise ValueError('This command is restricted to explicitly reviewed PDF batches.')
    count, bank_code, assessment, domain_code, domain_name, skill_code, skill_name = batch
    if len({q['source_id'] for q in candidates}) != count:
        raise ValueError('Duplicate question IDs in the reviewed batch.')
    for q in candidates:
        if (q['assessment'],q['section'],q['domain'],q['skill'])!=(assessment,'Reading and Writing',domain_name,skill_name):
            raise ValueError('Unexpected question classification.')
        if len(q['choices'])!=4 or type(q['answer']) is not int or not 0<=q['answer']<4:
            raise ValueError('Invalid answer choices.')
    # Consistent pre-upgrade backup is an essential part of this explicit operation.
    bundle=backup(database,backup_directory)['bundle']
    engine=make_engine(str(database))
    created=already=0
    try:
        initialize_database(engine)
        with write_transaction(engine) as db:
            teacher=db.scalar(select(User).where(User.username==teacher_username.strip().lower(),User.role=='teacher'))
            if not teacher: raise ValueError('The specified teacher account does not exist. No questions were imported.')
            bank=db.scalar(select(Bank).where(Bank.code==bank_code))
            if not bank: bank=Bank(code=bank_code,name=assessment);db.add(bank);db.flush()
            section=db.scalar(select(Section).where(Section.bank_id==bank.id,Section.code=='reading-writing'))
            if not section: section=Section(bank_id=bank.id,code='reading-writing',name='Reading and Writing');db.add(section);db.flush()
            domain=db.scalar(select(Domain).where(Domain.section_id==section.id,Domain.code==domain_code))
            if not domain: domain=Domain(section_id=section.id,code=domain_code,name=domain_name);db.add(domain);db.flush()
            skill=db.scalar(select(Skill).where(Skill.domain_id==domain.id,Skill.code==skill_code))
            if not skill: skill=Skill(domain_id=domain.id,code=skill_code,name=skill_name);db.add(skill);db.flush()
            for item in candidates:
                reference=f"{assessment} | ID {item['source_id']} | PDF page {item['page']}"
                matches=db.scalars(select(Question).join(Revision,Question.current_revision_id==Revision.id)
                    .where(Revision.source_reference.contains(f"{assessment} | ID {item['source_id']} |",autoescape=True))).all()
                if matches:
                    if len(matches)!=1: raise ValueError('Multiple existing questions share a source ID; manual review required.')
                    question=matches[0]; revision=db.get(Revision,question.current_revision_id)
                    choices=db.scalars(select(Choice).where(Choice.revision_id==revision.id).order_by(Choice.position)).all()
                    answer=db.get(AnswerKey,revision.id)
                    if revision.skill_id!=skill.id or any(getattr(revision,k)!=item[k] for k in ('stem','passage','explanation','difficulty')) or [c.text for c in choices]!=item['choices'] or not answer or answer.choice_id!=choices[item['answer']].id:
                        raise ValueError('Existing source question differs from the reviewed batch. No batch changes saved.')
                    if question.status!='published': raise ValueError('An existing source question was withdrawn or remains a draft; publish it explicitly after review.')
                    already+=1
                    continue
                values=dict(stem=item['stem'],passage=item['passage'],explanation=item['explanation'],
                    difficulty=item['difficulty'],skill_id=str(skill.id),answer=str(item['answer']),
                    source_name=data['source_name'],rights_note='Owner authorized import of this supplied PDF; source PDF SHA-256 '+data['source_sha256'],
                    source_reference=reference,**{f'choice_{i}':v for i,v in enumerate(item['choices'])})
                clean=validate(values)
                source=Source(name=clean['source_name'],rights_note=clean['rights_note'],created_by=teacher.id);db.add(source);db.flush()
                question=Question(created_by=teacher.id);db.add(question);db.flush()
                revision=Revision(question_id=question.id,number=1,skill_id=skill.id,difficulty=clean['difficulty'],
                    stem=clean['stem'],passage=clean['passage'],explanation=clean['explanation'],source_id=source.id,
                    source_reference=reference,content_hash=hashlib.sha256(json.dumps(clean,sort_keys=True).encode()).hexdigest(),created_by=teacher.id)
                db.add(revision);db.flush()
                for i,value in enumerate(item['choices']):
                    choice=Choice(revision_id=revision.id,position=i,text=value);db.add(choice);db.flush()
                    if i==item['answer']: db.add(AnswerKey(revision_id=revision.id,choice_id=choice.id))
                db.flush();revision.sealed=True;question.current_revision_id=revision.id;db.flush()
                publish_revision(db,teacher.id,question.id,revision.id)
                created+=1
        return dict(published=created,already_published=already,backup=bundle,teacher=teacher_username)
    finally: engine.dispose()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database',required=True,type=Path)
    parser.add_argument('--candidates',required=True,type=Path)
    parser.add_argument('--teacher',required=True)
    parser.add_argument('--backup-directory',required=True,type=Path)
    parser.add_argument('--apply',required=True,action='store_true')
    args=parser.parse_args()
    print(json.dumps(publish_batch(args.database,args.candidates,args.teacher,args.backup_directory)))
