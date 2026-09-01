import PropTypes from "prop-types";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

function ScoreBadge({ score }) {
  if (score == null) return null;
  const tier = score >= 8 ? "high" : score >= 5 ? "medium" : "low";
  const label = score >= 8 ? "Excellent" : score >= 5 ? "Good" : "Needs Work";
  return (
    <span className={`score-badge ${tier}`}>
      ★ {score}/10 · {label}
    </span>
  );
}

ScoreBadge.propTypes = {
  score: PropTypes.number,
};

ScoreBadge.defaultProps = {
  score: null,
};

export default function ArticleViewer({ article, critique, revisions }) {
  return (
    <div className="glass-card article-viewer fade-up">
      <div className="article-header">
        <span className="article-label">
          📄 Research Article
          {revisions > 0 && (
            <span style={{ marginLeft: 8, color: "var(--accent-from)" }}>
              · {revisions} revision{revisions !== 1 ? "s" : ""}
            </span>
          )}
        </span>
        {critique && <ScoreBadge score={critique.score} />}
      </div>
      <div className="markdown">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{article}</ReactMarkdown>
      </div>
    </div>
  );
}

ArticleViewer.propTypes = {
  article:   PropTypes.string.isRequired,
  revisions: PropTypes.number,
  critique:  PropTypes.shape({
    score: PropTypes.number,
  }),
};

ArticleViewer.defaultProps = {
  revisions: 0,
  critique:  null,
};
