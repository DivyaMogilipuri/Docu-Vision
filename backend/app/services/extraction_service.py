from PyPDF2 import  PdfReader
from pdf2image import convert_from_path
import pytesseract
from difflib import SequenceMatcher
from docx import Document
import re
import camelot
import uuid
import os
p_path="C:/Program Files/poppler-25.11.0/Library/bin"


# def extract_from_pdf(filepath:str)->dict :
#     pages_data = []

#     pdf=PdfReader(filepath)

#     pdf_pages=pdf.pages

#     full_pdf_text=""

#     for i,page in enumerate(pdf_pages):
#         text=page.extract_text() or ""
#         text=re.sub(r"\s+"," ",text).strip()

#         c_image=convert_from_path(pdf_path=filepath,first_page=i+1,last_page=i+1,dpi=300,poppler_path=p_path)
#         ocr_text=pytesseract.image_to_string(c_image[0])
#         ocr_text= re.sub(r"\s+", " ", ocr_text).strip()
#         unique_ocr_text=ocr_text.replace(text,"").strip()
        
       

#         full_pdf_text+=text+"\n"+unique_ocr_text+"\n"
#         pages_data.append({
#         "page_number": i+1,
#         "text": text + " " + unique_ocr_text,
#          # optional, later fill per page
#         })


#         #  for tables
#     try:
#         tables = camelot.read_pdf(filepath, pages="all")
#         final_tables = [table.df.to_dict(orient="records") for table in tables]
#     except:
#         final_tables = []
    

   
    

#     return {
#         "pages":pages_data,
#         "tables": final_tables
#     }

# def extract_from_docx(filepath:str)->str:
#     document=Document(filepath)
#     # text extraction
#     text=[]
#     for para in document.paragraphs:
#         text.append(para.text.strip())
#     # table extraction
#     table_data=[]
    
#     for tab in document.tables:
#         single_table=[]
        
#         for row in tab.rows:
#             row_data=[]
#             for cell in row.cells:
                
#                 if cell.text.strip():
#                     row_data.append(cell.text.strip())
#             single_table.append(row_data)
#         table_data.append(single_table)
#     # header extraction
#     header_data=[]
#     for sec in document.sections:
#         header=sec.header

#         for para in header.paragraphs:
#             header_data.append(para.text.strip())
#     # footer extraction

#     footer_Data=[]
#     footer=document.sections[0].footer
#     for para in footer.paragraphs:
        
#         clean_text = re.sub(r"\s+", " ", para.text, flags=re.UNICODE).strip()

#         footer_Data.append(clean_text)
    
    
#     return {
#         "paragraphs":text,
#         "tables":table_data,
#         "header":header_data,
#         "footer":footer_Data
        
#     }

# -------------------------------------version 1-----------------------------------



def extract_from_pdf(filepath: str, doc_type="general") -> dict:
    pdf = PdfReader(filepath)
    blocks = []

    for i, page in enumerate(pdf.pages):
        text = page.extract_text() or ""
        text = re.sub(r"\s+", " ", text).strip()

        images = convert_from_path(
            pdf_path=filepath,
            first_page=i+1,
            last_page=i+1,
            dpi=300,
            poppler_path=p_path
        )
        ocr_text = pytesseract.image_to_string(images[0])
        ocr_text = re.sub(r"\s+", " ", ocr_text).strip()

        combined = f"{text} {ocr_text}".strip()

        if combined:
            blocks.append({
                "block_id": str(uuid.uuid4()),
                "type": "paragraph",
                "page": i + 1,
                "text": combined
            })

    # Tables
    try:
        tables = camelot.read_pdf(filepath, pages="all")
        for table in tables:
            table_text = "\n".join(
                [" | ".join(row) for row in table.df.values.tolist()]
            )
            blocks.append({
                "block_id": str(uuid.uuid4()),
                "type": "table",
                "page": None,
                "text": table_text
            })
    except Exception:
        pass

    return {
        "doc_type": doc_type,
        "source": "pdf",
        "blocks": blocks
    }
def extract_from_docx(filepath: str, doc_type="general") -> dict:
    document = Document(filepath)
    blocks = []

    # Paragraphs
    for para in document.paragraphs:
        text = re.sub(r"\s+", " ", para.text).strip()

        if text:
            blocks.append({
                "block_id": str(uuid.uuid4()),
                "type": "paragraph",
                "page": None,   # DOCX does not expose real page numbers
                "text": text
            })

    # Tables
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
                "type": "table",
                "page": None,
                "text": "\n".join(table_rows)
            })

    # Headers
    for section in document.sections:
        for para in section.header.paragraphs:
            text = re.sub(r"\s+", " ", para.text).strip()
            if text:
                blocks.append({
                    "block_id": str(uuid.uuid4()),
                    "type": "header",
                    "page": None,
                    "text": text
                })

    # Footers
    for section in document.sections:
        for para in section.footer.paragraphs:
            text = re.sub(r"\s+", " ", para.text).strip()
            if text:
                blocks.append({
                    "block_id": str(uuid.uuid4()),
                    "type": "footer",
                    "page": None,
                    "text": text
                })

    return {
        "doc_type": doc_type,
        "source": "docx",
        "blocks": blocks
    }

    
    