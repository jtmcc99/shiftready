import { useState, useEffect } from 'react'
import AlertCard from './AlertCard.jsx'

const GENERATE_STAGES = [
  { at: 0,  label: 'Fetching live weather from NWS…' },
  { at: 4,  label: 'Pulling MTA subway alerts…' },
  { at: 8,  label: 'Checking NYC street closures & 311…' },
  { at: 13, label: 'Claude is analyzing conditions…' },
  { at: 20, label: 'Writing your shift briefing…' },
  { at: 27, label: 'Almost done…' },
]

function GeneratingOverlay() {
  const [elapsed, setElapsed] = useState(0)

  useEffect(() => {
    const t = setInterval(() => setElapsed(s => s + 1), 1000)
    return () => clearInterval(t)
  }, [])

  const stage = [...GENERATE_STAGES].reverse().find(s => elapsed >= s.at) || GENERATE_STAGES[0]
  const pct = Math.min((elapsed / 32) * 100, 95)

  return (
    <div className="generating-overlay">
      <div className="generating-card">
        <div className="generating-spinner-wrap">
          <div className="generating-spinner" />
        </div>
        <div className="generating-title">Generating Briefing</div>
        <div className="generating-stage">{stage.label}</div>
        <div className="generating-bar-track">
          <div className="generating-bar-fill" style={{ width: `${pct}%` }} />
        </div>
        <div className="generating-time">~{Math.max(0, 32 - elapsed)}s remaining</div>
      </div>
    </div>
  )
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function conditionsToEmoji(conditions = '') {
  const c = conditions.toLowerCase()
  if (c.includes('thunder')) return '⛈️'
  if (c.includes('snow') || c.includes('blizzard')) return '❄️'
  if (c.includes('fog') || c.includes('mist')) return '🌫️'
  if (c.includes('drizzle')) return '🌦️'
  if (c.includes('rain') || c.includes('shower')) return '🌧️'
  if (c.includes('overcast')) return '☁️'
  if (c.includes('partly') || c.includes('mostly cloudy')) return '⛅'
  if (c.includes('clear') || c.includes('sunny') || c.includes('fair')) return '☀️'
  return '🌡️'
}

function formatTime(isoString) {
  if (!isoString) return ''
  try {
    return new Date(isoString).toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
    })
  } catch {
    return isoString
  }
}

function StatusBadge({ status }) {
  const map = {
    normal:         { label: 'All Clear',       cls: 'badge-success'  },
    moderate_alert: { label: 'Moderate Alert',  cls: 'badge-warning'  },
    high_alert:     { label: 'High Alert',      cls: 'badge-critical' },
  }
  const { label, cls } = map[status] ?? { label: status, cls: 'badge-normal' }
  return <span className={`badge ${cls}`}>{label}</span>
}

function SeverityBar({ status }) {
  const cls = {
    normal:         'severity-bar-normal',
    moderate_alert: 'severity-bar-moderate',
    high_alert:     'severity-bar-critical',
  }[status] ?? 'severity-bar-normal'
  return <div className={`severity-bar ${cls}`} />
}

function LineBadge({ line }) {
  return (
    <span className={`line-badge line-${line}`} title={`${line} Train`}>
      {line}
    </span>
  )
}

function TransitStatusBadge({ status }) {
  const map = {
    suspended:    { label: 'Suspended',    cls: 'badge-critical' },
    delays:       { label: 'Delays',       cls: 'badge-warning'  },
    planned_work: { label: 'Planned Work', cls: 'badge-info'     },
    normal:       { label: 'Normal',       cls: 'badge-success'  },
  }
  const { label, cls } = map[status] ?? { label: status, cls: 'badge-normal' }
  return <span className={`badge ${cls}`}>{label}</span>
}

// ── Main component ────────────────────────────────────────────────────────────

const LINE_COLORS = {
  '1':'#EE352E','2':'#EE352E','3':'#EE352E',
  '4':'#00933C','5':'#00933C','6':'#00933C','7':'#B933AD',
  'A':'#0039A6','C':'#0039A6','E':'#0039A6',
  'B':'#FF6319','D':'#FF6319','F':'#FF6319','M':'#FF6319',
  'G':'#6CBE45','J':'#996633','Z':'#996633','L':'#A7A9AC',
  'N':'#FCCC0A','Q':'#FCCC0A','R':'#FCCC0A','W':'#FCCC0A',
}

function MiniLineBadge({ line }) {
  const bg = LINE_COLORS[line] || '#555'
  const textColor = ['N','Q','R','W'].includes(line) ? '#000' : '#fff'
  return (
    <span style={{
      display:'inline-flex',alignItems:'center',justifyContent:'center',
      width:20,height:20,borderRadius:'50%',background:bg,color:textColor,
      fontWeight:700,fontSize:10,flexShrink:0,
    }}>{line}</span>
  )
}

