from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt, RGBColor
from PIL import Image, ImageDraw, ImageFont


OUT = Path("ProctorAI_Phase_2_Report.docx")
FIG_DIR = Path("docs/generated")
FIG_DIR.mkdir(parents=True, exist_ok=True)
ARCH_FIG = FIG_DIR / "phase2_architecture.png"


def set_font(run, name="Times New Roman", size=9, bold=False, italic=False):
    run.font.name = name
    run._element.get_or_add_rPr().rFonts.set(qn("w:ascii"), name)
    run._element.get_or_add_rPr().rFonts.set(qn("w:hAnsi"), name)
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = RGBColor(0, 0, 0)


def set_cell_border(cell, color="D9D9D9", size="6"):
    tc_pr = cell._tc.get_or_add_tcPr()
    borders = tc_pr.first_child_found_in("w:tcBorders")
    if borders is None:
        borders = OxmlElement("w:tcBorders")
        tc_pr.append(borders)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        tag = f"w:{edge}"
        element = borders.find(qn(tag))
        if element is None:
            element = OxmlElement(tag)
            borders.append(element)
        element.set(qn("w:val"), "single")
        element.set(qn("w:sz"), size)
        element.set(qn("w:space"), "0")
        element.set(qn("w:color"), color)


def set_cell_shading(cell, fill):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def set_cell_margins(cell, top=80, start=80, bottom=80, end=80):
    tc_pr = cell._tc.get_or_add_tcPr()
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


def format_table(table, header_fill="E6E6E6"):
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.style = "Table Grid"
    for row_i, row in enumerate(table.rows):
        for cell in row.cells:
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            set_cell_border(cell)
            set_cell_margins(cell)
            if row_i == 0:
                set_cell_shading(cell, header_fill)
            for paragraph in cell.paragraphs:
                paragraph.paragraph_format.space_after = Pt(0)
                paragraph.paragraph_format.line_spacing = 1.0
                for run in paragraph.runs:
                    set_font(run, size=8, bold=(row_i == 0))


def remove_paragraph_borders(paragraph_or_style):
    p_pr = paragraph_or_style._element.get_or_add_pPr()
    p_bdr = p_pr.find(qn("w:pBdr"))
    if p_bdr is not None:
        p_pr.remove(p_bdr)


def set_columns(section, count):
    sect_pr = section._sectPr
    cols = sect_pr.find(qn("w:cols"))
    if cols is None:
        cols = OxmlElement("w:cols")
        sect_pr.append(cols)
    cols.set(qn("w:num"), str(count))
    cols.set(qn("w:space"), "360")


def add_heading(doc, text, level=1):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER if level == 1 else WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.space_before = Pt(8 if level == 1 else 5)
    p.paragraph_format.space_after = Pt(3)
    run = p.add_run(text.upper() if level == 1 else text)
    set_font(run, size=10 if level == 1 else 9, bold=True)
    return p


def add_para(doc, text, first_line=True):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.line_spacing = 1.0
    if first_line:
        p.paragraph_format.first_line_indent = Cm(0.35)
    run = p.add_run(text)
    set_font(run, size=9)
    return p


