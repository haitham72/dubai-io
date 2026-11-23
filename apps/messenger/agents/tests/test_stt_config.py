"""The realtime transcription block sends only what each model supports, checked against the SDK's own types."""
import pytest
from openai.types.realtime.audio_transcription import AudioTranscription

from mirsal_agents.stt import transcription_config


@pytest.mark.parametrize("model", ["gpt-realtime-whisper", "gpt-live-transcribe", "gpt-transcribe", "gpt-4o-transcribe",
                                   "gpt-4o-mini-transcribe", "whisper-1"])
def test_config_is_valid_for_the_sdk(model):
    cfg = transcription_config(model, "low", ["Arif Khan", "Sara Ali"])
    assert AudioTranscription.model_validate(cfg).model == model
    assert set(cfg) <= set(AudioTranscription.model_fields)


def test_each_model_gets_only_its_own_hints():
    whisper = transcription_config("gpt-realtime-whisper", "low", ["Arif Khan"])
    assert whisper == {"model": "gpt-realtime-whisper", "language": "en", "delay": "low"}     # takes no vocabulary
    live = transcription_config("gpt-live-transcribe", "low", ["Arif Khan", "Arif Khan", " "])
    assert "delay" not in live and live["languages"] == ["en", "ar"]
    assert "Arif Khan" in live["keywords"] and "Mirsal" in live["keywords"] and live["keywords"].count("Arif Khan") == 1
    assert "Arif Khan" in transcription_config("gpt-4o-transcribe", "low", ["Arif Khan"])["prompt"]
    assert len(transcription_config("gpt-live-transcribe", "low", [f"Name {i}" for i in range(500)])["keywords"]) == 100
