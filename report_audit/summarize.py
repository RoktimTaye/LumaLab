import json
from collections import Counter
from pathlib import Path
from zipfile import ZipFile
from lxml import etree as E
d=json.loads(Path('report_audit/audit.json').read_text(encoding='utf-8')); ps=d['paragraphs']
for style in Counter(p['style'] for p in ps):
    rows=[p for p in ps if p['style']==style and p['text']]
    print('\nSTYLE',style,len(rows))
    print('ALIGN',Counter(p['p'].get('jc',{}).get('val','left') for p in rows))
    print('SPACING',Counter(str(p['p'].get('spacing')) for p in rows).most_common(8))
    print('SIZE',Counter(str(r['fmt'].get('sz')) for p in rows for r in p['runs']))
    if style!='Normal':
        for p in rows: print(p['i'],p['text'])
print('\nNORMAL SAMPLES')
for p in ps[70:120]+ps[-35:]:
    if p['text']: print(p['i'],p['text'][:350],p['p'].get('ind'),p['p'].get('jc'),[(r['text'][:45],r['fmt'].get('sz'),r['fmt'].get('b')) for r in p['runs']][:5])
print('UNDERLINE',[(p['i'],r['text'][:80],r['fmt']['u']) for p in ps for r in p['runs'] if 'u' in r['fmt']][:30])
print('SPACING ALL',Counter(str(p['p'].get('spacing')) for p in ps).most_common())
print('EXTRA FILES',d['extra'].keys())
z=ZipFile(r'C:\Users\Raktim\Downloads\BCA 4th Sem Report 63.docx'); ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}; root=E.fromstring(z.read('word/document.xml'))
print('TABLE XML',E.tostring(root.find('.//w:tbl',ns),pretty_print=True).decode()[:14000])
print('FIELDS',root.xpath('.//w:instrText/text()',namespaces=ns))
print('PAGE BREAKS',len(root.xpath('.//w:br[@w:type="page"]',namespaces=ns)))
print('DRAWINGS',len(root.findall('.//w:drawing',ns)))
print('NUMBERING',d['extra'].get('word/numbering.xml','none')[:5000])
