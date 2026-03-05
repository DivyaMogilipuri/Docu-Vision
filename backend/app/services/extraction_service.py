import fitz  # PyMuPDF
import pytesseract
from pytesseract import Output
from pdf2image import convert_from_path
from docx import Document
from PIL import Image
import uuid
import re
from typing import List, Dict
import io

# Set your poppler path
POPPLER_PATH = r"C:/Program Files/poppler-25.11.0/Library/bin"



# =====================================================
# DIGITAL TEXT EXTRACTION
# =====================================================

def extract_digital_blocks(page, page_number, document_id):
    blocks = []
    text_dict = page.get_text("dict")

    for block in text_dict["blocks"]:
        if block["type"] == 0:  # text block
            for line in block["lines"]:
                line_text = ""
                x0 = y0 = x1 = y1 = None

                for span in line["spans"]:
                    if not line_text:
                        x0, y0 = span["bbox"][0], span["bbox"][1]
                    x1, y1 = span["bbox"][2], span["bbox"][3]
                    line_text += span["text"] + " "

                if line_text.strip():
                    blocks.append({
                        "block_id": str(uuid.uuid4()),
                        "document_id": document_id,
                        "type": "digital_text",
                        "page_number": page_number,
                        "text": line_text.strip(),
                        "x0": x0,
                        "y0": y0,
                        "x1": x1,
                        "y1": y1
                    })

    return blocks


# =====================================================
# OCR FROM EMBEDDED IMAGES ONLY
# =====================================================

def extract_ocr_from_images(page, page_number, document_id):

    blocks = []
    image_list = page.get_images(full=True)

    for img in image_list:

        xref = img[0]
        base_image = page.parent.extract_image(xref)
        image_bytes = base_image["image"]

        image = Image.open(io.BytesIO(image_bytes))

        # Get image rectangle on page
        rects = page.get_image_rects(xref)
        if not rects:
            continue

        img_rect = rects[0]

        scale_x = img_rect.width / image.width
        scale_y = img_rect.height / image.height

        ocr_data = pytesseract.image_to_data(image, output_type=Output.DICT)

        for i in range(len(ocr_data["text"])):

            word = ocr_data["text"][i].strip()
            conf = int(ocr_data["conf"][i]) if ocr_data["conf"][i].isdigit() else -1

            if word and conf > 40:

            

                x = ocr_data["left"][i]
                y = ocr_data["top"][i]
                w = ocr_data["width"][i]
                h = ocr_data["height"][i]

                # Convert image coords → page coords
                x0 = img_rect.x0 + (x * scale_x)
                y0 = img_rect.y0 + (y * scale_y)
                x1 = img_rect.x0 + ((x + w) * scale_x)
                y1 = img_rect.y0 + ((y + h) * scale_y)

                blocks.append({
                    "block_id": str(uuid.uuid4()),
                    "document_id": document_id,
                    "type": "ocr_word",
                    "page_number": page_number,
                    "text": word,
                    "x0": x0,
                    "y0": y0,
                    "x1": x1,
                    "y1": y1
                })

    return blocks

# =====================================================
# GROUP OCR WORDS INTO LINES
# =====================================================

def group_words_into_lines(blocks, y_threshold=12):

    if not blocks:
        return []

    blocks = sorted(
        blocks,
        key=lambda b: (
            b["page_number"],
            (b["y0"] + b["y1"]) / 2,
            b["x0"]
        )
    )

    lines = []
    current_line = []
    current_y = None

    for block in blocks:

        center_y = (block["y0"] + block["y1"]) / 2

        if current_y is None:

            current_y = center_y
            current_line.append(block)

        elif abs(center_y - current_y) <= y_threshold:

            current_line.append(block)

        else:

            lines.append(current_line)
            current_line = [block]
            current_y = center_y

    if current_line:
        lines.append(current_line)

    merged_lines = []

    for line in lines:

        line = sorted(line, key=lambda b: b["x0"])

        text = " ".join(b["text"] for b in line)

        merged_lines.append({
            "block_id": str(uuid.uuid4()),
            "document_id": line[0]["document_id"],
            "type": "ocr_text",
            "page_number": line[0]["page_number"],
            "text": text,
            "x0": min(b["x0"] for b in line),
            "y0": min(b["y0"] for b in line),
            "x1": max(b["x1"] for b in line),
            "y1": max(b["y1"] for b in line)
        })

    return merged_lines



