"""Per-run store for content that tools fetch.

Agents decide *what* to fetch and *whether it was enough*; they should not be
the transport for the bytes. A tool that returns 22k chars of scraped text
forces the model to re-emit all of it as output tokens - that single habit was
~62s of a ~112s run. So tools write the full content here and return a short
receipt instead.

The store is bound to a ContextVar rather than passed as an argument, so agents
stay constructed once and reused, and two concurrent API requests each see their
own store.
"""

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field


@dataclass
class Document:
    url: str
    text: str
    strategy: str
    title: str = ""

    @property
    def chars(self) -> int:
        return len(self.text)


@dataclass
class ResearchStore:
    results: list[dict] = field(default_factory=list)
    documents: dict[str, Document] = field(default_factory=dict)
    failures: dict[str, str] = field(default_factory=dict)

    def add_results(self, results: list[dict]) -> None:
        seen = {r["url"] for r in self.results}
        self.results.extend(r for r in results if r.get("url") not in seen)

    def add_document(self, doc: Document) -> None:
        self.documents[doc.url] = doc
        self.failures.pop(doc.url, None)

    def add_failure(self, url: str, error: str) -> None:
        self.failures[url] = error

    def as_research_text(self) -> str:
        """Assemble every scraped document into the writer's input."""
        return "\n\n".join(
            f"## Source: {doc.title or doc.url}\nURL: {doc.url}\n\n{doc.text}"
            for doc in self.documents.values()
        )

    @property
    def total_chars(self) -> int:
        return sum(doc.chars for doc in self.documents.values())


_current: ContextVar[ResearchStore | None] = ContextVar("research_store", default=None)


@contextmanager
def use_store(store: ResearchStore):
    """Bind a store for the duration of one pipeline run."""
    token = _current.set(store)
    try:
        yield store
    finally:
        _current.reset(token)


def current_store() -> ResearchStore:
    store = _current.get()
    if store is None:
        raise RuntimeError(
            "No ResearchStore bound. Wrap the call in `with use_store(store):` - "
            "store-backed tools cannot run outside a pipeline run."
        )
    return store
