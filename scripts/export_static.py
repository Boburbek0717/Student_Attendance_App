"""Render the public homepage and results page into plain files for a static host.

Uses an empty temporary database and a disposable secret; never reads live data.
Links into the course app (practice, portal) point at the hosted portfolio demo.
"""
import argparse
from pathlib import Path
import re
import secrets
import shutil
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.isolated import isolated_imports

APP_ORIGIN = 'https://sat-factory-portfolio-demo.onrender.com'
PAGES = {'/': 'index.html', '/results': 'results.html'}
# Root-relative links, rewritten so the pages work from any sub-path such as /<repo>/.
LINKS = [
    ('href="/results#', 'href="results.html#'),
    ('href="/results"', 'href="results.html"'),
    ('href="/#teacher"', 'href="./#about"'),
    ('href="/questions"', f'href="{APP_ORIGIN}/questions"'),
    ('href="/login"', f'href="{APP_ORIGIN}/login"'),
    ('href="/"', 'href="./"'),
    ('src="/static/', 'src="static/'),
]


def rewrite(html: str) -> str:
    html = re.sub(r'https?://testserver/static/', 'static/', html)
    for old, new in LINKS:
        html = html.replace(old, new)
    leftover = re.findall(r'(?:href|src)="/[^"]*"', html)
    if leftover:
        raise ValueError(f'Unhandled root-relative links: {sorted(set(leftover))}')
    return html


def export(destination: Path) -> list[Path]:
    from fastapi.testclient import TestClient
    with isolated_imports(), tempfile.TemporaryDirectory(prefix='sat-static-') as directory:
        from app.database import make_engine
        from app.main import create_app
        from app.web import APP_DIRECTORY
        engine = make_engine(str(Path(directory) / 'empty.sqlite3'))
        try:
            with TestClient(create_app(engine, secrets.token_hex(32))) as client:
                pages = {}
                for route, name in PAGES.items():
                    response = client.get(route)
                    response.raise_for_status()
                    pages[name] = rewrite(response.text)
        finally:
            engine.dispose()
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(APP_DIRECTORY / 'static', destination / 'static', ignore=shutil.ignore_patterns('vendor'))
    for name, html in pages.items():
        (destination / name).write_text(html, encoding='utf-8')
    (destination / '.nojekyll').write_text('', encoding='utf-8')
    return [destination / name for name in pages]


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('destination', nargs='?', default='output/static-site', help='Folder to replace with the site.')
    written = export(Path(parser.parse_args().destination))
    print('\n'.join(str(path) for path in written))


if __name__ == '__main__':
    main()
