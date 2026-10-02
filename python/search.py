#!/usr/bin/env python3
"""Offline, section-level search of local Django Markdown documentation."""
import argparse
import json
import os
import hashlib
import re
import sqlite3
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = Path(__file__).resolve().parent / 'index.sqlite3'
STOP = set('how do i to a an the of in for me my is what does can with django please show code documentation docs'.split())
ALIASES = {'build': 'create', 'creating': 'create', 'writing': 'write', 'models': 'model', 'views': 'view', 'fields': 'field', 'queries': 'query'}


def sections(text):
    """Yield heading, breadcrumb, source line, and body; ignore fenced headings."""
    stack, body = [], []
    heading, line, fence = '', 1, None
    for number, raw in enumerate(text.splitlines(), 1):
        marker = re.match(r'^\s{0,3}(`{3,}|~{3,})', raw)
        if marker:
            run = marker[1]
            if fence is None:
                fence = run
            elif run[0] == fence[0] and len(run) >= len(fence):
                fence = None
        match = None if fence else re.match(r'^(#{1,6})\s+(.+)', raw)
        if match:
            if heading:
                yield heading, ' › '.join(x[1] for x in stack), line, '\n'.join(body)
            depth, heading = len(match[1]), match[2]
            while stack and stack[-1][0] >= depth:
                stack.pop()
            stack.append((depth, heading))
            line, body = number, []
        else:
            body.append(raw)
    if heading:
        yield heading, ' › '.join(x[1] for x in stack), line, '\n'.join(body)


def terms(text):
    return [ALIASES.get(w, w) for w in re.findall(r'[a-z0-9_]+', text.lower()) if w not in STOP]


def connect():
    DB.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB)


def index():
    with connect() as conn:
        conn.execute('BEGIN IMMEDIATE')
        conn.execute('CREATE TABLE IF NOT EXISTS metadata (root TEXT)')
        conn.execute('DELETE FROM metadata')
        conn.execute('INSERT INTO metadata VALUES (?)', (str(ROOT),))
        conn.execute('DROP TABLE IF EXISTS sections')
        conn.execute("CREATE VIRTUAL TABLE sections USING fts5(heading, breadcrumb, body, keywords, path UNINDEXED, line UNINDEXED, tokenize='porter unicode61')")
        count = 0
        for path in sorted(ROOT.rglob('*.md')):
            relative = path.relative_to(ROOT)
            if relative.parts[0] in {'docsearch', 'releases', 'internals'} or any(p.startswith('.') for p in relative.parts):
                continue
            if str(relative) == 'intro/contributing.md':
                continue
            for heading, breadcrumb, line, body in sections(path.read_text()):
                keywords = ' '.join(terms(breadcrumb + ' ' + body))
                conn.execute('INSERT INTO sections VALUES (?, ?, ?, ?, ?, ?)', (heading, breadcrumb, body, keywords, str(relative), line))
                count += 1
    return count


def search(query, limit=10):
    rebuild = not DB.exists()
    if not rebuild:
        with connect() as conn:
            try:
                rebuild = conn.execute('SELECT root FROM metadata').fetchone() != (str(ROOT),)
            except sqlite3.OperationalError:
                rebuild = True
    if rebuild:
        index()
    words = terms(query)
    if not words:
        return []
    expression = ' OR '.join('"' + w + '"' for w in dict.fromkeys(words))
    results = []
    with connect() as conn:
        rows = conn.execute('SELECT heading, breadcrumb, body, path, line, bm25(sections, 8, 4, 1, 0.5) FROM sections WHERE sections MATCH ? ORDER BY bm25(sections, 8, 4, 1, 0.5) LIMIT 300', (expression,)).fetchall()
    practical = bool(re.search(r'\b(how|build|create|write|code|example)\b', query.lower()))
    for heading, breadcrumb, body, path, line, rank in rows:
        score = -rank
        heading_words = set(terms(breadcrumb))
        score *= 1 + len(set(words) & heading_words)
        if practical:
            if set(terms(breadcrumb.split(' › ')[0])) == (set(words) - {'create', 'write', 'example'}):
                score *= 3
            if {'create', 'model'} <= set(words) and set(terms(heading)) == {'create', 'model'}:
                score *= 4
            if path.startswith(('intro/', 'topics/', 'howto/')):
                score *= 2
            if re.search(r'example|simple|creating|writing', heading, re.I):
                score *= 2
            if '```' in body:
                score *= 1.3
        excerpt = re.sub(r'<[^>]+>', '', body)
        excerpt = re.sub(r'\[([^\]]+)\]\([^)]*\)', r'\1', excerpt)
        excerpt = ' '.join(excerpt.replace('`', '').split())[:240]
        results.append(dict(title=breadcrumb, path=str(ROOT / path), line=int(line), excerpt=excerpt, score=score))
    return sorted(results, key=lambda r: r['score'], reverse=True)[:limit]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    global ROOT, DB
    parser.add_argument('--docs', required=True, type=Path, help='Django Markdown root')
    parser.add_argument('--database', type=Path, help='Index location (defaults to user cache)')
    parser.add_argument('query', nargs='*')
    parser.add_argument('--index', action='store_true', help='Rebuild after updating the docs')
    parser.add_argument('--json', action='store_true')
    parser.add_argument('--limit', type=int, default=10)
    parser.add_argument('--open', type=int, metavar='N', help='Open result N in Neovim')
    args = parser.parse_args()
    ROOT = args.docs.expanduser().resolve()
    if not ROOT.is_dir() or not (ROOT / 'topics').is_dir() or not (ROOT / 'ref').is_dir():
        parser.error('--docs must be a Django Markdown documentation root containing topics/ and ref/')
    if args.limit < 1:
        parser.error('--limit must be positive')
    cache = Path(os.environ.get('XDG_CACHE_HOME', str(Path.home() / '.cache')))
    key = hashlib.sha256(str(ROOT).encode()).hexdigest()[:16]
    DB = args.database.expanduser().resolve() if args.database else cache / 'django-docs.nvim' / (key + '.sqlite3')
    if args.index:
        print(f'Indexed {index()} sections into {DB}')
    if not args.query:
        if not args.index:
            parser.error('Provide a search query or --index')
        return
    results = search(' '.join(args.query), args.limit)
    if args.open is not None:
        if not 1 <= args.open <= len(results):
            parser.error('Result number is out of range')
        result = results[args.open - 1]
        subprocess.run(['nvim', '+' + str(result['line']), result['path']], check=True)
    elif args.json:
        print(json.dumps(results, indent=2))
    else:
        for number, result in enumerate(results, 1):
            print(f"{number}. {result['title']}\n   {Path(result['path']).relative_to(ROOT)}:{result['line']}\n   {result['excerpt']}\n")
        if not results:
            print('No matches. Try a Django API name or a more specific topic.')


if __name__ == '__main__':
    main()
