function SummaryCard({ label, value, tone = 'neutral', icon: IconComponent }) {
  return (
    <article className={`summary-card ${tone}`}>
      <div className="summary-card-header">
        <span>{label}</span>
        {IconComponent && <IconComponent className="summary-card-icon" size={16} aria-hidden="true" />}
      </div>
      <strong>{value}</strong>
    </article>
  )
}

export default SummaryCard
