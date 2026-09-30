import uuid
from datetime import datetime
from pydantic import BaseModel,ConfigDict
from app.core.constants import LLMClassification
class LLMOutputOut(BaseModel):
 model_config=ConfigDict(from_attributes=True)
 id:uuid.UUID; session_id:uuid.UUID; document_id:uuid.UUID; checklist_item_id:uuid.UUID|None; classification:LLMClassification; recommendation:str; reason:str; evidence_json:list|None; created_at:datetime
