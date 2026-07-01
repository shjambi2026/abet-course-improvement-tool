from pathlib import Path

DOCUMENT_FOLDER = Path("course_documents")


def get_document_path(filename):
    if not filename:
        return None

    if isinstance(filename, list):
        filename = filename[-1] if filename else ""

    path = DOCUMENT_FOLDER / filename
    return path if path.exists() else None


def extract_text_from_file(filename):
    path = get_document_path(filename)

    if not path:
        return ""

    ext = path.suffix.lower()

    if ext == ".txt":
        return path.read_text(encoding="utf-8", errors="ignore")

    if ext == ".docx":
        try:
            from docx import Document
            doc = Document(str(path))
            return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
        except Exception:
            return ""

    if ext == ".pdf":
        try:
            from PyPDF2 import PdfReader
            reader = PdfReader(str(path))
            text = []
            for page in reader.pages:
                text.append(page.extract_text() or "")
            return "\n".join(text)
        except Exception:
            return ""

    return ""


def extract_texts(file_list):
    texts = []

    for file in file_list or []:
        text = extract_text_from_file(file)

        if text:
            texts.append(text)

    return "\n\n".join(texts)