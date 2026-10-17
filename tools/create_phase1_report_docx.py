from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt, RGBColor


OUTPUT = Path("ProctorAI_Phase_1_Report.docx")


def set_cell_shading(cell, fill):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), fill)
    tc_pr.append(shd)


def set_cell_border(cell, color="D9D9D9", size="6"):
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    borders = tc_pr.first_child_found_in("w:tcBorders")
    if borders is None:
        borders = OxmlElement("w:tcBorders")
        tc_pr.append(borders)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        tag = "w:{}".format(edge)
        element = borders.find(qn(tag))
        if element is None:
            element = OxmlElement(tag)
            borders.append(element)
        element.set(qn("w:val"), "single")
        element.set(qn("w:sz"), size)
        element.set(qn("w:space"), "0")
        element.set(qn("w:color"), color)


def set_cell_margins(cell, top=90, start=110, bottom=90, end=110):
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for margin, value in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = tc_mar.find(qn(f"w:{margin}"))
        if node is None:
            node = OxmlElement(f"w:{margin}")
            tc_mar.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def set_repeat_table_header(row):
    tr_pr = row._tr.get_or_add_trPr()
    tbl_header = OxmlElement("w:tblHeader")
    tbl_header.set(qn("w:val"), "true")
    tr_pr.append(tbl_header)


def remove_paragraph_borders(paragraph_or_style):
    p_pr = paragraph_or_style._element.get_or_add_pPr()
    p_bdr = p_pr.find(qn("w:pBdr"))
    if p_bdr is not None:
        p_pr.remove(p_bdr)


def format_table(table, header_fill="1F4E79", header_text="FFFFFF"):
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.style = "Table Grid"
    for row_index, row in enumerate(table.rows):
        for cell in row.cells:
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            set_cell_border(cell)
            set_cell_margins(cell)
            for paragraph in cell.paragraphs:
                paragraph.paragraph_format.space_after = Pt(0)
                paragraph.paragraph_format.line_spacing = 1.08
                for run in paragraph.runs:
                    run.font.name = "Aptos"
                    run._element.rPr.rFonts.set(qn("w:ascii"), "Aptos")
                    run._element.rPr.rFonts.set(qn("w:hAnsi"), "Aptos")
                    run.font.size = Pt(10)
            if row_index == 0:
                set_cell_shading(cell, header_fill)
                for paragraph in cell.paragraphs:
                    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    for run in paragraph.runs:
                        run.font.bold = True
                        run.font.color.rgb = RGBColor.from_string(header_text)
            elif row_index % 2 == 0:
                set_cell_shading(cell, "F7F9FC")
    set_repeat_table_header(table.rows[0])


def add_hyperlink(paragraph, text, url):
    part = paragraph.part
    rel_id = part.relate_to(
        url,
        "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink",
        is_external=True,
    )
    hyperlink = OxmlElement("w:hyperlink")
    hyperlink.set(qn("r:id"), rel_id)
    new_run = OxmlElement("w:r")
    r_pr = OxmlElement("w:rPr")
    color = OxmlElement("w:color")
    color.set(qn("w:val"), "0563C1")
    r_pr.append(color)
    underline = OxmlElement("w:u")
    underline.set(qn("w:val"), "single")
    r_pr.append(underline)
    new_run.append(r_pr)
    text_element = OxmlElement("w:t")
    text_element.text = text
    new_run.append(text_element)
    hyperlink.append(new_run)
    paragraph._p.append(hyperlink)


def add_paragraph(doc, text="", style=None, bold_lead=None):
    paragraph = doc.add_paragraph(style=style)
    if bold_lead and text.startswith(bold_lead):
        lead = paragraph.add_run(bold_lead)
        lead.bold = True
        paragraph.add_run(text[len(bold_lead) :])
    else:
        paragraph.add_run(text)
    return paragraph


def add_bullets(doc, items):
    for item in items:
        p = doc.add_paragraph(style="List Bullet")
        p.add_run(item)


