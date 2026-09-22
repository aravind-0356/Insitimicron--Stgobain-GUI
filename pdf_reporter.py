import os
import time
import logging
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader

logger = logging.getLogger(__name__)

class PDFReporter:
    def __init__(self, logo_path=None):
        self.styles = getSampleStyleSheet()
        self.logo_path = logo_path
        
        # Create custom styles
        self.styles.add(ParagraphStyle(name='SectionTitle', 
                                       parent=self.styles['Heading2'],
                                       textColor=colors.HexColor('#2c3e50'),
                                       spaceAfter=10))
        
        self.styles.add(ParagraphStyle(name='TableCaption', 
                                       parent=self.styles['Italic'],
                                       alignment=1,
                                       spaceBefore=10,
                                       spaceAfter=10))

    def generate_report(self, save_path: str, metadata: dict, results: dict, comments: str, graph_path: str):
        """
        Generate a professional PDF report for Flexural Testing.
        """
        try:
            doc = SimpleDocTemplate(save_path, pagesize=letter,
                                    rightMargin=0.75*inch, leftMargin=0.75*inch,
                                    topMargin=1.1*inch, bottomMargin=0.75*inch)
            elements = []

            # 1. Title
            title_style = ParagraphStyle(name='CenteredTitle', parent=self.styles['Heading1'], alignment=1)
            elements.append(Spacer(1, 0.2*inch))  # Space for the logo in the header
            elements.append(Paragraph("<b>Flexural Test Report</b>", title_style))
            elements.append(Spacer(1, 0.2*inch))
            
            # Line separator
            elements.append(Table([['']], colWidths=[7*inch], style=[
                ('LINEABOVE', (0, 0), (-1, -1), 1, colors.HexColor('#2c3e50'))
            ]))
            elements.append(Spacer(1, 0.2*inch))

            # 2. Test Metadata
            elements.append(Paragraph("Test Details", self.styles['SectionTitle']))
            
            meta_data = [
                ["Sample ID:", metadata.get('sample_name', '--'), "Test Number:", str(metadata.get('test_number', '--'))],
                ["Business Type:", metadata.get('business_type', '--'), "Temperature:", f"{metadata.get('temperature_c', '--')} °C"],
                ["Span Length:", f"{metadata.get('length_mm', '--')} mm", "", ""],
                ["Width:", f"{metadata.get('width_mm', '--')} mm", "Thickness:", f"{metadata.get('thickness_mm', '--')} mm"]
            ]
                
            meta_table = Table(meta_data, colWidths=[1.5*inch, 2*inch, 1.5*inch, 2*inch])
            meta_table.setStyle(TableStyle([
                ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
                ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
                ('FONTNAME', (2,0), (2,-1), 'Helvetica-Bold'),
                ('TEXTCOLOR', (0,0), (-1,-1), colors.HexColor('#34495e')),
                ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                ('BOTTOMPADDING', (0,0), (-1,-1), 6)
            ]))
            elements.append(meta_table)
            elements.append(Spacer(1, 0.3*inch))

            # 3. Mechanical Properties Results
            elements.append(Paragraph("Mechanical Properties", self.styles['SectionTitle']))
            
            def _fmt(val):
                return f"{val:.2f}" if val is not None else "--"
                
            res_data = [
                ["Property", "Value", "Unit"],
                ["Flexural Modulus (E)", _fmt(results.get('youngs_modulus')), "MPa"],
                ["Break Stress", _fmt(results.get('break_stress')), "MPa"],
                ["Break Strain", _fmt(results.get('break_strain')), "—"]
            ]
            
            res_table = Table(res_data, colWidths=[3.5*inch, 1.5*inch, 1.5*inch])
            res_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 11),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                ('TOPPADDING', (0, 0), (-1, 0), 10),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#ecf0f1')),
                ('GRID', (0, 0), (-1, -1), 1, colors.white)
            ]))
            elements.append(res_table)
            elements.append(Spacer(1, 0.3*inch))

            # 4. Stress-Strain Graph
            graph_elements = []
            graph_elements.append(Paragraph("Stress-Strain Curve", self.styles['SectionTitle']))
            if os.path.exists(graph_path):
                # Scale image to fit within page width (7 inches max)
                graph_img = Image(graph_path)
                
                # Keep aspect ratio
                aspect = graph_img.drawHeight / float(graph_img.drawWidth)
                graph_img.drawWidth = 6.5 * inch
                graph_img.drawHeight = 6.5 * inch * aspect
                
                graph_elements.append(graph_img)
            else:
                graph_elements.append(Paragraph("<i>Graph image not available.</i>", self.styles['Normal']))
            
            elements.append(KeepTogether(graph_elements))
            elements.append(Spacer(1, 0.3*inch))

            # 5. User Comments
            if comments and comments.strip():
                elements.append(Paragraph("Operator Notes", self.styles['SectionTitle']))
                
                # Wrap comments in a styled table to look like a comment box
                comment_table = Table([[Paragraph(comments, self.styles['Normal'])]], colWidths=[7*inch])
                comment_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f9f9f9')),
                    ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#bdc3c7')),
                    ('PADDING', (0, 0), (-1, -1), 10)
                ]))
                elements.append(comment_table)

            # Build PDF with page templates for header
            def add_header(canvas, doc):
                canvas.saveState()
                if self.logo_path and os.path.exists(self.logo_path):
                    logo = ImageReader(self.logo_path)
                    # Position logo at top left (x=0.5 inch, y=10.3 inch)
                    canvas.drawImage(logo, 0.5*inch, 10.3*inch, width=1.75*inch, height=0.5*inch, preserveAspectRatio=True, mask='auto')
                canvas.restoreState()

            doc.build(elements, onFirstPage=add_header, onLaterPages=add_header)
            logger.info("Successfully generated PDF report at %s", save_path)
            return True
            
        except Exception as e:
            logger.error("Error generating PDF: %s", str(e))
            raise
