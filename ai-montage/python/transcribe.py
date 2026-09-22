"""Локальная транскрипция речи через faster-whisper.

Использование: python transcribe.py --audio <путь.wav> --out <путь.json>
"""
import argparse
import json

from faster_whisper import WhisperModel


def transcribe(audio_path: str) -> dict:
    model = WhisperModel("base", device="cpu", compute_type="int8")
    segments, info = model.transcribe(audio_path, word_timestamps=True)

    words = []
    segment_list = []
    full_text_parts = []

    for segment in segments:
        segment_list.append(
            {"start": segment.start, "end": segment.end, "text": segment.text.strip()}
        )
        full_text_parts.append(segment.text.strip())
        if segment.words:
            for word in segment.words:
                words.append(
                    {"word": word.word.strip(), "start": word.start, "end": word.end}
                )

    return {
        "language": info.language,
        "duration": info.duration,
        "text": " ".join(full_text_parts).strip(),
        "segments": segment_list,
        "words": words,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audio", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    result = transcribe(args.audio)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"Расшифровка сохранена в {args.out}, слов: {len(result['words'])}")


if __name__ == "__main__":
    main()
