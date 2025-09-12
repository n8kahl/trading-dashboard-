from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import os
import re
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import create_engine
from app.models import Base
from app.services.paper_engine import SubmitIntent, submit, positions, pnl_for_date
from app.services.decision_artifacts import build_artifact

router = APIRouter(prefix="/paper", tags=["paper"])

_engine = None
_SessionLocal = None

def _normalize_db_url(url: str) -> str:
    if url.startswith("postgres://"):
        url = "postgresql+psycopg2://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg2://" + url[len("postgresql://"):]
    if "sslmode=" not in url:
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}sslmode=require"
    return url

def _ensure_db():
    global _engine, _SessionLocal
    if _engine is None or _SessionLocal is None:
        url = os.getenv("DATABASE_URL")
        if not url:
            raise RuntimeError("DATABASE_URL not set")
        url = _normalize_db_url(url)
        _engine = create_engine(url, pool_pre_ping=True, pool_size=5, max_overflow=5)
        Base.metadata.create_all(bind=_engine)
        _SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False)
    return _engine, _SessionLocal

def get_db():
    _engine, SessionLocal = _ensure_db()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/health")
def paper_health():
    try:
        _ensure_db()
        return {"ok": True, "db": "ready"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

class SubmitReq(BaseModel):
    symbol: str = Field(..., description="Ticker symbol")
    side: str = Field(..., description="buy or sell", pattern="^(buy|sell)$")
    qty: int = Field(..., gt=0)
    entry_px: Optional[float] = Field(None, description="Required for buy")
    exit_px: Optional[float] = Field(None, description="Required for sell")
    session: Optional[str] = Field(None, description="open/mid/power")
    strategy_id: Optional[str] = None
    score: Optional[float] = None
    expected_r: Optional[float] = None
    stop_r: Optional[float] = None
    tp_r: Optional[float] = None

@router.post("/submit")
def paper_submit(req: SubmitReq, db: Session = Depends(get_db)):
    intent = SubmitIntent(**req.dict())
    res = submit(db, intent)
    if not res.get("ok"):
        raise HTTPException(status_code=400, detail=res.get("error","submit failed"))
    return res

@router.get("/positions")
def paper_positions(db: Session = Depends(get_db)):
    return {"positions": positions(db)}

@router.get("/pnl")
def paper_pnl(date: Optional[str] = None, db: Session = Depends(get_db)):
    return pnl_for_date(db, date)

class ArtifactReq(BaseModel):
    symbol: str
    strategy: str
    score: float
    expected_r: float
    features: Dict[str, Any] = {}

@router.post("/artifact-log")
def paper_artifact(req: ArtifactReq):
    return {"ok": True, "artifact": build_artifact(req.symbol, req.strategy, req.score, req.expected_r, req.features)}
