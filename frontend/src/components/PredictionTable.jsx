function formatTime(timestamp) { return new Date(timestamp).toLocaleString() }

function PredictionTable({ predictions }) {
  return <section className="dashboard-panel prediction-table" aria-labelledby="recent-title"><h2 id="recent-title">Recent predictions</h2>
    {predictions.length === 0 ? <p className="chart-empty">No recent analyses yet.</p> : <div className="table-wrap"><table><thead><tr><th>Date/time</th><th>Machine</th><th>Condition</th><th>Risk</th><th>Recommendation</th></tr></thead><tbody>{predictions.map((record) => <tr key={record.id}><td>{formatTime(record.timestamp)}</td><td>{record.machineId || 'Unidentified'}</td><td><span className={`history-condition ${record.condition.toLowerCase()}`}>{record.condition}</span></td><td>{record.failureRisk}%</td><td>{record.recommendation}</td></tr>)}</tbody></table></div>}
  </section>
}

export default PredictionTable
