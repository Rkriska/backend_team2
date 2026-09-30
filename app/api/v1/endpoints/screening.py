import uuid
from fastapi import APIRouter,Depends,HTTPException,BackgroundTasks,status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models import Project,ScreeningSession,FormatCheckResult,ScreeningResult,LLMOutput
from app.schemas.screening import ScreeningStart,ScreeningOneDetail,ScreeningTwoDetail,ScreeningSessionOut
from app.core.constants import ScreeningStatus,FinalResult
from app.services.screening_worker import screening_one_worker,screening_two_worker
router=APIRouter(prefix='/screening',tags=['screening'])
async def new_session(body,number,db):
 if not (await db.execute(select(Project.id).where(Project.id==body.project_id))).scalar_one_or_none():raise HTTPException(404,'Project tidak ditemukan')
 s=ScreeningSession(project_id=body.project_id,screening_number=number,status=ScreeningStatus.PENDING);db.add(s);await db.flush();await db.refresh(s);return s
@router.post('/1/start',response_model=ScreeningSessionOut,status_code=201)
async def start_one(body:ScreeningStart,bg:BackgroundTasks,db:AsyncSession=Depends(get_db)):
 s=await new_session(body,1,db);bg.add_task(screening_one_worker,s.id,body.project_id);return s
@router.get('/1/{session_id}',response_model=ScreeningOneDetail)
async def get_one(session_id:uuid.UUID,db:AsyncSession=Depends(get_db)):
 s=(await db.execute(select(ScreeningSession).where(ScreeningSession.id==session_id,ScreeningSession.screening_number==1))).scalar_one_or_none()
 if not s:raise HTTPException(404,'Sesi tidak ditemukan')
 return ScreeningOneDetail.model_validate(s).model_copy(update={'format_check_results':(await db.execute(select(FormatCheckResult).where(FormatCheckResult.session_id==s.id))).scalars().all(),'screening_results':(await db.execute(select(ScreeningResult).where(ScreeningResult.session_id==s.id))).scalars().all()})
@router.post('/2/start',response_model=ScreeningSessionOut,status_code=201)
async def start_two(body:ScreeningStart,bg:BackgroundTasks,db:AsyncSession=Depends(get_db)):
 latest=(await db.execute(select(ScreeningSession).where(ScreeningSession.project_id==body.project_id,ScreeningSession.screening_number==1).order_by(ScreeningSession.created_at.desc()))).scalars().first()
 if not latest or latest.status!=ScreeningStatus.COMPLETED or latest.final_result!=FinalResult.LOLOS:raise HTTPException(409,'Screening 1 terbaru harus berstatus LOLOS')
 s=await new_session(body,2,db);bg.add_task(screening_two_worker,s.id,body.project_id);return s
@router.get('/2/{session_id}',response_model=ScreeningTwoDetail)
async def get_two(session_id:uuid.UUID,db:AsyncSession=Depends(get_db)):
 s=(await db.execute(select(ScreeningSession).where(ScreeningSession.id==session_id,ScreeningSession.screening_number==2))).scalar_one_or_none()
 if not s:raise HTTPException(404,'Sesi tidak ditemukan')
 return ScreeningTwoDetail.model_validate(s).model_copy(update={'llm_outputs':(await db.execute(select(LLMOutput).where(LLMOutput.session_id==s.id))).scalars().all(),'screening_results':(await db.execute(select(ScreeningResult).where(ScreeningResult.session_id==s.id))).scalars().all()})
async def decide(session_id,approved,db):
 s=(await db.execute(select(ScreeningSession).where(ScreeningSession.id==session_id))).scalar_one_or_none()
 if not s:raise HTTPException(404,'Sesi tidak ditemukan')
 from datetime import datetime
 s.rocan_approved=approved;s.rocan_approved_at=datetime.utcnow();await db.flush();await db.refresh(s);return s
@router.post('/{session_id}/approve',response_model=ScreeningSessionOut)
async def approve(session_id:uuid.UUID,db:AsyncSession=Depends(get_db)):return await decide(session_id,True,db)
@router.post('/{session_id}/reject',response_model=ScreeningSessionOut)
async def reject(session_id:uuid.UUID,db:AsyncSession=Depends(get_db)):return await decide(session_id,False,db)
