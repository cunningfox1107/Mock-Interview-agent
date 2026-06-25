import io
from pypdf import PdfReader

def extract_text_from_pdf(file_bytes):
    """
    Extracts all text from PDF bytes.
    """
    try:
        pdf_file = io.BytesIO(file_bytes)
        reader = PdfReader(pdf_file)
        full_text = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text:
                full_text.append(text)
        return "\n\n".join(full_text)
    except Exception as e:
        raise ValueError(f"Failed to read PDF: {str(e)}")

def chunk_text(text, chunk_size=2000, overlap=200):
    """
    Splits text into chunks with a sliding window.
    """
    if not text:
        return []
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk_words = words[i:i + chunk_size]
        chunks.append(" ".join(chunk_words))
        i += chunk_size - overlap
    return chunks
