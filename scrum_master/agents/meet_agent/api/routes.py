from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, File, HTTPException, Response, UploadFile, status

from scrum_master.agents.meet_agent.core.schemas import UploadResponse
from scrum_master.agents.meet_agent.services.file_service import FileService

router = APIRouter(
    prefix='/api/v1',
    tags=['custom_api'],
)


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
            detail=f'Upload failed: {e!s}',
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


@router.get('/health', summary='Health check')
async def health_check() -> Response:
    return Response(
        {
            'status': 'healthy',
            'service': 'meeting_protocol_agent',
        }
    )