def configure_document(doc):
    section = doc.sections[0]
    section.top_margin = Cm(2.0)
    section.bottom_margin = Cm(2.0)
    section.left_margin = Cm(2.2)
    section.right_margin = Cm(2.2)

    styles = doc.styles
    normal = styles["Normal"]
    normal.font.name = "Aptos"
    normal._element.rPr.rFonts.set(qn("w:ascii"), "Aptos")
    normal._element.rPr.rFonts.set(qn("w:hAnsi"), "Aptos")
    normal.font.size = Pt(10.5)
    normal.font.color.rgb = RGBColor(0, 0, 0)
    normal.paragraph_format.line_spacing = 1.15
    normal.paragraph_format.space_after = Pt(8)

    for style_name, size, before, after in [
        ("Title", 22, 0, 8),
        ("Heading 1", 15, 16, 6),
        ("Heading 2", 12, 10, 4),
    ]:
        style = styles[style_name]
        style.font.name = "Aptos Display" if style_name != "Normal" else "Aptos"
        style._element.rPr.rFonts.set(qn("w:ascii"), style.font.name)
        style._element.rPr.rFonts.set(qn("w:hAnsi"), style.font.name)
        style.font.size = Pt(size)
        style.font.bold = style_name != "Title" or True
        style.font.color.rgb = RGBColor(0, 0, 0)
        style.paragraph_format.space_before = Pt(before)
        style.paragraph_format.space_after = Pt(after)
        remove_paragraph_borders(style)


def add_title_page(doc):
    title = doc.add_paragraph(style="Title")
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    remove_paragraph_borders(title)
    run = title.add_run("Phase 1 Report")
    run.font.size = Pt(24)

    subtitle = doc.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle_run = subtitle.add_run("ProctorAI AI Based Online Proctoring System")
    subtitle_run.bold = True
    subtitle_run.font.size = Pt(16)

    add_paragraph(
        doc,
        "This report defines the problem domain, reviews related work, checks project feasibility, and finalizes the datasets planned for the ProctorAI college project.",
    )

    table = doc.add_table(rows=5, cols=2)
    rows = [
        ("Team ID", "[Enter Team ID]"),
        ("Team Member 1", "[Name] - [Roll Number]"),
        ("Team Member 2", "[Name] - [Roll Number]"),
        ("Team Member 3", "[Name] - [Roll Number]"),
        ("Submission Date", "15 September 2026"),
    ]
    for i, (left, right) in enumerate(rows):
        table.cell(i, 0).text = left
        table.cell(i, 1).text = right
    table.columns[0].width = Inches(2.0)
    table.columns[1].width = Inches(4.4)
    format_table(table, header_fill="2F5597")

    for cell in table.rows[0].cells:
        set_cell_shading(cell, "EAF1F8")
        for paragraph in cell.paragraphs:
            for run in paragraph.runs:
                run.font.color.rgb = RGBColor(0, 0, 0)

    note = doc.add_paragraph()
    note.add_run("Academic integrity note: ").bold = True
    note.add_run(
        "The project description and planned features are based on our ProctorAI system work. Literature-based claims are supported through the references section. The wording and structure of this report were prepared with editorial assistance and should be reviewed by the team before submission."
    )

    doc.add_page_break()


def add_problem_analysis(doc):
    doc.add_heading("1 Problem Domain and Problem Analysis", level=1)
    add_paragraph(
        doc,
        "Online examinations are now used in colleges, training platforms, and recruitment processes. The main difficulty is that the candidate is not sitting in a controlled examination hall. In a physical exam, an invigilator can observe the candidate, check the surroundings, notice suspicious behavior, and take action immediately. In an online exam, the candidate may use another device, receive help from another person, leave the screen, copy content, switch tabs, or stop monitoring permissions without the examiner noticing at the right time.",
    )
    add_paragraph(
        doc,
        "The problem domain of this project is AI based online exam proctoring. The aim of ProctorAI is to monitor a candidate during an online test and generate evidence based integrity events when suspicious activity is detected. The system is not designed to replace the human proctor completely. Instead, it supports the proctor by collecting signals from the camera, microphone, screen recording, browser activity, and device checks.",
    )
    add_paragraph(
        doc,
        "The project is important because a normal online test page cannot protect exam integrity by itself. A practical system needs setup checks before the test, continuous monitoring during the test, and review tools after suspicious events are detected.",
    )

    table = doc.add_table(rows=1, cols=3)
    headers = ["Risk Area", "Example Problem", "ProctorAI Response"]
    for index, header in enumerate(headers):
        table.cell(0, index).text = header
    rows = [
        ("Candidate identity and presence", "Candidate leaves the camera frame or another person appears.", "Detect face absent and multiple person events."),
        ("Unauthorized devices", "A mobile phone or second screen is used during the test.", "Detect phone objects and extra display conditions."),
        ("Browser misuse", "Candidate copies, pastes, exits fullscreen, or switches away from the test.", "Track browser integrity events with evidence."),
        ("Environment audio", "Background voice or suspicious noise is present.", "Monitor microphone signals and report audio events."),
        ("Evidence review", "Automatic detection may be wrong in real conditions.", "Send evidence to the proctor for human review."),
    ]
    for row in rows:
        cells = table.add_row().cells
        for i, value in enumerate(row):
            cells[i].text = value
    format_table(table)


