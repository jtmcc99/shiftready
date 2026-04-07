export default function AlertCard({ alert }) {
  const { severity = 'info', category, title, description, impact, action } = alert

  const severityLabel = {
    critical: 'CRITICAL',
    warning: 'WARNING',
    info: 'INFO',
  }[severity] ?? severity.toUpperCase()

  const severityClass = {
    critical: 'badge-critical',
    warning: 'badge-warning',
    info: 'badge-info',
  }[severity] ?? 'badge-normal'

  return (
    <div className="alert-card" data-severity={severity}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px', flexWrap: 'wrap' }}>
        <span className={`badge ${severityClass}`}>{severityLabel}</span>
        {category && (
          <span className="badge badge-normal" style={{ textTransform: 'capitalize' }}>
            {category.replace('_', ' ')}
          </span>
        )}
      </div>

      <div style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--text)', marginBottom: '6px' }}>
        {title}
      </div>

      {description && (
        <div style={{ fontSize: '0.875rem', color: 'var(--text-muted)', marginBottom: '10px', lineHeight: 1.5 }}>
          {description}
        </div>
      )}

      {impact && (
        <div style={{
          fontSize: '0.875rem',
          color: 'var(--text)',
          marginBottom: '8px',
          display: 'flex',
          gap: '6px',
          alignItems: 'flex-start',
        }}>
          <span>⚠️</span>
          <span><strong>Impact:</strong> {impact}</span>
        </div>
      )}

      {action && (
        <div style={{
          fontSize: '0.875rem',
          color: 'var(--text)',
          background: 'rgba(0,0,0,0.04)',
          borderRadius: '6px',
          padding: '7px 10px',
          display: 'flex',
          gap: '6px',
          alignItems: 'flex-start',
          borderLeft: '2px solid var(--accent)',
        }}>
          <span style={{ color: 'var(--accent)', fontWeight: 700 }}>→</span>
          <span>{action}</span>
        </div>
      )}
    </div>
  )
}
