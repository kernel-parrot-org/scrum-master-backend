from pydantic import BaseModel


class UploadResponse(BaseModel):
    status: str
    meeting_id: str
    audio_path: str
    message: str
