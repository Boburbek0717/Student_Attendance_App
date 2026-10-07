"""Disposable PDF parser process: no application imports, database or network calls."""
import json
from pathlib import Path
import sys
from extract_sqb_pdf import extract

if __name__ == '__main__':
    try:
        result = extract(Path(sys.argv[1]), 'auto')
        # Do not relay raw parser errors or embedded PDF text as diagnostics.
        for rejected in result['rejected']:
            if rejected['reason'] not in {
                'Question uses a graph or table; visual content must be preserved before import.',
                'Missing or repeated SQB metadata.',
                'Question spans too many pages or includes unreadable pages.',
                'Duplicate source question ID in this document.',
                'Unknown image or difficulty mismatch; manual visual review is required.',
            }:
                rejected['reason'] = 'Unsupported layout, image, repeated ID or incomplete question. Review this page manually.'
        encoded = json.dumps(result, ensure_ascii=True)
        if len(encoded) > 2 * 1024 * 1024:
            raise ValueError('Output too large')
        Path(sys.argv[2]).write_text(encoded, encoding='utf-8')
    except Exception:
        sys.exit(1)
