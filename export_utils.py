import html
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.units import inch
from io import BytesIO
import textwrap


def export_to_html(scraped_data=None, chat_history=None):
    """Export scraped data and/or chat history to HTML format"""
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Web Scraper Export - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</title>
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                line-height: 1.6;
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
                background-color: #f5f5f5;
            }}
            .container {{
                background-color: white;
                padding: 30px;
                border-radius: 10px;
                box-shadow: 0 0 10px rgba(0,0,0,0.1);
            }}
            h1 {{
                color: #333;
                border-bottom: 3px solid #4CAF50;
                padding-bottom: 10px;
            }}
            h2 {{
                color: #444;
                border-bottom: 1px solid #ddd;
                padding-bottom: 5px;
                margin-top: 30px;
            }}
            h3 {{
                color: #555;
                margin-top: 25px;
            }}
            .url-section {{
                background-color: #f9f9f9;
                padding: 20px;
                margin: 20px 0;
                border-left: 4px solid #4CAF50;
                border-radius: 5px;
            }}
            .chat-message {{
                background-color: #f0f0f0;
                padding: 15px;
                margin: 10px 0;
                border-radius: 8px;
                border-left: 4px solid #2196F3;
            }}
            .user-message {{
                background-color: #e3f2fd;
                border-left-color: #1976D2;
            }}
            .assistant-message {{
                background-color: #f1f8e9;
                border-left-color: #4CAF50;
            }}
            .timestamp {{
                color: #666;
                font-size: 0.9em;
                margin-bottom: 5px;
            }}
            .sources {{
                background-color: #fff3e0;
                padding: 10px;
                margin-top: 10px;
                border-radius: 5px;
                border-left: 3px solid #FF9800;
            }}
            .content {{
                white-space: pre-wrap;
                background-color: #fafafa;
                padding: 15px;
                border-radius: 5px;
                border: 1px solid #ddd;
                max-height: 500px;
                overflow-y: auto;
            }}
            .export-info {{
                background-color: #e8f5e8;
                padding: 15px;
                border-radius: 5px;
                margin-bottom: 20px;
                border: 1px solid #c8e6c8;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🕷️ Web Scraper Export</h1>
            
            <div class="export-info">
                <strong>Export Date:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br>
                <strong>Content:</strong> {('Scraped Data' if scraped_data else '') + (' & ' if scraped_data and chat_history else '') + ('Chat History' if chat_history else '')}
            </div>
    """
    
    # Add scraped data section
    if scraped_data:
        html_content += """
            <h2>📄 Scraped Data</h2>
        """
        
        for url, data in scraped_data.items():
            escaped_url = html.escape(url)
            escaped_content = html.escape(data['content'])
            scraped_at = data.get('scraped_at', 'Unknown')
            
            html_content += f"""
            <div class="url-section">
                <h3>🌐 {escaped_url}</h3>
                <div class="timestamp">Scraped at: {scraped_at}</div>
                <div class="content">{escaped_content}</div>
            </div>
            """
    
    # Add chat history section
    if chat_history:
        html_content += """
            <h2>💬 Chat History</h2>
        """
        
        for message in chat_history:
            role_class = "user-message" if message['role'] == 'user' else "assistant-message"
            role_icon = "🧑" if message['role'] == 'user' else "🤖"
            escaped_content = html.escape(message['content'])
            
            html_content += f"""
            <div class="chat-message {role_class}">
                <div class="timestamp">{role_icon} {message['role'].title()} - {message['timestamp']}</div>
                <div>{escaped_content}</div>
            """
            
            if message.get('sources'):
                html_content += """
                <div class="sources">
                    <strong>📖 Sources:</strong><br>
                """
                for source in message['sources']:
                    escaped_source = html.escape(source)
                    html_content += f"• {escaped_source}<br>"
                html_content += "</div>"
            
            html_content += "</div>"
    
    html_content += """
        </div>
    </body>
    </html>
    """
    
    return html_content


def export_to_pdf(scraped_data=None, chat_history=None):
    """Export scraped data and/or chat history to PDF format"""
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72,
                           topMargin=72, bottomMargin=18)
    
    # Get styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor='#333333',
        alignment=1,  # Center alignment
        spaceAfter=20
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor='#444444',
        spaceBefore=20,
        spaceAfter=10
    )
    
    normal_style = styles['Normal']
    normal_style.fontSize = 10
    
    # Build content
    story = []
    
    # Title
    story.append(Paragraph("🕷️ Web Scraper Export", title_style))
    story.append(Spacer(1, 12))
    
    # Export info
    export_info = f"""
    <b>Export Date:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br/>
    <b>Content:</b> {('Scraped Data' if scraped_data else '') + (' & ' if scraped_data and chat_history else '') + ('Chat History' if chat_history else '')}
    """
    story.append(Paragraph(export_info, normal_style))
    story.append(Spacer(1, 20))
    
    # Add scraped data
    if scraped_data:
        story.append(Paragraph("📄 Scraped Data", heading_style))
        
        for url, data in scraped_data.items():
            # URL heading
            story.append(Paragraph(f"🌐 <b>{url}</b>", styles['Heading3']))
            story.append(Paragraph(f"<i>Scraped at: {data.get('scraped_at', 'Unknown')}</i>", normal_style))
            story.append(Spacer(1, 6))
            
            # Content (truncated if too long)
            content = data['content']
            if len(content) > 2000:
                content = content[:2000] + "... [Content truncated for PDF export]"
            
            # Wrap long lines
            wrapped_content = ""
            for line in content.split('\n'):
                if len(line) > 80:
                    wrapped_lines = textwrap.fill(line, width=80)
                    wrapped_content += wrapped_lines + "\n"
                else:
                    wrapped_content += line + "\n"
            
            story.append(Paragraph(f"<pre>{wrapped_content}</pre>", normal_style))
            story.append(PageBreak())
    
    # Add chat history
    if chat_history:
        story.append(Paragraph("💬 Chat History", heading_style))
        
        for message in chat_history:
            role_icon = "🧑" if message['role'] == 'user' else "🤖"
            
            # Message header
            header = f"<b>{role_icon} {message['role'].title()}</b> - {message['timestamp']}"
            story.append(Paragraph(header, styles['Heading4']))
            
            # Message content
            content = message['content']
            if len(content) > 1000:
                content = content[:1000] + "... [Content truncated for PDF export]"
            
            story.append(Paragraph(content, normal_style))
            
            # Sources
            if message.get('sources'):
                sources_text = "<b>📖 Sources:</b><br/>"
                for source in message['sources']:
                    sources_text += f"• {source}<br/>"
                story.append(Paragraph(sources_text, normal_style))
            
            story.append(Spacer(1, 12))
    
    # Build PDF
    doc.build(story)
    pdf_content = buffer.getvalue()
    buffer.close()
    
    return pdf_content


def format_content_for_export(content, max_length=None):
    """Format content for export, with optional length limit"""
    if max_length and len(content) > max_length:
        return content[:max_length] + "... [Content truncated for export]"
    return content