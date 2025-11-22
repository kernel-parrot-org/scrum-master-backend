import logging

from google.cloud import speech_v1p1beta1 as speech

logger = logging.getLogger(__name__)


def transcribe_audio(gcp_uri: str) -> dict:
    try:
        logger.info(f'Transcribing audio: {gcp_uri}')

        audio = speech.RecognitionAudio(uri=gcp_uri)

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
