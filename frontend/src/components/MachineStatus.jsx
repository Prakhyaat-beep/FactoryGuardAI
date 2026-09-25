function MachineStatus({ machines, onSelectMachine }) {
  return (
    <section className="dashboard-panel machine-status" aria-labelledby="machine-status-title">
      <div className="panel-header-row">
        <h2 id="machine-status-title">Machine fleet status</h2>
        <span className="panel-count">{machines.length} tracked</span>
      </div>
      {machines.length === 0 ? (
        <p className="chart-empty">Add a Machine ID to analyses to monitor the latest status per machine.</p>
      ) : (
        <div className="machine-status-list">
          {machines.map((machine) => (
            <article key={machine.machineId} className="machine-status-card">
              <div className="machine-info">
                <strong>{machine.machineId}</strong>
                <span>Type: {machine.inputs?.type || 'M'} · Tool wear: {machine.inputs?.toolWear ?? 'N/A'} min</span>
              </div>
              <div className="machine-metrics">
                <span className={`history-condition ${machine.condition.toLowerCase()}`}>
                  {machine.condition}
                </span>
                <strong className="machine-risk">{machine.failureRisk}%</strong>
                {onSelectMachine && (
                  <button
                    type="button"
                    className="secondary-button checkup-btn"
                    onClick={() => onSelectMachine(machine.machineId)}
                  >
                    Checkup
                  </button>
                )}
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  )
}

export default MachineStatus