def add_caption(doc, text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(4)
    run = p.add_run(text)
    set_font(run, size=8, bold=True)
    return p


def configure_styles(doc):
    section = doc.sections[0]
    section.page_width = Inches(8.5)
    section.page_height = Inches(11)
    section.top_margin = Inches(0.7)
    section.bottom_margin = Inches(0.7)
    section.left_margin = Inches(0.65)
    section.right_margin = Inches(0.65)
    set_columns(section, 1)

    for style_name in ("Normal", "Title", "Heading 1", "Heading 2"):
        style = doc.styles[style_name]
        style.font.name = "Times New Roman"
        style._element.get_or_add_rPr().rFonts.set(qn("w:ascii"), "Times New Roman")
        style._element.get_or_add_rPr().rFonts.set(qn("w:hAnsi"), "Times New Roman")
        style.font.color.rgb = RGBColor(0, 0, 0)
        remove_paragraph_borders(style)
    doc.styles["Normal"].font.size = Pt(9)


def create_architecture_image():
    img = Image.new("RGB", (700, 980), "white")
    draw = ImageDraw.Draw(img)
    try:
        font_title = ImageFont.truetype("arial.ttf", 30)
        font_box = ImageFont.truetype("arial.ttf", 25)
        font_small = ImageFont.truetype("arial.ttf", 20)
    except Exception:
        font_title = font_box = font_small = None

    draw.text((155, 28), "ProctorAI Workflow", fill=(0, 0, 0), font=font_title)
    boxes = [
        ((145, 105, 555, 205), "Candidate Portal"),
        ((145, 255, 555, 355), "Setup Checks\nIdentity + Liveness"),
        ((145, 405, 555, 505), "Test Attempt\nMonitoring"),
        ((145, 555, 555, 655), "AI Sidecar\nYOLO + Face"),
        ((145, 705, 555, 805), "Backend API\nAuth + Evidence"),
        ((145, 855, 555, 945), "Proctor Portal\nReview Queue"),
    ]
    for box, label in boxes:
        draw.rounded_rectangle(box, radius=18, outline=(30, 30, 30), width=3, fill=(242, 246, 250))
        lines = label.split("\n")
        y = box[1] + 24
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font_box)
            x = box[0] + (box[2] - box[0] - (bbox[2] - bbox[0])) / 2
            draw.text((x, y), line, fill=(0, 0, 0), font=font_box)
            y += 38

    arrows = [
        ((350, 205), (350, 255)),
        ((350, 355), (350, 405)),
        ((350, 505), (350, 555)),
        ((350, 655), (350, 705)),
        ((350, 805), (350, 855)),
    ]
    for start, end in arrows:
        draw.line([start, end], fill=(0, 0, 0), width=4)
        ex, ey = end
        sx, sy = start
        if ey >= sy:
            draw.polygon([(ex, ey), (ex - 10, ey - 16), (ex + 10, ey - 16)], fill=(0, 0, 0))
        else:
            draw.polygon([(ex, ey), (ex - 10, ey + 16), (ex + 10, ey + 16)], fill=(0, 0, 0))

    draw.text(
        (110, 65),
        "Event evidence only; normal data is temporary.",
        fill=(40, 40, 40),
        font=font_small,
    )
    img.save(ARCH_FIG)


def add_title_block(doc):
    title = doc.add_paragraph(style="Title")
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.paragraph_format.space_after = Pt(4)
    remove_paragraph_borders(title)
    run = title.add_run("ProctorAI AI Based Online Proctoring System")
    set_font(run, size=18, bold=True)

    team = doc.add_paragraph()
    team.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = team.add_run("*TeamID: [Write Your Assigned Team ID Here]\n")
    set_font(run, size=10, bold=True)
    for i in range(1, 7):
        r = team.add_run(f"Student Name {i} (Roll No: XXXXXXXX)\n")
        set_font(r, size=9)
    r = team.add_run("Department of Computer Science Engineering and Technology\nBennett University, India")
    set_font(r, size=9)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(4)
    r = p.add_run("GitHub Link: https://github.com/MehulMTyagi/PROCTORAI")
    set_font(r, size=9, bold=True)

    abstract = (
        "Abstract - ProctorAI is an AI based online proctoring system designed for college level remote assessments. "
        "The problem addressed by the project is that online tests are difficult to supervise because a candidate may use another device, leave the camera frame, receive help, switch applications, or stop monitoring permissions. "
        "The proposed system combines a candidate portal, examiner/proctor portal, FastAPI backend, local AI sidecar, browser integrity monitoring, and protected evidence handling. "
        "The monitoring design includes face absence detection, multiple person detection, YOLO based phone detection, liveness verification, screen recording checks, copy and paste tracking, fullscreen and focus-loss events, and a planned identity identification step using registered and live candidate face images. "
        "Instead of automatically declaring misconduct, the system sends evidence backed integrity events to the proctor for review. "
        "The current Phase 2 work focuses on architecture, module integration, dataset planning, and evaluation design; final quantitative results will be updated after complete testing before project submission."
    )
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.space_after = Pt(4)
    r = p.add_run(abstract)
    set_font(r, size=9)
    r.bold = False
    p.runs[0].text = "Abstract - " + p.runs[0].text.replace("Abstract - ", "", 1)
    p.runs[0].bold = False

    idx = doc.add_paragraph()
    idx.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    r = idx.add_run(
        "Index Terms - Online proctoring, computer vision, YOLO, face detection, liveness verification, identity identification, integrity events, evidence review."
    )
    set_font(r, size=9, italic=True)


