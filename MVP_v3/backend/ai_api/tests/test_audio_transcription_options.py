from __future__ import annotations

import unittest
from unittest.mock import patch

from ai_api.app.main import _audio_transcription_options


class AudioTranscriptionOptionsTest(unittest.TestCase):
    def test_default_audio_transcription_uses_korean_prompt_without_diarization(self) -> None:
        with patch("ai_api.app.main.os.getenv", side_effect=lambda key, default=None: default):
            options = _audio_transcription_options()

        self.assertEqual(options["model"], "gpt-4o-transcribe")
        self.assertEqual(options["response_format"], "json")
        self.assertEqual(options["language"], "ko")
        self.assertEqual(options["stream"], "true")
        self.assertIn("전화번호", options["prompt"])
        self.assertIn("추측", options["prompt"])
        self.assertNotIn("chunking_strategy", options)

    def test_explicit_diarization_model_keeps_compatible_request_options(self) -> None:
        with patch.dict("os.environ", {"OPENAI_AUDIO_TRANSCRIPTION_MODEL": "gpt-4o-transcribe-diarize"}):
            options = _audio_transcription_options()

        self.assertEqual(options, {
            "model": "gpt-4o-transcribe-diarize",
            "stream": "true",
            "language": "ko",
            "response_format": "diarized_json",
            "chunking_strategy": "auto",
        })


if __name__ == "__main__":
    unittest.main()
