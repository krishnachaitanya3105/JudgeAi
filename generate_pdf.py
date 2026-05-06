"""Generate antigravityanalytics.pdf from markdown using fpdf2."""
import re
from fpdf import FPDF

MD_PATH = r"C:\Users\91703\.gemini\antigravity\brain\84b94302-7b14-431d-abb1-91555c325103\artifacts\antigravityanalytics.md"
OUT_PATH = r"d:\JudgeAI\antigravityanalytics.pdf"

with open(MD_PATH, "r", encoding="utf-8") as f:
    lines = f.readlines()


class DocPDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(100, 100, 100)
        self.cell(0, 8, "JudgeAI — Hackathon Submission Documentation", align="C")
        self.ln(4)
        self.set_draw_color(79, 70, 229)
        self.set_line_width(0.5)
        self.line(10, 14, self.w - 10, 14)
        self.ln(6)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")


pdf = DocPDF()
pdf.alias_nb_pages()
pdf.set_auto_page_break(auto=True, margin=20)
pdf.add_page()
pdf.set_font("Helvetica", size=10)

TABLE_ROWS = []
IN_TABLE = False
IN_CODE = False
CODE_LINES = []

def flush_table(pdf, rows):
    if not rows:
        return
    headers = rows[0]
    data_rows = rows[1:]  # skip separator row if present
    if data_rows and all(c.strip().replace("-","") == "" for c in data_rows[0]):
        data_rows = data_rows[1:]
    
    n_cols = len(headers)
    if n_cols == 0:
        return
    col_w = (pdf.w - 20) / n_cols
    
    # Header
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(79, 70, 229)
    pdf.set_text_color(255, 255, 255)
    for h in headers:
        pdf.cell(col_w, 7, h.strip(), border=1, fill=True)
    pdf.ln()
    
    # Data
    pdf.set_font("Helvetica", size=8.5)
    pdf.set_text_color(30, 30, 30)
    fill = False
    for row in data_rows:
        if fill:
            pdf.set_fill_color(245, 245, 250)
        else:
            pdf.set_fill_color(255, 255, 255)
        for i, cell in enumerate(row):
            txt = cell.strip()[:80]
            pdf.cell(col_w, 6, txt, border=1, fill=True)
        pdf.ln()
        fill = not fill
    pdf.ln(3)

def write_line(pdf, text):
    text = text.rstrip("\n")
    
    # Headings
    if text.startswith("# "):
        pdf.ln(6)
        pdf.set_font("Helvetica", "B", 18)
        pdf.set_text_color(79, 70, 229)
        pdf.multi_cell(0, 9, text[2:].strip())
        pdf.set_draw_color(79, 70, 229)
        pdf.line(10, pdf.get_y(), pdf.w - 10, pdf.get_y())
        pdf.ln(4)
        return
    if text.startswith("## "):
        pdf.ln(4)
        pdf.set_font("Helvetica", "B", 14)
        pdf.set_text_color(30, 41, 59)
        pdf.multi_cell(0, 8, text[3:].strip())
        pdf.set_draw_color(226, 232, 240)
        pdf.line(10, pdf.get_y(), pdf.w - 10, pdf.get_y())
        pdf.ln(3)
        return
    if text.startswith("### "):
        pdf.ln(3)
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(51, 65, 85)
        pdf.multi_cell(0, 7, text[4:].strip())
        pdf.ln(2)
        return
    
    # Blockquote
    if text.startswith("> "):
        pdf.set_font("Helvetica", "I", 10)
        pdf.set_text_color(79, 70, 229)
        pdf.set_fill_color(241, 245, 249)
        pdf.multi_cell(0, 6, "  " + text[2:].strip(), fill=True)
        pdf.ln(2)
        return
    
    # Horizontal rule
    if text.strip() == "---":
        pdf.set_draw_color(226, 232, 240)
        pdf.line(10, pdf.get_y(), pdf.w - 10, pdf.get_y())
        pdf.ln(4)
        return
    
    # Bullet points
    if text.startswith("- ") or text.startswith("* "):
        pdf.set_font("Helvetica", size=10)
        pdf.set_text_color(30, 30, 30)
        # Clean markdown formatting
        clean = text[2:].strip()
        clean = re.sub(r'\*\*(.*?)\*\*', r'\1', clean)
        clean = re.sub(r'\*(.*?)\*', r'\1', clean)
        clean = re.sub(r'`(.*?)`', r'\1', clean)
        clean = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', clean)
        pdf.multi_cell(0, 6, "  • " + clean)
        pdf.ln(1)
        return
    
    # Empty line
    if not text.strip():
        pdf.ln(3)
        return
    
    # Normal text
    pdf.set_font("Helvetica", size=10)
    pdf.set_text_color(30, 30, 30)
    clean = text.strip()
    clean = re.sub(r'\*\*(.*?)\*\*', r'\1', clean)
    clean = re.sub(r'\*(.*?)\*', r'\1', clean)
    clean = re.sub(r'`(.*?)`', r'\1', clean)
    clean = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', clean)
    pdf.multi_cell(0, 6, clean)
    pdf.ln(1)

i = 0
while i < len(lines):
    line = lines[i]
    
    # Code block
    if line.strip().startswith("```"):
        if IN_CODE:
            # End code block - render
            pdf.set_font("Courier", size=8)
            pdf.set_text_color(226, 232, 240)
            pdf.set_fill_color(30, 41, 59)
            for cl in CODE_LINES:
                pdf.cell(0, 5, cl.rstrip("\n")[:100], fill=True, new_x="LMARGIN", new_y="NEXT")
            pdf.ln(3)
            CODE_LINES = []
            IN_CODE = False
        else:
            IN_CODE = True
            CODE_LINES = []
        i += 1
        continue
    
    if IN_CODE:
        CODE_LINES.append(line)
        i += 1
        continue
    
    # Table
    if "|" in line and line.strip().startswith("|"):
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if not IN_TABLE:
            IN_TABLE = True
            TABLE_ROWS = [cells]
        else:
            TABLE_ROWS.append(cells)
        i += 1
        continue
    elif IN_TABLE:
        flush_table(pdf, TABLE_ROWS)
        TABLE_ROWS = []
        IN_TABLE = False
    
    write_line(pdf, line)
    i += 1

if IN_TABLE:
    flush_table(pdf, TABLE_ROWS)

pdf.output(OUT_PATH)
print(f"PDF generated successfully: {OUT_PATH}")
