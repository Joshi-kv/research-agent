import PropTypes from "prop-types";

function Section({ title, items, color }) {
  if (!items || items.length === 0) return null;
  return (
    <div className="critique-section">
      <div className="critique-section-title" style={{ color }}>
        {title}
      </div>
      <ul>
        {items.map((item, i) => (
          <li key={i}>{item}</li>
        ))}
      </ul>
    </div>
  );
}

Section.propTypes = {
  title: PropTypes.string.isRequired,
  items: PropTypes.arrayOf(PropTypes.string),
  color: PropTypes.string.isRequired,
};

Section.defaultProps = {
  items: [],
};

export default function CritiqueCard({ critique }) {
  if (!critique) return null;

  const scoreColor =
    critique.score >= 8
      ? "var(--success)"
      : critique.score >= 5
      ? "var(--warning)"
      : "var(--error)";

  return (
    <details className="glass-card critique-card fade-up">
      <summary className="critique-toggle">
        <div className="critique-toggle-inner">
          <span style={{ fontSize: "1.1rem" }}>🧐</span>
          <span style={{ fontWeight: 600, fontSize: "0.95rem" }}>
            Critic&apos;s Feedback
          </span>
          <span
            style={{
              fontSize: "0.82rem",
              fontWeight: 600,
              color: scoreColor,
              background: `${scoreColor}18`,
              padding: "2px 10px",
              borderRadius: 100,
              border: `1px solid ${scoreColor}40`,
            }}
          >
            {critique.score}/10
          </span>
        </div>
        <span className="critique-arrow">▶</span>
      </summary>

      <div className="critique-sections">
        {critique.criticism && (
          <div className="critique-overview">{critique.criticism}</div>
        )}
        <Section
          title="⚠ Accuracy Issues"
          items={critique.accuracy_points}
          color="var(--error)"
        />
        <Section
          title="💬 Clarity Issues"
          items={critique.clarity_issues}
          color="var(--warning)"
        />
        <Section
          title="✅ Suggestions"
          items={critique.suggestions}
          color="var(--success)"
        />
      </div>
    </details>
  );
}

CritiqueCard.propTypes = {
  critique: PropTypes.shape({
    score:           PropTypes.number.isRequired,
    criticism:       PropTypes.string,
    accuracy_points: PropTypes.arrayOf(PropTypes.string),
    clarity_issues:  PropTypes.arrayOf(PropTypes.string),
    suggestions:     PropTypes.arrayOf(PropTypes.string),
  }),
};

CritiqueCard.defaultProps = {
  critique: null,
};
