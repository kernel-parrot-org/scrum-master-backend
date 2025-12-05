import logging
import os
import uuid
from pathlib import Path

from google.cloud import speech_v1p1beta1 as speech
from google.cloud import storage
from scrum_master.shared.config.settings import get_settings

logger = logging.getLogger(__name__)


def _upload_local_file_to_gcs(file_path: str) -> str:
    """Upload local file to GCS and return GCS URI."""
    bucket_name = ''
    
    # Try to get bucket name from settings first
    try:
        settings = get_settings()
        bucket_name = settings.gcs.bucket_name
    except Exception as e:
        logger.warning(f'[TOOL] Failed to get settings: {e}')
    
    # Fallback to environment variables
    if not bucket_name:
        bucket_name = os.getenv('GCS_BUCKET_NAME') or os.getenv('GOOGLE_GCS_BUCKET_NAME', '')
    
    if not bucket_name:
        raise ValueError('GCS bucket name not configured. Please set GCS_BUCKET_NAME or GOOGLE_GCS_BUCKET_NAME environment variable.')
    
    try:
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        
        # Generate unique filename
        filename = f'transcribe_{uuid.uuid4()}_{Path(file_path).name}'
        blob = bucket.blob(filename)
        
        logger.info(f'[TOOL] Uploading local file to GCS: {file_path} -> gs://{bucket_name}/{filename}')
        blob.upload_from_filename(file_path, content_type='audio/wav')
        
        gcs_uri = f'gs://{bucket_name}/{filename}'
        logger.info(f'[TOOL] File uploaded to GCS: {gcs_uri}')
        return gcs_uri
    except Exception as e:
        logger.error(f'[TOOL] Failed to upload to GCS: {e}')
        raise


def transcribe_audio(gcp_uri: str) -> dict:
    try:
        logger.info(f'Transcribing audio: {gcp_uri}')

        # Check if it's a local file or GCS URI
        if gcp_uri.startswith('file://'):
            # Local file - upload to GCS first (required for long audio)
            file_path = gcp_uri.replace('file://', '')
            if not os.path.exists(file_path):
                raise FileNotFoundError(f'Local file not found: {file_path}')
            
            logger.info(f'[TOOL] Local file detected, uploading to GCS: {file_path}')
            gcp_uri = _upload_local_file_to_gcs(file_path)
            audio = speech.RecognitionAudio(uri=gcp_uri)
        elif gcp_uri.startswith('gs://'):
            # GCS URI - use uri parameter
            audio = speech.RecognitionAudio(uri=gcp_uri)
        else:
            # Try to treat as local file path - upload to GCS
            if os.path.exists(gcp_uri):
                logger.info(f'[TOOL] Treating as local file path, uploading to GCS: {gcp_uri}')
                gcp_uri = _upload_local_file_to_gcs(gcp_uri)
                audio = speech.RecognitionAudio(uri=gcp_uri)
            else:
                raise ValueError(f'Invalid audio URI format: {gcp_uri}. Expected gs:// or file:// URI or local file path.')

        client = speech.SpeechClient()

        diarization_config = speech.SpeakerDiarizationConfig(
            enable_speaker_diarization=True,
            min_speaker_count=2,
            max_speaker_count=10,
        )

        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,
            language_code='ru-RU',
            enable_automatic_punctuation=True,
            enable_word_time_offsets=True,
            diarization_config=diarization_config,
            model='latest_long',
            use_enhanced=True,
        )

        logger.info(f'[TOOL] Starting transcription for: {gcp_uri}')
        operation = client.long_running_recognize(config=config, audio=audio)

        response = operation.result(timeout=600)

        result = _parse_transcription_response(response)

        logger.info(
            f"[TOOL] Transcription completed: {result['num_speakers']} speakers, {result['duration']:.1f}s"
        )
        return result

    except Exception as e:
        logger.info(f'[TOOL] Transcription error: {e!s}')
        return {
            'status': 'error',
            'error_message': f'Transcription failed: {e!s}',
            'stage': 'transcribe_audio',
        }


def _parse_transcription_response(response: speech.RecognizeResponse) -> dict:
    segments = []
    all_words = []
    current_speaker = None
    current_segment_words = []

    for result in response.results:
        alternative = result.alternatives[0]

        for word_info in alternative.words:
            speaker_tag = getattr(word_info, 'speaker_tag', 1)

            word_data = {
                'word': word_info.word,
                'speaker': speaker_tag,
                'start': word_info.start_time.total_seconds(),
                'end': word_info.end_time.total_seconds(),
            }

            all_words.append(word_data)

            if current_speaker is None or current_speaker != speaker_tag:
                if current_segment_words:
                    segments.append(
                        {
                            'speaker': current_speaker,
                            'text': ' '.join(
                                [w['word'] for w in current_segment_words]
                            ),
                            'start': current_segment_words[0]['start'],
                            'end': current_segment_words[-1]['end'],
                        }
                    )

                current_speaker = speaker_tag
                current_segment_words = [word_data]
            else:
                current_segment_words.append(word_data)

    if current_segment_words:
        segments.append(
            {
                'speaker': current_speaker,
                'text': ' '.join([w['word'] for w in current_segment_words]),
                'start': current_segment_words[0]['start'],
                'end': current_segment_words[-1]['end'],
            }
        )

    full_text = ' '.join([w['word'] for w in all_words])

    duration = all_words[-1]['end'] if all_words else 0
    num_speakers = len(set(w['speaker'] for w in all_words))

    return {
        'status': 'success',
        'transcript': full_text,
        'segments': segments,
        'num_speakers': num_speakers,
        'duration': duration,
    }
