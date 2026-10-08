"""Versioned additive SQLite migration, never connected to the default engine.

Legacy tables keep their existing initialization. QB v1 is transactional and
refuses partial/unrecognized schemas. Future schema changes need a new version.
"""
from sqlalchemy import inspect, select, text
from app.database import Base
from app.question_bank import models
from app.question_bank.taxonomy import seed

VERSION = 5
ASSIGNMENT_TABLES = {"qb_assignments", "qb_assignment_items", "qb_assignment_recipients", "qb_assignment_attempts"}


def trigger_names(version=VERSION):
    return ({f"{table}_no_{event}" for table in ("qb_media", "qb_media_content") for event in ("update", "delete")} if version >= 5 else set()) | ({f"{table}_no_{event}" for table in ASSIGNMENT_TABLES for event in ("update", "delete")} if version >= 4 else set()) | ({"qb_publication_no_update", "qb_publication_no_delete"} if version >= 2 else set()) | {"qb_revision_no_update", "qb_revision_no_delete", "qb_attempt_no_update", "qb_attempt_no_delete",
            "qb_attempt_requires_snapshot", "qb_revision_insert_unsealed", "qb_revision_seal_valid",
            "qb_publish_insert", "qb_publish_update"} | {
        f"{table}_no_{event}" for table in ("qb_choices", "qb_answer_keys") for event in ("insert", "update", "delete")}


def validate_schema(connection, version=VERSION):
    inspector = inspect(connection)
    if {n for n in inspector.get_table_names() if n.startswith('qb_')} != {t.name for t in tables(version)}:
        raise ValueError("Incomplete Question Bank schema; restore or repair with matching code.")
    if list(connection.scalars(select(models.SchemaVersion.version).order_by(models.SchemaVersion.version))) != list(range(1, version+1)):
        raise ValueError("Unsupported Question Bank schema version.")
    for table in tables(version):
        if {c['name'] for c in inspector.get_columns(table.name)} != set(table.columns.keys()):
            raise ValueError("Question Bank schema columns differ from this release.")
    present = set(connection.scalars(text("SELECT name FROM sqlite_master WHERE type='trigger' AND name LIKE 'qb_%'")))
    if present != trigger_names(version):
        raise ValueError("Question Bank integrity triggers differ from this release.")


def tables(version=VERSION):
    return [t for name, t in Base.metadata.tables.items() if name.startswith("qb_")
            and (version >= 5 or name != "qb_media_content")
            and (version >= 2 or name != "qb_publication_events")
            and (version >= 4 or name not in ASSIGNMENT_TABLES)]


def _seal_trigger(connection, require_explanation=True):
    connection.exec_driver_sql(f"""CREATE TRIGGER qb_revision_seal_valid BEFORE UPDATE OF sealed ON qb_revisions
        WHEN NEW.sealed=1 AND (
          length(trim(NEW.stem))=0 OR {"length(trim(NEW.explanation))=0 OR" if require_explanation else ""}
          (NEW.question_type='multiple_choice' AND (
            (SELECT COUNT(*) FROM qb_choices WHERE revision_id=NEW.id)<2 OR
            EXISTS(SELECT 1 FROM qb_choices WHERE revision_id=NEW.id AND length(trim(text))=0) OR
            NOT EXISTS(SELECT 1 FROM qb_answer_keys WHERE revision_id=NEW.id AND choice_id IS NOT NULL))) OR
          (NEW.question_type='numeric' AND (
            EXISTS(SELECT 1 FROM qb_choices WHERE revision_id=NEW.id) OR
            NOT EXISTS(SELECT 1 FROM qb_answer_keys WHERE revision_id=NEW.id AND length(trim(numeric_answer))>0))))
        BEGIN SELECT RAISE(ABORT, 'Question snapshot is incomplete'); END""")


def _triggers(connection):
    connection.exec_driver_sql("""CREATE TRIGGER qb_revision_insert_unsealed BEFORE INSERT ON qb_revisions
        WHEN NEW.sealed=1 BEGIN SELECT RAISE(ABORT, 'Assemble answers before sealing'); END""")
    _seal_trigger(connection)
    for event in ("INSERT", "UPDATE"):
        connection.exec_driver_sql(f"""CREATE TRIGGER qb_publish_{event.lower()} BEFORE {event} ON qb_questions
          WHEN NEW.status='published' AND COALESCE((SELECT sealed FROM qb_revisions WHERE id=NEW.published_revision_id),0)!=1
          BEGIN SELECT RAISE(ABORT, 'Publish only a complete sealed revision'); END""")
    # Sealed revisions are snapshots. Correcting content means a new revision.
    for event in ("UPDATE", "DELETE"):
        connection.exec_driver_sql(f"""CREATE TRIGGER qb_revision_no_{event.lower()}
        BEFORE {event} ON qb_revisions WHEN OLD.sealed = 1
        BEGIN SELECT RAISE(ABORT, 'Sealed question revisions are immutable'); END""")
        connection.exec_driver_sql(f"""CREATE TRIGGER qb_attempt_no_{event.lower()}
        BEFORE {event} ON qb_attempts
        BEGIN SELECT RAISE(ABORT, 'Question attempts are immutable'); END""")
    for table in ("qb_choices", "qb_answer_keys"):
        for event in ("INSERT", "UPDATE", "DELETE"):
            checks = []
            if event != "INSERT": checks.append("(SELECT sealed FROM qb_revisions WHERE id=OLD.revision_id)=1")
            if event != "DELETE": checks.append("(SELECT sealed FROM qb_revisions WHERE id=NEW.revision_id)=1")
            connection.exec_driver_sql(f"""CREATE TRIGGER {table}_no_{event.lower()}
            BEFORE {event} ON {table} WHEN {' OR '.join(checks)}
            BEGIN SELECT RAISE(ABORT, 'Sealed question answers are immutable'); END""")
    connection.exec_driver_sql("""CREATE TRIGGER qb_attempt_requires_snapshot
        BEFORE INSERT ON qb_attempts
        WHEN COALESCE((SELECT sealed FROM qb_revisions WHERE id=NEW.revision_id),0) != 1
        BEGIN SELECT RAISE(ABORT, 'Attempts require a sealed revision'); END""")


