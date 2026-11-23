#!/usr/bin/env python3
"""Refresh one small opening search and one edition page, never the whole catalogue."""
import json
from datetime import datetime, timezone
from pathlib import Path
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import re

ROOT = Path(__file__).resolve().parents[1]


def fetch(url, agent, timeout):
    request = Request(url, headers={'User-Agent': agent, 'Accept': 'application/json'})
    with urlopen(request, timeout=timeout) as response:
        if response.status != 200 or 'json' not in response.headers.get('Content-Type', ''):
            raise ValueError('The source did not return JSON. Existing data is unchanged.')
        data = json.load(response)
        print(f"HTTP {response.status}; CORS={response.headers.get('Access-Control-Allow-Origin', 'not present')}; {url}")
        return data


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')


def main():
    config = json.loads((ROOT/'web/config.json').read_text())
    if config['source'] != 'https://openlibrary.org':
        raise ValueError('This collector is scoped to Open Library.')
    query = config['defaultSearch']
    parameters = {'fields': 'key,title,author_name,first_publish_year,edition_count,ebook_access,language',
                  'limit': config['pageSize'], 'page': 1}
    if not 1 <= parameters['limit'] <= 50:
        raise ValueError('pageSize must be between 1 and 50.')
    clauses = []
    if query['field'] == 'all':
        clauses.append('('+query['query']+')')
    elif query['field'] in ('title', 'author', 'subject'):
        parameters[query['field']] = query['query']
    else:
        raise ValueError('Invalid search field.')
    if query.get('from') or query.get('to'):
        clauses.append(f"first_publish_year:[{query.get('from') or '*'} TO {query.get('to') or '*'}]")
    if query.get('access') in ('public', 'borrowable', 'no_ebook'):
        clauses.append('ebook_access:'+query['access'])
    if clauses:
        parameters['q'] = ' AND '.join(clauses)
    if query.get('sort') in ('new', 'old'):
        parameters['sort'] = query['sort']
    url = config['source']+'/search.json?'+urlencode(parameters)
    result = fetch(url, config['refreshUserAgent'], config['timeoutMs']/1000)
    if not isinstance(result.get('docs'), list) or not result['docs'] or not isinstance(result.get('numFound', result.get('num_found')), int):
        raise ValueError('Invalid or empty search. Existing data is unchanged.')
    captured = now()
    seed = {'schema': 'bookgraveyard-opening/v1', 'capturedAt': captured, 'query': query,
            'sourceURL': url, 'search': result, 'editions': []}
    first = next((d for d in result['docs'] if re.fullmatch(r'/works/OL\d+W', d.get('key', '')) and d.get('edition_count', 0) > 1), None)
    if first:
        time.sleep(max(1.2, config['requestGapMs']/1000))
        edition_url = config['source']+first['key']+'/editions.json?'+urlencode({'limit': config['editionPageSize'], 'offset': 0})
        editions = fetch(edition_url, config['refreshUserAgent'], config['timeoutMs']/1000)
        if not isinstance(editions.get('entries'), list) or not editions['entries']:
            raise ValueError('Invalid editions response. Existing data is unchanged.')
        seed['editions'].append({'work': first['key'], 'capturedAt': now(), 'sourceURL': edition_url, 'data': editions})
    target = ROOT/'web/data/opening.json'
    target.parent.mkdir(exist_ok=True)
    staged = target.with_suffix('.tmp')
    staged.write_text(json.dumps(seed, ensure_ascii=False, indent=2)+'\n')
    staged.replace(target)
    print(f"Saved {len(result['docs'])} records and {len(seed['editions'])} edition pages at {captured}.")


if __name__ == '__main__':
    main()
