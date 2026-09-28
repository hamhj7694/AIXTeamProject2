from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from general_api.app.main import app
from audio_upload import MAX_AUDIO_BYTES


class AudioTranscriptionUploadValidationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self.client.close()

    def test_rejects_unsupported_audio_extension_before_proxying(self) -> None:
        response = self.client.post(
            "/api/audio/transcriptions",
            content=b"not audio",
            headers={"Content-Type": "audio/wav", "X-Audio-Filename": "recording.exe"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"]["code"], "AUDIO_FILE_TYPE_UNSUPPORTED")

    def test_rejects_empty_audio_before_proxying(self) -> None:
        response = self.client.post(
            "/api/audio/transcriptions",
            content=b"",
            headers={"Content-Type": "audio/wav", "X-Audio-Filename": "recording.wav"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"]["code"], "AUDIO_FILE_EMPTY")

    def test_rejects_oversized_declared_upload_without_buffering(self) -> None:
        response = self.client.post(
            "/api/audio/transcriptions",
            content=b"audio",
            headers={
                "Content-Type": "audio/wav",
                "Content-Length": str(MAX_AUDIO_BYTES + 1),
                "X-Audio-Filename": "recording.wav",
            },
        )

        self.assertEqual(response.status_code, 413)
        self.assertEqual(response.json()["detail"]["code"], "AUDIO_FILE_TOO_LARGE")


if __name__ == "__main__":
    unittest.main()
