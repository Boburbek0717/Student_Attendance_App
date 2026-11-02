"""Owner-supplied portfolio facts for the public homepage; no course records."""
from app.result_content import RESULTS

TUTOR = {
    'name': 'Boburbek Noraliyev',
    'first_name': 'Boburbek',
    'sat': 1430,
    'ielts': '8.5',
    'university': 'University of Szeged',
    'city': 'Szeged, Hungary',
    'teaching_since': 2024,
    # Shown only when filled in, e.g. {'label': 'Message me on Telegram', 'href': 'https://t.me/<handle>'}.
    'contact': None,
}

QUOTED_IDS = (1, 2, 3)


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