def add_literature_survey(doc):
    doc.add_heading("2 Literature Survey and Existing Systems", level=1)
    add_paragraph(
        doc,
        "Existing online proctoring systems usually follow one of three approaches: live proctoring, recorded proctoring, or automated AI based proctoring. Live proctoring depends on a human invigilator watching candidates in real time. Recorded proctoring stores video and activity logs for later review. Automated proctoring uses AI and browser signals to detect suspicious activity during the exam.",
    )
    add_paragraph(
        doc,
        "Research on AI based proctoring shows that common techniques include log tracking, face detection, object detection, and behavior analysis. These techniques are useful because cheating in an online exam can happen in different ways. Camera monitoring may detect face absence or a mobile phone, but it cannot detect copy paste activity by itself. Browser tracking can detect tab switching or shortcut keys, but it cannot detect another person in the room. This is why ProctorAI uses a multi signal approach.",
    )
    add_paragraph(
        doc,
        "Face detection and behavior analysis are frequently discussed in online proctoring studies. Object detection is also important because the system must recognize items such as mobile phones and the presence of more than one person. YOLO is suitable for this project because it is designed for real time object detection, which is needed while the candidate is actively taking the exam. The COCO dataset is also relevant because it is widely used for object detection and contains common object categories used in scene understanding.",
    )

    table = doc.add_table(rows=1, cols=4)
    for i, header in enumerate(["Area Studied", "What Existing Systems Use", "Use in ProctorAI", "Citation Needed"]):
        table.cell(0, i).text = header
    rows = [
        ("AI proctoring", "Face detection, object detection, log tracking, behavior analysis.", "Used as the overall system direction.", "Yes"),
        ("Face monitoring", "Face detection and recognition for identity and presence checks.", "Used for face absent and multiple face events.", "Yes"),
        ("Object detection", "Real time detection models such as YOLO.", "Used for phone and person detection.", "Yes"),
        ("Browser monitoring", "Activity logs and event tracking.", "Used for copy paste, focus lost, fullscreen exit, and shortcuts.", "Yes"),
        ("Human review", "Proctor reviews suspicious events and evidence.", "Used to reduce unfair automatic decisions.", "Recommended"),
    ]
    for row in rows:
        cells = table.add_row().cells
        for i, value in enumerate(row):
            cells[i].text = value
    format_table(table, header_fill="3F3F46")


def add_proposed_system(doc):
    doc.add_heading("3 Proposed System Overview", level=1)
    add_paragraph(
        doc,
        "ProctorAI is proposed as a web based AI online proctoring system for college examinations. It has two main parts: the candidate portal and the examiner or proctor portal. The candidate portal is used to select an assigned assessment, complete setup checks, and take the test. The proctor portal is used to create assessments, monitor candidate sessions, receive integrity events in real time, and review evidence.",
    )
    add_paragraph(
        doc,
        "The system will generate integrity events instead of directly declaring a candidate guilty. This is important because AI models can produce false positives due to lighting, camera position, background movement, or normal user behavior. A human proctor should be able to review the evidence before making a decision.",
    )
    add_bullets(
        doc,
        [
            "Candidate portal: assignment selection, setup checks, screen recording setup, liveness verification, and test attempt.",
            "Proctor portal: assessment creation, session monitoring, real time integrity event feed, evidence playback, and event review.",
            "AI service: face presence analysis, multiple person detection, phone detection, and other camera based signals.",
            "Browser monitoring: copy paste, fullscreen exit, app focus lost, shortcut attempts, and screen recording status.",
        ],
    )


def add_feasibility(doc):
    doc.add_heading("4 Feasibility Analysis", level=1)
    add_paragraph(
        doc,
        "Technical feasibility: ",
        bold_lead="Technical feasibility: ",
    ).add_run(
        "The project is technically feasible because modern browsers support camera, microphone, and screen recording permissions. A backend API can manage assessments, sessions, events, and evidence. Real time communication can be used to send integrity events to the proctor portal. AI models such as YOLO can support real time object detection."
    )
    add_paragraph(
        doc,
        "Operational feasibility: ",
        bold_lead="Operational feasibility: ",
    ).add_run(
        "The system fits college examination use because candidates can complete checks before starting the test and proctors can review suspicious events during or after the exam. This reduces the need for constant manual watching while still keeping human judgment in the process."
    )
    add_paragraph(
        doc,
        "Economic feasibility: ",
        bold_lead="Economic feasibility: ",
    ).add_run(
        "The project can be built using open source tools, browser APIs, and publicly available datasets. For a college project, the main cost is development time. If deployed publicly, storage for evidence clips and hosting would become the main operational costs."
    )
    add_paragraph(
        doc,
        "Limitations: ",
        bold_lead="Limitations: ",
    ).add_run(
        "Browser based screen recording cannot silently capture the full screen without the user's permission. AI detection can also miss events or create false positives. Because of this, ProctorAI should support human review instead of making automatic punishment decisions."
    )