def add_literature(doc):
    add_heading(doc, "II. Literature Survey")
    add_para(
        doc,
        "AI based proctoring research shows that online examination monitoring usually combines several signals rather than relying on one detector. A systematic review of AI based proctoring systems reported common use of face monitoring, gaze or behavior analysis, audio analysis, and log based activity tracking [1]. This supports the direction of ProctorAI because cheating or suspicious behavior can appear through the camera, browser, microphone, or device state.",
    )
    add_para(
        doc,
        "Face recognition and face detection are major components of proctoring systems. Surveys on face recognition based exam monitoring discuss methods such as Viola-Jones, CNN based face detectors, and MTCNN [2], [9]. For ProctorAI, face detection is used first as a presence and continuity signal: the system checks whether the candidate is visible, whether multiple people appear, and whether identity verification should be repeated.",
    )
    add_para(
        doc,
        "Object detection is required for detecting mobile phones and additional persons. YOLO style detectors are widely used for real time detection because they process an image in a single forward pass [5], [6]. COCO is useful as a base object detection dataset because it provides common object categories in natural scenes [7]. However, general object datasets do not fully represent exam room conditions, so a small custom validation set is still needed.",
    )
    add_para(
        doc,
        "Identity identification and liveness verification are also important for a production grade proctoring system. FaceNet and ArcFace show how face embeddings can be used to compare whether two face images belong to the same person [11], [12]. Face anti-spoofing surveys show that liveness checks are needed because a photo, video replay, or mask can attack a face recognition system [13]. ProctorAI therefore treats identity verification and liveness as separate steps.",
    )
    add_para(
        doc,
        "Recent discussions on remote proctoring also warn about bias, privacy, and unfair automatic decisions [15]. This is why ProctorAI uses human review: the AI system raises an integrity event with proof, but the final decision remains with the proctor.",
    )
    table = doc.add_table(rows=1, cols=4)
    for i, h in enumerate(["Study Area", "Main Method", "Limitation Observed", "Use in ProctorAI"]):
        table.cell(0, i).text = h
    rows = [
        ("AI proctoring surveys", "Review of face, audio, browser, and behavior signals", "Many systems depend heavily on automated flags", "Use multi-signal monitoring with human review"),
        ("Face recognition proctoring", "Face detection and verification models", "Identity alone cannot detect browser misuse", "Combine identity with browser and screen events"),
        ("YOLO object detection", "Real-time object detector for common objects", "General datasets may not match exam rooms", "Use YOLO plus custom validation scenarios"),
        ("Face anti-spoofing", "Liveness and presentation attack detection", "Spoof attacks vary across devices and lighting", "Use active liveness before test start"),
        ("Remote proctoring fairness", "Bias and vulnerability analysis", "Automated decisions can be unfair", "Keep proctor decision separate from AI risk score"),
    ]
    for row in rows:
        cells = table.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = v
    format_table(table)
    add_caption(doc, "Table I. Summary of literature gaps and ProctorAI design response.")
    add_para(
        doc,
        "The literature gap is that many approaches focus strongly on one signal, such as face recognition or object detection, while practical online cheating can happen through several channels at the same time. A candidate may remain visible on camera but copy content from another source, or may avoid browser misuse but use a second device outside the screen. ProctorAI addresses this gap by combining setup verification, browser activity, camera events, audio events, identity checks, and evidence review in one workflow.",
    )


