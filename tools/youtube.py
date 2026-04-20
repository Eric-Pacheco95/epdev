"""Fetch YouTube transcript via youtube-transcript-api.

CLI: python tools/youtube.py <video_id>
Output: JSON {"type": "transcript"|"unavailable", "content": str, "source": str, "video_id": str}
"""
import concurrent.futures
import json
import re
import sys


_MAX_CHARS = 25_000
_TIMEOUT_SEC = 10


def _sanitize(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"&gt;&gt;", "", text)
    text = re.sub(r"\d{1,2}:\d{2}:\d{2}(\.\d{3})?", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = text.encode("utf-8", errors="ignore").decode("utf-8")
    return text[:_MAX_CHARS]


def _fetch_transcript(video_id: str) -> list:
    from youtube_transcript_api import YouTubeTranscriptApi
    api = YouTubeTranscriptApi()
    fetched = api.fetch(video_id)
    return [{"text": s.text} for s in fetched.snippets]


def youtube_fetch(video_id: str) -> dict:
    if not video_id or not video_id.strip():
        return {"type": "unavailable", "source": "empty video_id", "video_id": video_id, "content": ""}

    video_id = video_id.strip()

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_fetch_transcript, video_id)
            try:
                transcript_list = future.result(timeout=_TIMEOUT_SEC)
            except concurrent.futures.TimeoutError:
                return {"type": "unavailable", "source": "timeout after 10s", "video_id": video_id, "content": ""}

        raw = " ".join(entry.get("text", "") for entry in transcript_list)
        content = _sanitize(raw)

        return {
            "type": "transcript",
            "content": content,
            "source": "youtube-transcript-api",
            "video_id": video_id,
        }

    except Exception as exc:
        return {"type": "unavailable", "source": str(exc)[:200], "video_id": video_id, "content": ""}


def main():
    video_id = sys.argv[1] if len(sys.argv) > 1 else ""
    result = youtube_fetch(video_id)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
