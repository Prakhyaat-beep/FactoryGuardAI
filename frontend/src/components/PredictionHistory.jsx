function formatTimestamp(timestamp) {
  return new Date(timestamp).toLocaleString()
}

function PredictionHistory({ history, loading, error, onOpen }) {
  return <section className="history-section" aria-labelledby="history-title">
    <div className="history-heading"><div><p className="section-kicker">Persistent records</p><h2 id="history-title">Prediction history</h2></div><span>{history.length} saved</span></div>
    {loading && <div className="history-message">Loading prediction history…</div>}
    {!loading && error && <div className="history-message history-error" role="alert">Unable to load history. {error}</div>}
    {!loading && !error && history.length === 0 && <div className="history-message">No saved predictions yet. Analyze a machine to create the first record.</div>}
    {!loading && !error && history.length > 0 && <div className="history-list">
      {history.map((record) => <article className="history-row" key={record.id}>
        <div><strong>{record.machineId || 'Unidentified machine'}</strong><span>{formatTimestamp(record.timestamp)}</span></div>
        <span className={`history-condition ${record.condition.toLowerCase()}`}>{record.condition}</span>
        <strong>{record.failureRisk}%</strong>
        <p>{record.recommendation}</p>
        <button className="history-button" type="button" onClick={() => onOpen(record)}>View details</button>
      </article>)}
    </div>}
  </section>
}

export default PredictionHistory
