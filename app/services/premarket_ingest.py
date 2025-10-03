from __future__ import annotations

import asyncio
import datetime as dt
import os
from typing import Any, Dict, List, Optional

import httpx
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import SessionLocal
from app.db.models import Feature


def _env(name: str, default: Optional[str] = None) -> Optional[str]:
    v = os.getenv(name)
    return v if v else default


def _now_utc() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


async def _yt_search_latest_video(channel_id: str, api_key: str, max_results: int = 5) -> Optional[Dict[str, Any]]:
    url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "key": api_key,
        "channelId": channel_id,
        "order": "date",
        "type": "video",
        "maxResults": max_results,
        "part": "snippet",
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(url, params=params)
        r.raise_for_status()
        j = r.json()
    items = j.get("items") or []
    return items[0] if items else None


async def _resolve_channel_id_from_url(channel_url: str) -> Optional[str]:
    """Resolve a YouTube channel handle/canonical URL to a channel_id (UC...)."""
    try:
        url = channel_url.rstrip('/')
        # Prefer the /about or /videos page for stable data
        if not url.endswith('/about') and not url.endswith('/videos'):
            url = url + '/about'
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(url)
            r.raise_for_status()
            html = r.text
        import re
        # Try canonical link first
        m = re.search(r'href="https://www\.youtube\.com/channel/(UC[\w-]{22})"', html)
        if m:
            return m.group(1)
        # Try JSON blob
        m = re.search(r'"channelId":"(UC[\w-]{22})"', html)
        if m:
            return m.group(1)
    except Exception:
        return None
    return None


async def _feed_latest_video(channel_id: str) -> Optional[Dict[str, Any]]:
    """Fetch latest video using public RSS feed (no API key)."""
    import xml.etree.ElementTree as ET
    feed = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(feed)
            r.raise_for_status()
            xml_text = r.text
        root = ET.fromstring(xml_text)
        ns = {
            'atom': 'http://www.w3.org/2005/Atom',
            'yt': 'http://www.youtube.com/xml/schemas/2015',
            'media': 'http://search.yahoo.com/mrss/'
        }
        entry = root.find('atom:entry', ns)
        if entry is None:
            return None
        vid_el = entry.find('yt:videoId', ns)
        title_el = entry.find('atom:title', ns)
        published_el = entry.find('atom:published', ns)
        # Optional long description
        desc_el = entry.find('media:group/media:description', ns)
        description = desc_el.text if desc_el is not None else None
        if vid_el is None:
            return None
        return {
            'id': {'videoId': vid_el.text},
            'snippet': {
                'title': title_el.text if title_el is not None else None,
                'publishedAt': published_el.text if published_el is not None else None,
                'description': description,
            },
        }
    except Exception:
        return None


def _pluck_transcript(video_id: str) -> Optional[str]:
    try:
        variants = YouTubeTranscriptApi.list_transcripts(video_id)
        # Prefer English (manually created), then auto
        try:
            tr = variants.find_transcript(["en"])  # type: ignore[attr-defined]
        except Exception:
            tr = variants.find_generated_transcript(["en"])  # type: ignore[attr-defined]
        segs = tr.fetch()
        text = " ".join(s.get("text", "") for s in segs)
        return text.strip() or None
    except (TranscriptsDisabled, NoTranscriptFound):
        return None
    except Exception:
        return None


def _extract_tickers(text: str) -> List[str]:
    # Heuristic: 1–5 uppercase letters, common ETF suffixes allowed
    import re
    raw = set(re.findall(r"\b[A-Z]{1,5}\b", text or ""))
    # Filter obvious stop words
    stop = {"THE", "AND", "YOU", "FOR", "WITH", "THIS", "WILL", "FROM", "THAT", "HAVE", "JUST", "YOUR"}
    return sorted([s for s in raw if s not in stop])[:25]


