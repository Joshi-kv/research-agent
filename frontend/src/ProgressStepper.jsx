import PropTypes from "prop-types";

const STEPS = [
  { key: "search",   label: "Web Search",    emoji: "🔍" },
  { key: "scrape",   label: "Scrape Sources", emoji: "🌐" },
  { key: "write",    label: "Write Draft",    emoji: "✍️" },
  { key: "critique", label: "Critique",       emoji: "🧐" },
  { key: "revise",   label: "Revise Article", emoji: "✨" },
];

function getStatus(stepKey, activeStep, doneSteps) {
  if (doneSteps.includes(stepKey)) return "done";
  if (activeStep === stepKey) return "active";
  return "pending";
}

export default function ProgressStepper({ activeStep, doneSteps, messages }) {
  return (
    <div className="glass-card stepper fade-up">
      <div className="stepper-title">Pipeline Progress</div>
      {STEPS.map((step) => {
        const status = getStatus(step.key, activeStep, doneSteps);
        const msg = messages[step.key] || "";
        return (
          <div key={step.key} className={`step ${status}`}>
            <div className="step-icon">
              {status === "active" ? (
                <div className="spinner" />
              ) : status === "done" ? (
                "✓"
              ) : (
                step.emoji
              )}
            </div>
            <div className="step-body">
              <div className="step-label">{step.label}</div>
              {msg && <div className="step-message">{msg}</div>}
            </div>
          </div>
        );
      })}
    </div>
  );
}

ProgressStepper.propTypes = {
  activeStep: PropTypes.string,
  doneSteps:  PropTypes.arrayOf(PropTypes.string).isRequired,
  messages:   PropTypes.objectOf(PropTypes.string).isRequired,
};

ProgressStepper.defaultProps = {
  activeStep: null,
};
