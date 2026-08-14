"""
main.py - FastAPI entrypoint for ARGO FloatChat v4.0 Ocean Intelligence Platform.

Serves:
  - AI Orchestrator & Gemini 2.5 Pro Assistant
  - Real Operational System Telemetry & Health API
  - Data Sources Manager & Live Connectors Dashboard
  - Dataset Previewer & Multi-Format Importers
  - Cache Health & Storage Manager
  - Interactive Plotly Visualizations & Leaflet Maps
  - CSV & Research Report Exporters
"""

import os
import logging
import threading
from pathlib import Path
from typing import List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, Query, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# ─── Logging Setup ────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("argo_floatchat")

# ─── Paths Configuration ──────────────────────────────────────────────────────

BASE_DIR   = Path(__file__).parent
STATIC_DIR = BASE_DIR / "static"
PLOTS_DIR  = STATIC_DIR / "plots"

STATIC_DIR.mkdir(exist_ok=True)
PLOTS_DIR.mkdir(parents=True, exist_ok=True)

PORT = int(os.environ.get("PORT", 8000))

# ─── Startup / Shutdown ───────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info("=" * 60)
    logger.info("  [*] ARGO FloatChat v4.0 — Ocean Intelligence Platform")
    logger.info("=" * 60)
    logger.info("  Dashboard: http://localhost:%d", PORT)
    logger.info("  API Docs:  http://localhost:%d/docs", PORT)
    logger.info("=" * 60)

    try:
        from backend.database import init_db
        init_db()
        from backend.pipeline import run_automatic_data_sync
        threading.Thread(target=run_automatic_data_sync, daemon=True).start()
    except Exception as e:
        logger.warning("[STARTUP] Pipeline initialization note: %s", e)

    yield
    logger.info("[*] ARGO FloatChat platform shutting down.")


# ─── App Definition ───────────────────────────────────────────────────────────

app = FastAPI(
    title="ARGO FloatChat API",
    description="AI-powered oceanographic intelligence platform for Argo profiling float datasets",
    version="4.0.0",
    lifespan=lifespan,
)

# CORS Middleware
origins = os.environ.get("CORS_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if "*" in origins else origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ─── Request Models ───────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)
    history: Optional[List[dict]] = []


class UrlImportRequest(BaseModel):
    url: str = Field(..., description="Public dataset HTTP/HTTPS/FTP URL")


class FileImportRequest(BaseModel):
    filename: str
    content_base64: str


# ─── Core API Routes ──────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_path = STATIC_DIR / "index.html"
    if not index_path.exists():
        return HTMLResponse("<h1>Error: static/index.html missing.</h1>", status_code=404)
    return HTMLResponse(content=index_path.read_text(encoding="utf-8"))


@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    try:
        from backend.chatbot import get_chat_response
        response = get_chat_response(request.message, history=request.history)
        return JSONResponse(content={"ok": True, "response": response})
    except Exception as e:
        logger.exception("Chat processing failure: %s", e)
        return JSONResponse(content={"ok": False, "error": str(e)}, status_code=500)


@app.get("/api/status")
async def status_endpoint():
    try:
        from backend.indexer import get_index_stats
        stats = get_index_stats()
        has_gemini = bool(os.environ.get("GEMINI_API_KEY")) and os.environ.get("GEMINI_API_KEY") != "your_gemini_api_key_here"
        return JSONResponse(content={
            "ok":             True,
            "version":        "4.0.0",
            "index":          stats,
            "gemini_enabled": has_gemini,
            "data_mode":      "argo",
        })
    except Exception as e:
        return JSONResponse(content={"ok": False, "error": str(e)}, status_code=500)


@app.get("/api/system/health")
async def system_health_endpoint():
    """Return real-time system operational telemetry (CPU, RAM, Disk, SQLite, FAISS)."""
    try:
        from backend.connectors import get_system_telemetry
        telemetry = get_system_telemetry()
        return JSONResponse(content={"ok": True, "telemetry": telemetry})
    except Exception as e:
        return JSONResponse(content={"ok": False, "error": str(e)}, status_code=500)


@app.get("/api/floats")
async def floats_endpoint(
    ocean: Optional[str] = Query(None),
    institution: Optional[str] = Query(None),
    variable: Optional[str] = Query(None),
    dac: Optional[str] = Query(None),
    wmo_search: Optional[str] = Query(None, alias="q"),
    bgc_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=200),
):
    try:
        from backend.indexer import list_floats
        floats = list_floats(
            ocean=ocean, institution=institution, variable=variable,
            dac=dac, wmo_search=wmo_search, bgc_only=bgc_only, limit=limit
        )
        return JSONResponse(content={"ok": True, "floats": floats, "count": len(floats)})
    except Exception as e:
        return JSONResponse(content={"ok": False, "error": str(e)}, status_code=500)


