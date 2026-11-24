from pathlib import Path
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_LINE_SPACING
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.shared import Inches, Pt
from PIL import Image

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / 'lumalab_report_content.md'
OUTPUT = ROOT / 'LumaLab Project Report.docx'

doc = Document()
sec = doc.sections[0]
sec.page_width = Inches(8.2677)
sec.page_height = Inches(11.6944)
sec.left_margin = Inches(1.0)
sec.right_margin = Inches(0.7826)
sec.top_margin = Inches(1.0396)
sec.bottom_margin = Inches(1.0569)
sec.header_distance = sec.top_margin
sec.footer_distance = sec.bottom_margin

def font(style, size, bold=False):
    style.font.name = 'Times New Roman'
    style.font.size = Pt(size)
    style.font.bold = bold
    style.font.color.rgb = None

normal = doc.styles['Normal']
font(normal, 12)
normal.paragraph_format.line_spacing = Pt(27.6)
normal.paragraph_format.line_spacing_rule = WD_LINE_SPACING.AT_LEAST
normal.paragraph_format.space_before = Pt(0)
normal.paragraph_format.space_after = Pt(0)

chapter = doc.styles.add_style('Report Chapter', WD_STYLE_TYPE.PARAGRAPH)
chapter.base_style = normal
font(chapter, 20, True)
chapter.paragraph_format.line_spacing = Pt(46)
chapter.paragraph_format.line_spacing_rule = WD_LINE_SPACING.AT_LEAST
chapter.paragraph_format.space_before = Pt(0)
chapter.paragraph_format.space_after = Pt(0)
chapter.paragraph_format.keep_with_next = True
chapter.paragraph_format.page_break_before = True
chapter.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER

sub = doc.styles.add_style('Report Section', WD_STYLE_TYPE.PARAGRAPH)
sub.base_style = normal
font(sub, 14, True)
sub.paragraph_format.line_spacing = Pt(32.2)
sub.paragraph_format.line_spacing_rule = WD_LINE_SPACING.AT_LEAST
sub.paragraph_format.space_before = Pt(6)
sub.paragraph_format.space_after = Pt(0)
sub.paragraph_format.keep_with_next = True

caption = doc.styles.add_style('Report Caption', WD_STYLE_TYPE.PARAGRAPH)
caption.base_style = normal
font(caption, 10)
caption.paragraph_format.line_spacing = Pt(15)
caption.paragraph_format.line_spacing_rule = WD_LINE_SPACING.AT_LEAST
caption.paragraph_format.space_before = Pt(4)
caption.paragraph_format.space_after = Pt(10)
caption.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
caption.paragraph_format.keep_together = True

toc = doc.styles.add_style('Report Contents', WD_STYLE_TYPE.PARAGRAPH)
toc.base_style = normal
font(toc, 12)
toc.paragraph_format.left_indent = Inches(0.25)
toc.paragraph_format.line_spacing = Pt(27.6)
toc.paragraph_format.line_spacing_rule = WD_LINE_SPACING.AT_LEAST

def body(t):
    p=doc.add_paragraph(t, 'Normal')
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.widow_control = True
    return p

def cover(t,size=12,bold=False,before=0):
    p=doc.add_paragraph()
    p.alignment=WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before=Pt(before)
    p.paragraph_format.line_spacing=Pt(27.6)
    p.paragraph_format.line_spacing_rule=WD_LINE_SPACING.AT_LEAST
    r=p.add_run(t)
    r.font.name='Times New Roman'; r.font.size=Pt(size); r.bold=bold
    return p

cover('A PROJECT REPORT ON',18,True)
cover('LUMALAB PHOTO EDITING SYSTEM',14,True,24)
cover('Submitted to:',12,False,28)
cover('CENTRE FOR COMPUTER SCIENCE AND APPLICATIONS',12,True,8)
cover('DIBRUGARH UNIVERSITY',12,True)
cover('In partial fulfilment of the requirements for the BCA fourth semester',12,False,18)
cover('Academic session: ____________________')
cover('Submitted by:',12,False,28)
cover('Student name: ______________________________')
cover('Roll number: _______________________________')
cover('Project guide: ______________________________',12,False,20)
cover('DIBRUGARH UNIVERSITY, ASSAM, INDIA',12,True,28)

doc.add_paragraph('CERTIFICATE', 'Report Chapter')
body('This page is reserved for the project guide and department to certify the completed report after reviewing the student details and project work.')
body('Student name: ______________________________    Roll number: ______________________________')
body('Project guide: ______________________________    Date: ______________________________')
body('Signature of project guide: ______________________________')

doc.add_paragraph('DECLARATION', 'Report Chapter')
body('I, ______________________________, declare that this report on LumaLab Photo Editing System describes the project work submitted for the BCA fourth semester. The source materials and project records used in the report are listed in the references.')
body('Student signature: ______________________________    Date: ______________________________')

lines = SOURCE.read_text(encoding='utf-8').splitlines()
chapters=[x[2:].strip() for x in lines if x.startswith('# ')]
doc.add_paragraph('CONTENTS', 'Report Chapter')
for c in chapters:
    doc.add_paragraph(c, 'Report Contents')

for line in lines:
    s=line.strip()
    if not s: continue
    if s.startswith('# '):
        doc.add_paragraph(s[2:], 'Report Chapter')
    elif s.startswith('## '):
        doc.add_paragraph(s[3:], 'Report Section')
    elif s.startswith('- '):
        p=doc.add_paragraph('•  '+s[2:], 'Normal')
        p.paragraph_format.left_indent=Inches(0.25)
        p.paragraph_format.first_line_indent=Inches(-0.15)
    elif s.startswith('[[diagram:'):
        spec=s[len('[[diagram:'):-2]
        rel, label=spec.split('|',1)
        path=ROOT / rel
        with Image.open(path) as im: w,h=im.size
        max_w, max_h = 6.15, 6.55
        scale=min(max_w/w,max_h/h)
        p=doc.add_paragraph()
        p.alignment=WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.keep_with_next=True
        p.add_run().add_picture(str(path),width=Inches(w*scale),height=Inches(h*scale))
        doc.add_paragraph(label,'Report Caption')
    else:
        body(s)

doc.core_properties.title='LumaLab Photo Editing System Project Report'
doc.core_properties.subject='BCA fourth semester project report'
doc.core_properties.keywords='LumaLab, photo editing, project report'
doc.save(OUTPUT)
print(OUTPUT)
