from zipfile import ZipFile
from lxml import etree as E
from collections import Counter
import json
from pathlib import Path

src=Path(r'C:\Users\Raktim\Downloads\BCA 4th Sem Report 63.docx')
out=Path('report_audit'); out.mkdir(exist_ok=True)
z=ZipFile(src); ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
def read(n): return E.fromstring(z.read(n))
def vals(el):
    if el is None: return {}
    d={}
    for c in el:
        k=E.QName(c).localname
        d[k]={E.QName(a).localname:b for a,b in c.attrib.items()} or True
    return d
styles=read('word/styles.xml'); doc=read('word/document.xml')
sd={s.get('{'+ns['w']+'}styleId'):s for s in styles.findall('w:style',ns)}
def chain(sid):
    if not sid or sid not in sd: return []
    s=sd[sid]; b=s.find('w:basedOn',ns)
    return (chain(b.get('{'+ns['w']+'}val')) if b is not None else [])+[s]
defaults=styles.find('w:docDefaults',ns)
dp=vals(defaults.find('w:pPrDefault/w:pPr',ns)); dr=vals(defaults.find('w:rPrDefault/w:rPr',ns))
rows=[]; fonts=Counter(); sizes=Counter(); props=Counter()
for i,p in enumerate(doc.findall('.//w:p',ns)):
    text=''.join(p.xpath('.//w:t/text()',namespaces=ns))
    ps=p.find('w:pPr/w:pStyle',ns); sid=ps.get('{'+ns['w']+'}val') if ps is not None else 'Normal'
    pp=dp.copy(); rp=dr.copy()
    for s in chain(sid): pp.update(vals(s.find('w:pPr',ns))); rp.update(vals(s.find('w:rPr',ns)))
    pp.update(vals(p.find('w:pPr',ns)))
    runs=[]
    for r in p.findall('w:r',ns):
        t=''.join(r.xpath('.//w:t/text()',namespaces=ns))
        rr=rp.copy(); rs=r.find('w:rPr/w:rStyle',ns)
        if rs is not None:
            for s in chain(rs.get('{'+ns['w']+'}val')): rr.update(vals(s.find('w:rPr',ns)))
        rr.update(vals(r.find('w:rPr',ns)))
        if t:
            runs.append({'text':t,'fmt':rr})
            fonts[str(rr.get('rFonts'))]+=len(t); sizes[str(rr.get('sz'))]+=len(t)
    row={'i':i,'text':text,'style':sid,'p':pp,'runs':runs,'table':bool(p.xpath('ancestor::w:tbl',namespaces=ns))}
    rows.append(row)
    if text: props[json.dumps(pp,sort_keys=True)]+=1
sections=[E.tostring(s,pretty_print=True).decode() for s in doc.findall('.//w:sectPr',ns)]
extra={}
for name in z.namelist():
    if name.startswith(('word/header','word/footer')) and name.endswith('.xml') or name in ['word/numbering.xml','docProps/app.xml','word/theme/theme1.xml']:
        extra[name]=z.read(name).decode()
data={'defaults':{'p':dp,'r':dr},'fonts':fonts,'sizes':sizes,'paragraph_properties':props,'sections':sections,'paragraphs':rows,'extra':extra}
(out/'audit.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
with (out/'paragraphs.txt').open('w',encoding='utf-8') as f:
    for p in rows:
        if not p['text']: continue
        fmts=Counter(json.dumps(r['fmt'],sort_keys=True) for r in p['runs'])
        f.write(f"{p['i']} [{p['style']}] {'TABLE ' if p['table'] else ''}{p['text']}\n P {json.dumps(p['p'])}\n R {json.dumps(fmts)}\n")
print(json.dumps({'paragraphs':len(rows),'nonempty':sum(bool(p['text']) for p in rows),'defaults':data['defaults'],'fonts':fonts,'sizes':sizes,'sections':sections,'common_p':props.most_common(12),'tables':len(doc.findall('.//w:tbl',ns))},indent=2))
