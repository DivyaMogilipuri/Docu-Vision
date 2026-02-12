from fastapi import File,UploadFile,APIRouter,HTTPException
import os
import shutil
import uuid
from services.extraction_service import extract_from_pdf,extract_from_docx
from services.ingestion import ingest_document


# APIRouter is a class in FastAPI that helps you organize your API endpoints
router=APIRouter(prefix="/upload",tags=['upload'])


@router.post("/")
def upload_file(file: UploadFile = File(...)):
    allowed_extensions = [".pdf", ".docx"]

    file_extension = os.path.splitext(file.filename)[1].lower()
    upload_dir = "C:/Users/divya/OneDrive/Documents/Projects/Docu Vision AI/backend/app/uploads"

    os.makedirs(upload_dir, exist_ok=True)

    if file_extension not in allowed_extensions:
        raise HTTPException(status_code=400, detail="This file extension is not allowed")

    doc_id = str(uuid.uuid4())
    file_upload_path = os.path.join(upload_dir, f"{doc_id}{file_extension}")

    with open(file_upload_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 🔹 Call ingestion pipeline (not extractors)
    response=ingest_document(
        filepath=file_upload_path,
        file_type=file_extension.replace(".", ""),
        doc_type="general"
    )

    return {
        "success": True,
        "document_id": doc_id,
        "response":response
    }

        




    return {"success":"file uploades succesfully",
            "extracted text" :extracted_text}