def add_datasets(doc):
    doc.add_heading("5 Dataset Finalization", level=1)
    add_paragraph(
        doc,
        "The following datasets and data sources are planned for ProctorAI. The goal is to use standard datasets for model support and a small custom validation set for realistic exam scenarios.",
    )
    table = doc.add_table(rows=1, cols=4)
    for i, header in enumerate(["Dataset or Source", "Purpose", "Why It Is Suitable", "Final Decision"]):
        table.cell(0, i).text = header
    rows = [
        ("COCO dataset", "Object detection base data.", "Contains labeled common objects and is widely used for object detection.", "Use as base/reference dataset."),
        ("YOLO pretrained model data", "Real time object detection.", "Useful for detecting objects such as persons and phones during a live exam.", "Use pretrained model and tune if needed."),
        ("Custom validation dataset", "Project-specific testing.", "Covers exam-like cases such as face absent, phone visible, multiple persons, poor lighting, and screen recording interruption.", "Prepare a small validation set."),
        ("Browser event logs", "Integrity event validation.", "Captures copy paste, focus lost, fullscreen exit, and shortcut activity.", "Generate during system testing."),
    ]
    for row in rows:
        cells = table.add_row().cells
        for i, value in enumerate(row):
            cells[i].text = value
    format_table(table, header_fill="1F4E79")


def add_conclusion(doc):
    doc.add_heading("6 Conclusion", level=1)
    add_paragraph(
        doc,
        "The Phase 1 study confirms that AI based online proctoring is a relevant and feasible project domain. Online examinations need more than a basic test interface because candidates may use unauthorized devices, leave the camera, receive help, or misuse browser features. Existing research also shows that online proctoring systems commonly use face detection, object detection, log tracking, and behavior analysis.",
    )
    add_paragraph(
        doc,
        "ProctorAI will use a multi signal approach by combining camera monitoring, microphone monitoring, screen recording, browser activity tracking, connected display checks, liveness verification, and real time event reporting. The system will generate evidence based integrity events and allow the proctor to review them before making a final decision.",
    )
    add_paragraph(
        doc,
        "The finalized datasets and data sources are COCO, YOLO pretrained model data, a custom validation dataset, and browser event logs generated during testing. Based on the problem analysis, literature survey, and feasibility study, the project can continue into the design and implementation phase.",
    )


def add_references(doc):
    doc.add_heading("References", level=1)
    refs = [
        (
            "A Systematic Review on AI based Proctoring Systems",
            "https://pmc.ncbi.nlm.nih.gov/articles/PMC8220875/",
        ),
        (
            "Survey of Online Exam Proctoring Model to Detect Cheating Behavior based on Face Recognition",
            "https://ieeexplore.ieee.org/abstract/document/10005488",
        ),
        (
            "YOLO You Only Look Once Unified Real Time Object Detection",
            "https://arxiv.org/abs/1506.02640",
        ),
        (
            "Microsoft COCO Common Objects in Context",
            "https://arxiv.org/abs/1405.0312",
        ),
    ]
    for index, (title, url) in enumerate(refs, start=1):
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Cm(0.6)
        p.paragraph_format.first_line_indent = Cm(-0.6)
        p.add_run(f"{index}. {title}. ")
        add_hyperlink(p, url, url)


def add_footer(doc):
    for section in doc.sections:
        footer = section.footer
        paragraph = footer.paragraphs[0]
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = paragraph.add_run("ProctorAI Phase 1 Report")
        run.font.size = Pt(9)
        run.font.color.rgb = RGBColor(90, 90, 90)


def main():
    doc = Document()
    configure_document(doc)
    add_title_page(doc)
    add_problem_analysis(doc)
    add_literature_survey(doc)
    add_proposed_system(doc)
    add_feasibility(doc)
    add_datasets(doc)
    add_conclusion(doc)
    add_references(doc)
    add_footer(doc)
    doc.save(OUTPUT)


if __name__ == "__main__":
    main()