# =====================================================
# MULTI-COLUMN DETECTION
# =====================================================
def detect_columns(page_blocks, page_width):

    if not page_blocks:
        return [page_blocks]

    # sort blocks left → right
    blocks_sorted = sorted(page_blocks, key=lambda b: b["x0"])

    # dynamic column gap threshold
    column_gap = page_width * 0.15

    columns = []
    current_column = [blocks_sorted[0]]

    prev_x = blocks_sorted[0]["x0"]

    for block in blocks_sorted[1:]:
        gap = block["x0"] - prev_x

        if gap > column_gap:
            columns.append(current_column)
            current_column = [block]
        else:
            current_column.append(block)

        prev_x = block["x0"]

    columns.append(current_column)

    return columns


def layout_sort(all_blocks, doc):

    final_blocks = []
    pages = {}

    for b in all_blocks:
        pages.setdefault(b["page_number"], []).append(b)

    for page_number in sorted(pages.keys()):

        page_blocks = pages[page_number]

        page = doc[page_number - 1]
        page_width = page.rect.width

        columns = detect_columns(page_blocks, page_width)

        # sort columns left → right
        columns = sorted(columns, key=lambda col: min(b["x0"] for b in col))

        for col in columns:
            col_sorted = sorted(col, key=lambda b: (b["y0"], b["x0"]))
            final_blocks.extend(col_sorted)

    return final_blocks

# =====================================================
# FULL PAGE OCR
# =====================================================
def extract_full_page_ocr(page, page_number, document_id):

    blocks = []

    pix = page.get_pixmap(dpi=300)

    image = Image.open(io.BytesIO(pix.tobytes()))

    ocr_data = pytesseract.image_to_data(image, output_type=Output.DICT)
    scale_x = page.rect.width / image.width
    scale_y = page.rect.height / image.height


    for i in range(len(ocr_data["text"])):

        word = ocr_data["text"][i].strip()
        conf = int(ocr_data["conf"][i]) if ocr_data["conf"][i].isdigit() else -1

        if word and conf > 40:

        

            x = ocr_data["left"][i]
            y = ocr_data["top"][i]
            w = ocr_data["width"][i]
            h = ocr_data["height"][i]
           
            blocks.append({
        "block_id": str(uuid.uuid4()),
        "document_id": document_id,
        "type": "ocr_word",
        "page_number": page_number,
        "text": word,
        "x0": x * scale_x,
        "y0": y * scale_y,
        "x1": (x + w) * scale_x,
        "y1": (y + h) * scale_y
})

    return group_words_into_lines(blocks)

# =====================================================
# MAIN PDF PIPELINE
# =====================================================

def extract_from_pdf_layout_aware(pdf_path):
    document_id = str(uuid.uuid4())
    doc = fitz.open(pdf_path)

    all_blocks = []

    for page_index, page in enumerate(doc):
        page_number = page_index + 1

        digital_blocks = extract_digital_blocks(page, page_number, document_id)

        ocr_word_blocks = extract_ocr_from_images(page, page_number, document_id)
        

        if not digital_blocks and not ocr_word_blocks:
            scanned_blocks = extract_full_page_ocr(page, page_number, document_id)
            page_blocks = scanned_blocks
        else:
            ocr_line_blocks = group_words_into_lines(ocr_word_blocks)
            page_blocks = digital_blocks + ocr_line_blocks

        # page_blocks = digital_blocks + ocr_line_blocks
        all_blocks.extend(page_blocks)

    all_blocks = layout_sort(all_blocks, doc)

    return {
        "document_id": document_id,
        "doc_type": "general",
        "source": "pdf",
        "blocks": all_blocks
    }


# =====================================================
# DOCX EXTRACTION
# =====================================================

def extract_from_docx(filepath: str, doc_type="general") -> dict:
    document_id = str(uuid.uuid4())
    document = Document(filepath)

    blocks = []

    for para in document.paragraphs:
        text = re.sub(r"\s+", " ", para.text).strip()
        if text:
            blocks.append({
                "block_id": str(uuid.uuid4()),
                "document_id": document_id,
                "type": "paragraph",
                "page_number": None,
                "text": text
            })

    for table in document.tables:
        table_rows = []
        for row in table.rows:
            row_data = [
                re.sub(r"\s+", " ", cell.text).strip()
                for cell in row.cells
                if cell.text.strip()
            ]
            if row_data:
                table_rows.append(" | ".join(row_data))

        if table_rows:
            blocks.append({
                "block_id": str(uuid.uuid4()),
                "document_id": document_id,
                "type": "table",
                "page_number": None,
                "text": "\n".join(table_rows)
            })

    return {
        "document_id": document_id,
        "doc_type": doc_type,
        "source": "docx",
        "blocks": blocks
    }