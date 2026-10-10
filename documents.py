import os
from pypdf import PdfReader


def load_pdf(path):
    reader = PdfReader(path)
    source = os.path.basename(path)
    result = []
    for number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        text = text.strip()
        if text:
            result.append({"text": text, "source": source, "page": number})
    return result