def _extract_events(text: str) -> List[Dict[str, Any]]:
    if not text:
        return []
    keys = ["CPI", "PPI", "FOMC", "JOBS", "NFP", "EARNINGS", "PCE", "FED", "GDP"]
    out: List[Dict[str, Any]] = []
    for k in keys:
        if k in text.upper():
            out.append({"name": k})
    return out[:10]


def _infer_sentiment(text: Optional[str]) -> str:
    if not text:
        return "neutral"
    t = text.lower()
    pos = sum(k in t for k in ["bullish", "breakout", "strength", "accumulation", "bid"])
    neg = sum(k in t for k in ["bearish", "breakdown", "weak", "distribution", "sell-off", "selloff"])
    if pos > neg and pos >= 1:
        return "bullish"
    if neg > pos and neg >= 1:
        return "bearish"
    return "neutral"


async def _already_ingested(session: AsyncSession, video_id: str) -> bool:
    stmt = (
        select(Feature)
        .where(Feature.horizon == "premarket")
        .where(Feature.symbol == "*")
        .order_by(desc(Feature.created_at))
        .limit(5)
    )
    res = await session.execute(stmt)
    for f in res.scalars().all():
        try:
            if (f.payload or {}).get("video_id") == video_id:
                return True
        except Exception:
            continue
    return False


async def ingest_premarket_once() -> Optional[Dict[str, Any]]:
    """Fetch latest premarket video metadata/transcript and store a Feature row.
    Requires env YOUTUBE_API_KEY and YT_CHANNEL_ID. Returns stored payload or None.
    """
    api_key = _env("YOUTUBE_API_KEY")
    channel_id = _env("YT_CHANNEL_ID")
    channel_url = _env("YT_CHANNEL_URL")

    latest: Optional[Dict[str, Any]] = None
    # Strategy: prefer API if key+id present; else resolve channel_id from URL and use public RSS.
    if api_key and channel_id:
        latest = await _yt_search_latest_video(channel_id, api_key, max_results=5)
    elif channel_id:
        latest = await _feed_latest_video(channel_id)
    elif channel_url:
        resolved = await _resolve_channel_id_from_url(channel_url)
        if resolved:
            latest = await _feed_latest_video(resolved)
        else:
            return None
    else:
        return None
    if not latest:
        return None
    vid = (latest.get("id") or {}).get("videoId")
    snip = latest.get("snippet") or {}
    if not vid:
        return None

    # Pull transcript (best effort)
    transcript = _pluck_transcript(vid)
    summary = None
    watchlist: List[str] = []
    events: List[Dict[str, Any]] = []
    description = (snip.get("description") or None)
    if transcript:
        # crude summary: first ~60 words
        parts = transcript.split()
        summary = " ".join(parts[:60]) + (" …" if len(parts) > 60 else "")
        watchlist = _extract_tickers(transcript)
        events = _extract_events(transcript)
    elif description:
        parts = description.split()
        summary = " ".join(parts[:60]) + (" …" if len(parts) > 60 else "")
        watchlist = _extract_tickers(description)
        events = _extract_events(description)

    payload: Dict[str, Any] = {
        "video_id": vid,
        "title": snip.get("title"),
        "published_at": snip.get("publishedAt"),
        "summary": summary,
        "watchlist": watchlist,
        "events": events,
        "source_url": f"https://www.youtube.com/watch?v={vid}",
        "ts": _now_utc().isoformat(),
        "sentiment": _infer_sentiment(transcript or description or ""),
        "top_watch": (watchlist or [])[0:3],
    }

    async with SessionLocal() as s:
        if await _already_ingested(s, vid):
            return None
        f = Feature(symbol="*", horizon="premarket", payload=payload)
        s.add(f)
        await s.commit()
        await s.refresh(f)
        return payload


async def run_on_startup() -> None:
    """Optional startup task: only runs when ENABLE_PREMARKET_INGEST=1.
    Non-fatal: silently skip on errors.
    """
    flag = _env("ENABLE_PREMARKET_INGEST")
    if not flag or flag == "0":
        return
    try:
        await ingest_premarket_once()
    except Exception:
        # best-effort; do not crash app
        pass
