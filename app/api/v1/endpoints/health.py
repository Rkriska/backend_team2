from fastapi import APIRouter
from sqlalchemy import text
from app.database import async_session_maker
from app.qdrant_client import get_qdrant_client
router=APIRouter(tags=['health'])
@router.get('/health')
async def health():
 postgres=qdrant='ok'
 try:
  async with async_session_maker() as db: await db.execute(text('SELECT 1'))
 except Exception: postgres='error'
 try: get_qdrant_client().get_collections()
 except Exception: qdrant='error'
 return {'status':'ok' if postgres==qdrant=='ok' else 'degraded','postgres':postgres,'qdrant':qdrant}
