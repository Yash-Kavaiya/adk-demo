"""YouTube acquisition: channel listing, downloads, captions, whisper fallback.

All functions are synchronous, deterministic, and idempotent: if the target
file already exists, the download is skipped (cheap resume).
"""

from __future__ import annotations

import logging
import re
import subprocess
from pathlib import Path

from yt_dlp import YoutubeDL

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Channel listing
# ---------------------------------------------------------------------------


def list_channel_videos(
    channel_url: str,
    max_videos: int | None = None,
    min_duration_sec: int = 0,
    max_duration_sec: int = 10**9,
) -> tuple[str, list[dict]]:
    """Return (channel_title, video dicts) for a channel/playlist URL.

    Uses a flat playlist extraction: no downloads, one metadata pass.
    """
    # Strip trailing whitespace and punctuation (. , /) from chat messages
    cleaned_url = re.sub(r"[.,;/\s]+$", "", channel_url.strip())
    normalized_url = cleaned_url
    if "/@" in normalized_url and not normalized_url.endswith("/videos"):
        normalized_url += "/videos"

    options = {
        "extract_flat": "in_playlist",
        "quiet": True,
        "no_warnings": True,
        "ignoreerrors": True,  # private/deleted videos don't kill intake
        "playlistend": max_videos * 3
        if max_videos
        else None,  # over-fetch, filter below
        "extractor_args": {
            "youtube": {
                "player_client": ["android", "web", "ios"],
            }
        },
    }
    options = {k: v for k, v in options.items() if v is not None}

    info = None
    with YoutubeDL(options) as ydl:
        try:
            info = ydl.extract_info(normalized_url, download=False)
        except Exception:
            # Fallback to original cleaned URL
            try:
                info = ydl.extract_info(cleaned_url, download=False)
            except Exception:
                pass

    channel_title = (info or {}).get("title") or "Unknown channel"
    videos: list[dict] = []
    for entry in (info or {}).get("entries") or []:
        if not entry:
            continue
        duration = int(entry.get("duration") or 0)
        if duration and not (min_duration_sec <= duration <= max_duration_sec):
            continue
        video_id = entry.get("id") or ""
        url = entry.get("url") or ""
        if video_id and "youtube.com" not in url and "youtu.be" not in url:
            url = f"https://www.youtube.com/watch?v={video_id}"
        if not video_id:
            continue
        videos.append(
            {
                "video_id": video_id,
                "title": entry.get("title") or video_id,
                "url": url,
                "duration_sec": duration,
                "upload_date": entry.get("upload_date") or "",
            }
        )
        if max_videos and len(videos) >= max_videos:
            break
    return channel_title, videos


# ---------------------------------------------------------------------------
# Download + audio
# ---------------------------------------------------------------------------


def download_video(url: str, dest_dir: Path, max_height: int = 480) -> Path:
    """Download a capped-resolution mp4; returns existing file on re-run."""
    dest_dir = Path(dest_dir)
    existing = sorted(dest_dir.glob("video.*"))
    if existing:
        return existing[0]

    outtmpl = str(dest_dir / "video.%(ext)s")
    options = {
        "format": f"bestvideo[height<={max_height}][ext=mp4]+bestaudio[ext=m4a]"
        f"/best[height<={max_height}][ext=mp4]/best[height<={max_height}]/best",
        "outtmpl": outtmpl,
        "merge_output_format": "mp4",
        "quiet": True,
        "no_warnings": True,
        "overwrites": False,
        "extractor_args": {
            "youtube": {
                "player_client": ["android", "web", "ios"],
            }
        },
    }
    with YoutubeDL(options) as ydl:
        ydl.download([url])
    downloaded = sorted(dest_dir.glob("video.*"))
    if not downloaded:
        raise RuntimeError(f"yt-dlp produced no file for {url}")
    return downloaded[0]