def add_methodology(doc):
    add_heading(doc, "III. Proposed Methodology")
    add_heading(doc, "A. System Architecture", level=2)
    add_para(
        doc,
        "The proposed methodology follows a multi-module architecture. The candidate first selects an assigned assessment and completes setup checks. These checks include consent, backend connectivity, camera permission, microphone permission, screen recording, connected display audit, liveness verification, and identity identification. The identity module compares a registered candidate image with a live setup image and sends uncertain cases to the proctor for review.",
    )
    add_para(
        doc,
        "During the test, the candidate portal monitors browser and media signals. Browser integrity events include copy, paste, fullscreen exit, focus lost, suspicious shortcuts, and stopped screen recording. Camera based events include face absent, multiple persons, phone detected, and liveness failure. Audio events include microphone interruption and background voice or noise signals. Evidence is attached as short clips or proof metadata instead of continuously streaming all media.",
    )
    add_para(
        doc,
        "The threat model considered in this project includes impersonation, use of a mobile phone, another person helping the candidate, leaving the camera frame, using copy-paste or shortcut keys, switching away from the test window, stopping screen recording, and attempting to use an extra display. These risks were selected because they are realistic for a college online assessment and can be detected using browser APIs, camera analysis, microphone analysis, and setup checks.",
    )
    create_architecture_image()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run().add_picture(str(ARCH_FIG), width=Inches(3.2))
    add_caption(doc, "Fig. 1. Proposed ProctorAI system workflow.")
    add_para(
        doc,
        "The backend stores users, assessments, attempts, answers, integrity events, evidence metadata, and proctor review decisions. A WebSocket or equivalent real time channel sends new integrity events to the proctor portal. The proctor portal displays each event with event type, severity, confidence, timestamp, evidence status, and review action. The final system will support confirmed suspicious, false positive, and inconclusive decisions.",
    )
    add_para(
        doc,
        "The AI sidecar is responsible for local computer vision inference. YOLO is used for phone and object detection, while face analysis is used for face count, face absence, liveness support, and identity continuity. This architecture keeps most normal monitoring data local and uploads only event specific evidence, which is more privacy aware than continuous cloud recording.",
    )
    add_heading(doc, "B. Identity Identification Workflow", level=2)
    add_para(
        doc,
        "The identity identification feature is designed as a setup step before the test begins. The candidate provides or captures a registered face image and then captures a live selfie during setup. The system extracts a face representation from both images and compares them using a similarity threshold. If the similarity is above the accepted threshold, the identity check passes. If the score is close to the threshold or below it, the proctor receives an identity review event instead of the candidate being automatically rejected.",
    )
    add_para(
        doc,
        "This design separates identity verification from liveness. Identity verification answers the question: is this the expected candidate? Liveness verification answers a different question: is the candidate physically present rather than showing a static photo or replayed video? Keeping these checks separate makes the workflow easier to explain and easier for a proctor to review.",
    )
    add_heading(doc, "C. Integrity Event Generation", level=2)
    add_para(
        doc,
        "Integrity events are generated only when a monitored condition crosses a threshold. For example, face absence should not be triggered by a single weak frame, because lighting and camera focus may temporarily affect detection. Instead, the system uses debounce rules such as consecutive-frame confirmation or confidence thresholds. Browser events such as copy, paste, fullscreen exit, and focus lost are generated directly from browser event listeners because they are discrete actions.",
    )
    add_para(
        doc,
        "Each event stores event type, timestamp, candidate session, severity, confidence or rule metadata, and evidence status. Camera based events use camera proof, while browser activity events should use screen evidence. This difference is important because a camera clip cannot prove a copy-paste action, but a short screen clip can provide better context for the proctor.",
    )
    table_steps = doc.add_table(rows=1, cols=3)
    for i, h in enumerate(["Step", "Process", "Output"]):
        table_steps.cell(0, i).text = h
    step_rows = [
        ("1", "Candidate logs in and selects assigned test", "Assessment session is initialized"),
        ("2", "Setup checks request consent, camera, microphone, screen, liveness, and identity", "Candidate is allowed or blocked before test"),
        ("3", "Candidate starts assessment after required checks pass", "Attempt record and heartbeat stream begin"),
        ("4", "Browser, camera, audio, and AI sidecar monitor signals", "Raw signals are converted into event candidates"),
        ("5", "Debounce and threshold rules confirm event candidates", "Integrity event is created"),
        ("6", "Evidence clip or proof metadata is attached", "Event becomes reviewable"),
        ("7", "Proctor portal receives live update", "Human review decision is recorded"),
    ]
    for row in step_rows:
        cells = table_steps.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = v
    format_table(table_steps)
    add_caption(doc, "Table II. Stepwise processing flow for ProctorAI.")
    table = doc.add_table(rows=1, cols=3)
    for i, h in enumerate(["Module", "Purpose", "Phase 2 Status"]):
        table.cell(0, i).text = h
    rows = [
        ("Candidate portal", "Assignment selection, setup checks, test attempt", "Implemented and being refined"),
        ("Proctor portal", "Live event queue and evidence review", "Implemented with review workflow planned for final hardening"),
        ("AI sidecar", "Face, liveness, and phone/object analysis", "Implemented for core signals"),
        ("Identity identification", "Compare registered and live candidate identity", "Included in final feature scope"),
        ("Evidence handling", "Store proof clips and hashes for review", "Implemented for event evidence"),
    ]
    for row in rows:
        cells = table.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = v
    format_table(table)
    add_caption(doc, "Table III. Major ProctorAI modules and Phase 2 status.")
    add_heading(doc, "D. Privacy and Review Policy", level=2)
    add_para(
        doc,
        "The system is intentionally designed as a review-support system rather than an automatic punishment system. Normal monitoring data remains temporary wherever possible. Evidence is attached only when an integrity event is generated. The proctor can mark an event as confirmed suspicious, false positive, or inconclusive. This is useful for academic fairness because AI models can make mistakes in low light, poor camera angles, noisy rooms, or unstable network conditions.",
    )
    add_para(
        doc,
        "The review policy also separates assessment score from integrity review. A candidate may complete the test and receive an academic score, while the proctor separately reviews integrity events. This separation is important because a suspicious event does not always prove misconduct. For example, a short face absence could happen due to camera freeze, and background voice could come from a family member in a shared room. The proctor review layer helps prevent unfair automatic decisions.",
    )
    add_para(
        doc,
        "The evidence policy follows a minimal collection approach. Continuous live streaming is avoided in the planned design unless specifically enabled for a future deployment. Instead, the system stores short event-related clips, hashes, timestamps, and metadata. This makes the system more suitable for a college project where privacy and storage cost both matter.",
    )


