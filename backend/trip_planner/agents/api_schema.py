from pydantic import BaseModel
from typing import Optional, List,Dict,Any

class TripChatSchema(BaseModel):
    text: Optional[str] = None
    image: Optional[Any] = None
    audio_file: Optional[Any] = None
    session_id: str