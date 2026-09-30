import uuid
from datetime import datetime
from pydantic import BaseModel,ConfigDict
from app.core.constants import ScreeningStatus,FinalResult,ScreeningStage
from app.schemas.llm_output import LLMOutputOut
class ScreeningStart(BaseModel): project_id:uuid.UUID
class FormatCheckResultOut(BaseModel):
 model_config=ConfigDict(from_attributes=True)
 id:uuid.UUID; session_id:uuid.UUID; document_id:uuid.UUID; checklist_item_id:uuid.UUID; passed:bool; notes:str|None; checked_at:datetime
class ScreeningResultOut(BaseModel):
 model_config=ConfigDict(from_attributes=True)
 id:uuid.UUID; session_id:uuid.UUID; document_id:uuid.UUID; stage:ScreeningStage; passed:bool; summary:str|None; created_at:datetime
class ScreeningSessionOut(BaseModel):
 model_config=ConfigDict(from_attributes=True)
 id:uuid.UUID; project_id:uuid.UUID; screening_number:int; status:ScreeningStatus; started_at:datetime|None; completed_at:datetime|None; final_result:FinalResult|None; rocan_approved:bool|None; rocan_approved_at:datetime|None; created_at:datetime
class ScreeningOneDetail(ScreeningSessionOut): format_check_results:list[FormatCheckResultOut]=[]; screening_results:list[ScreeningResultOut]=[]
class ScreeningTwoDetail(ScreeningSessionOut): llm_outputs:list[LLMOutputOut]=[]; screening_results:list[ScreeningResultOut]=[]
