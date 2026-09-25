import { useState } from 'react'
import ModelPerformance from '../components/ModelPerformance.jsx'
import ExplainableAiPanel from '../components/ExplainableAiPanel.jsx'

function MachineLearningPage({ experiment, loading, error }) {
  const [activeTab, setActiveTab] = useState('comparison')

  return (
    <div className="page-container ml-page">
      <div className="page-header">
        <div>
          <p className="eyebrow">Artificial Intelligence & Model Governance</p>
          <h1>Machine Learning Diagnostics</h1>
          <p>
            Evaluate algorithm benchmark metrics across the AI4I dataset and explore model explainability.
          </p>
        </div>
        <div className="tab-pill-group">
          <button
            type="button"
            className={`tab-pill ${activeTab === 'comparison' ? 'active' : ''}`}
            onClick={() => setActiveTab('comparison')}
          >
            Model Comparison
          </button>
          <button
            type="button"
            className={`tab-pill ${activeTab === 'xai' ? 'active' : ''}`}
            onClick={() => setActiveTab('xai')}
          >
            Explainable AI (XAI)
          </button>
        </div>
      </div>

      {activeTab === 'comparison' && (
        <ModelPerformance
          experiment={experiment}
          loading={loading}
          error={error}
        />
      )}

      {activeTab === 'xai' && (
        <section className="research-section xai-overview-section" aria-labelledby="xai-title">
          <div className="research-heading">
            <div>
              <p className="section-kicker">Transparent AI Framework</p>
              <h2 id="xai-title">Explainable AI & Decision Path Diagnostics</h2>
            </div>
            <span className="model-tag">Tree Path Attribution</span>
          </div>
          <p className="research-intro">
            Industrial machine safety requires full transparency. FactoryGuard AI implements decision-tree path decomposition to compute exact feature attributions for every prediction, explaining precisely how each telemetry signal increases or decreases failure probability.
          </p>

          <div className="xai-concept-grid">
            <article className="xai-card">
              <div className="xai-card-icon">⏱️</div>
              <h3>Tool Wear Progression</h3>
              <p>
                In CNC lathe operations, tool wear accumulates continuously due to abrasive contact with the workpiece. As wear passes 180–220 minutes, friction and thermal stresses spike exponentially, making it the highest-weighted predictive factor for tool failure.
              </p>
            </article>

            <article className="xai-card">
              <div className="xai-card-icon">⚡</div>
              <h3>Torque & Power Bounds</h3>
              <p>
                Torque measures spindle mechanical resistance. High torque combined with dull tooling triggers severe overstrain. Conversely, erratic low torque at high RPMs indicates power failure or loss of drive grip.
              </p>
            </article>

            <article className="xai-card">
              <div className="xai-card-icon">🌡️</div>
              <h3>Thermal Dissipation Delta</h3>
              <p>
                The differential between Process Temperature and Air Temperature indicates heat dissipation efficiency. When the differential drops below nominal thresholds, thermal dissipation failure occurs.
              </p>
            </article>

            <article className="xai-card">
              <div className="xai-card-icon">🔄</div>
              <h3>Rotational Speed Dynamic</h3>
              <p>
                Spindle speed directly affects surface cutting speed. Deviations outside nominal RPM bands compound cutting tool forces and accelerate chatter.
              </p>
            </article>
          </div>

          <div className="xai-sample-preview">
            <h3>Sample Decision Explanation</h3>
            <p className="panel-copy">
              Below is an illustrative model attribution output for a high-load CNC turning run:
            </p>
            <ExplainableAiPanel
              explanation={{
                condition: 'Warning',
                failureRisk: 44.5,
                baseProbability: 50.0,
                summary: 'Elevated Tool wear (195 min) and high Torque (58.4 Nm) are the primary drivers elevating failure risk.',
                topFeatures: [
                  {
                    feature: 'Tool wear',
                    value: '195 min',
                    impact: 28.5,
                    direction: 'increases_risk',
                    interpretation: 'Abrasive tool wear approaching replacement threshold',
                  },
                  {
                    feature: 'Torque',
                    value: '58.4 Nm',
                    impact: 19.2,
                    direction: 'increases_risk',
                    interpretation: 'High cutting resistance from heavy workpiece pass',
                  },
                  {
                    feature: 'Rotational speed',
                    value: '1,380 RPM',
                    impact: 5.4,
                    direction: 'increases_risk',
                    interpretation: 'Lower RPM under cutting load',
                  },
                  {
                    feature: 'Process temperature',
                    value: '309.2 K',
                    impact: -8.6,
                    direction: 'decreases_risk',
                    interpretation: 'Normal cooling within heat dissipation limits',
                  },
                ],
              }}
            />
          </div>
        </section>
      )}
    </div>
  )
}

export default MachineLearningPage
