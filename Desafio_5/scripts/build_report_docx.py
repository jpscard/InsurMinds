import os
import re
import shutil
import docx
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import parse_xml, OxmlElement
from docx.oxml.ns import nsdecls, qn

def set_cell_background(cell, color_hex):
    """Sets cell background color."""
    shading_elm = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{color_hex}"/>')
    cell._tc.get_or_add_tcPr().append(shading_elm)

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    """Sets inner margins (padding) for a cell in dxa (1 pt = 20 dxa)."""
    tcMar = parse_xml(
        f'<w:tcMar {nsdecls("w")}>'
        f'<w:top w:w="{top}" w:type="dxa"/>'
        f'<w:bottom w:w="{bottom}" w:type="dxa"/>'
        f'<w:left w:w="{left}" w:type="dxa"/>'
        f'<w:right w:w="{right}" w:type="dxa"/>'
        f'</w:tcMar>'
    )
    cell._tc.get_or_add_tcPr().append(tcMar)

def set_cell_borders(cell, top="D1D5DB", bottom="D1D5DB", left=None, right=None, sz="4"):
    """Sets subtle borders for a table cell."""
    top_xml = f'<w:top w:val="single" w:sz="{sz}" w:space="0" w:color="{top}"/>' if top else '<w:top w:val="none"/>'
    bot_xml = f'<w:bottom w:val="single" w:sz="{sz}" w:space="0" w:color="{bottom}"/>' if bottom else '<w:bottom w:val="none"/>'
    left_xml = f'<w:left w:val="single" w:sz="{sz}" w:space="0" w:color="{left}"/>' if left else '<w:left w:val="none"/>'
    right_xml = f'<w:right w:val="single" w:sz="{sz}" w:space="0" w:color="{right}"/>' if right else '<w:right w:val="none"/>'
    
    borders = parse_xml(
        f'<w:tcBorders {nsdecls("w")}>{top_xml}{left_xml}{bot_xml}{right_xml}</w:tcBorders>'
    )
    cell._tc.get_or_add_tcPr().append(borders)

def add_styled_heading(doc, text, level):
    p = doc.add_paragraph()
    p.paragraph_format.keep_with_next = True
    
    if level == 1:
        p.paragraph_format.space_before = Pt(18)
        p.paragraph_format.space_after = Pt(6)
        run = p.add_run(text)
        run.font.name = 'Segoe UI'
        run.font.size = Pt(14)
        run.font.bold = True
        run.font.color.rgb = RGBColor(0x0F, 0x2B, 0x48)
    elif level == 2:
        p.paragraph_format.space_before = Pt(14)
        p.paragraph_format.space_after = Pt(4)
        run = p.add_run(text)
        run.font.name = 'Segoe UI'
        run.font.size = Pt(12)
        run.font.bold = True
        run.font.color.rgb = RGBColor(0x1E, 0x3A, 0x8A)
    elif level == 3:
        p.paragraph_format.space_before = Pt(10)
        p.paragraph_format.space_after = Pt(3)
        run = p.add_run(text)
        run.font.name = 'Segoe UI'
        run.font.size = Pt(11)
        run.font.bold = True
        run.font.color.rgb = RGBColor(0x25, 0x63, 0xEB)
    else:
        p.paragraph_format.space_before = Pt(8)
        p.paragraph_format.space_after = Pt(2)
        run = p.add_run(text)
        run.font.name = 'Segoe UI'
        run.font.size = Pt(10)
        run.font.bold = True
        run.font.color.rgb = RGBColor(0x33, 0x41, 0x55)
    return p

