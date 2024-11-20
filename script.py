import argparse
parser = argparse.ArgumentParser()
parser.add_argument('input')
args = parser.parse_args()

import re, requests
import pandas as pd
from tqdm import tqdm
import difflib
import functools, operator
from lxml import etree

@functools.cache
def get_core_rank(acronym):
    response = requests.get(f'http://portal.core.edu.au/conf-ranks/?search={acronym}&by=acronym&source=all')
    response.raise_for_status()
    tree = etree.HTML(response.content)
    rank = tree.xpath('//table//tr[2]/td[4]/text()')
    if len(rank) == 0: return 'n/a'
    rank = rank[0].strip()
    if rank.startswith('National'): return 'n/a'
    return rank

papers = []
num_lines = sum(1 for _ in open(args.input))
for line in tqdm(open(args.input), total=num_lines):
    match = re.search(r'^\s*title\s*=\s*\{(.*)\},$', line)
    if match:
        title = match.group(1)
        title = title.replace('{', '').replace('}', '')
        url = 'https://api.crossref.org/works'
        params = {'query.title': title}
        response = requests.get(url, params=params)
        response.raise_for_status()
        listing = response.json()['message']
        for paper in listing['items']:
            # find results whose title is very similar to the title searched
            similarity = difflib.SequenceMatcher(None, title.lower(), paper['title'][0].lower())
            if similarity.ratio() < 0.9:
                continue
            # ignore preprint papers (not published anywhere)
            if 'published' not in paper or 'container-title' not in paper:
                continue
            papers.append({
                'year': paper['published']['date-parts'][0][0],
                'citations': paper['is-referenced-by-count'],
                'CORE': '' if paper['type'] == 'journal-article' else get_core_rank(paper['acronym']) if paper['type'] == 'book-chapter' else get_core_rank(paper['container-title'][0].split()[-1][1:-1]),
                'title': paper['title'][0],
                'where': paper['container-title'][0].replace('&amp;', '&'),
                'type': paper['type'],
                'link': paper['URL'],
            })
papers = sorted(papers, key=operator.itemgetter('year', 'citations', 'title'))
df = pd.DataFrame(papers)
df.to_excel(args.input[:-3] + 'xlsx')
