"""Run the local pre-push checks without importing the working application."""
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    node = shutil.which('node')
    git = shutil.which('git')
    if not node or not git:
        print('Install Node.js and Git before running the complete check.', file=sys.stderr)
        return 1
    commands = [
        ('Isolated Python tests', [sys.executable, 'scripts/verify.py']),
        ('JavaScript behavior tests', [node, '--test', *[str(p.relative_to(ROOT)) for p in sorted((ROOT / 'tests').glob('*.cjs'))]]),
        ('Dependency compatibility', [sys.executable, '-m', 'pip', 'check']),
        ('Unstaged whitespace', [git, 'diff', '--check']),
        ('Staged whitespace', [git, 'diff', '--cached', '--check']),
    ]
    for label, command in commands:
        print(f'\n{label}', flush=True)
        result = subprocess.run(command, cwd=ROOT)
        if result.returncode:
            print(f'Failed: {label}. No commit or push was performed.', file=sys.stderr)
            return result.returncode
    print('\nAll local checks passed. Review staged files before committing and pushing.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
