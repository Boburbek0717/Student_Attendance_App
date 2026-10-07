"""Conservative, format-independent parsing of labelled multiple-choice worksheets.

Only source evidence is accepted: no inferred answers, difficulty or taxonomy.
Unknown text remains visible in the prompt rather than being silently discarded.
"""
import hashlib
import json
import re

META = re.compile(r'^(Assessment|Test|Section|Domain|Skill|Category|Topic|Difficulty|Question Difficulty)\s*:\s*(.+)$', re.I | re.M)
QUESTION = re.compile(r'^(?:Question\s+(?:ID\s*:?\s*)?|Q\s*)(\d+|[a-fA-F0-9]{8})\b[.):]?[ \t]*|^(\d+)[.)]\s+', re.I | re.M)
OPTION = re.compile(r'^\s*(?:\(([A-Z])\)|([A-Z])[.)])\s+', re.M)
ANSWER = re.compile(r'^(?:Correct\s+Answer|Answer)\s*:\s*\(?([A-D])\)?\s*$', re.I | re.M)
DIFFICULTIES = {'easy':'easy','medium':'medium','hard':'hard'}


def metadata(text):
    result = {}
    aliases = {'test':'section','category':'skill','topic':'skill','question difficulty':'difficulty'}
    for match in META.finditer(text):
        key = aliases.get(match[1].lower(), match[1].lower())
        value = ' '.join(match[2].split())
        if key in result and result[key] != value:
            raise ValueError('Conflicting metadata labels.')
        result[key] = value
    return result


def answer_key(text):
    """Return None for question pages; a key page must consist entirely of key rows."""
    if not re.match(r'^\s*(?:Answer Key|Answers)\s*:?\s*\n', text, re.I): return None
    lines = text.strip().splitlines()[1:]
    result = {}
    for line in lines:
        if not line.strip(): continue
        match = re.fullmatch(r'\s*(?:Question\s+|Q\s*)?([\w-]+)\s*[.):\-]?\s+\(?([A-D])\)?\s*', line, re.I)
        if not match or match[1] in result:
            raise ValueError('Ambiguous answer-key row or repeated number.')
        result[match[1]] = ord(match[2].upper()) - ord('A')
    if not result: raise ValueError('Empty answer key.')
    return result


def parse_questions(text, page, keys=None):
    if len(text) > 50000: raise ValueError('Page text exceeds supported limits.')
    keys = keys or {}
    markers = list(QUESTION.finditer(text))
    if not markers: raise ValueError('No numbered question boundaries found.')
    defaults = metadata(text[:markers[0].start()])
    # Unrecognized page heading text cannot safely be thrown away.
    if META.sub('', text[:markers[0].start()]).strip():
        raise ValueError('Unrecognized text before the first question.')
    items = []
    for i, marker in enumerate(markers):
        number = marker[1] or marker[2]
        block = text[marker.end():markers[i+1].start() if i+1<len(markers) else len(text)]
        info = dict(defaults, **metadata(block))
        if not all(info.get(k) for k in ('assessment','section','domain','skill','difficulty')):
            raise ValueError('Missing labelled assessment, section, domain, category or difficulty.')
        if info['difficulty'].lower() not in DIFFICULTIES:
            raise ValueError('Difficulty must explicitly be Easy, Medium or Hard.')
        section = {'math':'Math','reading and writing':'Reading and Writing','reading & writing':'Reading and Writing'}.get(info['section'].lower())
        if not section: raise ValueError('Section must explicitly identify Math or Reading and Writing.')
        answers = list(ANSWER.finditer(block))
        if len(answers) > 1: raise ValueError('Multiple answer labels in one question.')
        correct = ord(answers[0][1].upper())-ord('A') if answers else keys.get(number)
        if correct is None: raise ValueError('No supplied answer for a question.')
        if number in keys and keys[number] != correct: raise ValueError('Inline answer conflicts with answer key.')
        clean = META.sub('', ANSWER.sub('', block)).strip()
        explanation = ''
        split = re.split(r'^(?:Explanation|Rationale)\s*:\s*', clean, maxsplit=1, flags=re.I|re.M)
        if len(split)==2: clean, explanation = split
        options = list(OPTION.finditer(clean))
        if [(m[1] or m[2]) for m in options] != list('ABCD'):
            raise ValueError('Expected exactly four ordered A-D choices on separate lines.')
        prompt = clean[:options[0].start()].strip()
        choices = [clean[m.end():options[j+1].start() if j<3 else len(clean)].strip() for j,m in enumerate(options)]
        if not prompt or not all(choices): raise ValueError('Empty question or choice.')
        # Explicit passage/question labels are optional; otherwise preserve everything in the stem.
        passage = ''
        labelled = re.fullmatch(r'Passage\s*:\s*(.*?)\n(?:Prompt|Question)\s*:\s*(.+)', prompt, re.S|re.I)
        if labelled: passage,prompt = labelled.groups()
        digest = hashlib.sha256(json.dumps([passage,prompt,choices],ensure_ascii=False).encode()).hexdigest()[:24]
        items.append(dict(source_id='auto-'+digest, source_number=number, page=page,
            assessment=info['assessment'], section=section, domain=info['domain'], skill=info['skill'],
            difficulty=info['difficulty'].lower(), passage=passage, stem=prompt, choices=choices,
            answer=correct, explanation=explanation.strip(), review_status='needs_review',
            extraction_method='labelled-text', evidence='Explicit labels and supplied answer; verify PDF layout.'))
    return items


def parse_labelled_sqb(text, page):
    """Recognize SQB metadata without fixing the assessment, skill or prompt."""
    match=re.fullmatch(
        r'Question ID (?P<id>[a-fA-F0-9]{8})\s+ID: (?P=id)\s+(?P<body>.*?)\s+'
        r'ID: (?P=id) Answer\s+Correct Answer:\s*(?P<answer>[A-D])\s+Rationale\s+'
        r'(?P<explanation>.*?)\s+Question Difficulty:\s*(?P<difficulty>Easy|Medium|Hard)\s+'
        r'Assessment\s+(?P<assessment>.*?)\s+Test\s+(?P<section>.*?)\s+Domain\s+'
        r'(?P<domain>.*?)\s+Skill\s+(?P<skill>.*?)\s+Difficulty',text.strip(),re.S)
    if not match: return None
    labels='\n'.join(f"{name.capitalize()}: {' '.join(match[name].split())}" for name in
                     ('assessment','section','domain','skill','difficulty'))
    raw=labels+'\nQuestion 1\n'+match['body']+'\nAnswer: '+match['answer']+'\nExplanation: '+match['explanation']
    items=parse_questions(raw,page)
    if len(items)!=1: raise ValueError('Ambiguous SQB question boundaries.')
    item=items[0];item['source_id']=match['id'].lower();item.pop('source_number',None)
    item['evidence']='Explicit SQB metadata and supplied answer; verify extracted reading order.'
    return item
