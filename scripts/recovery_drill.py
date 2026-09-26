"""Measure recovery on an automatically deleted fictional 30-student dataset."""
from pathlib import Path
import json
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.isolated import isolated_imports
from scripts.rehearse import rehearse
from scripts.backup import backup, restore


if __name__ == '__main__':
    with isolated_imports(), tempfile.TemporaryDirectory(prefix='sat-factory-recovery-') as folder:
        root = Path(folder)
        rehearse(root)
        snapshot = backup(root / 'fictional.db', root / 'backups', keep=14)
        result = restore(snapshot['bundle'], root / 'restored.sqlite3')
        result.pop('destination')
        print(json.dumps({'dataset':'fictional; 30 students; generated and deleted in temporary storage', **result}, indent=2))
