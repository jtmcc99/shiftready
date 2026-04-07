export default function BriefingHistory({ history, onSelectBriefing, loading }) {
  function formatDateTime(isoString) {
    if (!isoString) return ''
    try {
      const d = new Date(isoString)
      return d.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
        hour12: true,
      })
    } catch {
      return isoString
    }
  }

  function statusBadgeClass(status) {
    switch (status) {
      case 'high_alert':     return 'badge-critical'
      case 'moderate_alert': return 'badge-warning'
      case 'normal':         return 'badge-success'
      default:               return 'badge-normal'
    }
  }

  function statusLabel(status) {
    switch (status) {
      case 'high_alert':     return 'High Alert'
      case 'moderate_alert': return 'Moderate'
      case 'normal':         return 'Normal'
      default:               return status ?? 'Unknown'
    }
  }

  if (loading) {
    return (
      <div className="loading-center">
        <span className="loading-spinner" />
        <span>Loading briefing…</span>
      </div>
    )
  }

  if (!history || history.length === 0) {
    return (
      <div className="empty-state">
        <div className="empty-state-icon">🗂️</div>
        <div className="empty-state-title">No briefings generated yet</div>
        <div className="empty-state-desc">
          Your past briefings will appear here once you generate your first one from the
          Today's Briefing tab.
        </div>
      </div>
    )
  }

  return (
    <div>
      <div style={{
        fontSize: '0.875rem',
        color: 'var(--text-muted)',
        marginBottom: 14,
        fontWeight: 500,
      }}>
        {history.length} briefing{history.length !== 1 ? 's' : ''} on record
      </div>

      <div className="history-list">
        {history.map((item) => (
          <div
            key={item.id}
            className="history-item"
            onClick={() => onSelectBriefing(item.id)}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => e.key === 'Enter' && onSelectBriefing(item.id)}
          >
            {/* Left: date + summary */}
            <div className="history-item-main">
              <div className="history-item-date">
                {item.shift_date || formatDateTime(item.generated_at)}
                <span style={{ fontWeight: 400, color: 'var(--text-light)', marginLeft: 6, fontSize: '0.8125rem' }}>
                  {item.shift_date ? `· ${formatDateTime(item.generated_at)}` : ''}
                </span>
              </div>
              <div className="history-item-summary">
                {item.executive_summary || 'No summary available.'}
              </div>
            </div>

            {/* Right: badges */}
            <div className="history-item-meta">
              <span className={`badge ${statusBadgeClass(item.overall_status)}`}>
                {statusLabel(item.overall_status)}
              </span>
              {item.demo && (
                <span className="badge badge-demo">Demo</span>
              )}
              {item.critical_count > 0 && (
                <span className="history-count">
                  {item.critical_count} alert{item.critical_count !== 1 ? 's' : ''}
                </span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
