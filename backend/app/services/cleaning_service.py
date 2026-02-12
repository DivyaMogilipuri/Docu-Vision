import re
import unicodedata


def normalize_text(
    text: str,
    doc_type: str = "general",   # legal | medical | financial | general
    for_ml: bool = True
) -> str:
    """
    Normalize extracted document text for ML + search usage
    """

    if not text:
        return ""

    # 1️⃣ Unicode normalization (fix hidden inconsistencies)
    text = unicodedata.normalize("NFKC", text)

    # 2️⃣ Fix hyphenated line breaks (PDF artifacts)
    # Example: "infor-\nmation" → "information"
    text = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", text)

    # 3️⃣ Normalize bullets to "-"
    text = re.sub(
        r"(?m)^\s*[•▪●–—◦]\s+",
        "- ",
        text
    )

    # 4️⃣ Normalize whitespace
    text = re.sub(r"\s+", " ", text)
    text = text.strip()

    # 5️⃣ Handle abbreviations for sensitive documents
    if doc_type in ["legal", "medical", "financial"]:
        # Preserve ALL-CAPS abbreviations
        text = re.sub(
            r"\b([A-Z]{2,})\b",
            lambda m: m.group(1).lower() + "_abbr",
            text
        )

    # 6️⃣ Lowercase for embeddings (ML prefers this)
    if for_ml:
        text = text.lower()

    return text
