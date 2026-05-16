"""Enumerate Claude Code sessions from ~/.claude/projects/."""
from __future__ import annotations

import datetime as dt
import json
import os
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterator

PROJECTS_DIR = Path.home() / ".claude" / "projects"


@dataclass
class Session:
    session_id: str
    cwd: str
    project_dir: str
    path: str
    mtime: float
    size: int
    start_ts: str | None = None
    end_ts: str | None = None
    title: str | None = None
    first_prompt: str | None = None
    last_prompt: str | None = None
    user_msg_count: int = 0

    @property
    def project_name(self) -> str:
        return Path(self.cwd).name or self.cwd

    def to_dict(self) -> dict:
        return asdict(self)


def _decode_project_dir(name: str) -> str:
    if name.startswith("-"):
        return "/" + name[1:].replace("-", "/")
    return name.replace("-", "/")


def _is_real_prompt(text: str) -> bool:
    if not text:
        return False
    t = text.strip()
    if not t:
        return False
    for bad in ("<command-", "<local-command-", "<system-reminder"):
        if t.startswith(bad):
            return False
    if "Messages below were generated" in t:
        return False
    return True


def _extract_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        out = []
        for c in content:
            if isinstance(c, dict) and c.get("type") == "text":
                out.append(c.get("text", ""))
        return "\n".join(out)
    return ""


def parse_session_file(path: Path) -> Session | None:
    try:
        st = path.stat()
    except OSError:
        return None
    project_dir = path.parent.name
    sess = Session(
        session_id=path.stem,
        cwd=_decode_project_dir(project_dir),
        project_dir=project_dir,
        path=str(path),
        mtime=st.st_mtime,
        size=st.st_size,
    )
    try:
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                try:
                    j = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if j.get("cwd"):
                    sess.cwd = j["cwd"]
                ts = j.get("timestamp")
                if ts:
                    if sess.start_ts is None or ts < sess.start_ts:
                        sess.start_ts = ts
                    if sess.end_ts is None or ts > sess.end_ts:
                        sess.end_ts = ts
                t = j.get("type")
                if t == "ai-title":
                    sess.title = j.get("aiTitle") or sess.title
                elif t == "user" and not j.get("isSidechain") and not j.get("isMeta"):
                    text = _extract_text((j.get("message") or {}).get("content", ""))
                    if _is_real_prompt(text):
                        sess.user_msg_count += 1
                        snip = text.strip()
                        if not sess.first_prompt:
                            sess.first_prompt = snip
                        sess.last_prompt = snip
    except OSError:
        return None
    return sess


def list_sessions(projects_dir: Path = PROJECTS_DIR) -> list[Session]:
    if not projects_dir.exists():
        return []
    out: list[Session] = []
    for jsonl in projects_dir.rglob("*.jsonl"):
        s = parse_session_file(jsonl)
        if s is not None:
            out.append(s)
    out.sort(key=lambda s: s.mtime, reverse=True)
    return out


def iter_session_paths(projects_dir: Path = PROJECTS_DIR) -> Iterator[Path]:
    if not projects_dir.exists():
        return iter(())
    return projects_dir.rglob("*.jsonl")


def session_display_title(s: Session, maxlen: int = 60) -> str:
    """Best human-readable label."""
    candidate = s.title or s.first_prompt or s.session_id[:8]
    candidate = " ".join(candidate.split())
    if len(candidate) > maxlen:
        candidate = candidate[: maxlen - 1] + "…"
    return candidate
