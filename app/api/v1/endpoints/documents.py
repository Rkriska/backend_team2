import os,uuid,shutil
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter,Depends,HTTPException,UploadFile,File,Form,status,BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db,async_session_maker
from app.models import Project,Document,Chunk
from app.schemas.document import DocumentOut
from app.core.constants import DocType,DocStatus,COLLECTION_TOR,COLLECTION_REFERENCE
from app.config import settings
from app.services.document_extractor import extract_text_from_file
from app.qdrant_client import delete_points_by_payload
router=APIRouter(prefix='/documents',tags=['documents']); ALLOWED={'.pdf','.docx','.txt'}
async def extract_worker(document_id:uuid.UUID):
 async with async_session_maker() as db:
  d=(await db.execute(select(Document).where(Document.id==document_id))).scalar_one_or_none()
  if not d:return
  d.status=DocStatus.PROCESSING;await db.commit()
  try: d.extracted_text=extract_text_from_file(d.file_path);d.status=DocStatus.PROCESSED;d.processed_at=datetime.utcnow()
  except Exception: d.status=DocStatus.ERROR
  await db.commit()
@router.post('/upload',response_model=DocumentOut,status_code=status.HTTP_201_CREATED)
async def upload(background_tasks:BackgroundTasks,project_id:uuid.UUID=Form(...),doc_type:DocType=Form(...),file:UploadFile=File(...),db:AsyncSession=Depends(get_db)):
 if not (await db.execute(select(Project.id).where(Project.id==project_id))).scalar_one_or_none():raise HTTPException(404,'Project tidak ditemukan')
 name=Path(file.filename or '').name;ext=Path(name).suffix.lower()
 if ext not in ALLOWED:raise HTTPException(415,'Hanya PDF, DOCX, atau TXT')
 content=await file.read();limit=settings.MAX_UPLOAD_SIZE_MB*1024*1024
 if len(content)>limit:raise HTTPException(413,f'Maksimum {settings.MAX_UPLOAD_SIZE_MB} MB')
 base=Path(settings.UPLOAD_DIR).resolve();base.mkdir(parents=True,exist_ok=True);target=base/f'{uuid.uuid4()}{ext}';target.write_bytes(content)
 d=Document(project_id=project_id,doc_type=doc_type,file_name=name,file_path=str(target),status=DocStatus.PENDING);db.add(d);await db.flush();await db.refresh(d)
 background_tasks.add_task(extract_worker,d.id)
 return d
@router.get('/{document_id}',response_model=DocumentOut)
async def get(document_id:uuid.UUID,db:AsyncSession=Depends(get_db)):
 d=(await db.execute(select(Document).where(Document.id==document_id))).scalar_one_or_none()
 if not d:raise HTTPException(404,'Dokumen tidak ditemukan')
 return d
@router.delete('/{document_id}',status_code=204)
async def delete(document_id:uuid.UUID,db:AsyncSession=Depends(get_db)):
 d=(await db.execute(select(Document).where(Document.id==document_id))).scalar_one_or_none()
 if not d:raise HTTPException(404,'Dokumen tidak ditemukan')
 for c in (await db.execute(select(Chunk.collection_name).where(Chunk.document_id==d.id).distinct())).scalars(): delete_points_by_payload(c,str(d.id))
 try:Path(d.file_path).unlink(missing_ok=True)
 except OSError:pass
 await db.delete(d)
