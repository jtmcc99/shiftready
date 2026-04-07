import { useState, useEffect, useCallback } from 'react'
import TodaysBriefing from './components/TodaysBriefing.jsx'
import LiveConditions from './components/LiveConditions.jsx'
import BriefingHistory from './components/BriefingHistory.jsx'
import StaffTab from './components/StaffTab.jsx'

export default function App() {
  const [activeTab, setActiveTab] = useState('briefing')
  const [demoMode, setDemoMode] = useState(false)
  const [currentBriefing, setCurrentBriefing] = useState(null)
  const [conditions, setConditions] = useState(null)
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [conditionsLoading, setConditionsLoading] = useState(false)
  const [staffRisk, setStaffRisk] = useState(null)

  // ── Fetch conditions ──────────────────────────────────────────────────────
  const fetchConditions = useCallback(async (demo = demoMode) => {
    setConditionsLoading(true)
    try {
      const res = await fetch(`/api/conditions?demo=${demo}`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      setConditions(data)
    } catch (err) {
      console.error('Failed to fetch conditions:', err)
    } finally {
      setConditionsLoading(false)
    }
  }, [demoMode])

  // ── Fetch history ─────────────────────────────────────────────────────────
  const fetchHistory = useCallback(async () => {
    try {
      const res = await fetch('/api/briefing/history')
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      setHistory(await res.json())
    } catch (err) {
      console.error('Failed to fetch history:', err)
    }
  }, [])

  // ── Fetch staff risk ──────────────────────────────────────────────────────
  const fetchStaffRisk = useCallback(async (demo = demoMode) => {
    try {
      const res = await fetch(`/api/employees/risk?demo=${demo}`)
      if (!res.ok) return
      setStaffRisk(await res.json())
    } catch (err) {
      console.error('Failed to fetch staff risk:', err)
    }
  }, [demoMode])

  // ── On mount ──────────────────────────────────────────────────────────────
  useEffect(() => {
    fetchConditions(false)
    fetchHistory()
    fetchStaffRisk(false)
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // ── Toggle demo mode ──────────────────────────────────────────────────────
  const handleToggleDemo = (isDemo) => {
    setDemoMode(isDemo)
    fetchConditions(isDemo)
    fetchStaffRisk(isDemo)
  }

  // ── Generate briefing ─────────────────────────────────────────────────────
  const handleGenerateBriefing = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`/api/briefing/generate?demo=${demoMode}`, { method: 'POST' })
      if (!res.ok) {
        const body = await res.text()
        throw new Error(`HTTP ${res.status}: ${body}`)
      }
      const briefing = await res.json()
      setCurrentBriefing(briefing)
      setActiveTab('briefing')
      await fetchHistory()
      fetchStaffRisk(demoMode)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [demoMode, fetchHistory])

  // ── Select historical briefing ────────────────────────────────────────────
  const handleSelectBriefing = useCallback(async (id) => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`/api/briefing/${id}`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const briefing = await res.json()
      setCurrentBriefing(briefing)
      setActiveTab('briefing')
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [])

  // ── Current weather summary for header ────────────────────────────────────
  const weatherPill = conditions?.weather?.current
    ? `${conditions.weather.current.icon_emoji} ${conditions.weather.current.temp_f}°F · ${conditions.weather.current.conditions}`
    : null

  return (
    <div className="app">
      {/* ── Header ── */}
      <header className="header">
        <div className="header-left">
          <div className="header-brand">🚚 ShiftReady</div>
          <div className="header-subtitle">Daily Operations Briefing</div>
        </div>

        <div className="header-meta">
          {weatherPill && (
            <div className="header-weather-pill">{weatherPill}</div>
          )}
          <div className="mode-toggle">
            <button
              className={`mode-toggle-btn ${!demoMode ? 'active' : ''}`}
              onClick={() => handleToggleDemo(false)}
            >
              Live
            </button>
            <button
              className={`mode-toggle-btn ${demoMode ? 'active' : ''}`}
              onClick={() => handleToggleDemo(true)}
            >
              Demo
            </button>
          </div>
        </div>
      </header>

      {/* ── Tab nav ── */}
      <nav className="tab-nav">
        <button
          className={`tab-btn ${activeTab === 'briefing' ? 'active' : ''}`}
          onClick={() => setActiveTab('briefing')}
        >
          Today's Briefing
        </button>
        <button
          className={`tab-btn ${activeTab === 'conditions' ? 'active' : ''}`}
          onClick={() => setActiveTab('conditions')}
        >
          Live Conditions
        </button>
        <button
          className={`tab-btn ${activeTab === 'history' ? 'active' : ''}`}
          onClick={() => setActiveTab('history')}
        >
          Briefing History
        </button>
        <button
          className={`tab-btn ${activeTab === 'staff' ? 'active' : ''}`}
          onClick={() => setActiveTab('staff')}
        >
          Staff
          {staffRisk && staffRisk.high_risk_count > 0 && (
            <span className="tab-alert-dot">{staffRisk.high_risk_count}</span>
          )}
        </button>
      </nav>

      {/* ── Tab content ── */}
      <main className="tab-content">
        {activeTab === 'briefing' && (
          <TodaysBriefing
            briefing={currentBriefing}
            onGenerate={handleGenerateBriefing}
            loading={loading}
            error={error}
            demoMode={demoMode}
            staffRisk={staffRisk}
            onViewStaff={() => setActiveTab('staff')}
          />
        )}
        {activeTab === 'conditions' && (
          <LiveConditions
            conditions={conditions}
            onRefresh={() => fetchConditions(demoMode)}
            loading={conditionsLoading}
            demoMode={demoMode}
          />
        )}
        {activeTab === 'history' && (
          <BriefingHistory
            history={history}
            onSelectBriefing={handleSelectBriefing}
            loading={loading}
          />
        )}
        {activeTab === 'staff' && (
          <StaffTab
            demoMode={demoMode}
            onRiskUpdate={setStaffRisk}
          />
        )}
      </main>
    </div>
  )
}