def upgrade(engine):
    with engine.connect() as connection:
        connection.execute(text("BEGIN IMMEDIATE"))
        try:
            actual = {n for n in inspect(connection).get_table_names() if n.startswith("qb_")}
            if actual:
                if "qb_schema_versions" not in actual:
                    raise ValueError("Incomplete Question Bank schema.")
                versions = list(connection.scalars(select(models.SchemaVersion.version).order_by(models.SchemaVersion.version)))
                if versions not in ([1], [1,2], [1,2,3], [1,2,3,4], [1,2,3,4,5]):
                    raise ValueError("Unsupported Question Bank schema version.")
                validate_schema(connection, versions[-1])
            else:
                Base.metadata.create_all(connection, tables=tables(1))
                seed(connection)
                _triggers(connection)
                connection.execute(models.SchemaVersion.__table__.insert().values(version=1))
                versions = [1]
            if versions == [1]:
                models.PublicationEvent.__table__.create(connection)
                for event in ("UPDATE", "DELETE"):
                    connection.exec_driver_sql(f"CREATE TRIGGER qb_publication_no_{event.lower()} BEFORE {event} ON qb_publication_events BEGIN SELECT RAISE(ABORT, 'Publication history is immutable'); END")
                connection.execute(models.SchemaVersion.__table__.insert().values(version=2))
            if len(versions) < 3:
                connection.exec_driver_sql('DROP TRIGGER qb_revision_seal_valid')
                _seal_trigger(connection, require_explanation=False)
                connection.execute(models.SchemaVersion.__table__.insert().values(version=3))
            if len(versions) < 4:
                for table in (models.Assignment, models.AssignmentItem, models.AssignmentRecipient, models.AssignmentAttempt):
                    table.__table__.create(connection)
                for table in ASSIGNMENT_TABLES:
                    for event in ('UPDATE', 'DELETE'):
                        connection.exec_driver_sql(f"CREATE TRIGGER {table}_no_{event.lower()} BEFORE {event} ON {table} BEGIN SELECT RAISE(ABORT, 'Assignment history is immutable'); END")
                connection.execute(models.SchemaVersion.__table__.insert().values(version=4))
            if len(versions) < 5:
                models.MediaContent.__table__.create(connection)
                for table in ('qb_media', 'qb_media_content'):
                    for event in ('UPDATE', 'DELETE'):
                        connection.exec_driver_sql(f"CREATE TRIGGER {table}_no_{event.lower()} BEFORE {event} ON {table} BEGIN SELECT RAISE(ABORT, 'Question images are immutable'); END")
                connection.execute(models.SchemaVersion.__table__.insert().values(version=5))
            validate_schema(connection)
            connection.commit()
        except Exception:
            connection.rollback()
            raise


def downgrade_empty(engine):
    """Rollback only an unused foundation. Never erase question/activity records."""
    with engine.connect() as connection:
        connection.execute(text("BEGIN IMMEDIATE"))
        try:
            names = {n for n in inspect(connection).get_table_names() if n.startswith("qb_")}
            if not names:
                connection.commit()
                return
            if names != {t.name for t in tables()} or list(connection.scalars(select(models.SchemaVersion.version).order_by(models.SchemaVersion.version))) != list(range(1, VERSION+1)):
                raise ValueError("Unsupported Question Bank schema; rollback refused.")
            seed_tables = {"qb_schema_versions", "qb_banks", "qb_sections", "qb_domains", "qb_skills"}
            for name in names - seed_tables:
                if connection.exec_driver_sql(f'SELECT 1 FROM "{name}" LIMIT 1').first():
                    raise ValueError("Question Bank contains records; use backup recovery instead of destructive rollback.")
            # Dependency order, including the question/revision circular pointers.
            for name in ("qb_assignment_attempts", "qb_assignment_recipients", "qb_assignment_items", "qb_assignments", "qb_publication_events", "qb_bookmarks", "qb_attempts", "qb_answer_keys", "qb_choices", "qb_questions", "qb_revisions", "qb_media_content", "qb_media", "qb_sources", "qb_skills", "qb_domains", "qb_sections", "qb_banks", "qb_schema_versions"):
                Base.metadata.tables[name].drop(connection)
            connection.commit()
        except Exception:
            connection.rollback()
            raise