@app.get("/api/floats/{wmo}")
async def float_detail_endpoint(wmo: int):
    try:
        from backend.indexer import get_float
        float_info = get_float(wmo)
        if not float_info:
            return JSONResponse(content={"ok": False, "error": f"Float {wmo} not found"}, status_code=404)
        return JSONResponse(content={"ok": True, "float": float_info})
    except Exception as e:
        return JSONResponse(content={"ok": False, "error": str(e)}, status_code=500)


@app.get("/api/floats/{wmo}/profiles")
async def float_profiles_endpoint(wmo: int, limit: int = Query(200, ge=1, le=500)):
    try:
        from backend.indexer import get_float_profiles
        profiles = get_float_profiles(wmo, limit=limit)
        return JSONResponse(content={"ok": True, "wmo": wmo, "profiles": profiles, "count": len(profiles)})
    except Exception as e:
        return JSONResponse(content={"ok": False, "error": str(e)}, status_code=500)


@app.get("/api/floats/{wmo}/trajectory")
async def float_trajectory_endpoint(wmo: int):
    try:
        from backend.indexer import get_float_trajectory
        traj = get_float_trajectory(wmo)
        if not traj:
            return JSONResponse(content={"ok": False, "error": f"No trajectory for float {wmo}"}, status_code=404)
        return JSONResponse(content={"ok": True, **traj})
    except Exception as e:
        return JSONResponse(content={"ok": False, "error": str(e)}, status_code=500)


# ─── Data Sources & Dashboard Routes ──────────────────────────────────────────

@app.get("/api/sources")
@app.get("/api/sources/detailed")
async def sources_status_endpoint():
    """Return health & detailed operational telemetry for all connected data sources."""
    try:
        from backend.connectors import get_all_sources_status, get_system_telemetry
        from backend.database import SessionLocal, DownloadHistoryModel

        session = SessionLocal()
        try:
            history = session.query(DownloadHistoryModel).order_by(DownloadHistoryModel.id.desc()).limit(15).all()
            history_data = [{
                "id": h.id, "file_url": h.file_url, "source": h.source,
                "status": h.status, "size_bytes": h.size_bytes, "downloaded_at": h.downloaded_at
            } for h in history]
        finally:
            session.close()

        sources = get_all_sources_status()
        telemetry = get_system_telemetry()
        return JSONResponse(content={"ok": True, "sources": sources, "history": history_data, "telemetry": telemetry})
    except Exception as e:
        return JSONResponse(content={"ok": False, "error": str(e)}, status_code=500)


@app.post("/api/connectors/{source_id}/sync")
async def connector_sync_endpoint(source_id: str):
    """Trigger background synchronization for a specific data connector."""
    try:
        from backend.pipeline import start_connector_sync
        job_id = start_connector_sync(source_id)
        return JSONResponse(content={
            "ok": True,
            "job_id": job_id,
            "source_id": source_id,
            "message": f"Synchronization workflow initiated for connector '{source_id}'"
        })
    except Exception as e:
        logger.exception("Connector sync trigger failure: %s", e)
        return JSONResponse(content={"ok": False, "error": str(e)}, status_code=500)


@app.get("/api/connectors/{source_id}/sync-status")
async def connector_sync_status_endpoint(source_id: str):
    """Get current sync progress, logs, and metadata status for a connector."""
    try:
        from backend.pipeline import get_connector_sync_status
        status = get_connector_sync_status(source_id)
        return JSONResponse(content={"ok": True, "sync": status})
    except Exception as e:
        return JSONResponse(content={"ok": False, "error": str(e)}, status_code=500)


@app.get("/api/connectors/{source_id}/logs")
async def connector_logs_endpoint(source_id: str, limit: int = Query(50, ge=1, le=200)):
    """Get paginated import audit logs for a connector."""
    try:
        from backend.pipeline import get_connector_import_logs
        logs = get_connector_import_logs(source_id, limit=limit)
        return JSONResponse(content={"ok": True, "source_id": source_id, "logs": logs, "count": len(logs)})
    except Exception as e:
        return JSONResponse(content={"ok": False, "error": str(e)}, status_code=500)


