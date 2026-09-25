function RiskChart({ trends }) {
  if (trends.length < 2) return <section className="dashboard-panel"><h2>Risk trend</h2><p className="chart-empty">At least two saved predictions are needed to show a risk trend.</p></section>
  const width = 520
  const height = 180
  const padding = 28
  const points = trends.map((item, index) => {
    const x = padding + (index * (width - padding * 2)) / (trends.length - 1)
    const y = height - padding - (Number(item.failureRisk) * (height - padding * 2)) / 100
    return `${x},${y}`
  }).join(' ')
  return <section className="dashboard-panel" aria-labelledby="risk-chart-title"><h2 id="risk-chart-title">Risk trend</h2><svg className="risk-chart" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Chronological model-derived failure risk trend, from zero to one hundred percent"><line x1={padding} y1={padding} x2={padding} y2={height - padding} /><line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} /><text x="2" y={padding + 4}>100%</text><text x="8" y={height - padding}>0%</text><polyline points={points} /></svg><p className="chart-caption">Chronological model-derived risk indicator from saved analyses.</p></section>
}

export default RiskChart
