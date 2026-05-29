#!/usr/bin/env python3
"""Convert Markdown file to PDF using markdown and weasyprint."""

import sys
import markdown
from weasyprint import HTML, CSS


def md_to_pdf(md_file, pdf_file):
    """Convert Markdown file to PDF."""
    # Read markdown
    with open(md_file, "r", encoding="utf-8") as f:
        md_content = f.read()

    # Convert markdown to HTML
    html_content = markdown.markdown(
        md_content, extensions=["tables", "fenced_code", "codehilite"]
    )

    # Wrap in HTML template with basic styling
    html_template = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: Arial, Helvetica, sans-serif;
            font-size: 11pt;
            line-height: 1.4;
            color: #000;
            margin: 20px;
        }}
        h1 {{
            font-size: 18pt;
            font-weight: bold;
            margin-top: 30px;
            margin-bottom: 15px;
            border-bottom: 2px solid #000;
            padding-bottom: 5px;
        }}
        h2 {{
            font-size: 14pt;
            font-weight: bold;
            margin-top: 20px;
            margin-bottom: 10px;
            border-bottom: 1px solid #ccc;
            padding-bottom: 3px;
        }}
        h3 {{
            font-size: 12pt;
            font-weight: bold;
            margin-top: 15px;
            margin-bottom: 8px;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 10px 0;
            font-size: 10pt;
        }}
        th {{
            background-color: #f0f0f0;
            font-weight: bold;
            border: 1px solid #000;
            padding: 6px;
            text-align: left;
        }}
        td {{
            border: 1px solid #ccc;
            padding: 5px;
        }}
        ul, ol {{
            margin: 10px 0;
            padding-left: 25px;
        }}
        li {{
            margin: 5px 0;
        }}
        p {{
            margin: 8px 0;
        }}
        strong {{
            font-weight: bold;
        }}
        code {{
            font-family: Courier, monospace;
            background-color: #f0f0f0;
            padding: 2px 4px;
            border-radius: 3px;
        }}
        pre {{
            background-color: #f0f0f0;
            padding: 10px;
            border: 1px solid #ccc;
            border-radius: 5px;
            overflow-x: auto;
        }}
        pre code {{
            background-color: transparent;
            padding: 0;
        }}
        @page {{
            margin: 15mm;
            @bottom-center {{
                content: counter(page);
                font-size: 9pt;
            }}
        }}
    </style>
</head>
<body>
    {html_content}
</body>
</html>"""

    # Generate PDF
    HTML(string=html_template).write_pdf(pdf_file)
    print(f"PDF created: {pdf_file}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python md_to_pdf.py <input.md> <output.pdf>")
        sys.exit(1)

    md_file = sys.argv[1]
    pdf_file = sys.argv[2]

    md_to_pdf(md_file, pdf_file)
