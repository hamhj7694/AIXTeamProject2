from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
from urllib.parse import unquote

from fastapi import Request


MAX_AUDIO_BYTES = 25 * 1024 * 1024
SUPPORTED_AUDIO_EXTENSIONS = {".flac", ".mp3", ".mp4", ".mpeg", ".mpga", ".m4a", ".ogg", ".wav", ".webm"}


@dataclass(frozen=True)
class AudioUpload:
    filename: str
    content_type: str
    content: bytes


async def read_audio_upload(request: Request) -> AudioUpload:
    raw_filename = unquote(request.headers.get("X-Audio-Filename", ""))
    filename = PurePosixPath(raw_filename.replace("\\", "/")).name.strip()
    if not filename or PurePosixPath(filename).suffix.lower() not in SUPPORTED_AUDIO_EXTENSIONS:
        raise ValueError("AUDIO_FILE_TYPE_UNSUPPORTED")

    content_type = request.headers.get("content-type", "application/octet-stream").split(";", 1)[0].strip().lower()
    if not (content_type.startswith("audio/") or content_type in {"video/mp4", "application/octet-stream"}):
        raise ValueError("AUDIO_FILE_TYPE_UNSUPPORTED")

    content_length = request.headers.get("content-length")
    if content_length:
        try:
            declared_size = int(content_length)
        except ValueError as exc:
            raise ValueError("AUDIO_REQUEST_INVALID") from exc
        if declared_size < 0:
            raise ValueError("AUDIO_REQUEST_INVALID")
        if declared_size > MAX_AUDIO_BYTES:
            raise ValueError("AUDIO_FILE_TOO_LARGE")

    chunks: list[bytes] = []
    size = 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > MAX_AUDIO_BYTES:
            raise ValueError("AUDIO_FILE_TOO_LARGE")
        chunks.append(chunk)
    if size == 0:
        raise ValueError("AUDIO_FILE_EMPTY")
    return AudioUpload(filename=filename, content_type=content_type, content=b"".join(chunks))