function StaffingImpact({ risk, onViewStaff }) {
  if (!risk || risk.total_employees === 0) {
    return (
      <div className="section">
        <div className="section-title">Staffing Impact</div>
        <div className="card" style={{ color: 'var(--text-muted)', fontSize: 14 }}>
          No employee commute data on file.{' '}
          <button className="link-btn" onClick={onViewStaff}>Add employees →</button>
        </div>
      </div>
    )
  }

  const atRisk = risk.employees.filter(e => e.risk_level !== 'low')
  const bgMap = { high: 'var(--critical-bg)', moderate: 'var(--warning-bg)', low: 'var(--success-bg)' }
  const colorMap = { high: 'var(--critical)', moderate: 'var(--warning)', low: 'var(--success)' }

  return (
    <div className="section">
      <div className="section-title">Staffing Impact</div>
      <div className="card" style={{ marginBottom: atRisk.length ? 12 : 0 }}>
        <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', gap:8 }}>
          <div>
            <span style={{
              fontWeight:700, fontSize:15,
              color: colorMap[risk.overall_risk],
            }}>
              {risk.overall_risk === 'high' ? '🚨' : risk.overall_risk === 'moderate' ? '⚠️' : '✅'}{' '}
              {risk.summary}
            </span>
          </div>
          <button className="link-btn" onClick={onViewStaff} style={{ whiteSpace:'nowrap' }}>
            View all staff →
          </button>
        </div>
        {risk.data_note && (
          <div style={{ marginTop:8, fontSize:12, color:'var(--text-muted)' }}>{risk.data_note}</div>
        )}
      </div>

      {atRisk.length > 0 && (
        <div style={{ display:'flex', flexDirection:'column', gap:8 }}>
          {atRisk.map(emp => (
            <div key={emp.id} style={{
              background: bgMap[emp.risk_level],
              border: `1px solid ${emp.risk_level === 'high' ? 'var(--critical-border)' : 'var(--warning-border)'}`,
              borderRadius: 'var(--radius-sm)', padding: '12px 14px',
            }}>
              <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', gap:8, flexWrap:'wrap' }}>
                <div style={{ fontWeight:600 }}>{emp.name}
                  <span style={{ fontWeight:400, color:'var(--text-muted)', marginLeft:6, fontSize:13 }}>
                    {emp.role}
                  </span>
                </div>
                <span style={{
                  fontSize:11, fontWeight:700, padding:'2px 8px', borderRadius:20,
                  background: emp.risk_level === 'high' ? 'var(--critical)' : 'var(--warning)',
                  color:'#fff',
                }}>
                  {emp.risk_level === 'high' ? 'HIGH RISK' : 'MODERATE'}
                </span>
              </div>

              <div style={{ display:'flex', gap:4, flexWrap:'wrap', margin:'6px 0' }}>
                {emp.subway_lines?.map(l => <MiniLineBadge key={l} line={l} />)}
                {emp.home_neighborhood && (
                  <span style={{ fontSize:12, color:'var(--text-muted)' }}>
                    {emp.home_neighborhood}{emp.home_borough ? `, ${emp.home_borough}` : ''}
                  </span>
                )}
              </div>

              <div style={{ fontSize:13, color: colorMap[emp.risk_level] }}>
                {emp.risk_reasons.join(' · ')}
                {emp.estimated_delay_min > 0 && ` (~${emp.estimated_delay_min} min delay)`}
              </div>

              {(emp.phone || emp.email) && (
                <div style={{ display:'flex', gap:12, marginTop:6 }}>
                  {emp.phone && <a href={`tel:${emp.phone}`} className="contact-link">📞 {emp.phone}</a>}
                  {emp.email && <a href={`mailto:${emp.email}`} className="contact-link">✉ {emp.email}</a>}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default function TodaysBriefing({ briefing, onGenerate, loading, error, demoMode, staffRisk, onViewStaff }) {
  // ── Generating overlay (shown over empty state and over existing briefing) ──
  if (loading) return <GeneratingOverlay />

  // ── Empty state ──────────────────────────────────────────────────────────
  if (!briefing) {
    return (
      <div className="empty-state">
        <div className="empty-state-icon">📋</div>
        <div className="empty-state-title">No briefing yet</div>
        <div className="empty-state-desc">
          Generate your morning briefing to see today's operational outlook — weather impacts,
          transit disruptions, route closures, and staffing predictions.
          <br /><br />
          <strong>Takes about 30 seconds</strong> while the agent fetches live data and writes your briefing.
        </div>
        {error && <div className="error-banner" style={{ maxWidth: 480, marginBottom: 16 }}>{error}</div>}
        <button className="btn-generate" style={{ maxWidth: 360 }} onClick={onGenerate}>
          {demoMode ? '🎭 Generate Demo Briefing' : '⚡ Generate Today\'s Briefing'}
        </button>
        {demoMode && (
          <div style={{ marginTop: 12, fontSize: '0.8125rem', color: 'var(--text-muted)' }}>
            Demo mode — uses hardcoded scenario (rain, L suspended, Broadway closure)
          </div>
        )}
      </div>
    )
  }

  const {
    shift_date,
    generated_at,
    overall_status,
    executive_summary,
    critical_alerts = [],
    weather_impact = {},
    transit_status = {},
    route_disruptions = [],
    recommendations = [],
    data_quality = {},
    demo,
  } = briefing

  const weatherEmoji = weather_impact.icon || conditionsToEmoji(weather_impact.conditions)
  const affectedLines = (transit_status.lines || []).filter(l => l.status !== 'normal')
  const normalLines = transit_status.lines_normal || []

  return (
    <div>
      {/* Demo banner */}
      {demo && (
        <div className="demo-banner">
          🎭 Demo Mode — This briefing was generated from sample data, not live feeds.
        </div>
      )}

      {error && <div className="error-banner">{error}</div>}

      {/* Status bar */}
      <SeverityBar status={overall_status} />
      <div className="briefing-status-bar">
        <StatusBadge status={overall_status} />
        <span className="briefing-date">{shift_date}</span>
        <span className="briefing-time">Generated at {formatTime(generated_at)}</span>
        <button className="btn" onClick={onGenerate} style={{ marginLeft: 'auto' }}>
          ↻ Regenerate
        </button>
      </div>

      {/* Executive summary */}
      <div className="section">
        <div className="section-title">Executive Summary</div>
        <div className="card">
          <p className="exec-summary">{executive_summary}</p>
        </div>
      </div>

      {/* Critical alerts */}
      {critical_alerts.length > 0 && (
        <div className="section">
          <div className="section-title">Critical Alerts ({critical_alerts.length})</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {critical_alerts.map((alert) => (
              <AlertCard key={alert.id || alert.title} alert={alert} />
            ))}
          </div>
        </div>
      )}

      {/* Weather impact */}
      <div className="section">
        <div className="section-title">Weather Impact</div>
        <div className="card" style={{ marginBottom: 12 }}>
          <div className="weather-main">
            <div className="weather-icon-block">
              <div className="weather-icon">{weatherEmoji}</div>
            </div>
            <div className="weather-details">
              <div style={{ display: 'flex', alignItems: 'baseline', gap: 10 }}>
                <div className="temp-display">{weather_impact.current_temp_f ?? '—'}°F</div>
                <div className="weather-condition">{weather_impact.conditions}</div>
              </div>
              <div className="weather-meta">
                {weather_impact.wind_mph != null && (
                  <span className="weather-meta-item">💨 {weather_impact.wind_mph} mph</span>
                )}
                {weather_impact.precipitation_chance != null && (
                  <span className="weather-meta-item">🌧️ {weather_impact.precipitation_chance}% precip</span>
                )}
                {weather_impact.severity && (
                  <span className={`badge badge-${
                    weather_impact.severity === 'critical' ? 'critical'
                    : weather_impact.severity === 'high' ? 'warning'
                    : weather_impact.severity === 'moderate' ? 'warning'
                    : 'success'
                  }`}>
                    {weather_impact.severity.toUpperCase()}
                  </span>
                )}
              </div>
              {weather_impact.forecast_summary && (
                <div style={{ fontSize: '0.875rem', color: 'var(--text-muted)', marginTop: 6 }}>
                  {weather_impact.forecast_summary}
                </div>
              )}
            </div>
          </div>

          {/* Operational impacts */}
          {(weather_impact.operational_impacts || []).length > 0 && (
            <div className="impact-list" style={{ marginTop: 14 }}>
              {weather_impact.operational_impacts.map((imp, i) => (
                <div key={i} className="impact-item">
                  <span className="impact-bullet">▸</span>
                  <span>{imp}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Hourly forecast */}
        {(weather_impact.hourly_outlook || []).length > 0 && (
          <div className="hourly-row">
            {weather_impact.hourly_outlook.map((h, i) => (
              <div key={i} className="hourly-item">
                <div className="hourly-time">{h.hour}</div>
                <div className="hourly-icon">{conditionsToEmoji(h.conditions)}</div>
                <div className="hourly-temp">{h.temp_f}°</div>
                <div className="hourly-precip">{h.precip_chance}%</div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Transit status */}
      <div className="section">
        <div className="section-title">Transit Status</div>

        {affectedLines.length > 0 && (
          <div className="transit-grid" style={{ marginBottom: 12 }}>
            {affectedLines.map((line) => (
              <div
                key={line.line}
                className={`transit-line-card has-issue status-${line.status}`}
              >
                <LineBadge line={line.line} />
                <div className="transit-line-info">
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4, flexWrap: 'wrap' }}>
                    <span className="transit-line-name">{line.line} Train</span>
                    <TransitStatusBadge status={line.status} />
                  </div>
                  {line.description && (
                    <div className="transit-line-desc">{line.description}</div>
                  )}
                  {(line.zones_affected || []).length > 0 && (
                    <div style={{ marginTop: 5, display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                      {line.zones_affected.map(z => (
                        <span key={z} className="recommendation-zone">{z}</span>
                      ))}
                    </div>
                  )}
                  {line.staffing_impact && (
                    <div style={{ marginTop: 5, fontSize: '0.8125rem', color: 'var(--text-muted)' }}>
                      👥 {line.staffing_impact}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}

        {normalLines.length > 0 && (
          <div className="card">
            <div className="normal-lines-summary">
              <span className="status-dot status-dot-green" />
              <span>{normalLines.length} line{normalLines.length !== 1 ? 's' : ''} operating normally:</span>
              <div className="normal-lines-badges">
                {normalLines.map(l => <LineBadge key={l} line={l} />)}
              </div>
            </div>
          </div>
        )}

        {transit_status.summary && (
          <div style={{ marginTop: 10, fontSize: '0.875rem', color: 'var(--text-muted)' }}>
            {transit_status.summary}
          </div>
        )}
      </div>

      {/* Staffing impact */}
      <StaffingImpact risk={staffRisk} onViewStaff={onViewStaff} />

      {/* Route disruptions */}
      {route_disruptions.length > 0 && (
        <div className="section">
          <div className="section-title">Route Disruptions ({route_disruptions.length})</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {route_disruptions.map((d) => (
              <div key={d.id || d.location} className="disruption-card">
                <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 8, flexWrap: 'wrap' }}>
                  <div className="disruption-location">{d.location}</div>
                  <span className={`badge badge-${d.severity === 'high' ? 'critical' : d.severity === 'moderate' ? 'warning' : 'normal'}`}>
                    {(d.severity || 'low').toUpperCase()}
                  </span>
                </div>
                {d.type && <span className="disruption-type-badge">{d.type.replace('_', ' ')}</span>}
                {(d.zones_affected || []).length > 0 && (
                  <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                    {d.zones_affected.map(z => <span key={z} className="recommendation-zone">{z}</span>)}
                  </div>
                )}
                {d.impact && <div className="disruption-impact">{d.impact}</div>}
                {d.recommendation && (
                  <div className="disruption-recommendation">→ {d.recommendation}</div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recommendations */}
      {recommendations.length > 0 && (
        <div className="section">
          <div className="section-title">Recommended Actions</div>
          <div className="recommendation-list">
            {recommendations.map((rec, i) => (
              <div key={i} className="recommendation-item">
                <div className="recommendation-number">{rec.priority ?? i + 1}</div>
                <div className="recommendation-body">
                  <div className="recommendation-action">{rec.action}</div>
                  {rec.reason && (
                    <div className="recommendation-reason">{rec.reason}</div>
                  )}
                  {rec.zone && (
                    <span className="recommendation-zone">{rec.zone}</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Data quality footer */}
      <div style={{ marginTop: 8 }}>
        <div className="data-quality">
          <div className="data-quality-item">
            <span className={`status-dot ${data_quality.weather_source && data_quality.weather_source !== 'unavailable' ? 'status-dot-green' : 'status-dot-gray'}`} />
            Weather: {data_quality.weather_source ?? 'unknown'}
          </div>
          <div className="data-quality-item">
            <span className={`status-dot ${data_quality.transit_available ? 'status-dot-green' : 'status-dot-red'}`} />
            Transit: {data_quality.transit_available ? 'available' : 'unavailable'}
          </div>
          <div className="data-quality-item">
            <span className={`status-dot ${data_quality.closures_available ? 'status-dot-green' : 'status-dot-red'}`} />
            Closures: {data_quality.closures_available ? 'available' : 'unavailable'}
          </div>
          <div className="data-quality-item">
            <span className={`status-dot ${data_quality.complaints_available ? 'status-dot-green' : 'status-dot-red'}`} />
            311 data: {data_quality.complaints_available ? 'available' : 'unavailable'}
          </div>
        </div>
      </div>
    </div>
  )
}
