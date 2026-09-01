// SSE client for the /research endpoint
const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

/**
 * Run a research topic through the pipeline and stream events back.
 *
 * @param {string} topic
 * @param {object} options
 * @param {function} options.onProgress  - called with { step, message } for each progress event
 * @param {function} options.onDone      - called with { article, critique, revisions, errors }
 * @param {function} options.onError     - called with { message }
 * @returns {function} abort - call to cancel the stream
 */
export function streamResearch(topic, { onProgress, onDone, onError }) {
  const controller = new AbortController();

  (async () => {
    let response;
    try {
      response = await fetch(`${API_BASE}/research`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topic }),
        signal: controller.signal,
      });
    } catch (err) {
      if (err.name !== "AbortError") onError?.({ message: err.message });
      return;
    }

    if (!response.ok) {
      onError?.({ message: `Server error ${response.status}` });
      return;
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      let done, value;
      try {
        ({ done, value } = await reader.read());
      } catch {
        break;
      }
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split("\n\n");
      buffer = parts.pop(); // keep incomplete chunk

      for (const part of parts) {
        if (!part.trim()) continue;
        let eventType = "message";
        let dataLine = "";
        for (const line of part.split("\n")) {
          if (line.startsWith("event:")) eventType = line.slice(6).trim();
          if (line.startsWith("data:")) dataLine = line.slice(5).trim();
        }
        if (!dataLine) continue;
        try {
          const payload = JSON.parse(dataLine);
          if (eventType === "progress") onProgress?.(payload);
          else if (eventType === "done") onDone?.(payload);
          else if (eventType === "error") onError?.(payload);
        } catch {
          // malformed JSON — skip
        }
      }
    }
  })();

  return () => controller.abort();
}
