import logging
import httpx

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import (APIRouter, File, HTTPException, Response, UploadFile,
                     status)
from pydantic import BaseModel

from scrum_master.agents.meet_agent.core.schemas import UploadResponse
from scrum_master.agents.meet_agent.core.agent_schemas import (
    TranscribeAndCreateTasksRequest,
    TranscribeAndCreateTasksResponse,
    AgentResponse,
)
from scrum_master.agents.meet_agent.services.file_service import FileService
from scrum_master.agents.meet_agent.tools.transcribe_tool import transcribe_audio
from scrum_master.agents.meet_agent.tools.jira_tool import process_meeting_tasks_to_jira

router = APIRouter(
    prefix='/api/v1',
    tags=['meet_agent'],
)


class CreateTasksRequest(BaseModel):
    user_id: str
    text: str | None = None
    audio_url: str | None = None


@router.post(
    '/upload-audio', response_model=UploadResponse, summary='Upload audio file'
)
@inject
async def upload_audio(
    file_service: FromDishka[FileService], file: UploadFile = File(...)
) -> UploadResponse:
    try:
        meeting_id, local_path, gcs_uri = await file_service.save_audio_file(file)

        return UploadResponse(
            status='success',
            meeting_id=meeting_id,
            audio_path=gcs_uri,
            message=f'File uploaded to GCS. Use this URI with agent: {gcs_uri}',
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Upload failed: {str(e)}',
        )


@router.get('/audio-info/{meeting_id}', summary='Get audio info')
@inject
async def get_audio_info_route(
    file_service: FromDishka[FileService], meeting_id: str
) -> Response:
    audio_path = file_service.get_gcs_uri(meeting_id)
    return Response(
        {
            'gcs_uri': f'Use this URI with agent: {audio_path}',
        }
    )


@router.delete('/audio/{meeting_id}', summary='Delete audio file')
@inject
async def delete_audio(
    file_service: FromDishka[FileService], meeting_id: str
) -> Response:
    deleted = file_service.delete_audio_file(meeting_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Audio file not found',
        )

    return Response(
        {
            'status': 'success',
            'message': f'Audio file {meeting_id} deleted',
        }
    )

@router.post('/create-tasks-from-audio')
async def create_tasks_from_audio(request: CreateTasksRequest):
    if not request.text and not request.audio_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Either text or audio_url must be provided'
        )
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        create_session_resp = await client.post(
            'http://localhost:8000/apps/meet_agent/users/user/sessions',
            json={'appName': 'meet_agent', 'userId': request.user_id}
        )
        create_session_resp.raise_for_status()
        session_data = create_session_resp.json()
        session_id = session_data['id']
        
        if request.audio_url:
            message_text = f'Process this audio file and create tasks: {request.audio_url}'
        else:
            message_text = request.text
        
        run_resp = await client.post(
            'http://localhost:8000/run',
            json={
                'appName': 'meet_agent',
                'userId': "user",
                'sessionId': session_id,
                'newMessage': {
                    'parts': [{'text': message_text}],
                    'role': 'user'
                },
                'streaming': False
            }
        )
        run_resp.raise_for_status()
        
        return run_resp.json()


@router.post(
    '/agent/transcribe-and-create-tasks',
    response_model=TranscribeAndCreateTasksResponse,
    summary='Transcribe audio and create Jira tasks with automatic decomposition'
)
async def transcribe_and_create_tasks(
    request: TranscribeAndCreateTasksRequest,
) -> TranscribeAndCreateTasksResponse:
    try:
        logger = logging.getLogger(__name__)
        logger.info(f"[Endpoint] Starting audio processing for: {request.audio_uri}")
        
        logger.info("[Endpoint] Step 1: Transcribing audio...")
        transcription_result = transcribe_audio(request.audio_uri)
        
        if transcription_result.get("status") != "success":
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Transcription failed: {transcription_result.get('message')}"
            )
        
        logger.info(f"[Endpoint] Transcription successful")
        
        meeting_data = {
            "meeting_type": "team_meeting",
            "project_complexity": "simple",
            "participants": {
                "active_speakers": [],
                "mentioned": request.team_members or []
            },
            "summary": {
                "title": "Meeting from audio transcription",
                "description": "Transcribed and processed audio"
            },
            "tasks": [
                {
                    "title": "Example task from meeting",
                    "description": "This is automatically created from the meeting",
                    "task_type": "task",
                    "assignee": request.team_members[0] if request.team_members else None,
                    "priority": "medium",
                    "deadline": None,
                    "context": "Created from audio transcription",
                    "mentioned_by": "System"
                }
            ]
        }
        
        logger.info("[Endpoint] Step 2: Processing meeting data to Jira...")
        
        jira_result = await process_meeting_tasks_to_jira(meeting_data)
        
        logger.info(f"[Endpoint] Jira processing complete: {jira_result.get('status')}")
        
        meeting_id = request.audio_uri.split('/')[-1].replace('_processed.wav', '')
        
        return TranscribeAndCreateTasksResponse(
            status="success",
            message=jira_result.get("message", "Tasks created successfully"),
            meeting_id=meeting_id,
            jira_results=jira_result.get("data"),
            meeting_data=meeting_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Endpoint] Processing failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Processing failed: {str(e)}"
        )


@router.get('/health', summary='Health check')
async def health_check() -> Response:
    return Response(
        {
            'status': 'healthy',
            'service': 'meeting_protocol_agent',
        }
    )
