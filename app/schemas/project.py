import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from app.core.constants import ProjectStatus
class ProjectCreate(BaseModel):
 name: str = Field(min_length=1,max_length=255); client_name: str = Field(min_length=1,max_length=255); description: str|None=None
class ProjectUpdate(BaseModel):
 name:str|None=None; client_name:str|None=None; description:str|None=None; status:ProjectStatus|None=None
class ProjectOut(BaseModel):
 model_config=ConfigDict(from_attributes=True)
 id:uuid.UUID; name:str; client_name:str; description:str|None; status:ProjectStatus; created_at:datetime; updated_at:datetime
class ProjectDetail(ProjectOut): screening_status:list[dict]=[]