def add_results(doc):
    add_heading(doc, "IV. Experimental Results")
    add_heading(doc, "A. Dataset Description", level=2)
    add_para(
        doc,
        "The project uses a combination of public datasets, pretrained model knowledge, and custom validation data. COCO is selected for object detection support because it contains common objects such as persons and mobile phones in natural contexts [7]. WIDER FACE is relevant for face detection benchmarking because it contains many face images with variation in scale, pose, and occlusion [8]. A custom validation set will be prepared for exam-like cases such as normal candidate sitting, face absent, multiple persons, phone visible, poor lighting, background movement, and screen recording interruption.",
    )
    table_dataset = doc.add_table(rows=1, cols=4)
    for i, h in enumerate(["Data Source", "Used For", "Sample Type", "Ethical Note"]):
        table_dataset.cell(0, i).text = h
    data_rows = [
        ("COCO", "Phone/person/object reference", "Public images", "Used as model reference only"),
        ("WIDER FACE", "Face detection reference", "Public face images", "Used for understanding detection variation"),
        ("Custom setup images", "Exam-like validation", "Team-created scenarios", "Use consent and avoid unnecessary personal storage"),
        ("Browser event logs", "Copy/paste/focus validation", "Synthetic event actions", "No private content stored"),
        ("Evidence clips", "Review workflow testing", "Short event clips", "Store only event-related proof"),
    ]
    for row in data_rows:
        cells = table_dataset.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = v
    format_table(table_dataset)
    add_caption(doc, "Table IV. Dataset and validation data plan.")
    add_heading(doc, "B. Evaluation Metrics", level=2)
    add_para(
        doc,
        "For event detection, the planned evaluation metrics are precision, recall, F1-score, false positive rate, event delivery latency, and evidence availability rate. Precision measures how many generated events are actually relevant. Recall measures how many expected events are detected. F1-score balances precision and recall. Latency measures how quickly the proctor receives an event after it occurs. Evidence availability rate measures whether each event includes usable proof for review.",
    )
    add_para(
        doc,
        "The formulas used for classification-style event evaluation are: Precision = TP / (TP + FP), Recall = TP / (TP + FN), and F1-score = 2 x Precision x Recall / (Precision + Recall). Here TP means a suspicious event was correctly detected, FP means the system raised an unnecessary event, and FN means a suspicious event was missed. These metrics will be computed separately for each signal type because phone detection, face absence, copy-paste, and identity mismatch have different error patterns.",
    )
    table = doc.add_table(rows=1, cols=4)
    for i, h in enumerate(["Metric", "Meaning", "Why It Matters", "Target Direction"]):
        table.cell(0, i).text = h
    rows = [
        ("Precision", "Correct events among all raised events", "Reduces unnecessary proctor workload", "Higher is better"),
        ("Recall", "Detected events among all expected events", "Reduces missed suspicious behavior", "Higher is better"),
        ("F1-score", "Balance of precision and recall", "Useful when both false alarms and missed events matter", "Higher is better"),
        ("Latency", "Time from event occurrence to proctor view", "Important for real-time review", "Lower is better"),
        ("Evidence availability", "Events with playable proof", "Allows fair human review", "Higher is better"),
    ]
    for row in rows:
        cells = table.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = v
    format_table(table)
    add_caption(doc, "Table V. Evaluation metrics planned for ProctorAI.")
    add_heading(doc, "C. Current Validation and Comparison", level=2)
    table = doc.add_table(rows=1, cols=5)
    for i, h in enumerate(["Signal", "Detector or Source", "Expected Output", "Evidence Type", "Status"]):
        table.cell(0, i).text = h
    rows = [
        ("Face absent", "Camera and face count", "FACE_ABSENT event", "Camera clip/proof", "Implemented"),
        ("Multiple persons", "Camera and face count", "MULTIPLE_PERSONS event", "Camera clip/proof", "Implemented"),
        ("Phone visible", "YOLO object detection", "PHONE_DETECTED event", "Camera clip/proof", "Implemented"),
        ("Copy or paste", "Browser event listener", "Clipboard event", "Screen clip", "Implemented"),
        ("Identity mismatch", "Face comparison", "Identity review event", "Planned identity proof", "Final scope"),
    ]
    for row in rows:
        cells = table.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = v
    format_table(table)
    add_caption(doc, "Table VI. Planned and current integrity signal validation.")
    add_para(
        doc,
        "At this stage, the report records Phase 2 design and module validation rather than final model accuracy. Final numerical performance values will be added after full testing on the custom validation set. This is academically safer than reporting artificial accuracy values before the complete experiment is finished.",
    )
    add_heading(doc, "D. Baseline Comparison Plan", level=2)
    table = doc.add_table(rows=1, cols=5)
    for i, h in enumerate(["Method", "Camera Events", "Browser Events", "Evidence Review", "Expected Limitation"]):
        table.cell(0, i).text = h
    rows = [
        ("Manual online invigilation", "Human observation", "Limited unless screen shared", "Manual notes", "Difficult to scale"),
        ("Camera-only proctoring", "Face and object events", "Not covered", "Camera proof only", "Cannot prove browser misuse"),
        ("Browser-only monitoring", "Not covered", "Focus, clipboard, fullscreen", "Screen proof", "Cannot detect phones or extra persons"),
        ("ProctorAI", "Face, phone, liveness, identity", "Clipboard, focus, fullscreen, screen stop", "Camera and screen evidence", "Needs careful threshold tuning"),
    ]
    for row in rows:
        cells = table.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = v
    format_table(table)
    add_caption(doc, "Table VII. Comparison plan with baseline proctoring approaches.")
    add_heading(doc, "E. Hyperparameter Tuning", level=2)
    add_para(
        doc,
        "The main parameters to tune are object detection confidence threshold, consecutive-frame count for event confirmation, liveness motion threshold, audio activity threshold, and identity match threshold. The tuning strategy will compare lenient, moderate, and strict settings on the validation set. The selected configuration should reduce false positives while still detecting important integrity risks.",
    )
    table = doc.add_table(rows=1, cols=4)
    for i, h in enumerate(["Parameter", "Candidate Values", "Validation Signal", "Selection Rule"]):
        table.cell(0, i).text = h
    rows = [
        ("YOLO confidence", "0.25, 0.40, 0.60", "Phone false positives and misses", "Best F1-score"),
        ("Face absent frames", "2, 3, 5 consecutive frames", "Temporary camera glitches", "Low false positive rate"),
        ("Liveness threshold", "Low, medium, high motion", "Challenge pass/fail reliability", "Best valid-user pass rate"),
        ("Audio threshold", "Low, medium, high level", "Background noise detection", "Balanced false alarms"),
        ("Identity similarity", "Lenient, moderate, strict", "Selfie match validation", "Manual review band near threshold"),
    ]
    for row in rows:
        cells = table.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = v
    format_table(table)
    add_caption(doc, "Table VIII. Hyperparameter tuning plan.")
    add_heading(doc, "F. Implementation Environment", level=2)
    add_para(
        doc,
        "The implementation uses a React and TypeScript candidate portal, a React based examiner/proctor portal, a FastAPI backend, SQLite for reliable local development, PostgreSQL as the production target, and a Python AI sidecar for computer vision tasks. The local development environment uses fixed service ports for the API, AI engine, web portal, and candidate portal so that candidate-to-proctor event flow can be tested repeatedly.",
    )
    add_heading(doc, "G. Validation Scenarios", level=2)
    table = doc.add_table(rows=1, cols=4)
    for i, h in enumerate(["Scenario", "Expected Event", "Evidence Expected", "Pass Condition"]):
        table.cell(0, i).text = h
    rows = [
        ("Candidate remains visible", "No suspicious event", "None", "No false alert generated"),
        ("Candidate leaves frame", "FACE_ABSENT", "Camera proof", "Event appears in proctor queue"),
        ("Phone shown to camera", "PHONE_DETECTED", "Camera clip", "YOLO confidence stored"),
        ("Copy and paste attempted", "Clipboard event", "Screen clip", "Browser event sent live"),
        ("Screen sharing stopped", "SCREEN_RECORDING_STOPPED", "Screen state proof", "Test is blocked or flagged"),
        ("Different person appears", "IDENTITY_MISMATCH or UNKNOWN_FACE", "Identity proof", "Proctor review requested"),
    ]
    for row in rows:
        cells = table.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = v
    format_table(table)
    add_caption(doc, "Table IX. Validation scenarios for final testing.")
    add_para(
        doc,
        "The final validation will be performed by running each scenario multiple times under normal light, low light, different camera angles, and temporary network interruptions. This is needed because proctoring systems fail most often in ordinary real-world conditions rather than in clean laboratory conditions. The expected result is not zero false positives, but a controlled event workflow where false positives can be reviewed and dismissed by the proctor.",
    )


