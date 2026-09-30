import uuid
from datetime import datetime
from sqlalchemy import select
from app.database import async_session_maker
from app.models import Document,ChecklistItem,ScreeningSession,FormatCheckResult,ScreeningResult
from app.core.constants import DocType,DocStatus,ScreeningStatus,FinalResult,ScreeningStage
from app.services.rule_engine import check_format,get_all_rules
async def seed_checklists(db):
 existing={x for x in (await db.execute(select(ChecklistItem.item_key))).scalars()}
 for r in get_all_rules():
  if r['item_key'] not in existing: db.add(ChecklistItem(**{k:r[k] for k in ('item_key','description','category','checklist_number')}))
 await db.flush()
async def screening_one_worker(session_id:uuid.UUID,project_id:uuid.UUID):
 async with async_session_maker() as db:
  session=(await db.execute(select(ScreeningSession).where(ScreeningSession.id==session_id))).scalar_one_or_none()
  if not session:return
  session.status=ScreeningStatus.RUNNING;session.started_at=datetime.utcnow();await seed_checklists(db);await db.commit()
  try:
   docs=(await db.execute(select(Document).where(Document.project_id==project_id,Document.doc_type.in_([DocType.TOR,DocType.RAB]),Document.status==DocStatus.PROCESSED))).scalars().all()
   if not docs: raise ValueError('TOR atau RAB yang telah diproses tidak ditemukan')
   items={i.item_key:i for i in (await db.execute(select(ChecklistItem).where(ChecklistItem.is_active.is_(True),ChecklistItem.category=='FORMAT'))).scalars()}
   overall=True
   for doc in docs:
    checks=check_format(doc.extracted_text or '',doc.doc_type.value)
    passed=all(c['passed'] for c in checks);overall &= passed
    for c in checks: db.add(FormatCheckResult(session_id=session_id,document_id=doc.id,checklist_item_id=items[c['item_key']].id,passed=c['passed'],notes=c['notes']))
    db.add(ScreeningResult(session_id=session_id,document_id=doc.id,stage=ScreeningStage.FORMAT,passed=passed,summary='Format lengkap' if passed else 'Format memerlukan revisi'))
   session.status=ScreeningStatus.COMPLETED;session.completed_at=datetime.utcnow();session.final_result=FinalResult.LOLOS if overall else FinalResult.REVISI
   await db.commit()
  except Exception:
   session.status=ScreeningStatus.FAILED;session.completed_at=datetime.utcnow();await db.commit()
async def screening_two_worker(session_id:uuid.UUID,project_id:uuid.UUID):
 from app.services.rag_pipeline import run_screening_2
 async with async_session_maker() as db: await run_screening_2(session_id,project_id,db)