def add_formatted_runs(paragraph, text, default_font='Segoe UI', default_size=10, default_color=RGBColor(0x1F, 0x29, 0x37), italic_base=False):
    """Parses markdown bold, italic, code, and links into styled runs."""
    tokens = re.split(r'(\*\*.*?\*\*|\*.*?\*|`.*?`|\[.*?\]\(.*?\))', text)
    for token in tokens:
        if not token:
            continue
        if token.startswith('**') and token.endswith('**') and len(token) >= 4:
            run = paragraph.add_run(token[2:-2])
            run.font.name = default_font
            run.font.size = Pt(default_size)
            run.font.bold = True
            run.font.italic = italic_base
            run.font.color.rgb = default_color
        elif token.startswith('*') and token.endswith('*') and len(token) >= 2 and not token.startswith('**'):
            run = paragraph.add_run(token[1:-1])
            run.font.name = default_font
            run.font.size = Pt(default_size)
            run.font.italic = True
            run.font.color.rgb = default_color
        elif token.startswith('`') and token.endswith('`') and len(token) >= 2:
            run = paragraph.add_run(token[1:-1])
            run.font.name = 'Consolas'
            run.font.size = Pt(default_size - 0.5)
            run.font.color.rgb = RGBColor(0x0F, 0x17, 0x2A)
        elif token.startswith('[') and '](' in token and token.endswith(')'):
            m = re.match(r'\[(.*?)\]\((.*?)\)', token)
            if m:
                link_text = m.group(1)
                run = paragraph.add_run(link_text)
                run.font.name = default_font
                run.font.size = Pt(default_size)
                run.font.color.rgb = RGBColor(0x25, 0x63, 0xEB)
                run.font.underline = True
            else:
                run = paragraph.add_run(token)
                run.font.name = default_font
                run.font.size = Pt(default_size)
        else:
            run = paragraph.add_run(token)
            run.font.name = default_font
            run.font.size = Pt(default_size)
            run.font.italic = italic_base
            run.font.color.rgb = default_color