def add_intro(doc):
    add_heading(doc, "I. Introduction")
    add_para(
        doc,
        "Online examinations are useful because they allow students to appear for tests without being physically present in a classroom. At the same time, they create a serious supervision problem. In a normal examination hall, an invigilator can observe the candidate, check the surroundings, and notice suspicious actions. In an online test, the candidate may use a phone, receive help from another person, leave the camera frame, switch tabs, copy answers, or stop screen recording.",
    )
    add_para(
        doc,
        "The problem addressed in this project is the lack of reliable and reviewable supervision in online assessments. Many simple online test systems only provide questions and answer submission. They do not provide strong setup checks, candidate identity verification, browser activity tracking, or evidence based proctor review. This makes them weak for serious college examinations.",
    )
    add_para(
        doc,
        "ProctorAI is proposed as an AI based online proctoring system for college assessments. It combines a candidate portal, examiner/proctor portal, backend API, local AI sidecar, screen recording checks, camera and microphone monitoring, liveness verification, and event evidence review. The system is designed to detect suspicious behavior and send integrity events to a proctor instead of automatically punishing the candidate.",
    )
    add_para(
        doc,
        "The main contribution of this project is a privacy-aware multi-signal proctoring workflow. The system uses AI and browser signals together: face absence, multiple persons, phone detection, copy and paste, focus lost, fullscreen exit, screen recording stopped, background audio, liveness failure, and identity identification. The proctor receives proof and can review the event before making a decision.",
    )
    add_para(
        doc,
        "The motivation for including identity identification is that a candidate may complete setup checks but another person may attempt the assessment. The project therefore includes an identity workflow where a live candidate image is compared with a registered candidate image. This feature is planned as a reviewable verification step rather than an automatic rejection mechanism, because face recognition systems can be affected by camera quality, lighting, pose, and demographic bias.",
    )
    add_para(
        doc,
        "The scope of Phase 2 is to present the architecture, modules, research basis, dataset plan, and evaluation strategy. The project will be completed and fully tested before final project submission, but this report avoids reporting final accuracy values before the validation set is complete.",
    )


