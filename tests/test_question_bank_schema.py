from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from sqlalchemy import inspect, select, text, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.database import Base, initialize_database, make_engine
from app.models import User, Group, Enrollment, LessonPackage
from app.question_bank.models import Bank, Section, Domain, Skill, Question, Revision, Choice, AnswerKey, Attempt, Bookmark
from app.question_bank.migrations import upgrade, downgrade_empty, tables
from scripts.backup import inspect_database, backup, restore


class QuestionBankSchemaTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'fictional.sqlite3'
        self.engine = make_engine(str(self.path))
        self.addCleanup(self.engine.dispose)
        # Simulate the real pre-feature schema, without reading a working DB.
        Base.metadata.create_all(self.engine, tables=[t for n,t in Base.metadata.tables.items() if not n.startswith('qb_')])
        with Session(self.engine) as db:
            db.add_all([User(id=1, username='teacher', display_name='Fictional teacher', password_hash='unused', role='teacher'), User(id=2, username='student', display_name='Fictional student', password_hash='unused', role='student')])
            db.add(Group(id=1, name='Fictional class')); db.flush()
            db.add(Enrollment(id=1, student_id=2, group_id=1)); db.flush()
            db.add(LessonPackage(enrollment_id=1)); db.commit()

    def content(self):
        with Session(self.engine) as db:
            skill = db.scalar(select(Skill.id).order_by(Skill.id))
            q = Question(created_by=1); db.add(q); db.flush()
            revision = Revision(question_id=q.id, number=1, skill_id=skill, difficulty='easy', stem='What is 2 + 2?', explanation='Two pairs make four.', content_hash='a'*64, created_by=1)
            db.add(revision); db.flush()
            choices = [Choice(revision_id=revision.id, position=i, text=str(i+3)) for i in range(3)]
            db.add_all(choices); db.flush()
            db.add(AnswerKey(revision_id=revision.id, choice_id=choices[1].id)); db.flush()
            revision.sealed = True
            q.current_revision_id = revision.id
            db.commit()
            return q.id, revision.id, choices[1].id

    def test_upgrade_existing_and_fresh_is_repeatable(self):
        legacy = inspect_database(self.path)
        initialize_database(self.engine); initialize_database(self.engine)
        upgraded = inspect_database(self.path)
        for name, digest in legacy['fingerprints'].items():
            self.assertEqual(upgraded['fingerprints'][name], digest)
        self.assertEqual(upgraded['balance_digest'], legacy['balance_digest'])
        with Session(self.engine) as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(Bank)), 1)
            self.assertEqual(db.scalar(select(func.count()).select_from(Section)), 2)
            self.assertEqual(db.scalar(select(func.count()).select_from(Domain)), 8)
            self.assertEqual(db.scalar(select(func.count()).select_from(Skill)), 30)
        fresh = make_engine(str(Path(self.directory.name)/'fresh.sqlite3'))
        try:
            initialize_database(fresh)
            self.assertEqual(set(inspect(fresh).get_table_names()),set(Base.metadata.tables))
        finally: fresh.dispose()

    def test_failed_upgrade_rolls_back_schema_and_legacy_data(self):
        with patch('app.question_bank.migrations.seed', side_effect=RuntimeError('fictional failure')):
            with self.assertRaises(RuntimeError): upgrade(self.engine)
        self.assertFalse(any(n.startswith('qb_') for n in inspect(self.engine).get_table_names()))
        self.assertEqual(inspect_database(self.path)['balance_count'],1)
        upgrade(self.engine)

    def test_empty_downgrade_and_reupgrade_preserve_legacy(self):
        before = inspect_database(self.path)
        upgrade(self.engine); downgrade_empty(self.engine)
        self.assertEqual(inspect_database(self.path), before)
        upgrade(self.engine)

    def test_downgrade_refuses_content(self):
        upgrade(self.engine); self.content()
        with self.assertRaisesRegex(ValueError,'contains records'): downgrade_empty(self.engine)
        self.assertEqual(len([n for n in inspect(self.engine).get_table_names() if n.startswith('qb_')]),len(tables()))

    def test_answers_and_published_pointer_cannot_cross_revisions(self):
        upgrade(self.engine)
        q1,r1,c1=self.content(); q2,r2,c2=self.content()
        with self.engine.begin() as db:
            with self.assertRaises(IntegrityError):
                db.execute(text('INSERT INTO qb_attempts(student_id,question_id,revision_id,choice_id,is_correct,number,submission_key,created_at) VALUES (2,:q,:r,:c,1,1,\'cross\',CURRENT_TIMESTAMP)'),dict(q=q1,r=r1,c=c2))
        with self.assertRaises(IntegrityError):
            with self.engine.begin() as db:
                db.execute(text('UPDATE qb_questions SET published_revision_id=:r,status=\'published\' WHERE id=:q'),dict(r=r2,q=q1))

    def test_attempt_snapshot_and_retry_uniqueness(self):
        upgrade(self.engine); q,r,c=self.content()
        with Session(self.engine) as db:
            db.add(Attempt(student_id=2,question_id=q,revision_id=r,choice_id=c,is_correct=True,number=1,submission_key='retry'))
            db.add(Bookmark(student_id=2,question_id=q)); db.commit()
        with self.engine.begin() as db:
            for statement in ["UPDATE qb_revisions SET stem='changed'", "DELETE FROM qb_choices", "UPDATE qb_answer_keys SET choice_id=NULL", "UPDATE qb_attempts SET is_correct=0", "DELETE FROM qb_attempts"]:
                with self.assertRaises(IntegrityError): db.execute(text(statement))
        with Session(self.engine) as db:
            db.add(Attempt(student_id=2,question_id=q,revision_id=r,choice_id=c,is_correct=True,number=2,submission_key='retry'))
            with self.assertRaises(IntegrityError): db.commit()
            db.rollback()
            question=db.get(Question,q); question.status='archived'; db.commit()
            self.assertEqual(db.scalar(select(func.count()).select_from(Attempt)),1)
        self.assertEqual(inspect_database(self.path)['counts']['qb_attempts'],1)

    def test_partial_or_future_schema_fails_closed(self):
        upgrade(self.engine)
        with self.engine.begin() as db: db.execute(text('UPDATE qb_schema_versions SET version=999 WHERE version=1'))
        with self.assertRaisesRegex(ValueError,'Unsupported'): upgrade(self.engine)

    def test_version_one_upgrade_preserves_content_and_backup_compatibility(self):
        upgrade(self.engine); q,r,c=self.content()
        with self.engine.begin() as db:
            db.execute(text('DROP TABLE qb_publication_events'))
            db.execute(text('DELETE FROM qb_schema_versions WHERE version=2'))
        before=inspect_database(self.path)
        upgrade(self.engine)
        after=inspect_database(self.path)
        for name in ('qb_questions','qb_revisions','qb_choices','qb_answer_keys'):
            self.assertEqual(before['fingerprints'][name],after['fingerprints'][name])
        self.assertEqual(after['counts']['qb_publication_events'],0)

    def test_backup_restore_preserves_question_history_and_balances(self):
        upgrade(self.engine)
        q, r, c = self.content()
        with Session(self.engine) as db:
            db.add(Attempt(student_id=2, question_id=q, revision_id=r, choice_id=c,
                           is_correct=True, number=1, submission_key='backup-example'))
            db.add(Bookmark(student_id=2, question_id=q))
            db.commit()
        before = inspect_database(self.path)
        bundle = backup(self.path, Path(self.directory.name) / 'backups')['bundle']
        destination = Path(self.directory.name) / 'restored.sqlite3'
        report = restore(bundle, destination)
        self.assertEqual(inspect_database(destination), before)
        self.assertEqual(report['counts']['qb_attempts'], 1)
        self.assertEqual(report['counts']['qb_bookmarks'], 1)
        self.assertGreaterEqual(report['recovery_seconds'], 0)

    def test_missing_integrity_trigger_rejected_by_startup_and_backup(self):
        upgrade(self.engine)
        with self.engine.begin() as db:
            db.execute(text('DROP TRIGGER qb_attempt_no_update'))
        with self.assertRaisesRegex(ValueError, 'triggers'): upgrade(self.engine)
        with self.assertRaisesRegex(ValueError, 'triggers'): inspect_database(self.path)

    def test_incomplete_revision_cannot_be_sealed_or_published(self):
        upgrade(self.engine)
        with Session(self.engine) as db:
            question = Question(created_by=1)
            db.add(question); db.flush()
            revision = Revision(question_id=question.id, number=1,
                skill_id=db.scalar(select(Skill.id).order_by(Skill.id)),
                difficulty='easy', stem='Incomplete', explanation='',
                content_hash='b'*64, created_by=1)
            db.add(revision); db.commit()
            q, r = question.id, revision.id
        with self.engine.begin() as db:
            with self.assertRaises(IntegrityError):
                db.execute(text('UPDATE qb_revisions SET sealed=1 WHERE id=:r'), {'r':r})
            with self.assertRaises(IntegrityError):
                db.execute(text("UPDATE qb_questions SET status='published', published_revision_id=:r WHERE id=:q"), {'r':r,'q':q})
            with self.assertRaises(IntegrityError):
                db.execute(text("INSERT INTO qb_attempts(student_id,question_id,revision_id,response_text,is_correct,number,submission_key,created_at) VALUES (2,:q,:r,'4',0,1,'unsealed',CURRENT_TIMESTAMP)"), {'r':r,'q':q})
