"""Generate TruthLens Interview Guide PDF from markdown source."""
from pathlib import Path
import re
from fpdf import FPDF

MD_PATH = Path(__file__).parent / "TruthLens-Interview-Guide.md"
PDF_PATH = Path(__file__).parent / "TruthLens-Interview-Guide.pdf"


class GuidePDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(100, 100, 100)
        self.cell(
            0,
            8,
            sanitize("TruthLens - Interview Preparation Guide"),
            align="C",
            new_x="LMARGIN",
            new_y="NEXT",
        )
        self.ln(2)
        self.set_x(self.l_margin)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(100, 100, 100)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")


def sanitize(text: str) -> str:
    if not text:
        return ""
    replacements = {
        "\u2014": "-",
        "\u2013": "-",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2026": "...",
        "\u2192": "->",
        "\u25ba": ">",
        "\u2502": "|",
        "\u2500": "-",
        "\u2514": "+",
        "\u251c": "+",
        "\u25b6": ">",
        "\u25bc": "v",
        "\u250c": "+",
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text.encode("latin-1", errors="replace").decode("latin-1")


def safe_multi_cell(pdf: FPDF, h: float, text: str, font: str = "Helvetica", style: str = "", size: int = 10) -> None:
    text = (text or " ").strip() or " "
    pdf.set_font(font, style, size)
    pdf.set_x(pdf.l_margin)
    w = pdf.epw
    if len(text) > 100 and " " not in text[:100]:
        for i in range(0, len(text), 90):
            pdf.set_x(pdf.l_margin)
            pdf.multi_cell(w, h, text[i : i + 90])
        return
    while len(text) > 100:
        break_at = text.rfind(" ", 0, 100)
        if break_at < 30:
            break_at = 100
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(w, h, text[:break_at])
        text = text[break_at:].lstrip()
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(w, h, text)


def write_pdf(md_text: str) -> None:
    pdf = GuidePDF()
    pdf.alias_nb_pages()
    pdf.set_margins(18, 18, 18)
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    in_code = False
    for raw_line in md_text.splitlines():
        line = sanitize(raw_line.rstrip())

        # Skip wide ASCII diagram lines
        stripped = line.replace(" ", "")
        if stripped and len(line) > 60 and all(c in "|-+>v^\\/_: .[]()" for c in stripped):
            continue

        if line.startswith("```"):
            in_code = not in_code
            continue

        if in_code:
            pdf.set_text_color(40, 40, 40)
            safe_multi_cell(pdf, 4, line or " ", font="Courier", size=8)
            pdf.set_text_color(0, 0, 0)
            continue

        if not line.strip():
            pdf.ln(3)
            continue

        if line.startswith("# "):
            pdf.ln(4)
            pdf.set_text_color(20, 60, 120)
            safe_multi_cell(pdf, 9, line[2:].strip(), style="B", size=18)
            pdf.set_text_color(0, 0, 0)
            continue

        if line.startswith("## "):
            pdf.ln(3)
            pdf.set_text_color(30, 80, 140)
            safe_multi_cell(pdf, 8, line[3:].strip(), style="B", size=14)
            pdf.set_text_color(0, 0, 0)
            continue

        if line.startswith("### "):
            pdf.ln(2)
            safe_multi_cell(pdf, 7, line[4:].strip(), style="B", size=12)
            continue

        if line.startswith("|") and "|" in line[1:]:
            if re.match(r"^\|[\s\-:|]+\|$", line):
                continue
            safe_multi_cell(pdf, 5, line, font="Courier", size=8)
            continue

        if line.startswith("- ") or line.startswith("* "):
            safe_multi_cell(pdf, 5, "* " + line[2:].strip())
            continue

        if re.match(r"^\d+\.\s", line):
            safe_multi_cell(pdf, 5, line)
            continue

        if line.startswith("**") and line.endswith("**"):
            safe_multi_cell(pdf, 5, line.strip("*"), style="B")
            continue

        if line.startswith(">"):
            pdf.set_text_color(50, 50, 50)
            safe_multi_cell(pdf, 5, line.lstrip("> ").strip(), style="I")
            pdf.set_text_color(0, 0, 0)
            continue

        if line.startswith("---"):
            pdf.ln(2)
            pdf.set_draw_color(200, 200, 200)
            pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
            pdf.ln(3)
            continue

        line = re.sub(r"\*\*([^*]+)\*\*", r"\1", line)
        line = re.sub(r"`([^`]+)`", r"\1", line)
        safe_multi_cell(pdf, 5, line)

    pdf.output(str(PDF_PATH))


if __name__ == "__main__":
    text = MD_PATH.read_text(encoding="utf-8")
    write_pdf(text)
    print(f"Created: {PDF_PATH}")
