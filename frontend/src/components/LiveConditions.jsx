import { useEffect, useRef, useState } from 'react'

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

function minutesAgo(isoString) {
  if (!isoString) return null
  try {
    const diff = (Date.now() - new Date(isoString).getTime()) / 60000
    if (diff < 1) return 'just now'
    if (diff < 60) return `${Math.round(diff)} min ago`
    return `${Math.round(diff / 60)} hr ago`
  } catch {
    return null
  }
}

function LineBadge({ line }) {
  return (
    <span className={`line-badge line-${line}`} title={`${line} Train`}>
      {line}
    </span>
  )
}

function lineStatusClass(status) {
  switch (status) {
    case 'suspended':    return 'status-dot-red'
    case 'delays':       return 'status-dot-yellow'
    case 'planned_work': return 'status-dot-yellow'
    default:             return 'status-dot-green'
  }
}

const ALL_LINES = ['1','2','3','4','5','6','7','A','C','E','B','D','F','M','G','L','N','Q','R','W','J','Z']

// ── Component ─────────────────────────────────────────────────────────────────

export default function LiveConditions({ conditions, onRefresh, loading, demoMode }) {
  const [tick, setTick] = useState(0)
  const intervalRef = useRef(null)

  // Auto-refresh every 5 minutes
  useEffect(() => {
    intervalRef.current = setInterval(() => {
      onRefresh()
      setTick(t => t + 1)
    }, 5 * 60 * 1000)
    return () => clearInterval(intervalRef.current)
  }, [onRefresh])

  const weather    = conditions?.weather
  const transit    = conditions?.transit
  const closures   = conditions?.closures
  const complaints = conditions?.complaints_311
  const fetchedAt  = conditions?.fetched_at

  // Build complaint type counts
  const complaintCounts = {}
  if (complaints?.complaints) {
    for (const c of complaints.complaints) {
      complaintCounts[c.complaint_type] = (complaintCounts[c.complaint_type] ?? 0) + 1
    }
  }
  const sortedComplaints = Object.entries(complaintCounts).sort((a, b) => b[1] - a[1])
  const maxCount = sortedComplaints[0]?.[1] ?? 1

  return (
    <div>
      {/* Demo banner */}
      {demoMode && (
        <div className="demo-banner">
          🎭 Demo Mode — Showing hardcoded sample data, not live feeds.
        </div>
      )}

      {/* Last updated + refresh */}
      <div className="last-updated-bar">
        <span className="last-updated-text">
          {fetchedAt ? `Last updated: ${minutesAgo(fetchedAt)}` : 'Not yet loaded'}
        </span>
        <button className="btn" onClick={onRefresh} disabled={loading}>
          {loading
            ? <><span className="loading-spinner loading-spinner-sm" /> Refreshing…</>
            : '↻ Refresh'}
        </button>
      </div>

      {loading && !conditions && (
        <div className="loading-center">
          <span className="loading-spinner" />
          <span>Loading conditions…</span>
        </div>
      )}

      {/* ── Weather ── */}
      {weather && (
        <div className="section">
          <div className="section-title">
            Current Weather
            {weather.source && (
              <span style={{ marginLeft: 8, fontWeight: 400, fontSize: '0.75rem', color: 'var(--text-light)', textTransform: 'none', letterSpacing: 0 }}>
                via {weather.source}
              </span>
            )}
          </div>

          <div className="card" style={{ marginBottom: 12 }}>
            <div className="weather-main">
              <div className="weather-icon-block">
                <div className="weather-icon">
                  {weather.current?.icon_emoji || conditionsToEmoji(weather.current?.conditions)}
                </div>
              </div>
              <div className="weather-details">
                <div style={{ display: 'flex', alignItems: 'baseline', gap: 10 }}>
                  <div className="temp-display">{weather.current?.temp_f ?? '—'}°F</div>
                  <div className="weather-condition">{weather.current?.conditions ?? 'Unknown'}</div>
                </div>
                <div className="weather-meta">
                  {weather.current?.wind_mph != null && (
                    <span className="weather-meta-item">💨 {weather.current.wind_mph} mph {weather.current.wind_direction || ''}</span>
                  )}
                  {weather.current?.precipitation_chance != null && (
                    <span className="weather-meta-item">🌧️ {weather.current.precipitation_chance}% precip</span>
                  )}
                  {weather.current?.humidity != null && (
                    <span className="weather-meta-item">💧 {weather.current.humidity}% humidity</span>
                  )}
                </div>
                {weather.today?.high_f != null && (
                  <div style={{ fontSize: '0.875rem', color: 'var(--text-muted)', marginTop: 4 }}>
                    High {weather.today.high_f}°F · Low {weather.today.low_f}°F
                  </div>
                )}
                {weather.today?.detailed_forecast && (
                  <div style={{ fontSize: '0.8125rem', color: 'var(--text-muted)', marginTop: 6, lineHeight: 1.5 }}>
                    {weather.today.detailed_forecast}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* 8-hour hourly forecast */}
          {(weather.hourly || []).length > 0 && (
            <div className="hourly-row">
              {weather.hourly.slice(0, 8).map((h, i) => (
                <div key={i} className="hourly-item">
                  <div className="hourly-time">{h.time}</div>
                  <div className="hourly-icon">{conditionsToEmoji(h.conditions)}</div>
                  <div className="hourly-temp">{h.temp_f}°</div>
                  <div className="hourly-precip">{h.precipitation_chance}%</div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── Subway status ── */}
      <div className="section">
        <div className="section-title">Subway Status</div>
        {transit?.error ? (
          <div className="card" style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>
            ⚠️ {transit.summary || 'Transit data temporarily unavailable'}
          </div>
        ) : (
          <>
            <div className="transit-grid">
              {ALL_LINES.map(line => {
                const lineData = transit?.lines?.[line]
                const status = lineData?.status ?? 'normal'
                const alerts = lineData?.alerts ?? []
                return (
                  <div
                    key={line}
                    style={{
                      display: 'flex',
                      alignItems: 'flex-start',
                      gap: 10,
                      background: 'var(--card)',
                      border: '1px solid var(--border)',
                      borderRadius: 'var(--radius-sm)',
                      padding: '10px 12px',
                      borderLeft: status !== 'normal'
                        ? `3px solid ${status === 'suspended' ? 'var(--critical)' : '#f59e0b'}`
                        : undefined,
                    }}
                  >
                    <LineBadge line={line} />
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <span className={`status-dot ${lineStatusClass(status)}`} />
                        <span style={{ fontSize: '0.875rem', fontWeight: 600, color: 'var(--text)' }}>
                          {line} Train
                        </span>
                        {status !== 'normal' && (
                          <span className={`badge ${status === 'suspended' ? 'badge-critical' : 'badge-warning'}`} style={{ fontSize: '0.625rem' }}>
                            {status === 'suspended' ? 'SUSPENDED' : status === 'delays' ? 'DELAYS' : 'PLANNED WORK'}
                          </span>
                        )}
                      </div>
                      {alerts[0]?.header && (
                        <div style={{
                          fontSize: '0.75rem',
                          color: 'var(--text-muted)',
                          marginTop: 3,
                          overflow: 'hidden',
                          display: '-webkit-box',
                          WebkitLineClamp: 2,
                          WebkitBoxOrient: 'vertical',
                        }}>
                          {alerts[0].header}
                        </div>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
            {transit?.summary && (
              <div style={{ marginTop: 10, fontSize: '0.8125rem', color: 'var(--text-muted)' }}>
                {transit.summary}
              </div>
            )}
          </>
        )}
      </div>

      {/* ── Street closures ── */}
      <div className="section">
        <div className="section-title">Street Closures</div>
        {closures?.error ? (
          <div className="card" style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>
            ⚠️ Street closure data temporarily unavailable
          </div>
        ) : (closures?.closures || []).length === 0 ? (
          <div className="card" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span className="status-dot status-dot-green" />
            <span style={{ fontSize: '0.9rem', color: 'var(--success)' }}>
              No active closures found in database
            </span>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {closures.closures.map((c, i) => (
              <div key={i} className="card" style={{ padding: '12px 16px' }}>
                <div style={{ fontWeight: 600, fontSize: '0.9375rem', marginBottom: 4 }}>
                  {c.on_street}
                  {c.from_street && ` from ${c.from_street}`}
                  {c.to_street && ` to ${c.to_street}`}
                </div>
                <div style={{ fontSize: '0.8125rem', color: 'var(--text-muted)', display: 'flex', gap: 16, flexWrap: 'wrap' }}>
                  {c.purpose && <span>📋 {c.purpose}</span>}
                  {c.borough && <span>📍 {c.borough}</span>}
                  {c.start_date && (
                    <span>
                      🕐 {new Date(c.start_date).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })}
                      {c.end_date && ` – ${new Date(c.end_date).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })}`}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ── 311 Activity ── */}
      <div className="section">
        <div className="section-title">
          311 Activity — Manhattan (Last 24h)
          {complaints?.count != null && (
            <span style={{ marginLeft: 8, fontWeight: 400, fontSize: '0.75rem', color: 'var(--text-light)', textTransform: 'none', letterSpacing: 0 }}>
              {complaints.count} complaints
            </span>
          )}
        </div>
        {complaints?.error ? (
          <div className="card" style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>
            ⚠️ 311 data temporarily unavailable
          </div>
        ) : sortedComplaints.length === 0 ? (
          <div className="card" style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>
            No relevant complaints in the last 24 hours
          </div>
        ) : (
          <div className="card">
            <div className="complaints-chart">
              {sortedComplaints.map(([type, count]) => (
                <div key={type} className="complaint-bar-row">
                  <div className="complaint-bar-label" title={type}>{type}</div>
                  <div className="complaint-bar-track">
                    <div
                      className="complaint-bar-fill"
                      style={{ width: `${Math.round((count / maxCount) * 100)}%` }}
                    />
                  </div>
                  <div className="complaint-bar-count">{count}</div>
                </div>
              ))}
            </div>

            {/* Recent incidents */}
            {(complaints.complaints || []).length > 0 && (
              <div style={{ marginTop: 16, borderTop: '1px solid var(--border)', paddingTop: 14 }}>
                <div style={{ fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--text-muted)', marginBottom: 8 }}>
                  Recent Incidents
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  {complaints.complaints.slice(0, 5).map((c, i) => (
                    <div key={i} style={{ fontSize: '0.8125rem', color: 'var(--text-muted)', display: 'flex', gap: 8 }}>
                      <span style={{ color: 'var(--text-light)', flexShrink: 0 }}>
                        {c.created_date ? new Date(c.created_date).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' }) : ''}
                      </span>
                      <span>
                        <span style={{ color: 'var(--text)', fontWeight: 500 }}>{c.complaint_type}</span>
                        {c.incident_address && ` · ${c.incident_address}`}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
