# -*- coding: utf-8 -*-
"""
docx_lib.py —— 按《综合实践III报告参考模板》排版规则生成 docx 的工具库
作者：【姓名】  学号：【学号】  创建时间：2026-07
排版规则（来自模板附录）：
  - 章标题：三号(16pt) 黑体 居中，每章另起一页；
  - 节标题：小四(12pt) 黑体 左对齐（二级标题退位缩进可选）；
  - 正文：小四(12pt) 宋体，首行缩进2字符，1.5倍行距；
  - 图题：图下方 五号(10.5pt) 居中，编号"图X-Y"；
  - 表题：表上方 五号(10.5pt) 居中，编号"表X-Y"；
  - 目录：插入 Word TOC 域（打开后右键"更新域"或按 F9）。
"""
import os

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

BLACK = RGBColor(0, 0, 0)

EA_HEI = "黑体"
EA_SONG = "宋体"
ASCII_FONT = "Times New Roman"
MONO = "Consolas"


def _set_rfonts(rpr, ea):
    rFonts = rpr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rpr.append(rFonts)
    rFonts.set(qn("w:ascii"), ASCII_FONT)
    rFonts.set(qn("w:hAnsi"), ASCII_FONT)
    rFonts.set(qn("w:eastAsia"), ea)


def _set_style_font(style, ea, size_pt, bold=False):
    style.font.name = ASCII_FONT
    style.font.size = Pt(size_pt)
    style.font.bold = bold
    style.font.color.rgb = BLACK
    rpr = style.element.get_or_add_rPr()
    _set_rfonts(rpr, ea)


def init_styles(doc):
    """配置内置样式，保证目录/导航可用且外观符合模板。"""
    st = doc.styles

    # Heading 1: 三号黑体 居中
    h1 = st["Heading 1"]
    _set_style_font(h1, EA_HEI, 16, bold=False)
    h1.font.color.rgb = BLACK
    pf = h1.paragraph_format
    pf.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pf.space_before = Pt(6)
    pf.space_after = Pt(18)
    pf.line_spacing = 1.5

    # Heading 2: 小四黑体 左对齐
    h2 = st["Heading 2"]
    _set_style_font(h2, EA_HEI, 12, bold=False)
    h2.font.color.rgb = BLACK
    pf = h2.paragraph_format
    pf.alignment = WD_ALIGN_PARAGRAPH.LEFT
    pf.space_before = Pt(10)
    pf.space_after = Pt(6)
    pf.line_spacing = 1.5

    # Heading 3: 小四黑体
    h3 = st["Heading 3"]
    _set_style_font(h3, EA_HEI, 12, bold=False)
    h3.font.color.rgb = BLACK
    pf = h3.paragraph_format
    pf.alignment = WD_ALIGN_PARAGRAPH.LEFT
    pf.space_before = Pt(6)
    pf.space_after = Pt(4)
    pf.line_spacing = 1.5

    # Normal: 小四宋体，1.5倍行距
    n = st["Normal"]
    _set_style_font(n, EA_SONG, 12, bold=False)
    n.paragraph_format.line_spacing = 1.5
    n.paragraph_format.space_after = Pt(0)

    # 封面用标题样式
    if "CoverTitle" not in [s.name for s in st]:
        cs = st.add_style("CoverTitle", 1)  # paragraph style
    cs = st["CoverTitle"]
    _set_style_font(cs, EA_HEI, 26, bold=True)
    cs.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # 图题/表题样式（五号）
    if "CapStyle" not in [s.name for s in st]:
        cap = st.add_style("CapStyle", 1)
    cap = st["CapStyle"]
    _set_style_font(cap, EA_SONG, 10.5, bold=False)
    cap.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cap.paragraph_format.line_spacing = 1.2

    # 代码样式（小五 Consolas/等线）
    if "CodeStyle" not in [s.name for s in st]:
        code = st.add_style("CodeStyle", 1)
    code = st["CodeStyle"]
    code.font.name = MONO
    code.font.size = Pt(9)
    rpr = code.element.get_or_add_rPr()
    rf = rpr.find(qn("w:rFonts"))
    if rf is None:
        rf = OxmlElement("w:rFonts")
        rpr.append(rf)
    rf.set(qn("w:ascii"), MONO)
    rf.set(qn("w:hAnsi"), MONO)
    rf.set(qn("w:eastAsia"), "宋体")
    code.paragraph_format.line_spacing = 1.0
    code.paragraph_format.space_after = Pt(0)


def add_para(doc, text, style=None, align=None, indent_chars=0,
             space_after=0, bold=False, size=None, font_ea=None):
    p = doc.add_paragraph(style=style)
    run = p.add_run(text)
    if bold or size or font_ea:
        run.bold = bold
        if size:
            run.font.size = Pt(size)
        if font_ea:
            rpr = run._element.get_or_add_rPr()
            _set_rfonts(rpr, font_ea)
    if align is not None:
        p.alignment = align
    if indent_chars:
        # 首行缩进按字符数：小四=12pt，1字符≈12pt
        p.paragraph_format.first_line_indent = Pt(12 * indent_chars)
    if space_after:
        p.paragraph_format.space_after = Pt(space_after)
    return p


