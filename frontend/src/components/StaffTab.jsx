import { useState, useEffect, useRef } from 'react'

const SUBWAY_LINES = ['1','2','3','4','5','6','7','A','C','E','B','D','F','M','G','J','Z','L','N','Q','R','W','S']
const ROLES = ['courier', 'driver', 'dispatcher', 'manager', 'supervisor']
const BOROUGHS = ['Manhattan', 'Brooklyn', 'Queens', 'Bronx', 'Staten Island', 'New Jersey', 'Other']
const MODES = ['subway', 'bus', 'bike', 'walk', 'drive', 'multiple']
const ZONES = ['', 'Uptown', 'Midtown', 'Chelsea', 'East Village', 'Downtown']

const LINE_COLORS = {
  '1':'#EE352E','2':'#EE352E','3':'#EE352E',
  '4':'#00933C','5':'#00933C','6':'#00933C',
  '7':'#B933AD',
  'A':'#0039A6','C':'#0039A6','E':'#0039A6',
  'B':'#FF6319','D':'#FF6319','F':'#FF6319','M':'#FF6319',
  'G':'#6CBE45',
  'J':'#996633','Z':'#996633',
  'L':'#A7A9AC',
  'N':'#FCCC0A','Q':'#FCCC0A','R':'#FCCC0A','W':'#FCCC0A',
  'S':'#808183',
}

function LineBadge({ line, size = 'sm' }) {
  const bg = LINE_COLORS[line] || '#555'
  const textColor = ['N','Q','R','W'].includes(line) ? '#000' : '#fff'
  const sz = size === 'lg' ? 28 : 22
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
      width: sz, height: sz, borderRadius: '50%',
      background: bg, color: textColor,
      fontWeight: 700, fontSize: size === 'lg' ? 13 : 11,
      flexShrink: 0,
    }}>
      {line}
    </span>
  )
}

function RiskBadge({ level }) {
  const map = {
    high:     { label: 'HIGH RISK',     bg: '#fef2f2', color: '#dc2626', border: '#fecaca' },
    moderate: { label: 'MODERATE',      bg: '#fff7ed', color: '#ea580c', border: '#fed7aa' },
    low:      { label: 'ON TIME',        bg: '#f0fdf4', color: '#16a34a', border: '#bbf7d0' },
  }
  const s = map[level] || map.low
  return (
    <span style={{
      padding: '2px 8px', borderRadius: 20, fontSize: 11, fontWeight: 700,
      background: s.bg, color: s.color, border: `1px solid ${s.border}`,
      whiteSpace: 'nowrap',
    }}>
      {s.label}
    </span>
  )
}

const EMPTY_FORM = {
  name: '', role: 'courier', home_neighborhood: '', home_borough: 'Brooklyn',
  subway_lines: [], bus_lines: '', commute_mode: 'subway',
  shift_start: '09:00', zone_assignment: '', phone: '', email: '', notes: '',
}