@app.post("/api/connectors/{source_id}/rebuild-faiss")
async def rebuild_faiss_endpoint(source_id: str):
    """Rebuild FAISS vectors for a specific connector source."""
    try:
        from backend.pipeline import rebuild_faiss_for_source
        result = rebuild_faiss_for_source(source_id)
        return JSONResponse(content={"ok": True, **result})
    except Exception as e:
        return JSONResponse(content={"ok": False, "error": str(e)}, status_code=500)


@app.post("/api/connectors/{source_id}/rebuild-sqlite")
async def rebuild_sqlite_endpoint(source_id: str):
    """Rebuild SQLite records for a connector by re-scanning disk files."""
    try:
        from backend.pipeline import rebuild_sqlite_for_source
        result = rebuild_sqlite_for_source(source_id)
        return JSONResponse(content={"ok": True, **result})
    except Exception as e:
        return JSONResponse(content={"ok": False, "error": str(e)}, status_code=500)


@app.post("/api/connectors/{source_id}/cancel")
async def cancel_sync_endpoint(source_id: str):
    """Cancel an in-progress connector sync job."""
    try:
        from backend.pipeline import cancel_connector_sync
        cancelled = cancel_connector_sync(source_id)
        return JSONResponse(content={"ok": True, "cancelled": cancelled, "source_id": source_id})
    except Exception as e:
        return JSONResponse(content={"ok": False, "error": str(e)}, status_code=500)


@app.delete("/api/connectors/{source_id}/data")
async def delete_connector_data_endpoint(source_id: str):
    """Delete all imported data (SQLite records + FAISS vectors) for a connector."""
    try:
        from backend.pipeline import delete_connector_data
        result = delete_connector_data(source_id)
        return JSONResponse(content={"ok": True, **result})
    except Exception as e:
        return JSONResponse(content={"ok": False, "error": str(e)}, status_code=500)


@app.get("/api/system/consistency-audit")
async def consistency_audit_endpoint(source_id: Optional[str] = Query(None)):
    """Run a full platform consistency audit and return a pass/fail report."""
    try:
        from backend.pipeline import run_consistency_audit
        report = run_consistency_audit(source_id=source_id)
        return JSONResponse(content={"ok": True, "report": report})
    except Exception as e:
        return JSONResponse(content={"ok": False, "error": str(e)}, status_code=500)


@app.get("/api/stats/by-source")
async def stats_by_source_endpoint():
    """Return per-source breakdown of floats, profiles, and FAISS vectors."""
    try:
        from backend.indexer import get_index_stats
        from backend.faiss_vector_store import vector_store

        stats = get_index_stats()
        faiss_by_source = vector_store.get_indexed_count_by_source()

        # Merge profile counts and FAISS counts per source
        source_data: dict = {}
        for row in stats.get("by_source", []):
            src = row["source"]
            source_data[src] = source_data.get(src, {"source": src, "profiles": 0, "floats": 0, "faiss_vectors": 0})
            source_data[src]["profiles"] = row["profiles"]
        for row in stats.get("floats_by_source", []):
            src = row["source"]
            if src not in source_data:
                source_data[src] = {"source": src, "profiles": 0, "floats": 0, "faiss_vectors": 0}
            source_data[src]["floats"] = row["floats"]
        for src, count in faiss_by_source.items():
            if src not in source_data:
                source_data[src] = {"source": src, "profiles": 0, "floats": 0, "faiss_vectors": 0}
            source_data[src]["faiss_vectors"] = count

        return JSONResponse(content={
            "ok": True,
            "by_source": list(source_data.values()),
            "totals": {
                "floats": stats["total_floats"],
                "profiles": stats["total_profiles"],
                "faiss_float_vectors": vector_store.get_total_float_vectors(),
                "faiss_total_vectors": vector_store.index.ntotal if hasattr(vector_store, "index") else 0,
            }
        })
    except Exception as e:
        return JSONResponse(content={"ok": False, "error": str(e)}, status_code=500)


@app.post("/api/import/preview")
async def import_preview_endpoint(req: FileImportRequest):
    """Inspect dataset headers and preview metadata before import."""
    try:
        import base64
        from backend.pipeline import TEMP_DIR
        from backend.format_importer import preview_dataset_headers

        dest_path = TEMP_DIR / req.filename
        file_bytes = base64.b64decode(req.content_base64)
        with open(dest_path, "wb") as f:
            f.write(file_bytes)

        preview = preview_dataset_headers(dest_path)
        return JSONResponse(content={"ok": True, "preview": preview})
    except Exception as e:
        return JSONResponse(content={"ok": False, "error": str(e)}, status_code=500)


