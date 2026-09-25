function ParameterField({ name, label, unit, hint, min, max, step, value, error, onChange }) {
  const inputId = `${name}-input`
  return <div className="form-field"><label htmlFor={inputId}>{label} <span>{unit}</span></label><input id={inputId} name={name} type="number" min={min} max={max} step={step} value={value} onChange={onChange} aria-describedby={`${name}-help ${name}-error`} aria-invalid={Boolean(error)} /><small id={`${name}-help`}>{hint}</small>{error && <span className="field-error" id={`${name}-error`}>{error}</span>}</div>
}
export default ParameterField
