const MODEL_NAMES = {
  logistic_regression: 'Logistic Regression',
  decision_tree: 'Decision Tree',
  random_forest: 'Random Forest',
  svm: 'Support Vector Machine (SVM)',
  gradient_boosting: 'Gradient Boosting Classifier',
}

const MODEL_COLORS = {
  logistic_regression: '#e74c3c',
  decision_tree: '#e5b364',
  random_forest: '#3498db',
  svm: '#9b59b6',
  gradient_boosting: '#83e4bb',
}

const METRICS = [
  ['precision', 'Precision'],
  ['recall', 'Recall'],
  ['f1_score', 'F1-score'],
  ['roc_auc', 'ROC-AUC'],
]

function percentage(value) {
  if (value === null || value === undefined) return 'N/A'
  return `${(Number(value) * 100).toFixed(2)}%`
}

function ModelPerformance({ experiment, loading, error }) {
  if (loading) return <section className="research-message">Loading model experiment results…</section>
  if (error) return <section className="research-message history-error" role="alert">{error}</section>
  if (!experiment) return null

  const models = Object.entries(experiment.models)
  const selectedKey = experiment.selected_model
  const selectedName = MODEL_NAMES[selectedKey] || selectedKey

  return (
    <section className="research-section" aria-labelledby="research-title">
      <div className="research-heading">
        <div>
          <p className="section-kicker">Multi-Model Governance</p>
          <h2 id="research-title">5-Model Performance Comparison</h2>
        </div>
        <span className="model-tag">Production Model: {selectedName}</span>
      </div>
      <p className="research-intro">
        All 5 models are evaluated under identical conditions: the same 80/20 stratified split, standard preprocessing pipeline, and random state. The production model is dynamically selected by the highest test-set F1-score on the minority machine-failure class (1), balancing false alarms against missed breakdowns.
      </p>

      {/* Comparative Metric Bar Chart */}
      <div className="metric-chart">
        <h3>Class 1 (Failure) Benchmark Metrics</h3>
        {METRICS.map(([key, label]) => (
          <div className="metric-row" key={key}>
            <span>{label}</span>
            <div>
              {models.map(([name, result]) => {
                const val = result[key]
                const widthPercent = val != null ? Math.min(100, Math.max(0, val * 100)) : 0
                const color = MODEL_COLORS[name] || '#15556b'
                const displayName = MODEL_NAMES[name] || name

                return (
                  <i
                    key={name}
                    className={name}
                    style={{ width: `${widthPercent}%`, backgroundColor: color }}
                    title={`${displayName} - ${label}: ${percentage(val)}`}
                  />
                )
              })}
            </div>
          </div>
        ))}
        <div className="metric-key">
          {models.map(([name]) => (
            <span key={name} className={name} style={{ borderLeft: `3px solid ${MODEL_COLORS[name] || '#83e4bb'}` }}>
              {MODEL_NAMES[name] || name}
            </span>
          ))}
        </div>
      </div>

      {/* Comprehensive Benchmark Table */}
      <div className="performance-table-wrap">
        <table className="performance-table">
          <thead>
            <tr>
              <th>Model</th>
              <th>Accuracy</th>
              <th>Precision</th>
              <th>Recall</th>
              <th>F1 Score</th>
              <th>ROC-AUC</th>
              <th>Train Time</th>
              <th>Inference / Record</th>
            </tr>
          </thead>
          <tbody>
            {models.map(([name, result]) => {
              const isSelected = name === selectedKey
              const displayName = MODEL_NAMES[name] || name

              return (
                <tr key={name} className={isSelected ? 'selected-model' : ''}>
                  <td>
                    <strong>{displayName}</strong>
                    {isSelected && <small>★ Selected by F1</small>}
                  </td>
                  <td>{percentage(result.accuracy)}</td>
                  <td>{percentage(result.precision)}</td>
                  <td>{percentage(result.recall)}</td>
                  <td>
                    <strong>{percentage(result.f1_score)}</strong>
                  </td>
                  <td>{percentage(result.roc_auc)}</td>
                  <td>{result.training_time_seconds}s</td>
                  <td>{result.inference_time_per_record_ms} ms</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {/* Held-Out Confusion Matrices Grid */}
      <div className="confusion-grid">
        <h3>Held-out Confusion Matrices (N = {experiment.test_rows || 2000})</h3>
        {models.map(([name, result]) => (
          <article key={name} className={name === selectedKey ? 'selected-matrix-card' : ''}>
            <div className="matrix-title-row">
              <strong>{MODEL_NAMES[name] || name}</strong>
              {name === selectedKey && <span className="selected-badge">Top F1</span>}
            </div>
            <div
              className="confusion-matrix"
              aria-label={`${MODEL_NAMES[name]} confusion matrix: true negatives ${result.confusion_matrix[0][0]}, false positives ${result.confusion_matrix[0][1]}, false negatives ${result.confusion_matrix[1][0]}, true positives ${result.confusion_matrix[1][1]}`}
            >
              <span>TN<br /><b>{result.confusion_matrix[0][0]}</b></span>
              <span>FP<br /><b>{result.confusion_matrix[0][1]}</b></span>
              <span>FN<br /><b>{result.confusion_matrix[1][0]}</b></span>
              <span>TP<br /><b>{result.confusion_matrix[1][1]}</b></span>
            </div>
          </article>
        ))}
      </div>
    </section>
  )
}

export default ModelPerformance
