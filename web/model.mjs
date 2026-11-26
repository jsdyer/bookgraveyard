export const ORIGIN = 'https://openlibrary.org';
export const FIELDS = 'key,title,author_name,first_publish_year,edition_count,ebook_access,language';
const string = (v,max=500) => typeof v === 'string' ? v.slice(0,max) : '';
const strings = (v,limit=30) => Array.isArray(v) ? v.filter(x=>typeof x==='string').slice(0,limit).map(x=>x.slice(0,300)) : [];
const int = (v,fallback=0) => Number.isSafeInteger(v) && v>=0 ? v : fallback;
export const workKey = key => /^\/works\/OL\d+W$/.test(key||'') ? key : /^OL\d+W$/.test(key||'') ? `/works/${key}` : null;
export const editionKey = key => /^\/books\/OL\d+M$/.test(key||'') ? key : null;
export function validateConfig(c) {
  if (!c || c.source !== ORIGIN || !Array.isArray(c.presets)) throw Error('The source configuration must use Open Library.');
  for (const key of ['pageSize','editionPageSize']) if (!Number.isInteger(c[key]) || c[key]<1 || c[key]>50) throw Error(`${key} must be between 1 and 50.`);
  if (!(c.requestGapMs>=1100 && c.timeoutMs>=1000 && c.timeoutMs<=60000 && c.cacheMinutes>0 && c.maxShelfItems>0 && c.maxShelfItems<=1000 && c.maxImportBytes<=5000000)) throw Error('Check the configured request and storage limits.');
  searchURL(c.defaultSearch,1,c);
  for (const preset of c.presets) searchURL({...c.defaultSearch,...preset},1,c);
  return c;
}
export function searchURL(input,page=1,config={pageSize:12}) {
  const query=string(input.query,250).trim();
  if (!query) throw Error('Enter a title, author, subject or a few search words.');
  if (!['all','title','author','subject'].includes(input.field)) throw Error('Choose a valid search field.');
  const years=[input.from,input.to].map(v=>String(v??'').trim());
  for (const y of years) if (y && (!/^\d{1,4}$/.test(y) || Number(y)<1 || Number(y)>9999)) throw Error('Enter a publication year between 1 and 9999, or leave it blank.');
  if (years.every(Boolean) && Number(years[0])>Number(years[1])) throw Error('The first year must be before the last year.');
  const url=new URL('/search.json',ORIGIN); const clauses=[];
  if(input.field==='all') clauses.push(`(${query})`); else url.searchParams.set(input.field,query);
  if(years.some(Boolean)) clauses.push(`first_publish_year:[${years[0]||'*'} TO ${years[1]||'*'}]`);
  if(['public','borrowable','no_ebook'].includes(input.access)) clauses.push(`ebook_access:${input.access}`);
  if(clauses.length) url.searchParams.set('q',clauses.join(' AND '));
  if(['old','new'].includes(input.sort)) url.searchParams.set('sort',input.sort);
  url.searchParams.set('fields',FIELDS);url.searchParams.set('limit',String(config.pageSize));
  url.searchParams.set('page',String(Math.max(1,Math.floor(page)||1)));
  return url.href;
}
export function sourceSearch(input,config) {const u=new URL(searchURL(input,1,config));u.pathname='/search';u.searchParams.delete('fields');return u.href;}
export function editionsURL(key,offset=0,limit=20){if(!workKey(key)) throw Error('Invalid Open Library work.');const u=new URL(`${workKey(key)}/editions.json`,ORIGIN);u.searchParams.set('limit',String(Math.min(50,Math.max(1,limit))));u.searchParams.set('offset',String(Math.max(0,Math.floor(offset)||0)));return u.href;}
export function normalizeWork(d){const key=workKey(d?.key);if(!key || !string(d.title)) return null;return {key,title:string(d.title),authors:strings(d.author_name??d.authors),firstYear:int(d.first_publish_year??d.firstYear,null),editionCount:int(d.edition_count??d.editionCount),access:['public','borrowable','no_ebook','printdisabled'].includes(d.ebook_access??d.access)?(d.ebook_access??d.access):'unknown',languages:strings(d.language??d.languages,20)};}
export function normalizeEdition(d){const key=editionKey(d?.key);if(!key)return null;return {key,title:string(d.title)||'Untitled edition',date:string(d.publish_date??d.date,100),publishers:strings(d.publishers),places:strings(d.publish_places??d.places),pages:int(d.number_of_pages??d.pages,null),pagination:string(d.pagination,100),format:string(d.physical_format??d.format,100),isbn:strings([...(d.isbn_13||[]),...(d.isbn_10||[]),...(d.isbn||[])],10),oclc:strings(d.oclc_numbers??d.oclc,10),lccn:strings(d.lccn,10),languages:Array.isArray(d.languages)?d.languages.map(l=>typeof l==='string'?l:string(l?.key).replace('/languages/','')).filter(Boolean).slice(0,20):[]};}
export function normalizeSearch(raw){if(!raw || !Array.isArray(raw.docs)) throw Error('Open Library returned an unexpected search response.');const records=raw.docs.map(normalizeWork).filter(Boolean);return {total:int(raw.numFound??raw.num_found),exact:raw.numFoundExact!==false,records,ignoredCount:raw.docs.length-records.length};}
export const accessLabel = value => ({public:'Readable copy listed',borrowable:'Borrowing listed',no_ebook:'Catalogue record',printdisabled:'Restricted access',unknown:'Access not specified'}[value]||'Access not specified');
export function validateReceipt(data,max=200){if(data?.schema!=='bookgraveyard/v1' || !Array.isArray(data.records) || data.records.length>max || !Number.isFinite(Date.parse(data.capturedAt))) throw Error('Choose a Book Graveyard receipt or reading-list JSON file.');const records=data.records.map(normalizeWork);if(records.some(x=>!x))throw Error('The imported file contains an invalid book record.');let query=null;if(data.query && typeof data.query==='object') {query={query:string(data.query.query,250),field:string(data.query.field),from:string(data.query.from,4),to:string(data.query.to,4),access:string(data.query.access),sort:string(data.query.sort)};searchURL(query);}
return {schema:'bookgraveyard/v1',kind:data.kind==='shelf'?'shelf':'search',capturedAt:new Date(data.capturedAt).toISOString(),query,page:int(data.page,1)||1,pageSize:Number.isInteger(data.pageSize)&&data.pageSize>=1&&data.pageSize<=50?data.pageSize:Math.min(50,Math.max(1,records.length||12)),total:int(data.total,records.length),records};}
export function makeReceipt(records,query=null,page=1,total=records.length,kind='search',capturedAt=new Date().toISOString(),pageSize=12){return validateReceipt({schema:'bookgraveyard/v1',kind,capturedAt,query,page,pageSize,total,records},1000);}
export function addToShelf(shelf,book,max=200){const item=normalizeWork(book);if(!item)throw Error('Invalid book.');if(shelf.some(x=>x.key===item.key)) return shelf;if(shelf.length>=max)throw Error(`Your shelf holds up to ${max} books. Export it before starting another.`);return [...shelf,item];}
export function csv(records){const cell=v=>'"'+String(v??'').replaceAll('"','""')+'"';return [['Title','Authors','First publication year','Reported editions','Access','Open Library'],...records.map(r=>[r.title,r.authors.join('; '),r.firstYear??'',r.editionCount,accessLabel(r.access),ORIGIN+r.key])].map(row=>row.map(v=>cell(/^[\t\r\n ]*[=+@-]/.test(String(v))?'\''+v:v)).join(',')).join('\r\n');}
