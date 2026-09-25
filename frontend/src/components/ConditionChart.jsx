const ORDER = ['Normal', 'Warning', 'Critical']

function ConditionChart({ counts }) {
  const total = ORDER.reduce((sum, condition) => sum + (counts[condition] || 0), 0)
  return <section className="dashboard-panel" aria-labelledby="condition-chart-title"><h2 id="condition-chart-title">Condition distribution</h2>
    {total === 0 ? <p className="chart-empty">No saved predictions yet.</p> : <><div className="condition-chart" role="img" aria-label={`Normal ${counts.Normal || 0}, Warning ${counts.Warning || 0}, Critical ${counts.Critical || 0}`}>
      {ORDER.map((condition) => <div key={condition} className={`chart-segment ${condition.toLowerCase()}`} style={{ width: `${((counts[condition] || 0) / total) * 100}%` }} />)}
    </div><div className="chart-legend">{ORDER.map((condition) => <span key={condition}><i className={condition.toLowerCase()} />{condition}: <strong>{counts[condition] || 0}</strong></span>)}</div></>}
  </section>
}

export default ConditionChart