def add_body(doc, text, indent=2):
    """正文：小四宋体，首行缩进两字符。"""
    return add_para(doc, text, indent_chars=indent)


def add_h1(doc, text, page_break=True):
    p = doc.add_heading(level=1)
    r = p.add_run(text)
    r.bold = False
    if page_break:
        p.paragraph_format.page_break_before = True
    return p


def add_h2(doc, text):
    p = doc.add_heading(level=2)
    p.add_run(text).bold = False
    return p


def add_h3(doc, text):
    p = doc.add_heading(level=3)
    p.add_run(text).bold = False
    return p


def add_center_title(doc, text, size=26):
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.bold = True
    run.font.size = Pt(size)
    rpr = run._element.get_or_add_rPr()
    _set_rfonts(rpr, EA_HEI)
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    return p


def add_fig(doc, img_path, caption, width_cm=13.0):
    """插图：图片居中，图题在下方（五号）。"""
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(6)
    run = p.add_run()
    run.add_picture(img_path, width=Cm(width_cm))
    cap = doc.add_paragraph(style="CapStyle")
    cap.add_run(caption)
    return p


def add_table(doc, caption, headers, rows, col_widths=None, font_size=10.5):
    """表格：表题在上方（五号居中），内容五号。"""
    cap = doc.add_paragraph(style="CapStyle")
    cap.add_run(caption)
    cap.paragraph_format.space_before = Pt(6)
    n_cols = len(headers)
    t = doc.add_table(rows=1 + len(rows), cols=n_cols)
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    # 表头
    for j, h in enumerate(headers):
        cell = t.cell(0, j)
        cell.text = ""
        para = cell.paragraphs[0]
        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = para.add_run(h)
        run.bold = True
        run.font.size = Pt(font_size)
        _shade(cell, "DCE6F1")
    # 内容
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            cell = t.cell(i + 1, j)
            cell.text = ""
            para = cell.paragraphs[0]
            para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = para.add_run(str(val))
            run.font.size = Pt(font_size)
    if col_widths:
        for j, w in enumerate(col_widths):
            for row in t.rows:
                row.cells[j].width = Cm(w)
    return t


def _shade(cell, hex_color):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:fill"), hex_color)
    tcPr.append(shd)


def add_code(doc, code, caption=None):
    """代码段：灰底小五等宽字体。caption 为可选的小字说明。"""
    if caption:
        p = doc.add_paragraph()
        r = p.add_run(caption)
        r.font.size = Pt(9)
        r.font.color.rgb = None
        p.paragraph_format.space_before = Pt(6)
        p.paragraph_format.space_after = Pt(2)
    lines = code.strip("\n").split("\n")
    for ln in lines:
        p = doc.add_paragraph(style="CodeStyle")
        run = p.add_run(ln if ln else " ")
        run.font.size = Pt(9)
        _shade_para(p, "F2F2F2")
    doc.add_paragraph().paragraph_format.space_after = Pt(0)


def _shade_para(p, hex_color):
    pPr = p._p.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:fill"), hex_color)
    pPr.append(shd)


def add_toc(doc):
    """插入目录（Word TOC 域，打开后 F9/右键更新）。"""
    p = doc.add_paragraph()
    p.paragraph_format.page_break_before = True
    run = p.add_run()
    fldChar = OxmlElement("w:fldChar")
    fldChar.set(qn("w:fldCharType"), "begin")
    instrText = OxmlElement("w:instrText")
    instrText.set(qn("xml:space"), "preserve")
    instrText.text = 'TOC \\o "1-2" \\h \\z \\u'
    fldChar2 = OxmlElement("w:fldChar")
    fldChar2.set(qn("w:fldCharType"), "separate")
    t = OxmlElement("w:t")
    t.text = "（目录：请在 Word 中右键此处 → 更新域 自动生成）"
    fldChar3 = OxmlElement("w:fldChar")
    fldChar3.set(qn("w:fldCharType"), "end")
    r = run._element
    r.append(fldChar)
    r.append(instrText)
    r.append(fldChar2)
    r.append(t)
    r.append(fldChar3)
    return p


def add_page_number_footer(doc):
    """页脚居中页码（PAGE 域）。"""
    section = doc.sections[0]
    footer = section.footer
    p = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run()
    fld1 = OxmlElement("w:fldChar"); fld1.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText"); instr.set(qn("xml:space"), "preserve")
    instr.text = "PAGE"
    fld2 = OxmlElement("w:fldChar"); fld2.set(qn("w:fldCharType"), "end")
    run._element.append(fld1)
    run._element.append(instr)
    run._element.append(fld2)
    run.font.size = Pt(10.5)


def new_doc():
    doc = Document()
    init_styles(doc)
    for section in doc.sections:
        section.top_margin = Cm(2.54)
        section.bottom_margin = Cm(2.54)
        section.left_margin = Cm(3.0)
        section.right_margin = Cm(2.6)
    add_page_number_footer(doc)
    return doc


def rel(path):
    """相对工程根目录解析路径（调用方传入 ROOT）。"""
    return path
