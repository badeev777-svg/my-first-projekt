import io
import edge_tts
from groq import AsyncGroq
from src.config import Config

TTS_VOICE = "en-US-JennyNeural"


async def transcribe_audio(audio_bytes: bytes) -> str:
    client = AsyncGroq(api_key=Config.GROQ_API_KEY)
    transcription = await client.audio.transcriptions.create(
        file=("voice.ogg", audio_bytes),
        model="whisper-large-v3",
        response_format="text",
        language="en",
    )
    return transcription


async def synthesize_speech(text: str) -> bytes:
    communicate = edge_tts.Communicate(text, voice=TTS_VOICE)
    audio_stream = io.BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_stream.write(chunk["data"])
    return audio_stream.getvalue()
