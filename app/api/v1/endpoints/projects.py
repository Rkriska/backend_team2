import uuid
from fastapi import APIRouter,Depends,HTTPException,status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models import Project,ScreeningSession,ScreeningResult,LLMOutput
from app.schemas.project import ProjectCreate,ProjectUpdate,ProjectOut,ProjectDetail
router=APIRouter(prefix='/projects',tags=['projects'])
async def project_or_404(id:uuid.UUID,db):
 p=(await db.execute(select(Project).where(Project.id==id))).scalar_one_or_none()
 if not p: raise HTTPException(404,'Project tidak ditemukan')
 return p
@router.post('',response_model=ProjectOut,status_code=status.HTTP_201_CREATED)
async def create(body:ProjectCreate,db:AsyncSession=Depends(get_db)):
 p=Project(**body.model_dump());db.add(p);await db.flush();await db.refresh(p);return p
@router.get('',response_model=list[ProjectOut])
async def list_projects(db:AsyncSession=Depends(get_db)): return (await db.execute(select(Project).order_by(Project.created_at.desc()))).scalars().all()
@router.get('/{project_id}',response_model=ProjectDetail)
async def get(project_id:uuid.UUID,db:AsyncSession=Depends(get_db)):
 p=await project_or_404(project_id,db); rows=(await db.execute(select(ScreeningSession).where(ScreeningSession.project_id==project_id).order_by(ScreeningSession.created_at.desc()))).scalars().all();return ProjectDetail.model_validate(p).model_copy(update={'screening_status':[{'id':str(x.id),'number':x.screening_number,'status':x.status.value,'final_result':x.final_result.value if x.final_result else None} for x in rows]})
@router.patch('/{project_id}',response_model=ProjectOut)
async def update(project_id:uuid.UUID,body:ProjectUpdate,db:AsyncSession=Depends(get_db)):
 p=await project_or_404(project_id,db)
 for k,v in body.model_dump(exclude_unset=True).items(): setattr(p,k,v)
 await db.flush();await db.refresh(p);return p
@router.delete('/{project_id}',status_code=204)
async def delete(project_id:uuid.UUID,db:AsyncSession=Depends(get_db)):
 await db.delete(await project_or_404(project_id,db))
@router.get('/{project_id}/results')
async def results(project_id:uuid.UUID,db:AsyncSession=Depends(get_db)):
 p=await project_or_404(project_id,db);sessions=(await db.execute(select(ScreeningSession).where(ScreeningSession.project_id==project_id).order_by(ScreeningSession.created_at.desc()))).scalars().all();return {'project':ProjectOut.model_validate(p).model_dump(mode='json'),'sessions':[{'session_id':str(s.id),'screening_number':s.screening_number,'status':s.status.value,'final_result':s.final_result.value if s.final_result else None,'results':[{'passed':r.passed,'summary':r.summary,'stage':r.stage.value} for r in (await db.execute(select(ScreeningResult).where(ScreeningResult.session_id==s.id))).scalars()],'llm_outputs':[{'classification':o.classification.value,'reason':o.reason,'recommendation':o.recommendation,'evidence':o.evidence_json} for o in (await db.execute(select(LLMOutput).where(LLMOutput.session_id==s.id))).scalars()]} for s in sessions]}
