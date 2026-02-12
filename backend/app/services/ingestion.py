# app/services/ingestion_service.py

import uuid

from services.extraction_service import extract_from_pdf, extract_from_docx
from services.cleaning_service import normalize_text


def ingest_document(
    filepath: str,
    file_type: str,
    doc_type: str = "general"
):
    document_id = str(uuid.uuid4())

    # 1️⃣ Extract
    if file_type == "pdf":
        extracted = extract_from_pdf(filepath, doc_type=doc_type)

    elif file_type == "docx":
        extracted = extract_from_docx(filepath, doc_type=doc_type)

    else:
        raise ValueError("Unsupported file type")

    # 2️⃣ Normalize (now based on blocks, not pages)
    normalized_blocks = []

    for block in extracted["blocks"]:

        clean_text = normalize_text(
            block["text"],
            doc_type=doc_type,
            for_ml=True
        )

        if clean_text:   # avoid empty blocks after normalization
            normalized_blocks.append({
                "block_id": str(uuid.uuid4()),  # normalized block id
                "document_id": document_id,
                "source_block_id": block["block_id"],  # reference to raw block
                "type": block.get("type"),
                "page_number": block.get("page"),
                "text": clean_text
            })

    return {
        "document_id": document_id,
        "doc_type": doc_type,
        "source": extracted["source"],
        "blocks": normalized_blocks
    }
