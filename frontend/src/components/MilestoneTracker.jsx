import React, { useState, useEffect } from 'react'
import axios from 'axios'
import { Flag, CheckCircle, Clock, AlertCircle } from 'lucide-react'
import { format } from 'date-fns'

const STATUS_CONFIG = {
  'Achieved': { icon: CheckCircle, color: 'text-green-400', bg: 'bg-green-500/10', border: 'border-green-500/30' },
  'Pending':  { icon: Clock,       color: 'text-blue-400',  bg: 'bg-blue-500/10',  border: 'border-blue-500/30' },
  'Missed':   { icon: AlertCircle, color: 'text-red-400',   bg: 'bg-red-500/10',   border: 'border-red-500/30' }
}

function MilestoneTracker({ activityId }) {
  const [milestones, setMilestones] = useState([])
  const [loading, setLoading] = useState(false)

  const fetchMilestones = async () => {
    if (!activityId) return
    setLoading(true)
    try {
      const resp = await axios.get(`/api/activity/${activityId}/milestones`)
      setMilestones(resp.data)
    } catch (e) {
      console.error("Failed to fetch milestones", e)
    }
    setLoading(false)
  }

  const handleAchieve = async (id) => {
    try {
      await axios.post(`/api/milestone/${id}/achieve`)
      fetchMilestones()
    } catch (e) {
      console.error("Failed to achieve milestone", e)
    }
  }

  useEffect(() => {
    fetchMilestones()
    const interval = setInterval(fetchMilestones, 15000)
    return () => clearInterval(interval)
  }, [activityId])

  if (milestones.length === 0 && !loading) return null

  return (
    <div className="glass-panel p-6">
      <div className="flex items-center gap-3 mb-6">
        <Flag size={20} className="text-brand-blue" />
        <h3 className="text-sm font-bold tracking-wider text-slate-300 uppercase">
          Milestones
        </h3>
      </div>

      <div className="flex flex-col gap-4">
        {milestones.map((ms) => {
          const cfg = STATUS_CONFIG[ms.status] || STATUS_CONFIG.Pending
          const Icon = cfg.icon
          
          return (
            <div key={ms.id} className={`p-4 rounded-xl border ${cfg.border} ${cfg.bg} transition-all`}>
              <div className="flex items-start justify-between">
                <div className="flex gap-4">
                  <div className={`mt-1 p-2 rounded-lg bg-slate-900/50 ${cfg.color}`}>
                    <Icon size={18} />
                  </div>
                  <div>
                    <h4 className="font-bold text-slate-200">{ms.name}</h4>
                    <p className="text-xs text-slate-500 mt-1">{ms.description}</p>
                    <div className="flex items-center gap-3 mt-3">
                       <span className="text-[10px] font-mono text-slate-400 bg-slate-800/50 px-2 py-0.5 rounded">
                         Target: {ms.target_date ? format(new Date(ms.target_date), 'MMM d, yyyy') : 'TBD'}
                       </span>
                       {ms.reached_at && (
                         <span className="text-[10px] font-mono text-green-400/70">
                           Reached: {format(new Date(ms.reached_at), 'MMM d, HH:mm')}
                         </span>
                       )}
                    </div>
                  </div>
                </div>

                {ms.status === 'Pending' && (
                  <button 
                    onClick={() => handleAchieve(ms.id)}
                    className="px-3 py-1 bg-green-500/20 text-green-400 text-[10px] font-bold rounded-md border border-green-500/30 hover:bg-green-500/30 transition-all uppercase"
                  >
                    Achieve
                  </button>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default MilestoneTracker
