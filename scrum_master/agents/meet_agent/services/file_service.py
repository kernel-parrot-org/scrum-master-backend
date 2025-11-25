import logging
import os
import uuid
from pathlib import Path

import aiofiles
from fastapi import HTTPException, UploadFile, status
from google.cloud import storage
from pydub import AudioSegment

logger = logging.getLogger(__name__)


def _preprocess_audio(audio_path: str) -> str:
    try:
        audio = AudioSegment.from_file(audio_path)
        audio = audio.set_channels(1).set_frame_rate(16000)

        target_dbfs = -20.0
        change_in_dbfs = target_dbfs - audio.dBFS
        audio = audio.apply_gain(change_in_dbfs)

        output_path = audio_path.rsplit('.', 1)[0] + '_processed.wav'
        audio.export(output_path, format='wav')
        return output_path
    except Exception as e:
        print(f'[FileService] Audio preprocessing failed: {e}')
        return audio_path


class FileService:
    def __init__(
        self,
        upload_dir: str,
        max_upload_size: int,
        allowed_extensions: set[str],
        gcs_bucket_name: str,
    ):
        self.upload_dir = upload_dir
        self.max_upload_size = max_upload_size
        self.allowed_extensions = allowed_extensions
        self.gcs_bucket_name = gcs_bucket_name

        os.makedirs(self.upload_dir, exist_ok=True)

        if gcs_bucket_name:
            self.gcs_client = storage.Client()
            self.gcs_bucket = self.gcs_client.bucket(gcs_bucket_name)
        else:
            self.gcs_client = None
            self.gcs_bucket = None
            logger.warning('[FileService] GCS bucket name not configured, GCS uploads will be disabled')

    async def save_audio_file(self, file: UploadFile) -> tuple[str, str, str]:
        ext = Path(file.filename).suffix.lower()
        if ext not in self.allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file extension. Allowed: {', '.join(self.allowed_extensions)}",
            )

        content = await file.read()
        if len(content) > self.max_upload_size:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f'File too large. Max size: {self.max_upload_size / 1024 / 1024}MB',
            )

        meeting_id = str(uuid.uuid4())
        filename = f'{meeting_id}{ext}'
        local_path = os.path.join(self.upload_dir, filename)

        async with aiofiles.open(local_path, 'wb') as f:
            await f.write(content)

        processed_path = _preprocess_audio(local_path)

        gcs_uri = await self._upload_to_gcs(processed_path)
        return meeting_id, processed_path, gcs_uri

    async def _upload_to_gcs(self, file_path: str) -> str:
        if not self.gcs_bucket:
            logger.warning('[FileService] GCS not configured, skipping upload')
            return ''

        try:
            filename = os.path.basename(file_path)
            blob = self.gcs_bucket.blob(filename)
            blob.upload_from_filename(file_path, content_type='audio/wav')

            gcs_uri = f'gs://{self.gcs_bucket_name}/{filename}'
            logger.info(f'[FileService] Uploaded processed file to GCS: {gcs_uri}')
            return gcs_uri

        except Exception as e:
            logger.error(f'[FileService] GCS upload failed: {e}')
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f'Failed to upload to GCS: {e!s}',
            )

    def get_gcs_uri(self, meeting_id: str) -> str:
        if not self.gcs_bucket:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='GCS not configured',
            )

        blobs = list(
            self.gcs_client.list_blobs(self.gcs_bucket_name, prefix=meeting_id)
        )

        if not blobs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Audio file not found in GCS',
            )

        return f'gs://{self.gcs_bucket_name}/{blobs[0].name}'

    def get_audio_path(self, meeting_id: str) -> str:
        upload_dir = Path(self.upload_dir)
        files = list(upload_dir.glob(f'{meeting_id}.*'))

        if not files:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Audio file not found',
            )

        return str(files[0].absolute())

    def delete_audio_file(self, meeting_id: str) -> bool:
        deleted = False

        try:
            audio_path = self.get_audio_path(meeting_id)
            os.remove(audio_path)
            deleted = True
        except (HTTPException, FileNotFoundError):
            pass

        if self.gcs_client and self.gcs_bucket_name:
            try:
                blobs = list(
                    self.gcs_client.list_blobs(self.gcs_bucket_name, prefix=meeting_id)
                )
                for blob in blobs:
                    blob.delete()
                    deleted = True
            except Exception as e:
                logger.error(f'[FileService] Failed to delete from GCS: {e}')

        return deleted
