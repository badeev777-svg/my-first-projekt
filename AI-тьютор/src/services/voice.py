import asyncio
import io
import os
import tempfile

import edge_tts
import whisper

TTS_VOICE = "en-US-JennyNeural"

_model: whisper.Whisper | None = None


def _get_model() -> whisper.Whisper:
    global _model
    if _model is None:
        _model = whisper.load_model("base")
    return _model


async def transcribe_audio(audio_bytes: bytes) -> str:
    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as f:
        f.write(audio_bytes)
        tmp_path = f.name
    try:
        loop = asyncio.get_event_loop()
        model = _get_model()
        result = await loop.run_in_executor(
            None,
            lambda: model.transcribe(tmp_path, language="en")
        )
        return result["text"].strip()
    finally:
        os.unlink(tmp_path)


async def synthesize_speech(text: str) -> bytes:
    communicate = edge_tts.Communicate(text, voice=TTS_VOICE)
    audio_stream = io.BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_stream.write(chunk["data"])
    return audio_stream.getvalue()
