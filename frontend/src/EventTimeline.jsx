import React, { useState, useEffect } from 'react'
import axios from 'axios'
import { Zap, AlertTriangle, AlertCircle, Info, X, ChevronDown, ChevronUp, Clock } from 'lucide-react'

const SEVERITY_CONFIG = {
  critical: { 
    icon: AlertCircle, 
    color: 'text-red-400', 
    bg: 'bg-red-500/10', 
    border: 'border-red-500/30',
    dot: 'bg-red-500',
    glow: 'shadow-[0_0_8px_rgba(239,68,68,0.3)]'
  },
  warning: { 
    icon: AlertTriangle, 
    color: 'text-amber-400', 
    bg: 'bg-amber-500/10', 
    border: 'border-amber-500/30',
    dot: 'bg-amber-500',
    glow: 'shadow-[0_0_8px_rgba(245,158,11,0.3)]'
  },
  normal: { 
    icon: Info, 
    color: 'text-blue-400', 
    bg: 'bg-blue-500/10', 
    border: 'border-blue-500/30',
    dot: 'bg-blue-500',
    glow: ''
  }
}

const STATUS_BADGE = {
  pending:    { label: 'PENDING',    cls: 'bg-amber-500/20 text-amber-400 border-amber-500/30' },
  processing: { label: 'PROCESSING', cls: 'bg-blue-500/20 text-blue-400 border-blue-500/30' },
  resolved:   { label: 'RESOLVED',   cls: 'bg-green-500/20 text-green-400 border-green-500/30' },
  dismissed:  { label: 'DISMISSED',  cls: 'bg-slate-500/20 text-slate-400 border-slate-500/30' },
}