def add_conclusion_refs(doc):
    add_heading(doc, "V. Conclusion")
    add_para(
        doc,
        "This Phase 2 report presents the design and development direction of ProctorAI, an AI based online proctoring system for college assessments. The system addresses the problem of weak supervision in online tests by combining candidate setup checks, identity verification, liveness, object detection, browser integrity monitoring, evidence upload, and proctor review.",
    )
    add_para(
        doc,
        "The current limitation is that final quantitative accuracy and latency results still need to be measured after completing the full validation dataset and final project testing. Future work before final submission includes completing identity identification, improving hosted deployment reliability, tuning thresholds, and generating final proctoring reports.",
    )
    add_para(
        doc,
        "The most important future improvement is to make the system reliable across different devices and networks. The final version should use a durable hosted backend, persistent database, protected evidence storage, and a stable real-time event channel. The identity identification module should also be evaluated carefully because face matching can be affected by light, pose, camera quality, and bias. For this reason, ProctorAI keeps identity mismatch as a proctor-review event rather than an automatic failure condition.",
    )
    add_para(
        doc,
        "Before final project submission, the system will be tested using the validation scenarios described in this report. The final report should replace the planned values with measured precision, recall, F1-score, latency, and evidence availability results.",
    )
    doc.add_page_break()
    add_heading(doc, "References")
    refs = [
        "A. Nigam, R. Pasricha, T. Singh, and P. Churi, \"A systematic review on AI-based proctoring systems: Past, present and future,\" Education and Information Technologies, 2021.",
        "R. A. Pramudita et al., \"Survey of online exam proctoring model to detect cheating behavior based on face recognition,\" IEEE Conference Publication, 2022.",
        "A. H. M. et al., \"Towards effective and efficient online exam systems using deep learning-based cheating detection approach,\" Computers and Education: Artificial Intelligence, vol. 3, 2022.",
        "D. Somavarapu et al., \"A systematic-narrative review of online proctoring systems and a case for open standards,\" 2025.",
        "J. Redmon, S. Divvala, R. Girshick, and A. Farhadi, \"You only look once: Unified, real-time object detection,\" Proc. CVPR, 2016.",
        "J. Terven and D. Cordova-Esparza, \"A comprehensive review of YOLO architectures in computer vision: From YOLOv1 to YOLOv8 and YOLO-NAS,\" arXiv:2304.00501, 2023.",
        "T.-Y. Lin et al., \"Microsoft COCO: Common objects in context,\" Proc. ECCV, 2014.",
        "S. Yang, P. Luo, C. C. Loy, and X. Tang, \"WIDER FACE: A face detection benchmark,\" Proc. CVPR, 2016.",
        "K. Zhang, Z. Zhang, Z. Li, and Y. Qiao, \"Joint face detection and alignment using multitask cascaded convolutional networks,\" IEEE Signal Processing Letters, 2016.",
        "V. Bazarevsky et al., \"BlazeFace: Sub-millisecond neural face detection on mobile GPUs,\" arXiv:1907.05047, 2019.",
        "F. Schroff, D. Kalenichenko, and J. Philbin, \"FaceNet: A unified embedding for face recognition and clustering,\" Proc. CVPR, 2015.",
        "J. Deng, J. Guo, N. Xue, and S. Zafeiriou, \"ArcFace: Additive angular margin loss for deep face recognition,\" Proc. CVPR, 2019.",
        "Z. Yu, Y. Qin, X. Li, C. Zhao, Z. Lei, and G. Zhao, \"Deep learning for face anti-spoofing: A survey,\" arXiv:2106.14948, 2021.",
        "T. Baltrusaitis, A. Zadeh, Y. C. Lim, and L.-P. Morency, \"OpenFace 2.0: Facial behavior analysis toolkit,\" Proc. FG, 2018.",
        "M. Burgess et al., \"Watching the watchers: Bias and vulnerability in remote proctoring software,\" USENIX Security Symposium, 2022.",
    ]
    for i, ref in enumerate(refs, 1):
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Cm(0.42)
        p.paragraph_format.first_line_indent = Cm(-0.42)
        p.paragraph_format.space_after = Pt(1)
        r = p.add_run(f"[{i}] {ref}")
        set_font(r, size=8)


def main():
    doc = Document()
    configure_styles(doc)
    add_title_block(doc)
    add_intro(doc)
    add_literature(doc)
    add_methodology(doc)
    add_results(doc)
    add_conclusion_refs(doc)
    doc.save(OUT)


if __name__ == "__main__":
    main()
