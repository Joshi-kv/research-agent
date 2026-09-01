import asyncio
import json
import logging

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from pipeline.research_pipeline import ResearchPipeline, ResearchState

logger = logging.getLogger(__name__)
router = APIRouter(tags=["research"])


class ResearchRequest(BaseModel):
    topic: str
    provider: str = "google"
    accept_score: int = 8


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


STEP_MESSAGES: dict[str, str] = {
    "search":   "Searching the web for sources…",
    "scrape":   "Scraping and reading sources…",
    "write":    "Writing the first draft…",
    "critique": "Critiquing the draft…",
    "revise":   "Revising based on feedback…",
}


def _run_pipeline(
    req: ResearchRequest,
    queue: asyncio.Queue,
    loop: asyncio.AbstractEventLoop,
) -> None:
    """Run the blocking pipeline in a thread, posting SSE events to the queue."""

    def emit(event: str, data: dict) -> None:
        asyncio.run_coroutine_threadsafe(queue.put(_sse(event, data)), loop)

    class _StreamingPipeline(ResearchPipeline):
        """Subclass that emits SSE progress events instead of rich console output."""

        def _log(self, title: str, content: str = "") -> None:
            title_lower = title.lower()
            for key, msg in STEP_MESSAGES.items():
                if key in title_lower:
                    emit("progress", {"step": key, "message": msg})
                    return
            emit("progress", {"step": "info", "message": title})

    try:
        pipeline = _StreamingPipeline(
            provider=req.provider,
            verbose=True,
            accept_score=req.accept_score,
        )
        state: ResearchState = pipeline.run_state(req.topic)

        critique_data = None
        if state.critique:
            critique_data = {
                "score":           state.critique.score,
                "criticism":       state.critique.criticism,
                "accuracy_points": state.critique.accuracy_points,
                "clarity_issues":  state.critique.clarity_issues,
                "suggestions":     state.critique.suggestions,
            }

        emit("done", {
            "article":   state.article,
            "critique":  critique_data,
            "revisions": state.revisions,
            "errors":    state.errors,
        })
    except Exception as exc:
        logger.exception("pipeline failed")
        emit("error", {"message": str(exc)})
    finally:
        # Sentinel: tells the async generator to stop
        asyncio.run_coroutine_threadsafe(queue.put(None), loop)


@router.post("/research")
async def research(req: ResearchRequest):
    """Stream research pipeline progress as Server-Sent Events."""
    loop = asyncio.get_event_loop()
    queue: asyncio.Queue = asyncio.Queue()

    loop.run_in_executor(None, _run_pipeline, req, queue, loop)

    async def event_stream():
        yield _sse("progress", {"step": "start", "message": f'Starting research on "{req.topic}"…'})
        while True:
            item = await queue.get()
            if item is None:
                break
            yield item

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