def extract_audio(video_path: Path, dest_dir: Path) -> Path:
    """16 kHz mono wav for whisper; idempotent."""
    dest = Path(dest_dir) / "audio.wav"
    if dest.exists():
        return dest
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        str(dest),
    ]
    _run(cmd, f"audio extraction for {video_path}")
    return dest


# ---------------------------------------------------------------------------
# Transcripts
# ---------------------------------------------------------------------------


def fetch_captions(
    url: str, dest_dir: Path, langs: tuple[str, ...] = ("en.*", "en")
) -> Path | None:
    """Fetch human or auto captions as vtt. Returns None when unavailable."""
    dest_dir = Path(dest_dir)
    existing = sorted(dest_dir.glob("captions.*.vtt")) + sorted(
        dest_dir.glob("captions.vtt")
    )
    if existing:
        return existing[0]

    options = {
        "skip_download": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": list(langs),
        "subtitlesformat": "vtt",
        "outtmpl": str(dest_dir / "captions.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
        "ignoreerrors": True,
    }
    try:
        with YoutubeDL(options) as ydl:
            ydl.download([url])
    except Exception as exc:  # noqa: BLE001 - yt-dlp raises many exception types
        logger.warning("caption fetch failed for %s: %s", url, exc)
        return None
    found = sorted(dest_dir.glob("captions.*.vtt")) + sorted(
        dest_dir.glob("captions.vtt")
    )
    return found[0] if found else None


def whisper_transcribe(
    audio_path: Path, dest_dir: Path, model_size: str = "base"
) -> Path:
    """Local faster-whisper transcription with timestamps; idempotent."""
    dest = Path(dest_dir) / "transcript.txt"
    if dest.exists():
        return dest

    from faster_whisper import WhisperModel  # heavy import, deferred

    model = WhisperModel(model_size, device="auto", compute_type="auto")
    segments, _info = model.transcribe(str(audio_path), vad_filter=True)
    lines = [f"[{_fmt_ts(seg.start)}] {seg.text.strip()}" for seg in segments]
    dest.write_text("\n".join(lines), encoding="utf-8")
    return dest


_VTT_TS = re.compile(r"(?P<h>\d{1,2}):(?P<m>\d{2}):(?P<s>\d{2})[.,]\d+\s*-->")
_VTT_TAG = re.compile(r"<[^>]+>")


def vtt_to_text(vtt_path: Path, dest_dir: Path) -> Path:
    """Convert WebVTT captions to timestamped plain text; idempotent.

    Output lines look like: [00:01:12] the spoken words ...
    Consecutive duplicate lines (auto-caption scrolling artifacts) are dropped.
    """
    dest = Path(dest_dir) / "transcript.txt"
    if dest.exists():
        return dest

    lines_out: list[str] = []
    last_text = ""
    ts = "00:00:00"
    for raw in Path(vtt_path).read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith(("WEBVTT", "Kind:", "Language:")):
            continue
        match = _VTT_TS.search(line)
        if match:
            ts = f"{match.group('h')}:{match.group('m')}:{match.group('s')}"
            continue  # timestamp line; text follows on the next line(s)
        if line.isdigit():
            continue  # cue index
        text = _VTT_TAG.sub("", line).strip()
        if not text or text == last_text:
            continue
        lines_out.append(f"[{ts}] {text}")
        last_text = text
    dest.write_text("\n".join(lines_out), encoding="utf-8")
    return dest


def load_transcript_text(path: Path, max_chars: int = 120_000) -> str:
    text = Path(path).read_text(encoding="utf-8", errors="ignore")
    if len(text) > max_chars:  # very long videos: keep head+tail for coverage
        half = max_chars // 2
        text = text[:half] + "\n...[middle truncated]...\n" + text[-half:]
    return text


# ---------------------------------------------------------------------------
# internals
# ---------------------------------------------------------------------------


def _fmt_ts(seconds: float) -> str:
    total = int(seconds)
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def _run(cmd: list[str], what: str) -> None:
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"{what} failed: {proc.stderr[-2000:]}")
