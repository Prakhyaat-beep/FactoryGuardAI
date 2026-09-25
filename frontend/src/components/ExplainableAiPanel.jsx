import { Sparkles, Layers } from 'lucide-react'

function ExplainableAiPanel({ explanation }) {
  if (!explanation) {
    return (
      <section className="dashboard-panel xai-panel">
        <div className="panel-header-row">
          <h2 style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Sparkles size={18} />
            <span>Prediction Drivers</span>
          </h2>
          <span className="model-tag">Model XAI</span>
        </div>
        <p className="chart-empty">Awaiting telemetry reading for feature impact attribution.</p>
      </section>
    )
  }

  const { condition, failureRisk, summary, topFeatures = [] } = explanation
  const maxImpact = Math.max(...topFeatures.map((item) => Math.abs(item.impact || 0)), 10)

  return (
    <section className="dashboard-panel xai-panel" aria-labelledby="xai-panel-title">
      <div className="panel-header-row">
        <div>
          <h2 id="xai-panel-title" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Sparkles size={18} />
            <span>Prediction Drivers</span>
          </h2>
          <p className="panel-subtitle">Model Decision Attribution (Tree Path Analysis)</p>
        </div>
        <span className={`telemetry-condition ${condition ? condition.toLowerCase() : 'normal'}`}>
          {condition || 'Normal'} · {failureRisk}% Risk
        </span>
      </div>

      {summary && (
        <div className="xai-summary-box">
          <strong>Key Finding:</strong> {summary}
        </div>
      )}

      <div className="xai-features-container">
        <h3>Top Contributing Parameters</h3>
        <div className="xai-feature-list">
          {topFeatures.map((item, index) => {
            const isRisk = item.direction === 'increases_risk'
            const percentWidth = Math.min(100, Math.round((Math.abs(item.impact || 0) / maxImpact) * 100))

            return (
              <article key={item.feature || index} className="xai-feature-row">
                <div className="xai-feature-meta">
                  <span className="xai-feature-name">{item.feature}</span>
                  <span className="xai-feature-value">{item.value}</span>
                </div>

                <div className="xai-bar-wrap">
                  <div
                    className={`xai-bar ${isRisk ? 'risk-increasing' : 'risk-decreasing'}`}
                    style={{ width: `${percentWidth}%` }}
                    title={`${item.feature}: ${item.impact > 0 ? '+' : ''}${item.impact}% impact`}
                  />
                </div>

                <div className="xai-impact-label">
                  <span className={isRisk ? 'impact-up' : 'impact-down'}>
                    {item.impact > 0 ? `+${item.impact}% risk` : `${item.impact}% risk`}
                  </span>
                  {item.interpretation && (
                    <small className="xai-interpretation">{item.interpretation}</small>
                  )}
                </div>
              </article>
            )
          })}
        </div>
      </div>
    </section>
  )
}

export default ExplainableAiPanel