def build_docx_from_markdown(md_path, docx_path):
    with open(md_path, 'r', encoding='utf-8') as f:
        content = f.read()

    lines = content.split('\n')
    doc = Document()

    # Set page layout to Letter with 1 inch margins
    for section in doc.sections:
        section.top_margin = Inches(0.9)
        section.bottom_margin = Inches(0.9)
        section.left_margin = Inches(1.0)
        section.right_margin = Inches(1.0)
        section.page_width = Inches(8.5)
        section.page_height = Inches(11.0)
        
        # Configure Header & Footer
        header = section.header
        hp = header.paragraphs[0]
        hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        hrun = hp.add_run("InsureAlert — Desafio 5: Comunicação Proativa com Segurados")
        hrun.font.name = 'Segoe UI'
        hrun.font.size = Pt(8.5)
        hrun.font.color.rgb = RGBColor(0x94, 0xA3, 0xB8)
        
        footer = section.footer
        fp = footer.paragraphs[0]
        fp.alignment = WD_ALIGN_PARAGRAPH.LEFT
        frun = fp.add_run("InsurMinds — Desafio 5 | Grupo JL (Leonardo Pereira & João Cardoso)")
        frun.font.name = 'Segoe UI'
        frun.font.size = Pt(8.5)
        frun.font.color.rgb = RGBColor(0x94, 0xA3, 0xB8)

    i = 0
    n = len(lines)

    in_code_block = False
    code_block_lines = []
    code_block_lang = ""

    while i < n:
        line = lines[i]
        stripped = line.strip()

        # Handle code blocks
        if stripped.startswith('```'):
            if not in_code_block:
                in_code_block = True
                code_block_lang = stripped[3:].strip()
                code_block_lines = []
                i += 1
                continue
            else:
                in_code_block = False
                # If it's a mermaid diagram for architecture, embed the actual diagram image!
                if 'mermaid' in code_block_lang and any('subgraph Apresentacao' in l for l in code_block_lines):
                    arch_img = 'docs/images/arch_diagram_extracted.png'
                    if os.path.exists(arch_img):
                        p = doc.add_paragraph()
                        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                        p.paragraph_format.space_before = Pt(8)
                        p.paragraph_format.space_after = Pt(2)
                        p_run = p.add_run()
                        p_run.add_picture(arch_img, height=Inches(7.2))
                        cp = doc.add_paragraph()
                        cp.alignment = WD_ALIGN_PARAGRAPH.CENTER
                        cp.paragraph_format.space_after = Pt(8)
                        crun = cp.add_run("Figura: Arquitetura da Solução — Visão Completa em Camadas e Esteira Multi-Agente")
                        crun.font.name = 'Segoe UI'
                        crun.font.size = Pt(9)
                        crun.font.italic = True
                        crun.font.color.rgb = RGBColor(0x64, 0x74, 0x8B)
                elif 'mermaid' in code_block_lang and any('flowchart TD' in l for l in code_block_lines):
                    # For flowchart, add a styled summary box
                    p = doc.add_paragraph()
                    p.paragraph_format.space_before = Pt(6)
                    p.paragraph_format.space_after = Pt(4)
                    p.paragraph_format.left_indent = Inches(0.2)
                    run_t = p.add_run("Fluxo Procedural do Pipeline Multi-Agente:\n")
                    run_t.font.bold = True
                    run_t.font.color.rgb = RGBColor(0x1E, 0x3A, 0x8A)
                    flow_steps = [
                        "1. Disparo Operacional: Operador aciona 'Executar Pipeline' (POST /api/pipeline/run)",
                        "2. Agente 1 — Coleta Meteorológica: Ingestão de alertas ativos no INMET (/avisos/ativos) com contingência automática de 3 cenários",
                        "3. Agente 2 — Análise Semântica: Categorização em 7 tipos de evento, mapeamento de severidade e filtragem por relevância atuarial",
                        "4. Agente 3 — Motor de Regras: Cruzamento geoespacial e coberturas de apólice, cálculo de Score Atuarial e deduplicação",
                        "5. Agente 4 — Comunicação Humanizada: Geração com Google Gemini 2.5 Flash Lite (ou templates institucionais sem emojis), adaptação omnicanal e simulação com carimbo de envio",
                        "6. Conclusão e Auditoria: Atualização do estado global do servidor, emissão de métricas atuariais (ROI, sinistros evitados) e registro contínuo no Barramento de Auditoria (Event Bus)"
                    ]
                    for step in flow_steps:
                        sp = doc.add_paragraph()
                        sp.paragraph_format.left_indent = Inches(0.35)
                        sp.paragraph_format.space_after = Pt(2)
                        srun = sp.add_run(step)
                        srun.font.name = 'Segoe UI'
                        srun.font.size = Pt(9.5)
                        srun.font.color.rgb = RGBColor(0x33, 0x41, 0x55)
                else:
                    # Regular code block
                    table = doc.add_table(rows=1, cols=1)
                    table.alignment = WD_TABLE_ALIGNMENT.CENTER
                    cell = table.cell(0, 0)
                    set_cell_background(cell, "F1F5F9")
                    set_cell_borders(cell, top="CBD5E1", bottom="CBD5E1", left="CBD5E1", right="CBD5E1")
                    set_cell_margins(cell, top=100, bottom=100, left=150, right=150)
                    cell.width = Inches(6.5)
                    cp = cell.paragraphs[0]
                    cp.paragraph_format.space_after = Pt(0)
                    cp.paragraph_format.line_spacing = 1.05
                    c_run = cp.add_run('\n'.join(code_block_lines))
                    c_run.font.name = 'Consolas'
                    c_run.font.size = Pt(8.5)
                    c_run.font.color.rgb = RGBColor(0x0F, 0x17, 0x2A)
                    doc.add_paragraph().paragraph_format.space_after = Pt(4)
                
                i += 1
                continue

        if in_code_block:
            code_block_lines.append(line)
            i += 1
            continue

        # Blank line
        if not stripped:
            i += 1
            continue

        # Horizontal Rule
        if stripped in ('---', '***', '___'):
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(6)
            p.paragraph_format.space_after = Pt(6)
            run = p.add_run("—" * 50)
            run.font.color.rgb = RGBColor(0xE2, 0xE8, 0xF0)
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            i += 1
            continue

        # Headings
        if stripped.startswith('#'):
            h_match = re.match(r'^(#{1,6})\s+(.*)$', stripped)
            if h_match:
                level = len(h_match.group(1))
                h_text = h_match.group(2).strip()
                
                if level == 1 and i < 5:
                    # Main Document Title
                    # Add logo if exists
                    logo_path = 'docs/images/logo_dark.png'
                    if os.path.exists(logo_path):
                        lp = doc.add_paragraph()
                        lp.alignment = WD_ALIGN_PARAGRAPH.CENTER
                        lp.paragraph_format.space_before = Pt(6)
                        lp.paragraph_format.space_after = Pt(6)
                        l_run = lp.add_run()
                        l_run.add_picture(logo_path, width=Inches(2.2))
                    
                    p = doc.add_paragraph()
                    p.paragraph_format.space_before = Pt(4)
                    p.paragraph_format.space_after = Pt(2)
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    trun = p.add_run("RELATÓRIO TÉCNICO — INSURMINDS DESAFIO 5")
                    trun.font.name = 'Segoe UI'
                    trun.font.size = Pt(12)
                    trun.font.bold = True
                    trun.font.color.rgb = RGBColor(0x25, 0x63, 0xEB)
                    
                    p2 = doc.add_paragraph()
                    p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    p2.paragraph_format.space_after = Pt(12)
                    t2run = p2.add_run("InsureAlert — Sistema Multi-Agente de Comunicação Proativa com Segurados")
                    t2run.font.name = 'Segoe UI'
                    t2run.font.size = Pt(16)
                    t2run.font.bold = True
                    t2run.font.color.rgb = RGBColor(0x0F, 0x2B, 0x48)
                else:
                    add_styled_heading(doc, h_text, level)
                i += 1
                continue

        # Standalone Images: ![caption](path)
        img_match = re.match(r'^!\[(.*?)\]\((.*?)\)$', stripped)
        if img_match:
            caption = img_match.group(1)
            img_src = img_match.group(2).strip()
            
            # Resolve relative path
            img_file = img_src.replace('\\', '/')
            if not os.path.exists(img_file):
                img_file = os.path.join('docs/images', os.path.basename(img_src))
            
            if os.path.exists(img_file):
                p = doc.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p.paragraph_format.space_before = Pt(8)
                p.paragraph_format.space_after = Pt(2)
                
                # Standard width for screenshots
                p_run = p.add_run()
                p_run.add_picture(img_file, width=Inches(5.4))
                
                if caption:
                    cp = doc.add_paragraph()
                    cp.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    cp.paragraph_format.space_after = Pt(8)
                    crun = cp.add_run(f"Figura: {caption}")
                    crun.font.name = 'Segoe UI'
                    crun.font.size = Pt(9)
                    crun.font.italic = True
                    crun.font.color.rgb = RGBColor(0x64, 0x74, 0x8B)
            i += 1
            continue

        # Blockquotes: > text
        if stripped.startswith('>'):
            quote_text = stripped[1:].strip()
            while i + 1 < n and lines[i+1].strip().startswith('>'):
                i += 1
                quote_text += "\n" + lines[i].strip()[1:].strip()
            
            # Shaded single cell table for clean callout
            table = doc.add_table(rows=1, cols=1)
            table.alignment = WD_TABLE_ALIGNMENT.CENTER
            cell = table.cell(0, 0)
            set_cell_background(cell, "F8FAFC")
            set_cell_borders(cell, top="E2E8F0", bottom="E2E8F0", left="2563EB", right="E2E8F0", sz="8")
            set_cell_margins(cell, top=80, bottom=80, left=140, right=140)
            cell.width = Inches(6.5)
            
            cp = cell.paragraphs[0]
            cp.paragraph_format.space_after = Pt(0)
            add_formatted_runs(cp, quote_text, default_size=9.5, italic_base=False)
            
            doc.add_paragraph().paragraph_format.space_after = Pt(4)
            i += 1
            continue

        # Markdown Tables: | col | col |
        if stripped.startswith('|') and '|' in stripped[1:]:
            table_lines = []
            while i < n and lines[i].strip().startswith('|'):
                table_lines.append(lines[i].strip())
                i += 1
            
            # Parse table rows
            parsed_rows = []
            for tl in table_lines:
                if re.match(r'^\|(\s*:?-+:?\s*\|)+$', tl):
                    continue
                cells = [c.strip() for c in tl.strip('|').split('|')]
                parsed_rows.append(cells)
            
            if parsed_rows:
                num_cols = max(len(r) for r in parsed_rows)
                for r in parsed_rows:
                    while len(r) < num_cols:
                        r.append("")
                
                # Check if this is an image table (e.g. side-by-side screenshots)
                is_image_table = False
                for r in parsed_rows:
                    for c in r:
                        if '![' in c and '](' in c:
                            is_image_table = True
                            break
                
                table = doc.add_table(rows=len(parsed_rows), cols=num_cols)
                table.alignment = WD_TABLE_ALIGNMENT.CENTER
                
                tblPr = table._tbl.tblPr
                tblCellMar = parse_xml(
                    f'<w:tblCellMar {nsdecls("w")}>'
                    f'<w:top w:w="80" w:type="dxa"/>'
                    f'<w:bottom w:w="80" w:type="dxa"/>'
                    f'<w:left w:w="120" w:type="dxa"/>'
                    f'<w:right w:w="120" w:type="dxa"/>'
                    f'</w:tblCellMar>'
                )
                tblPr.append(tblCellMar)
                
                col_width = Inches(6.5 / num_cols)
                
                for row_idx, row_data in enumerate(parsed_rows):
                    is_header = (row_idx == 0 and not is_image_table)
                    for col_idx, cell_text in enumerate(row_data):
                        cell = table.cell(row_idx, col_idx)
                        cell.width = col_width
                        cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
                        
                        if is_header:
                            set_cell_background(cell, "1E3A8A")
                            set_cell_borders(cell, top="1E3A8A", bottom="1E3A8A", left="3B82F6", right="3B82F6")
                        else:
                            bg = "F8FAFC" if row_idx % 2 == 1 else "FFFFFF"
                            set_cell_background(cell, bg)
                            set_cell_borders(cell, top="E2E8F0", bottom="E2E8F0", left=None, right=None)
                        
                        set_cell_margins(cell, top=70, bottom=70, left=100, right=100)
                        
                        p = cell.paragraphs[0]
                        p.paragraph_format.space_after = Pt(0)
                        p.paragraph_format.line_spacing = 1.05
                        
                        img_in_cell = re.search(r'!\[(.*?)\]\((.*?)\)', cell_text)
                        if img_in_cell:
                            caption_c = img_in_cell.group(1)
                            img_path_c = img_in_cell.group(2).strip()
                            if not os.path.exists(img_path_c):
                                img_path_c = os.path.join('docs/images', os.path.basename(img_path_c))
                            if os.path.exists(img_path_c):
                                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                                run_img = p.add_run()
                                run_img.add_picture(img_path_c, width=Inches(3.0))
                                if caption_c:
                                    cp = cell.add_paragraph()
                                    cp.alignment = WD_ALIGN_PARAGRAPH.CENTER
                                    cp.paragraph_format.space_after = Pt(2)
                                    crun = cp.add_run(caption_c)
                                    crun.font.name = 'Segoe UI'
                                    crun.font.size = Pt(8.5)
                                    crun.font.italic = True
                                    crun.font.color.rgb = RGBColor(0x64, 0x74, 0x8B)
                        else:
                            if is_header:
                                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                                run = p.add_run(cell_text)
                                run.font.name = 'Segoe UI'
                                run.font.size = Pt(9)
                                run.font.bold = True
                                run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
                            else:
                                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                                add_formatted_runs(p, cell_text, default_size=8.5)
                
                doc.add_paragraph().paragraph_format.space_after = Pt(6)
            continue

        # Bullet Lists: - item or * item
        bullet_match = re.match(r'^[-*]\s+(.*)$', stripped)
        if bullet_match:
            item_text = bullet_match.group(1)
            p = doc.add_paragraph(style='List Bullet')
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.left_indent = Inches(0.25)
            add_formatted_runs(p, item_text, default_size=9.5)
            i += 1
            continue

        # Numbered Lists: 1. item
        num_match = re.match(r'^(\d+)\.\s+(.*)$', stripped)
        if num_match:
            num = num_match.group(1)
            item_text = num_match.group(2)
            p = doc.add_paragraph()
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.left_indent = Inches(0.25)
            num_run = p.add_run(f"{num}. ")
            num_run.font.name = 'Segoe UI'
            num_run.font.size = Pt(9.5)
            num_run.font.bold = True
            num_run.font.color.rgb = RGBColor(0x1E, 0x3A, 0x8A)
            add_formatted_runs(p, item_text, default_size=9.5)
            i += 1
            continue

        # Regular Paragraph
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(3.5)
        p.paragraph_format.line_spacing = 1.15
        add_formatted_runs(p, stripped, default_size=10)
        i += 1

    doc.save(docx_path)
    print(f"Document successfully created: {docx_path}")

if __name__ == '__main__':
    md_file = 'relatorio_sistema.md'
    
    # 1. Backup original docx if not yet backed up
    for f in os.listdir('.'):
        if f.endswith('.docx') and 'InsurMinds' in f and 'Backup' not in f:
            backup_name = 'InsurMinds – Desafio 5 (Backup Original).docx'
            if not os.path.exists(backup_name):
                shutil.copy2(f, backup_name)
                print(f"Backed up original file '{f}' to '{backup_name}'")
            target_docx = f
            break
    else:
        target_docx = 'InsurMinds – Desafio 5 (Atualizado).docx'
        
    print(f"Building updated DOCX for: {target_docx}...")
    build_docx_from_markdown(md_file, target_docx)
    
    # Also create relatorio_sistema.docx
    print("Building relatorio_sistema.docx...")
    build_docx_from_markdown(md_file, 'relatorio_sistema.docx')
    print("All documents generated successfully!")
