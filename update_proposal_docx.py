from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt, RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from pathlib import Path

src = Path(r'C:\Users\Mehul\OneDrive\Desktop\proposal report.docx')
out = Path(r'C:\Users\Mehul\OneDrive\Desktop\proposal report revised.docx')
doc = Document(src)
paras = doc.paragraphs
assert len(paras) >= 89 and paras[0].text == 'ProctorAI Milestone 1 Proposal Report'

# Correct the supervisor metadata using the university's faculty listing.
p = next(p for p in doc.paragraphs if p.text.strip() == 'Supervisor- Mr Vicky Vikrant')
p.runs[0].text = 'Supervisor- Dr. Vicky Vikrant'
# Add the supervisor's complete school designation while matching the centered cover block.
ben = next(p for p in doc.paragraphs if p.text.strip() == 'Bennett University')
school = ben.insert_paragraph_before('School of Computer Science Engineering and Technology')
school.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = school.runs[0]
r.bold = True
r.font.name = 'Aptos'
r.font.size = Pt(12)

# Keep the abstract on page two as requested in the supplied feedback.
abstract = next(p for p in doc.paragraphs if p.text.strip() == 'Abstract and proposal summary')
abstract.paragraph_format.page_break_before = True

# Update only the in-text citation markers; preserve the author's sentence wording.
lit = next(p for p in doc.paragraphs if p.text.startswith('While researching on online proctoring'))
for run in lit.runs:
    run.text = run.text.replace('[1][4]', '[1, 4]').replace('object detection [2]', 'object detection [2, 3]')
# If citations span multiple runs, normalize the paragraph without changing any other wording.
if '[1, 4]' not in lit.text:
    lit.text = lit.text.replace('[1][4]', '[1, 4]').replace('object detection [2]', 'object detection [2, 3]')

# Use official publication versions and provide clickable publisher/proceedings links.
def clear_paragraph(p):
    for child in list(p._p):
        if child.tag != qn('w:pPr'):
            p._p.remove(child)

def add_link(p, label, url):
    rel = p.part.relate_to(url, 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink', is_external=True)
    hyperlink = OxmlElement('w:hyperlink')
    hyperlink.set(qn('r:id'), rel)
    run = OxmlElement('w:r')
    props = OxmlElement('w:rPr')
    color = OxmlElement('w:color'); color.set(qn('w:val'), '0563C1'); props.append(color)
    underline = OxmlElement('w:u'); underline.set(qn('w:val'), 'single'); props.append(underline)
    run.append(props)
    text = OxmlElement('w:t'); text.text = label; run.append(text)
    hyperlink.append(run)
    p._p.append(hyperlink)

refs = {
    '[1]': ('[1] A. Nigam, R. Pasricha, T. Singh, and P. Churi, “A systematic review on AI-based proctoring systems: Past, present and future,” Education and Information Technologies, vol. 26, no. 5, pp. 6421–6445, 2021. DOI: ', 'https://doi.org/10.1007/s10639-021-10597-x'),
    '[2]': ('[2] J. Redmon, S. Divvala, R. Girshick, and A. Farhadi, “You Only Look Once: Unified, Real-Time Object Detection,” in Proceedings of the IEEE Conference on Computer Vision and Pattern Recognition (CVPR), 2016, pp. 779–788. ', 'https://openaccess.thecvf.com/content_cvpr_2016/html/Redmon_You_Only_Look_CVPR_2016_paper.html'),
    '[3]': ('[3] T.-Y. Lin, M. Maire, S. Belongie, J. Hays, P. Perona, D. Ramanan, P. Dollár, and C. L. Zitnick, “Microsoft COCO: Common Objects in Context,” in Computer Vision – ECCV 2014, Lecture Notes in Computer Science, vol. 8693, pp. 740–755, Springer, 2014. DOI: ', 'https://doi.org/10.1007/978-3-319-10602-1_48'),
    '[4]': ('[4] B. Burgess, A. Ginsberg, E. W. Felten, and S. Cohney, “Watching the Watchers: Bias and Vulnerability in Remote Proctoring Software,” in Proceedings of the 31st USENIX Security Symposium, 2022, pp. 571–588. ', 'https://www.usenix.org/conference/usenixsecurity22/presentation/burgess'),
}
for p in list(doc.paragraphs):
    key = next((k for k in refs if p.text.startswith(k + ' ')), None)
    if key:
        clear_paragraph(p)
        text, url = refs[key]
        p.add_run(text)
        add_link(p, url, url)
        p.paragraph_format.space_after = Pt(8)
        p.paragraph_format.keep_together = True
        for run in p.runs:
            run.font.size = Pt(10)

# Remove the redundant subheading and blank spacer paragraphs from the references block.
ps = list(doc.paragraphs)
ref_heading = next(i for i,p in enumerate(ps) if p.text.strip() == 'References')
sub = next((p for p in ps[ref_heading+1:] if p.text.strip() == 'Research references'), None)
if sub is not None:
    sub._element.getparent().remove(sub._element)
ps = list(doc.paragraphs)
for p in ps[ref_heading+1:]:
    if not p.text.strip() and p._p.getparent() is not None:
        p._element.getparent().remove(p._element)

# Add unobtrusive page numbers after the cover page.
for section in doc.sections:
    section.different_first_page_header_footer = True
    footer = section.footer
    fp = footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = fp.add_run()
    run.font.size = Pt(9)
    run.font.color.rgb = RGBColor(100, 116, 139)
    fld = OxmlElement('w:fldSimple'); fld.set(qn('w:instr'), 'PAGE')
    fp._p.append(fld)

# Keep cover metadata centered and visually consistent with the existing cover.
for p in doc.paragraphs:
    if p.text.startswith('Supervisor-') or p.text.strip() in {'Assistant Professor', 'School of Computer Science Engineering and Technology', 'Bennett University'}:
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER

doc.core_properties.title = 'ProctorAI Milestone 1 Proposal Report'
doc.core_properties.subject = 'AI Native Multimodal Proctoring and Assessment Integrity Monitoring System for Remote Assessments'
doc.save(out)
print(out)
print('paragraphs', len(doc.paragraphs), 'tables', len(doc.tables), 'images', len(doc.inline_shapes))