function EmployeeModal({ employee, onSave, onClose }) {
  const [form, setForm] = useState(employee
    ? { ...employee, bus_lines: (employee.bus_lines || []).join(', ') }
    : { ...EMPTY_FORM }
  )
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const toggleLine = (line) => {
    set('subway_lines', form.subway_lines.includes(line)
      ? form.subway_lines.filter(l => l !== line)
      : [...form.subway_lines, line]
    )
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!form.name.trim()) { setError('Name is required'); return }
    setSaving(true); setError(null)
    const payload = {
      ...form,
      bus_lines: form.bus_lines.split(',').map(s => s.trim()).filter(Boolean),
    }
    try {
      const url = employee ? `/api/employees/${employee.id}` : '/api/employees'
      const method = employee ? 'PUT' : 'POST'
      const res = await fetch(url, {
        method, headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      onSave(await res.json())
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="modal-backdrop" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="modal">
        <div className="modal-header">
          <h2>{employee ? 'Edit Employee' : 'Add Employee'}</h2>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>
        <form className="modal-body" onSubmit={handleSubmit}>
          {error && <div className="form-error">{error}</div>}

          <div className="form-row">
            <div className="form-field">
              <label>Full Name *</label>
              <input value={form.name} onChange={e => set('name', e.target.value)} placeholder="Jane Smith" required />
            </div>
            <div className="form-field">
              <label>Role</label>
              <select value={form.role} onChange={e => set('role', e.target.value)}>
                {ROLES.map(r => <option key={r} value={r}>{r.charAt(0).toUpperCase() + r.slice(1)}</option>)}
              </select>
            </div>
          </div>

          <div className="form-row">
            <div className="form-field">
              <label>Home Neighborhood</label>
              <input value={form.home_neighborhood} onChange={e => set('home_neighborhood', e.target.value)} placeholder="Williamsburg" />
            </div>
            <div className="form-field">
              <label>Borough</label>
              <select value={form.home_borough} onChange={e => set('home_borough', e.target.value)}>
                {BOROUGHS.map(b => <option key={b} value={b}>{b}</option>)}
              </select>
            </div>
          </div>

          <div className="form-field">
            <label>Subway Lines (tap to select)</label>
            <div className="line-picker">
              {SUBWAY_LINES.map(line => (
                <button
                  key={line} type="button"
                  className={`line-pick-btn ${form.subway_lines.includes(line) ? 'selected' : ''}`}
                  style={form.subway_lines.includes(line) ? {
                    background: LINE_COLORS[line] || '#555',
                    color: ['N','Q','R','W'].includes(line) ? '#000' : '#fff',
                    borderColor: LINE_COLORS[line] || '#555',
                  } : {}}
                  onClick={() => toggleLine(line)}
                >
                  {line}
                </button>
              ))}
            </div>
          </div>

          <div className="form-row">
            <div className="form-field">
              <label>Bus Lines (comma-separated)</label>
              <input value={form.bus_lines} onChange={e => set('bus_lines', e.target.value)} placeholder="M14, B38" />
            </div>
            <div className="form-field">
              <label>Commute Mode</label>
              <select value={form.commute_mode} onChange={e => set('commute_mode', e.target.value)}>
                {MODES.map(m => <option key={m} value={m}>{m.charAt(0).toUpperCase() + m.slice(1)}</option>)}
              </select>
            </div>
          </div>

          <div className="form-row">
            <div className="form-field">
              <label>Shift Start</label>
              <input type="time" value={form.shift_start} onChange={e => set('shift_start', e.target.value)} />
            </div>
            <div className="form-field">
              <label>Zone Assignment</label>
              <select value={form.zone_assignment} onChange={e => set('zone_assignment', e.target.value)}>
                <option value="">Unassigned</option>
                {ZONES.filter(Boolean).map(z => <option key={z} value={z}>{z}</option>)}
              </select>
            </div>
          </div>

          <div className="form-row">
            <div className="form-field">
              <label>Phone</label>
              <input value={form.phone} onChange={e => set('phone', e.target.value)} placeholder="555-0100" />
            </div>
            <div className="form-field">
              <label>Email</label>
              <input type="email" value={form.email} onChange={e => set('email', e.target.value)} placeholder="jane@example.com" />
            </div>
          </div>

          <div className="form-field">
            <label>Notes</label>
            <textarea value={form.notes} onChange={e => set('notes', e.target.value)} placeholder="Any additional context..." rows={2} />
          </div>

          <div className="modal-footer">
            <button type="button" className="btn btn-ghost" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-primary" disabled={saving}>
              {saving ? 'Saving…' : employee ? 'Save Changes' : 'Add Employee'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

function UploadModal({ onUpload, onClose }) {
  const [file, setFile] = useState(null)
  const [overwrite, setOverwrite] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const inputRef = useRef()

  const handleUpload = async () => {
    if (!file) return
    setUploading(true); setError(null)
    const form = new FormData()
    form.append('file', file)
    try {
      const res = await fetch(`/api/employees/upload?overwrite=${overwrite}`, {
        method: 'POST', body: form,
      })
      if (!res.ok) { const t = await res.text(); throw new Error(t) }
      const data = await res.json()
      setResult(data)
      onUpload(data.employees)
    } catch (err) {
      setError(err.message)
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="modal-backdrop" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="modal" style={{ maxWidth: 480 }}>
        <div className="modal-header">
          <h2>Upload Employee CSV</h2>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>
        <div className="modal-body">
          {!result ? (
            <>
              <p style={{ color: 'var(--text-muted)', marginBottom: 16 }}>
                Upload a CSV or JSON file with employee commute information.
                Each row becomes one employee record.
              </p>
              <a
                href="/api/employees/template"
                download="shiftready_employees_template.csv"
                className="btn btn-ghost"
                style={{ marginBottom: 16, display: 'inline-block' }}
              >
                ↓ Download CSV Template
              </a>
              <div
                className="file-drop-zone"
                onClick={() => inputRef.current?.click()}
                onDragOver={e => { e.preventDefault(); e.currentTarget.classList.add('drag-over') }}
                onDragLeave={e => e.currentTarget.classList.remove('drag-over')}
                onDrop={e => {
                  e.preventDefault()
                  e.currentTarget.classList.remove('drag-over')
                  const f = e.dataTransfer.files[0]
                  if (f) setFile(f)
                }}
              >
                <input
                  ref={inputRef} type="file" accept=".csv,.json"
                  style={{ display: 'none' }}
                  onChange={e => setFile(e.target.files[0])}
                />
                {file
                  ? <><div style={{ fontSize: 32 }}>📄</div><div>{file.name}</div></>
                  : <><div style={{ fontSize: 32 }}>📂</div><div>Click or drag a .csv or .json file here</div></>
                }
              </div>
              <label style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 12, cursor: 'pointer' }}>
                <input type="checkbox" checked={overwrite} onChange={e => setOverwrite(e.target.checked)} />
                <span style={{ color: 'var(--text-muted)', fontSize: 14 }}>
                  Replace all existing employees (overwrite mode)
                </span>
              </label>
              {error && <div className="form-error" style={{ marginTop: 12 }}>{error}</div>}
              <div className="modal-footer">
                <button className="btn btn-ghost" onClick={onClose}>Cancel</button>
                <button className="btn btn-primary" onClick={handleUpload} disabled={!file || uploading}>
                  {uploading ? 'Uploading…' : 'Upload'}
                </button>
              </div>
            </>
          ) : (
            <div style={{ textAlign: 'center', padding: '16px 0' }}>
              <div style={{ fontSize: 48 }}>✅</div>
              <div style={{ fontSize: 20, fontWeight: 700, marginBottom: 8 }}>
                {result.uploaded} employee{result.uploaded !== 1 ? 's' : ''} imported
              </div>
              <button className="btn btn-primary" onClick={onClose} style={{ marginTop: 16 }}>Done</button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default function StaffTab({ demoMode }) {
  const [employees, setEmployees] = useState([])
  const [risk, setRisk] = useState(null)
  const [loading, setLoading] = useState(true)
  const [riskLoading, setRiskLoading] = useState(false)
  const [showModal, setShowModal] = useState(false)
  const [showUpload, setShowUpload] = useState(false)
  const [editingEmployee, setEditingEmployee] = useState(null)
  const [deleteConfirm, setDeleteConfirm] = useState(null)

  const fetchEmployees = async () => {
    setLoading(true)
    try {
      const res = await fetch('/api/employees')
      setEmployees(await res.json())
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const fetchRisk = async () => {
    setRiskLoading(true)
    try {
      const res = await fetch(`/api/employees/risk?demo=${demoMode}`)
      setRisk(await res.json())
    } catch (err) {
      console.error(err)
    } finally {
      setRiskLoading(false)
    }
  }

  useEffect(() => { fetchEmployees() }, [])
  useEffect(() => { if (employees.length > 0) fetchRisk() }, [employees.length, demoMode])

  const handleSave = (emp) => {
    setEmployees(prev => {
      const exists = prev.find(e => e.id === emp.id)
      return exists ? prev.map(e => e.id === emp.id ? emp : e) : [...prev, emp]
    })
    setShowModal(false)
    setEditingEmployee(null)
    setTimeout(fetchRisk, 300)
  }

  const handleDelete = async (id) => {
    await fetch(`/api/employees/${id}`, { method: 'DELETE' })
    setEmployees(prev => prev.filter(e => e.id !== id))
    setDeleteConfirm(null)
    setTimeout(fetchRisk, 300)
  }

  const handleUpload = (newEmployees) => {
    fetchEmployees()
    setShowUpload(false)
    setTimeout(fetchRisk, 500)
  }

  // Merge risk data into employees for display
  const riskMap = {}
  if (risk) {
    risk.employees.forEach(r => { riskMap[r.id] = r })
  }

  const RISK_ORDER = { high: 0, moderate: 1, low: 2 }
  const displayEmployees = [...employees].sort((a, b) => {
    const ra = riskMap[a.id]?.risk_level || 'low'
    const rb = riskMap[b.id]?.risk_level || 'low'
    return (RISK_ORDER[ra] ?? 2) - (RISK_ORDER[rb] ?? 2)
  })

  return (
    <div className="tab-inner">
      {/* Risk summary banner */}
      {risk && risk.total_employees > 0 && (
        <div className={`risk-banner risk-banner--${risk.overall_risk}`}>
          <div className="risk-banner-left">
            <span className="risk-banner-icon">
              {risk.overall_risk === 'high' ? '🚨' : risk.overall_risk === 'moderate' ? '⚠️' : '✅'}
            </span>
            <div>
              <div className="risk-banner-title">
                {risk.overall_risk === 'high' ? 'Staffing Alert' : risk.overall_risk === 'moderate' ? 'Staffing Watch' : 'Staffing Normal'}
              </div>
              <div className="risk-banner-summary">{risk.summary}</div>
            </div>
          </div>
          <button className="btn btn-ghost btn-sm" onClick={fetchRisk} disabled={riskLoading}>
            {riskLoading ? '…' : '↻ Refresh'}
          </button>
        </div>
      )}

      {/* Toolbar */}
      <div className="staff-toolbar">
        <div className="staff-toolbar-left">
          <h2 className="section-title" style={{ margin: 0 }}>
            Staff ({employees.length})
          </h2>
          {demoMode && <span className="badge badge-demo">Demo Mode</span>}
        </div>
        <div className="staff-toolbar-right">
          <button className="btn btn-ghost" onClick={() => setShowUpload(true)}>
            ↑ Upload CSV
          </button>
          <button className="btn btn-primary" onClick={() => { setEditingEmployee(null); setShowModal(true) }}>
            + Add Employee
          </button>
        </div>
      </div>

      {/* Employee list */}
      {loading ? (
        <div className="empty-state"><div className="loading-spinner" /></div>
      ) : employees.length === 0 ? (
        <div className="empty-state">
          <div style={{ fontSize: 48, marginBottom: 12 }}>👥</div>
          <div style={{ fontWeight: 600, marginBottom: 8 }}>No employees yet</div>
          <div style={{ color: 'var(--text-muted)', marginBottom: 20 }}>
            Add employees with their commute info to enable lateness predictions and alerts.
          </div>
          <div style={{ display: 'flex', gap: 12, justifyContent: 'center' }}>
            <button className="btn btn-ghost" onClick={() => setShowUpload(true)}>↑ Upload CSV</button>
            <button className="btn btn-primary" onClick={() => setShowModal(true)}>+ Add Employee</button>
          </div>
        </div>
      ) : (
        <div className="employee-list">
          {displayEmployees.map(emp => {
            const r = riskMap[emp.id]
            return (
              <div key={emp.id} className={`employee-card ${r ? `employee-card--${r.risk_level}` : ''}`}>
                <div className="employee-card-top">
                  <div className="employee-info">
                    <div className="employee-name">{emp.name}</div>
                    <div className="employee-meta">
                      <span className="badge badge-role">{emp.role}</span>
                      {emp.zone_assignment && (
                        <span className="badge badge-zone">{emp.zone_assignment}</span>
                      )}
                      {emp.shift_start && (
                        <span style={{ color: 'var(--text-muted)', fontSize: 13 }}>
                          ⏰ {emp.shift_start}
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="employee-actions">
                    {r && <RiskBadge level={r.risk_level} />}
                    <button
                      className="btn btn-ghost btn-sm"
                      onClick={() => { setEditingEmployee(emp); setShowModal(true) }}
                    >
                      Edit
                    </button>
                    <button
                      className="btn btn-ghost btn-sm btn-danger"
                      onClick={() => setDeleteConfirm(emp.id)}
                    >
                      ✕
                    </button>
                  </div>
                </div>

                <div className="employee-commute">
                  {/* Home */}
                  <div className="commute-detail">
                    <span className="commute-label">🏠</span>
                    <span>
                      {[emp.home_neighborhood, emp.home_borough].filter(Boolean).join(', ') || '—'}
                    </span>
                  </div>
                  {/* Mode */}
                  <div className="commute-detail">
                    <span className="commute-label">🚌</span>
                    <span style={{ textTransform: 'capitalize' }}>{emp.commute_mode || '—'}</span>
                  </div>
                  {/* Subway lines */}
                  {emp.subway_lines?.length > 0 && (
                    <div className="commute-detail">
                      <span className="commute-label">🚇</span>
                      <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                        {emp.subway_lines.map(l => <LineBadge key={l} line={l} />)}
                      </div>
                    </div>
                  )}
                  {/* Bus lines */}
                  {emp.bus_lines?.length > 0 && (
                    <div className="commute-detail">
                      <span className="commute-label">🚍</span>
                      <span>{emp.bus_lines.join(', ')}</span>
                    </div>
                  )}
                </div>

                {/* Risk details */}
                {r && r.risk_level !== 'low' && (
                  <div className={`employee-risk-detail employee-risk-detail--${r.risk_level}`}>
                    <div className="risk-reasons">
                      {r.risk_reasons.map((reason, i) => (
                        <span key={i} className="risk-reason-tag">⚠ {reason}</span>
                      ))}
                    </div>
                    {r.estimated_delay_min > 0 && (
                      <div style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 4 }}>
                        Estimated delay: ~{r.estimated_delay_min} min
                      </div>
                    )}
                    <div className="risk-recommendation">{r.recommendation}</div>
                    {(r.phone || r.email) && (
                      <div className="contact-row">
                        {r.phone && <a href={`tel:${r.phone}`} className="contact-link">📞 {r.phone}</a>}
                        {r.email && <a href={`mailto:${r.email}`} className="contact-link">✉ {r.email}</a>}
                      </div>
                    )}
                  </div>
                )}

                {deleteConfirm === emp.id && (
                  <div className="delete-confirm">
                    <span>Remove {emp.name}?</span>
                    <button className="btn btn-danger btn-sm" onClick={() => handleDelete(emp.id)}>Remove</button>
                    <button className="btn btn-ghost btn-sm" onClick={() => setDeleteConfirm(null)}>Cancel</button>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}

      {showModal && (
        <EmployeeModal
          employee={editingEmployee}
          onSave={handleSave}
          onClose={() => { setShowModal(false); setEditingEmployee(null) }}
        />
      )}
      {showUpload && (
        <UploadModal onUpload={handleUpload} onClose={() => setShowUpload(false)} />
      )}
    </div>
  )
}
