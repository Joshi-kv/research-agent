import { useState, useRef } from "react";
import "./index.css";
import { streamResearch } from "./api";
import ProgressStepper from "./ProgressStepper";
import ArticleViewer from "./ArticleViewer";
import CritiqueCard from "./CritiqueCard";

const PIPELINE_STEPS = ["search", "scrape", "write", "critique", "revise"];

export default function App() {
  const [topic, setTopic] = useState("");
  const [running, setRunning] = useState(false);
  const [activeStep, setActiveStep] = useState(null);
  const [doneSteps, setDoneSteps] = useState([]);
  const [stepMessages, setStepMessages] = useState({});
  const [result, setResult] = useState(null);   // { article, critique, revisions }
  const [error, setError] = useState(null);
  const abortRef = useRef(null);

  function reset() {
    setActiveStep(null);
    setDoneSteps([]);
    setStepMessages({});
    setResult(null);
    setError(null);
  }

  function handleProgress({ step, message }) {
    if (!PIPELINE_STEPS.includes(step)) return;

    setActiveStep(step);
    setDoneSteps((prev) => {
      const idx = PIPELINE_STEPS.indexOf(step);
      return PIPELINE_STEPS.slice(0, idx).filter((s) => !prev.includes(s)).concat(prev);
    });
    if (message) {
      setStepMessages((prev) => ({ ...prev, [step]: message }));
    }
  }

  function handleDone(payload) {
    // Mark all steps done
    setDoneSteps(PIPELINE_STEPS);
    setActiveStep(null);
    setResult(payload);
    setRunning(false);
  }

  function handleError(payload) {
    setError(payload.message || "Something went wrong.");
    setRunning(false);
  }

  function handleSubmit(e) {
    e.preventDefault();
    if (!topic.trim() || running) return;

    reset();
    setRunning(true);

    abortRef.current = streamResearch(topic.trim(), {
      onProgress: handleProgress,
      onDone:     handleDone,
      onError:    handleError,
    });
  }

  function handleStop() {
    abortRef.current?.();
    setRunning(false);
  }

  const showStepper = running || result || error;

  return (
    <div className="app">
      <div className="content">
        {/* ── Header ── */}
        <header className="header">
          <div className="header-badge">🤖 AI Research Agent</div>
          <h1>Deep Research,<br />Instantly</h1>
          <p>
            Enter any topic. The agent searches the web, scrapes sources,
            writes a draft, critiques it, and delivers a polished article.
          </p>
        </header>

        {/* ── Search ── */}
        <div className="glass-card">
          <form className="search-form" onSubmit={handleSubmit}>
            <div className="search-input-wrap">
              <input
                id="topic-input"
                className="search-input"
                type="text"
                placeholder="e.g. The future of quantum computing…"
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                disabled={running}
                autoFocus
              />
            </div>
            {running ? (
              <button
                type="button"
                className="btn-primary"
                onClick={handleStop}
                style={{ background: "rgba(239,68,68,0.7)" }}
              >
                ✕ Stop
              </button>
            ) : (
              <button
                id="research-btn"
                type="submit"
                className="btn-primary"
                disabled={!topic.trim()}
              >
                🔍 Research
              </button>
            )}
          </form>
        </div>

        {/* ── Error ── */}
        {error && (
          <div className="error-banner fade-up">
            <span>⚠</span>
            <span>{error}</span>
          </div>
        )}

        {/* ── Progress ── */}
        {showStepper && !result && (
          <ProgressStepper
            activeStep={activeStep}
            doneSteps={doneSteps}
            messages={stepMessages}
          />
        )}

        {/* ── Results ── */}
        {result && (
          <>
            <ArticleViewer
              article={result.article}
              critique={result.critique}
              revisions={result.revisions}
            />
            <CritiqueCard critique={result.critique} />
          </>
        )}
      </div>
    </div>
  );
}
