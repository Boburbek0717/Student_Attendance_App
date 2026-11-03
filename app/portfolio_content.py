"""Owner-supplied portfolio facts for the public homepage; no course records."""
from app.result_content import RESULTS

TUTOR = {
    'name': 'Boburbek Noraliyev',
    'first_name': 'Boburbek',
    'sat': 1430,
    'ielts': '8.5',
    'university': 'University of Szeged',
    'scholarship': 'Stipendium Hungaricum',
    'city': 'Szeged, Hungary',
    'teaching_since': 2024,
    # Shown only when filled in, e.g. {'label': 'Message me on Telegram', 'href': 'https://t.me/<handle>'}.
    'contact': None,
    # Links to free practice and the course portal; hidden while those parts are not in use.
    'app_links': False,
}

QUOTED_IDS = (1, 2, 3)

# The results page files each result under the kind of result its owner-supplied tag names.
RESULT_FILES = (
    {'key': 'top-totals', 'title': 'Top totals', 'intro': 'The three highest totals among my students.',
     'matches': lambda tag: tag.endswith(' TOTAL')},
    {'key': 'math', 'title': 'Math highlights', 'intro': 'Results led by the Math section.',
     'matches': lambda tag: 'MATH' in tag},
    {'key': 'from-scratch', 'title': 'Started from scratch', 'intro': 'Both began with no SAT preparation; one reached his score after four months of individual lessons.',
     'matches': lambda tag: tag == 'STARTED FROM SCRATCH'},
    {'key': 'persistence', 'title': 'Persistence paid off', 'intro': 'A target missed on the first attempt and reached on the next.',
     'matches': lambda tag: tag == 'PERSISTENCE PAID OFF'},
)

# The one visible line of proof on a report: verbatim from the student's own quote, or the owner's summary
# where it adds a fact the figures do not show. Full quotes stay behind the "Read the story" disclosure.
REPORT_PROOF = {
    1: '“I never imagined I could feel so comfortable with math.”',
    2: '“I achieved my score after just four months of individual lessons.”',
    3: '“I kept working hard, tried again, and earned a score high enough to qualify for a scholarship at a state university.”',
    5: 'Just 10 points from a perfect Math score.',
}


def portfolio_figures():
    """Figures derived from the published results, so the page cannot drift from them."""
    totals = [row['ebrw'] + row['math'] for row in RESULTS]
    best = max(RESULTS, key=lambda row: row['ebrw'] + row['math'])
    top_math = max(row['math'] for row in RESULTS)
    ranked = sorted(RESULTS, key=lambda row: (-(row['ebrw'] + row['math']), row['name']))
    return {
        'count': len(RESULTS),
        'average': f"{sum(totals) / len(totals):.1f}",
        'best': best,
        'best_total': best['ebrw'] + best['math'],
        'top_math': top_math,
        'top_math_count': sum(row['math'] == top_math for row in RESULTS),
        'ranked': [dict(row, total=row['ebrw'] + row['math']) for row in ranked],
        'quoted': [next(row for row in RESULTS if row['id'] == key) for key in QUOTED_IDS],
    }


def result_files():
    """Results grouped for the results page, highest total first; an unmatched tag gets its own file."""
    ranked = portfolio_figures()['ranked']
    files = [dict(file, results=[]) for file in RESULT_FILES]
    for row in ranked:
        home = next((file for file in files if file['matches'](row['tag'])), None)
        if home is None:
            home = {'key': f"tag-{row['id']}", 'title': row['tag'].capitalize(), 'intro': '', 'results': []}
            files.append(home)
        home['results'].append(dict(row, proof=REPORT_PROOF.get(row['id'], '')))
    return [{key: value for key, value in file.items() if key != 'matches'} for file in files if file['results']]
