import asyncio
import json
import logging
import time
from contextlib import asynccontextmanager, suppress
from datetime import UTC
from uuid import uuid4

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.chaos.routes import router as chaos_router
from app.config import Settings
from app.db import database
from app.http_guard import HttpGuard
from app.integrations.llm import GroqProvider
from app.integrations.n8n import IntegrationError, N8nClient
from app.investigation.routes import router as investigation_router
from app.investigation.service import Investigator
from app.models import Heartbeat
from app.monitoring.models import Execution, Incident, Workflow
from app.monitoring.routes import router as monitoring_router
from app.monitoring.service import Monitor
from app.repairs.routes import router as repair_router
from app.repairs.service import Repairer
from app.schemas import HeartbeatInput
from app.security import admin, ingest
from app.warroom import router as warroom_router
from app.worker_lock import worker_lock

logger = logging.getLogger("agentsentinel")


def create_app(settings: Settings | None = None) -> FastAPI:
    if not logger.handlers:
        logger.addHandler(logging.StreamHandler())
    logger.setLevel(logging.INFO)
    logger.propagate = False
    config = settings or Settings()
    engine, sessions = database(config.database_url)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        with worker_lock(config.database_url):
            async with httpx.AsyncClient(
                timeout=config.http_timeout_seconds, follow_redirects=False, trust_env=False
            ) as http:
                app.state.n8n = N8nClient(
                    http, config.n8n_base_url, config.n8n_api_key.get_secret_value()
                )
                app.state.groq = GroqProvider(
                    http,
                    config.groq_api_key.get_secret_value(),
                    config.groq_model,
                    timeout=config.groq_timeout_seconds,
                    secrets=tuple(
                        getattr(config, key).get_secret_value()
                        for key in (
                            "admin_api_token",
                            "ingest_api_token",
                            "n8n_api_key",
                            "groq_api_key",
                            "n8n_write_api_key",
                            "snapshot_encryption_key",
                        )
                    ),
                )
                app.state.monitor = Monitor(sessions, app.state.n8n, config)
                app.state.investigator = Investigator(
                    sessions, app.state.n8n, app.state.groq, config
                )
                writer = N8nClient(
                    http, config.n8n_base_url, config.n8n_write_api_key.get_secret_value()
                )
                app.state.repairer = Repairer(sessions, app.state.n8n, writer, config)
                repair_task = asyncio.create_task(app.state.repairer.run())
                analysis_task = asyncio.create_task(app.state.investigator.run())
                task = asyncio.create_task(app.state.monitor.run())
                try:
                    yield
                finally:
                    repair_task.cancel()
                    with suppress(asyncio.CancelledError):
                        await repair_task
                    analysis_task.cancel()
                    with suppress(asyncio.CancelledError):
                        await analysis_task
                    task.cancel()
                    with suppress(asyncio.CancelledError):
                        await task
            engine.dispose()

    app = FastAPI(
        title="AgentSentinel",
        version="0.6.0",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.state.settings, app.state.engine = config, engine
    app.state.sessions = sessions
    app.include_router(monitoring_router)
    app.include_router(investigation_router)
    app.include_router(repair_router)
    app.include_router(chaos_router)
    app.include_router(warroom_router)
    app.state.chaos_lock = asyncio.Lock()
    app.add_middleware(HttpGuard)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=config.hosts, www_redirect=False)

    @app.middleware("http")
    async def request_log(request: Request, call_next):
        request_id, start = str(uuid4()), time.monotonic()
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        logger.info(
            json.dumps(
                {
                    "request_id": request_id,
                    "method": request.method,
                    "status": response.status_code,
                    "duration_ms": round((time.monotonic() - start) * 1000, 2),
                }
            )
        )
        return response

    @app.exception_handler(RequestValidationError)
    async def invalid_input(_request, _exc):
        return JSONResponse(status_code=422, content={"detail": "Invalid request fields"})

    @app.exception_handler(SQLAlchemyError)
    async def database_error(_request, _exc):
        return JSONResponse(
            status_code=503, content={"detail": "Database unavailable or unmigrated"}
        )

    @app.get("/health/live")
    def live():
        return {"status": "alive"}

    @app.get("/health/ready")
    def ready():
        with engine.connect() as connection:
            revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar()
            if revision != "0005":
                raise HTTPException(503, "Database migration required")
            connection.execute(select(Heartbeat.id).limit(1))
        return {"status": "ready", "database": "reachable"}

    @app.get("/api/v1/status", dependencies=[Depends(admin)])
    def status():
        with sessions() as session:
            count = session.scalar(select(func.count()).select_from(Heartbeat))
            latest = session.scalar(select(Heartbeat).order_by(Heartbeat.id.desc()).limit(1))
            monitored = session.scalar(
                select(func.count()).select_from(Workflow).where(Workflow.enabled.is_(True))
            )
            incident_count = session.scalar(select(func.count()).select_from(Incident))
            execution_count = session.scalar(select(func.count()).select_from(Execution))
        return {
            "service": "AgentSentinel",
            "version": "0.6.0",
            "database": "reachable",
            "kill_switch": app.state.repairer.paused(),
            "monitoring_enabled": config.monitoring_enabled and monitored > 0,
            "monitored_workflows": monitored,
            "incident_count": incident_count,
            "execution_count": execution_count,
            "repairs_enabled": config.repairs_enabled and not app.state.repairer.paused(),
            "integrations": {
                "n8n": bool(config.n8n_api_key.get_secret_value()),
                "groq": bool(config.groq_api_key.get_secret_value()),
            },
            "heartbeat_count": count,
            "last_heartbeat": latest.received_at.replace(tzinfo=UTC).isoformat()
            if latest
            else None,
        }

    @app.post("/api/v1/integrations/{provider}/check", dependencies=[Depends(admin)])
    async def check(provider: str):
        if provider not in {"n8n", "groq"}:
            raise HTTPException(404, "Unknown integration")
        try:
            await getattr(app.state, provider).check()
        except IntegrationError as exc:
            raise HTTPException(502, str(exc)) from None
        return {"provider": provider, "status": "connected"}

    @app.post("/api/v1/heartbeat", dependencies=[Depends(ingest)])
    def heartbeat(body: HeartbeatInput):
        with sessions() as session:
            session.add(Heartbeat(**body.model_dump()))
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                return {"status": "already_received"}
        return {"status": "recorded"}

    return app
