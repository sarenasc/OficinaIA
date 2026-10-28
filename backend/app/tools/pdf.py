"""PDF reports, text extraction and merging for authorized local resources."""
from functools import partial
from html import escape
from io import BytesIO

from app.security.permissions import resource_path
from app.tools.files import publish_bytes


def reader(session, agent, source):
    from pypdf import PdfReader
    path = resource_path(session, agent, source["resource_id"], source["path"], "read")
    if path.suffix.lower() != ".pdf" or path.stat().st_size > 20 * 1024 * 1024:
        raise ValueError("PDF requerido, máximo 20 MB")
    result = PdfReader(path, strict=True)
    if result.is_encrypted or len(result.pages) > 200:
        raise ValueError("PDF cifrado o superior a 200 páginas no admitido")
    return result


def read_pdf(session, agent, args):
    document = reader(session, agent, args)
    pages, total = [], 0
    for number, page in enumerate(document.pages, 1):
        text = page.extract_text() or ""
        total += len(text)
        if total > 200000:
            raise ValueError("Texto PDF supera 200000 caracteres")
        pages.append({"page": number, "text": text, "has_text": bool(text.strip())})
    empty = [p["page"] for p in pages if not p["has_text"]]
    return {"pages": pages, "page_count": len(pages), "metadata": {str(k): str(v) for k, v in (document.metadata or {}).items()},
            "pages_without_text": empty, "possibly_scanned": bool(empty), "ocr_performed": False,
            "notice": "Las páginas sin texto pueden ser escaneadas o estar vacías; no se ejecutó OCR" if empty else "PDF con texto extraíble"}


def create_pdf(session, task, agent, args):
    from reportlab.graphics.charts.barcharts import VerticalBarChart
    from reportlab.graphics.shapes import Drawing
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.pdfgen.canvas import Canvas
    from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    if not args["path"].lower().endswith(".pdf"):
        raise ValueError("El documento debe tener extensión .pdf")
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="ReportTitle", parent=styles["Title"], alignment=TA_CENTER))
    story = [Paragraph(escape(args["title"]), styles["ReportTitle"]), Spacer(1, 12)]
    for text in args.get("paragraphs", []):
        story.extend([Paragraph(escape(text).replace("\n", "<br/>"), styles["BodyText"]), Spacer(1, 10)])
    for table in args.get("tables", []):
        headers, rows = table["headers"], table["rows"]
        if not headers or len(headers) > 10 or any(len(row) != len(headers) for row in rows):
            raise ValueError("Tabla PDF requiere de 1 a 10 columnas y filas del mismo ancho")
        cells = [[Paragraph(escape(str(cell)), styles["BodyText"]) for cell in row] for row in [headers, *rows]]
        rendered = Table(cells, repeatRows=1, colWidths=[6.7 * inch / len(headers)] * len(headers))
        rendered.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DCECEF")),
                                     ("GRID", (0, 0), (-1, -1), 0.4, colors.grey), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
        story.extend([rendered, Spacer(1, 14)])
    for chart in args.get("charts", []):
        if len(chart["labels"]) != len(chart["values"]) or not chart["labels"]:
            raise ValueError("Etiquetas y valores del gráfico deben tener la misma longitud")
        drawing = Drawing(470, 220)
        bars = VerticalBarChart()
        bars.x, bars.y, bars.width, bars.height = 45, 50, 400, 150
        bars.data = [chart["values"]]
        bars.valueAxis.valueMin = min(0, min(chart["values"]))
        bars.valueAxis.valueMax = max(0, max(chart["values"])) or 1
        bars.categoryAxis.categoryNames = chart["labels"]
        bars.categoryAxis.labels.angle = 25
        bars.bars[0].fillColor = colors.HexColor("#25676F")
        drawing.add(bars)
        story.extend([Paragraph(escape(chart["title"]), styles["Heading2"]), drawing, Spacer(1, 10)])
    for image in args.get("images", []):
        from PIL import Image as PILImage
        path = resource_path(session, agent, image["resource_id"], image["path"], "read")
        if path.suffix.lower() not in {".png", ".jpg", ".jpeg"} or path.stat().st_size > 10 * 1024 * 1024:
            raise ValueError("Imagen PDF debe ser PNG/JPG de hasta 10 MB")
        with PILImage.open(path) as source:
            if source.width * source.height > 20000000:
                raise ValueError("Imagen demasiado grande")
            source.verify()
        rendered = Image(str(path), width=400, height=250, kind="proportional")
        story.append(rendered)
        if image.get("caption"):
            story.append(Paragraph(escape(image["caption"]), styles["BodyText"]))
    if args.get("sources"):
        story.append(Paragraph("Fuentes", styles["Heading2"]))
        story.extend(Paragraph(escape(source), styles["BodyText"]) for source in args["sources"])
    buffer = BytesIO()
    def page_frame(canvas, document):
        canvas.saveState()
        canvas.setFont("Helvetica", 9)
        canvas.drawString(document.leftMargin, 770, args.get("header", "Oficina IA")[:100])
        canvas.drawString(document.leftMargin, 25, args.get("footer", "")[:100])
        canvas.drawRightString(565, 25, f"Página {document.page}")
        canvas.restoreState()
    document = SimpleDocTemplate(buffer, pagesize=(612, 792), title=args["title"],
                                 leftMargin=45, rightMargin=45, topMargin=40, bottomMargin=40)
    # Stable output binds overwrite approval to exactly the reviewed content.
    document.build(story, onFirstPage=page_frame, onLaterPages=page_frame, canvasmaker=partial(Canvas, invariant=1))
    return publish_pdf(session, task, agent, args, buffer.getvalue(), "pdf.create")


def publish_pdf(session, task, agent, args, content, tool):
    from pypdf import PdfReader
    if not args["path"].lower().endswith(".pdf") or len(content) > 20 * 1024 * 1024:
        raise ValueError("Salida PDF inválida o superior a 20 MB")
    check = PdfReader(BytesIO(content), strict=True)
    if not check.pages or len(check.pages) > 200:
        raise ValueError("PDF vacío o superior a 200 páginas")
    return {**publish_bytes(session, task, agent, args["resource_id"], args["path"], content, tool), "page_count": len(check.pages)}


def merge_pdf(session, task, agent, args):
    from pypdf import PdfWriter
    writer = PdfWriter()
    try:
        for source in args["sources"]:
            document = reader(session, agent, source)
            for page in document.pages:
                if len(writer.pages) >= 200:
                    raise ValueError("PDF combinado supera 200 páginas")
                # Remove annotations/actions rather than carrying executable links into output.
                page.pop("/Annots", None)
                page.pop("/AA", None)
                writer.add_page(page)
        buffer = BytesIO()
        writer.write(buffer)
        return publish_pdf(session, task, agent, args, buffer.getvalue(), "pdf.merge")
    finally:
        writer.close()
