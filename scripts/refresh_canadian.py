"""Manual bounded metadata/text capture for editorially selected public-domain books."""
import datetime,json,pathlib,subprocess,re,urllib.parse
ROOT=pathlib.Path(__file__).resolve().parents[1]
def get(url):
    raw=subprocess.run(['curl','--location','--fail','--silent','--show-error','--max-time','45',url],check=True,capture_output=True).stdout
    if len(raw)>6000000: raise ValueError('Response exceeds 6 MB')
    return raw

def prepare(text):
    start=re.search(r'\*\*\*\s*START OF (?:THE|THIS) PROJECT GUTENBERG.*?\*\*\*',text,re.I|re.S)
    end=re.search(r'\*\*\*\s*END OF (?:THE|THIS) PROJECT GUTENBERG',text,re.I)
    if start and end and end.start()>start.end(): text=text[start.end():end.start()]
    else:
        # Older mirrors use END OF THE PROJECT GUTENBERG EBOOK without stars.
        end=re.search(r'End of (?:The |the )?Project Gutenberg',text)
        if end:text=text[:end.start()]
    words=re.findall(r"[\w]+(?:['’–-][\w]+)*",text)
    paragraphs=[' '.join(p.split()) for p in re.split(r'\n\s*\n',text)]
    candidates=[p for p in paragraphs if 65<=len(p.split())<=160 and not re.search(r'gutenberg|license|copyright|e-?text',p,re.I)]
    if not candidates or len(words)<1000: raise ValueError('Text did not contain readable book passages')
    # Evenly spread a small discovery sample; not a replacement ebook.
    sample=[{'index':i+1,'text':candidates[round(i*(len(candidates)-1)/min(23,len(candidates)-1))]} for i in range(min(24,len(candidates)))] if len(candidates)>1 else [{'index':1,'text':candidates[0]}]
    return len(words),sample

def capture(config):
    checked=datetime.datetime.now(datetime.timezone.utc).isoformat();books=[]
    for entry in config['books']:
        id=entry['id']
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,199}',id):raise ValueError('Invalid identifier')
        data=json.loads(get('https://archive.org/metadata/'+id));meta=data.get('metadata',{})
        if meta.get('possible-copyright-status')!='NOT_IN_COPYRIGHT' or meta.get('copyright-region')!='US':raise ValueError('Expected explicit US public-domain metadata')
        files=[f for f in data['files'] if str(f.get('private','')).lower() not in ('true','1')]
        plain=next((f for f in files if f.get('format')=='Text' and f['name'].endswith('.txt')),None)
        if not plain:raise ValueError('No plain text mirror')
        url='https://archive.org/download/'+id+'/'+urllib.parse.quote(plain['name'])
        raw=get(url);text=raw.decode('utf-8-sig',errors='replace');words,passages=prepare(text)
        epub_source=entry.get('epubCatalogue','');epub_offered=False
        if epub_source:
            if not re.fullmatch(r'https://standardebooks\.org/ebooks/[a-z0-9-]+/[a-z0-9-]+',epub_source):raise ValueError('Unsupported EPUB catalogue URL')
            html=get(epub_source).decode('utf-8');epub_offered=bool(re.search(r'href="[^"]+\.epub"',html))
        books.append({'epubCatalogue':epub_source,'epubOffered':epub_offered,'epubCatalogueCheckedAt':checked if epub_source else None,**entry,'title':meta.get('title',id),'author':meta.get('creator',''),'checkedAt':checked,'wordCount':words,'passages':passages,'epubListed':any('epub' in f.get('format','').lower() for f in files),'source':'https://archive.org/details/'+id,'textSource':url,'formatsSource':'https://www.gutenberg.org/ebooks/'+str(entry['gutenbergId']),'rights':'Mirror records NOT_IN_COPYRIGHT in the United States; confirm rights where you are.','wordCountMethod':'Approximate words in mirrored plain text, excluding recognized Gutenberg licence delimiters; may include front matter.'})
    return {'schema':'bookgraveyard.canadian.v1','checkedAt':checked,'books':books}
if __name__=='__main__':
    result=capture(json.loads((ROOT/'web/canadian-config.json').read_text()));target=ROOT/'web/data/canadian.json';temporary=target.with_suffix('.tmp');temporary.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');temporary.replace(target);print('Saved',len(result['books']),'books and bounded passage samples')
