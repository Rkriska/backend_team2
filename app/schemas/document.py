import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.core.constants import DocType,DocStatus
class DocumentOut(BaseModel):
 model_config=ConfigDict(from_attributes=True)
 id:uuid.UUID; project_id:uuid.UUID; doc_type:DocType; file_name:str; file_path:str; status:DocStatus; uploaded_at:datetime; processed_at:datetime|None; extracted_text:str|None=None
