from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.jobs.scheduler import start_scheduler
from app.routers import (
    activity, auth, evaluations, files, groups, milestones, notes, notifications, projects, tasks, teacher, users,
)

@asynccontextmanager
async def lifespan(_: FastAPI):
    scheduler = start_scheduler()
    yield
    if scheduler:
        scheduler.shutdown(wait=False)


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    # Bearer tokens, not cookies, so credentials are not needed (and * + credentials is invalid)
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_: Request, exc: RequestValidationError):
    """Flatten Pydantic errors into the {"detail": "message"} shape used everywhere else."""
    parts = []
    for err in exc.errors():
        loc = ".".join(str(p) for p in err["loc"] if p not in ("body", "query", "path"))
        msg = err["msg"].removeprefix("Value error, ")
        parts.append(f"{loc}: {msg}" if loc else msg)
    return JSONResponse(status_code=422, content={"detail": "; ".join(parts)})


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}


# groups.router first so /groups/my is matched before /groups/{group_id}
for r in (auth, groups, projects, tasks, milestones, files, notes, activity, evaluations, notifications, teacher, users):
    app.include_router(r.router, prefix=settings.api_prefix)