@app.post("/api/import/url")
async def import_url_endpoint(req: UrlImportRequest):
    try:
        from backend.pipeline import start_public_url_import
        job_id = start_public_url_import(req.url)
        return JSONResponse(content={"ok": True, "job_id": job_id, "message": f"Import started for URL: {req.url}"})
    except Exception as e:
        return JSONResponse(content={"ok": False, "error": str(e)}, status_code=500)


@app.post("/api/import/file")
async def import_file_endpoint(req: FileImportRequest):
    try:
        import base64
        from backend.pipeline import DOWNLOADS_DIR, TEMP_DIR
        from backend.format_importer import import_and_validate_file, generate_ai_dataset_summary
        from backend.indexer import build_index

        dest_path = DOWNLOADS_DIR / req.filename
        file_bytes = base64.b64decode(req.content_base64)
        with open(dest_path, "wb") as f:
            f.write(file_bytes)

        records, val_res = import_and_validate_file(dest_path, TEMP_DIR)
        build_index(verbose=False)

        summary_md = generate_ai_dataset_summary(req.filename, records, val_res)

        return JSONResponse(content={
            "ok": True,
            "filename": req.filename,
            "validation": val_res,
            "imported_records": len(records),
            "summary_md": summary_md,
        })
    except Exception as e:
        return JSONResponse(content={"ok": False, "error": str(e)}, status_code=500)


@app.get("/api/import/status/{job_id}")
async def import_job_status_endpoint(job_id: str):
    from backend.pipeline import get_import_job_status
    status = get_import_job_status(job_id)
    return JSONResponse(content={"ok": True, "job": status})


@app.get("/api/cache/status")
async def cache_status_endpoint():
    from backend.pipeline import get_cache_status
    return JSONResponse(content={"ok": True, "cache": get_cache_status()})


@app.post("/api/cache/purge")
async def cache_purge_endpoint():
    from backend.pipeline import purge_temporary_cache
    count = purge_temporary_cache()
    return JSONResponse(content={"ok": True, "purged_files": count})


@app.get("/api/pipeline/sync")
async def pipeline_sync_endpoint():
    from backend.pipeline import run_automatic_data_sync
    threading.Thread(target=run_automatic_data_sync, daemon=True).start()
    return JSONResponse(content={"ok": True, "message": "Automatic pipeline sync started."})


@app.get("/api/export/csv/{wmo}/{cycle}")
async def export_csv_endpoint(wmo: int, cycle: int, variable: str = "TEMP"):
    try:
        from backend.indexer import get_profile
        from backend.argo_parser import parse_argo_profile
        from backend.reporter import export_profile_csv

        pmeta = get_profile(wmo, cycle)
        if not pmeta:
            raise HTTPException(status_code=404, detail="Profile not found")

        data = parse_argo_profile(pmeta["filepath"])
        values = data.get(variable.lower()) or data.get("temp", [])
        pres = data.get("pres", [])

        csv_str = export_profile_csv(pres, values, variable=variable)
        filename = f"argo_{wmo}_cycle_{cycle}_{variable.lower()}.csv"

        return Response(
            content=csv_str,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        return JSONResponse(content={"ok": False, "error": str(e)}, status_code=500)


@app.get("/api/export/report/{wmo}/{cycle}")
async def export_report_endpoint(wmo: int, cycle: int, variable: str = "TEMP"):
    try:
        from backend.indexer import get_float, get_profile
        from backend.argo_parser import parse_argo_profile
        from backend.ai_orchestrator import generate_expert_scientific_explanation
        from backend.reporter import export_markdown_report

        fl = get_float(wmo) or {"wmo": wmo}
        pmeta = get_profile(wmo, cycle)
        if not pmeta:
            raise HTTPException(status_code=404, detail="Profile not found")

        data = parse_argo_profile(pmeta["filepath"])
        values = data.get(variable.lower()) or data.get("temp", [])
        pres = data.get("pres", [])

        analytics_text = generate_expert_scientific_explanation(variable, pres, values, wmo, cycle, fl.get("ocean", ""))
        p_data = {"date": data.get("date"), "lat": data.get("lat"), "lon": data.get("lon"), "variable": variable, "pres": pres}

        report_md = export_markdown_report(wmo, cycle, fl, p_data, analytics_text)
        filename = f"argo_report_{wmo}_cycle_{cycle}.md"

        return Response(
            content=report_md,
            media_type="text/markdown",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        return JSONResponse(content={"ok": False, "error": str(e)}, status_code=500)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=False, log_level="info")
