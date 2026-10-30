"""
SpendWise PDF Generator
Generates clean, professional expense reports in PDF using ReportLab.
"""
import io
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def generate_expense_pdf(user_name, expenses, summary):
    """
    Creates a styled PDF in-memory buffer.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#0f172a'),
        spaceAfter=4
    )
    subtitle_style = ParagraphStyle(
        'DocSub',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#64748b'),
        spaceAfter=14
    )
    kpi_title_style = ParagraphStyle(
        'KPITitle',
        parent=styles['Normal'],
        fontSize=9,
        leading=11,
        textColor=colors.HexColor('#64748b')
    )
    kpi_val_style = ParagraphStyle(
        'KPIVal',
        parent=styles['Normal'],
        fontSize=14,
        leading=18,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#0f172a')
    )

    elements = []

    # Header
    elements.append(Paragraph("<b>SpendWise</b> - Expense Report", title_style))
    elements.append(Paragraph(f"Generated for: <b>{user_name}</b> | Generated on: {datetime.now().strftime('%d %b %Y, %I:%M %p')}", subtitle_style))

    # KPI Summary Cards in a Table
    kpi_data = [
        [
            Paragraph("Total Expenses", kpi_title_style),
            Paragraph("Total Transactions", kpi_title_style),
            Paragraph("Average Daily", kpi_title_style),
            Paragraph("Highest Expense", kpi_title_style)
        ],
        [
            Paragraph(f"₹{summary.get('total_expenses', 0):,.2f}", kpi_val_style),
            Paragraph(f"{summary.get('total_count', 0)}", kpi_val_style),
            Paragraph(f"₹{summary.get('daily_avg', 0):,.2f}", kpi_val_style),
            Paragraph(f"₹{summary.get('highest_expense', 0):,.2f}", kpi_val_style)
        ]
    ]
    kpi_table = Table(kpi_data, colWidths=[135, 135, 135, 135])
    kpi_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#e2e8f0')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
    ]))
    elements.append(kpi_table)
    elements.append(Spacer(1, 16))

    # Expense Table Header
    table_data = [
        ["Date & Time", "Description", "Category", "Payment", "Amount (₹)", "Notes"]
    ]

    for exp in expenses:
        notes_val = exp['notes'] if 'notes' in exp.keys() and exp['notes'] else '-'
        table_data.append([
            str(exp['expense_date'])[:16],
            str(exp['title'])[:24],
            str(exp['category']),
            str(exp['payment_method']),
            f"₹{float(exp['amount']):,.2f}",
            str(notes_val)[:20]
        ])

    table = Table(table_data, colWidths=[100, 120, 95, 75, 75, 75])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0f172a')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('TOPPADDING', (0, 0), (-1, 0), 6),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('ALIGN', (4, 0), (4, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 1), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 5),
    ]))
    elements.append(table)

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()