function EventTimeline({ activityId }) {
  const [events, setEvents] = useState([])
  const [loading, setLoading] = useState(false)
  const [filter, setFilter] = useState('all')  // all | pending | resolved
  const [expanded, setExpanded] = useState(true)
  const [expandedEvent, setExpandedEvent] = useState(null)

  const fetchEvents = async () => {
    setLoading(true)
    try {
      let url = '/api/events?limit=30'
      if (activityId) url += `&activity_id=${activityId}`
      if (filter !== 'all') url += `&status=${filter}`
      const resp = await axios.get(url)
      setEvents(resp.data)
    } catch (e) {
      console.error("Failed to fetch events", e)
    }
    setLoading(false)
  }

  const handleDismiss = async (eventId) => {
    try {
      await axios.post(`/api/events/${eventId}/dismiss`)
      fetchEvents()
    } catch (e) {
      console.error("Failed to dismiss event", e)
    }
  }

  useEffect(() => {
    fetchEvents()
    const interval = setInterval(fetchEvents, 8000)
    return () => clearInterval(interval)
  }, [activityId, filter])

  const formatTime = (ts) => {
    if (!ts) return ''
    const d = new Date(ts)
    const now = new Date()
    const diffMs = now - d
    const diffMin = Math.floor(diffMs / 60000)
    
    if (diffMin < 1) return 'just now'
    if (diffMin < 60) return `${diffMin}m ago`
    if (diffMin < 1440) return `${Math.floor(diffMin / 60)}h ago`
    return d.toLocaleDateString()
  }

  const formatEventType = (type) => {
    return type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
  }

  const pendingCount = events.filter(e => e.status === 'pending').length

  return (
    <div className="glass-panel overflow-hidden">
      {/* Header */}
      <button 
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-6 py-4 hover:bg-slate-800/30 transition-colors"
      >
        <div className="flex items-center gap-3">
          <Zap size={18} className="text-purple-400" />
          <h3 className="text-sm font-bold tracking-wider text-slate-300 uppercase">
            Event Bus
          </h3>
          {pendingCount > 0 && (
            <span className="px-2 py-0.5 bg-red-500/20 text-red-400 text-[10px] font-bold rounded-full border border-red-500/30 animate-pulse">
              {pendingCount} PENDING
            </span>
          )}
        </div>
        <div className="flex items-center gap-3">
          <span className="text-[10px] text-slate-500 font-mono">{events.length} events</span>
          {expanded ? <ChevronUp size={16} className="text-slate-500" /> : <ChevronDown size={16} className="text-slate-500" />}
        </div>
      </button>

      {expanded && (
        <>
          {/* Filter Tabs */}
          <div className="flex items-center gap-1 px-6 pb-3 border-b border-slate-700/50">
            {['all', 'pending', 'processing', 'resolved', 'dismissed'].map(f => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`px-3 py-1 text-[10px] font-bold uppercase tracking-wider rounded-md transition-all ${
                  filter === f 
                    ? 'bg-purple-500/20 text-purple-300 border border-purple-500/30' 
                    : 'text-slate-500 hover:text-slate-300 hover:bg-slate-800/50 border border-transparent'
                }`}
              >
                {f}
              </button>
            ))}
          </div>

          {/* Timeline */}
          <div className="max-h-[400px] overflow-y-auto">
            {loading && events.length === 0 ? (
              <div className="p-8 text-center text-slate-500 text-sm">Loading events...</div>
            ) : events.length === 0 ? (
              <div className="p-8 text-center text-slate-600 text-sm">
                No events {filter !== 'all' ? `with status "${filter}"` : 'recorded yet'}
              </div>
            ) : (
              <div className="relative px-6 py-4">
                {/* Vertical timeline line */}
                <div className="absolute left-[33px] top-4 bottom-4 w-[2px] bg-gradient-to-b from-slate-700 via-slate-700/50 to-transparent" />

                {events.map((evt, idx) => {
                  const sev = SEVERITY_CONFIG[evt.severity] || SEVERITY_CONFIG.normal
                  const statusBadge = STATUS_BADGE[evt.status] || STATUS_BADGE.pending
                  const SevIcon = sev.icon
                  const isExpanded = expandedEvent === evt.id
                  const payload = typeof evt.payload === 'string' ? JSON.parse(evt.payload) : (evt.payload || {})

                  return (
                    <div key={evt.id} className="relative flex gap-4 mb-4 last:mb-0 group">
                      {/* Timeline dot */}
                      <div className={`relative z-10 mt-1 w-4 h-4 rounded-full ${sev.dot} ${sev.glow} flex-shrink-0 ring-4 ring-slate-900`} />
                      
                      {/* Event card */}
                      <div className={`flex-1 rounded-lg border ${sev.border} ${sev.bg} p-3 transition-all hover:bg-opacity-20 cursor-pointer`}
                           onClick={() => setExpandedEvent(isExpanded ? null : evt.id)}
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div className="flex items-center gap-2 min-w-0">
                            <SevIcon size={14} className={sev.color} />
                            <span className={`text-xs font-bold ${sev.color}`}>
                              {formatEventType(evt.event_type)}
                            </span>
                            <span className={`px-1.5 py-0.5 text-[9px] font-bold rounded border ${statusBadge.cls}`}>
                              {statusBadge.label}
                            </span>
                          </div>
                          <div className="flex items-center gap-2 flex-shrink-0">
                            <span className="text-[10px] text-slate-500 flex items-center gap-1">
                              <Clock size={10} />
                              {formatTime(evt.created_at)}
                            </span>
                            {evt.status === 'pending' && (
                              <button 
                                onClick={(e) => { e.stopPropagation(); handleDismiss(evt.id) }}
                                className="p-1 text-slate-600 hover:text-red-400 transition-colors opacity-0 group-hover:opacity-100"
                                title="Dismiss"
                              >
                                <X size={12} />
                              </button>
                            )}
                          </div>
                        </div>

                        {/* Source & refs */}
                        <div className="mt-1.5 flex items-center gap-3 text-[10px] text-slate-500 font-mono">
                          <span>src:{evt.source}</span>
                          {evt.task_id && <span>task:{evt.task_id}</span>}
                          {evt.activity_id && <span>act:{evt.activity_id}</span>}
                          {evt.resolved_by && <span>→ {evt.resolved_by}</span>}
                        </div>

                        {/* Expanded payload */}
                        {isExpanded && Object.keys(payload).length > 0 && (
                          <div className="mt-3 pt-3 border-t border-slate-700/30">
                            <pre className="text-[11px] text-slate-400 font-mono whitespace-pre-wrap break-all leading-relaxed">
                              {JSON.stringify(payload, null, 2)}
                            </pre>
                          </div>
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}

export default EventTimeline
