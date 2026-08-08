from superagent.agents.orchestrator import AgentOrchestrator


def test_multimodal_user_content_preserves_image_audio_video_and_text_file() -> None:
    blocks = AgentOrchestrator._multimodal_user_content(
        "Analyze these attachments.",
        [
            {"kind": "image", "name": "a.png", "mime_type": "image/png", "data": "aGVsbG8="},
            {"kind": "audio", "name": "a.wav", "mime_type": "audio/wav", "data": "YXVkaW8="},
            {"kind": "video", "name": "a.mp4", "mime_type": "video/mp4", "data": "dmlkZW8="},
            {"kind": "file", "name": "notes.md", "mime_type": "text/markdown", "data": "bm90ZXM=", "text_content": "# Notes"},
        ],
    )
    assert isinstance(blocks, list)
    assert blocks[0] == {"type": "text", "text": "Analyze these attachments."}
    assert blocks[1]["type"] == "image_url"
    assert blocks[2]["type"] == "input_audio"
    assert blocks[3]["type"] == "input_video"
    assert blocks[4]["type"] == "text"
    assert "# Notes" in blocks[4]["text"]


def test_multimodal_user_content_without_attachments_is_plain_text() -> None:
    assert AgentOrchestrator._multimodal_user_content("hello", []) == "hello"
