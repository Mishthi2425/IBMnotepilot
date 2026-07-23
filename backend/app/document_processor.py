import os
import uuid
from typing import List, Dict, Any
from PyPDF2 import PdfReader
from docx import Document
import shutil
from pathlib import Path


class DocumentProcessor:
    def __init__(self, upload_dir: str = "./uploads"):
        self.upload_dir = upload_dir
        Path(upload_dir).mkdir(parents=True, exist_ok=True)

    def process(self, content: bytes, filename: str, doc_id: str) -> List[str]:
        file_path = os.path.join(self.upload_dir, f"{doc_id}_{filename}")

        with open(file_path, "wb") as f:
            f.write(content)

        text = ""
        if filename.lower().endswith('.pdf'):
            text = self._extract_pdf(file_path)
        elif filename.lower().endswith('.docx'):
            text = self._extract_docx(file_path)
        else:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                text = f.read()

        return self._chunk_text(text)

    def _extract_pdf(self, file_path: str) -> str:
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        return text

    def _extract_docx(self, file_path: str) -> str:
        doc = Document(file_path)
        text = ""
        for paragraph in doc.paragraphs:
            if paragraph.text.strip():
                text += paragraph.text + "\n"
        return text

    def _chunk_text(self, text: str, chunk_size: int = 250, overlap: int = 50) -> List[str]:
        words = text.split()
        chunks = []
        for i in range(0, len(words), chunk_size - overlap):
            chunk = ' '.join(words[i:i + chunk_size])
            if chunk.strip() and len(chunk.strip()) > 20:
                chunks.append(chunk.strip())
        return chunks
