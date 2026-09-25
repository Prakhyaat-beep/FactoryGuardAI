import { useState } from 'react'
import { motion } from 'framer-motion'
import { Zap, History, Sliders, Play } from 'lucide-react'
import ParameterField from '../components/ParameterField.jsx'
import PredictionResult from '../components/PredictionResult.jsx'
import PredictionHistory from '../components/PredictionHistory.jsx'

const NUMERIC_FIELDS = [
  { name: 'airTemperature', label: 'Air temperature', unit: 'K', min: 250, max: 400, step: '0.1', hint: '250–400 K' },
  { name: 'processTemperature', label: 'Process temperature', unit: 'K', min: 250, max: 450, step: '0.1', hint: '250–450 K' },
  { name: 'rotationalSpeed', label: 'Rotational speed', unit: 'RPM', min: 1, max: 20000, step: '1', hint: '1–20,000 RPM' },
  { name: 'torque', label: 'Torque', unit: 'Nm', min: 0, max: 1000, step: '0.1', hint: '0–1,000 Nm' },
  { name: 'toolWear', label: 'Tool wear', unit: 'min', min: 0, max: 10000, step: '1', hint: '0–10,000 min' },
]

function PredictionsPage({
  form,
  errors,
  prediction,
  apiError,
  isLoading,
  history,
  historyState,
  userMachines = [],
  onChange,
  onSelectMachine,
  onSubmit,
  onReset,
  onOpenHistoryRecord,
}) {
  const [activeTab, setActiveTab] = useState('quick')

  const handleMachineSelect = (event) => {
    const selectedId = event.target.value
    if (onSelectMachine) {
      onSelectMachine(selectedId)
    } else {
      onChange({ target: { name: 'machineId', value: selectedId } })
    }
  }

  return (
    <motion.div
      className="page-container predictions-page"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      <div className="page-header">
        <div>
          <div className="eyebrow-badge">
            <Zap size={14} />
            <span>Ad-hoc Analysis</span>
          </div>
          <h1>Failure Risk Prediction</h1>
          <p className="hero-subtext">
            Evaluate custom telemetry inputs or review past records.
          </p>
        </div>
        <div className="tab-pill-group">
          <button
            type="button"
            className={`tab-pill ${activeTab === 'quick' ? 'active' : ''}`}
            onClick={() => setActiveTab('quick')}
          >
            <Sliders size={14} style={{ display: 'inline', marginRight: '6px' }} />
            <span>Quick Prediction</span>
          </button>
          <button
            type="button"
            className={`tab-pill ${activeTab === 'history' ? 'active' : ''}`}
            onClick={() => setActiveTab('history')}
          >
            <History size={14} style={{ display: 'inline', marginRight: '6px' }} />
            <span>Prediction History ({history.length})</span>
          </button>
        </div>
      </div>

      {activeTab === 'quick' && (
        <section className="prediction-area" aria-label="Machine prediction workspace">
          <section className="workspace">
            <form className="panel parameter-panel" onSubmit={onSubmit} noValidate>
              <div className="panel-heading">
                <div>
                  <p className="section-kicker">Telemetry Parameters</p>
                  <h2>Input Configuration</h2>
                </div>
                <span className="model-tag">Scikit-learn Model</span>
              </div>
              <p className="panel-copy">
                Select one of your assigned machines or enter custom telemetry parameters to start continuous prediction & simulation.
              </p>
              <div className="field-grid">
                <div className="form-field">
                  <label htmlFor="machineId">
                    Target Machine
                  </label>
                  {userMachines && userMachines.length > 0 ? (
                    <select
                      id="machineId"
                      name="machineId"
                      value={form.machineId}
                      onChange={handleMachineSelect}
                      aria-describedby="machineId-help machineId-error"
                    >
                      <option value="">-- Select Assigned Machine --</option>
                      {userMachines.map((m) => (
                        <option key={m.machineId} value={m.machineId}>
                          {m.machineId} ({m.condition || 'Online'})
                        </option>
                      ))}
                    </select>
                  ) : (
                    <input
                      id="machineId"
                      name="machineId"
                      type="text"
                      maxLength="100"
                      value={form.machineId}
                      onChange={onChange}
                      placeholder="e.g. CNC-LATHE-01"
                      aria-describedby="machineId-help machineId-error"
                    />
                  )}
                  <small id="machineId-help">Assign prediction & initialize continuous simulation stream</small>
                  {errors.machineId && (
                    <span className="field-error" id="machineId-error">{errors.machineId}</span>
                  )}
                </div>
                {NUMERIC_FIELDS.map((field) => (
                  <ParameterField
                    key={field.name}
                    {...field}
                    value={form[field.name]}
                    error={errors[field.name]}
                    onChange={onChange}
                  />
                ))}
                <div className="form-field">
                  <label htmlFor="type">Product Variant</label>
                  <select
                    id="type"
                    name="type"
                    value={form.type}
                    onChange={onChange}
                    aria-describedby="type-help type-error"
                  >
                    <option value="L">L — Low quality variant</option>
                    <option value="M">M — Medium quality variant</option>
                    <option value="H">H — High quality variant</option>
                  </select>
                  <small id="type-help">Tool quality grade</small>
                  {errors.type && (
                    <span className="field-error" id="type-error">{errors.type}</span>
                  )}
                </div>
              </div>
              {apiError && (
                <div className="api-error" role="alert">
                  <strong>Prediction failed:</strong> {apiError}
                </div>
              )}
              <div className="form-actions">
                <button className="primary-button" type="submit" disabled={isLoading}>
                  <Play size={14} style={{ marginRight: '6px' }} />
                  <span>{isLoading ? 'Analyzing…' : 'Run Prediction'}</span>
                </button>
                <button
                  className="secondary-button"
                  type="button"
                  onClick={onReset}
                  disabled={isLoading}
                >
                  Reset
                </button>
              </div>
            </form>
            <PredictionResult prediction={prediction} />
          </section>
        </section>
      )}

      {activeTab === 'history' && (
        <PredictionHistory
          history={history}
          loading={historyState.loading}
          error={historyState.error}
          onOpen={onOpenHistoryRecord}
        />
      )}
    </motion.div>
  )
}

export default PredictionsPage
