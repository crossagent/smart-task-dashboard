import React, { useState, useEffect } from 'react'
import axios from 'axios'
import { Calendar, Filter, ArrowRight, Activity as ActivityIcon } from 'lucide-react'
import { format, subDays } from 'date-fns'

function ActivityList({ onSelect }) {
  const [activities, setActivities] = useState([])
  const [loading, setLoading] = useState(true)
  const [startDate, setStartDate] = useState(format(subDays(new Date(), 7), 'yyyy-MM-dd'))
  const [endDate, setEndDate] = useState(format(new Date(), 'yyyy-MM-dd'))

  const fetchActivities = async () => {
    setLoading(true)
    try {
      const resp = await axios.get(`/api/activities?start=${startDate}&end=${endDate}`)
      setActivities(resp.data)
    } catch (err) {
      console.error("Failed to fetch activities", err)
    }
    setLoading(false)
  }

  useEffect(() => {
    fetchActivities()
  }, [startDate, endDate])

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold flex items-center gap-2">
          <ActivityIcon className="text-brand-blue" />
          Active Engineering Threads
        </h2>
        
        <div className="flex items-center gap-4 bg-slate-800/50 p-2 rounded-lg border border-slate-700">
          <div className="flex items-center gap-2">
            <Calendar size={14} className="text-slate-400" />
            <input 
              type="date" 
              value={startDate} 
              onChange={e => setStartDate(e.target.value)}
              className="bg-transparent text-sm outline-none cursor-pointer"
            />
          </div>
          <span className="text-slate-600">→</span>
          <div className="flex items-center gap-2">
            <input 
              type="date" 
              value={endDate} 
              onChange={e => setEndDate(e.target.value)}
              className="bg-transparent text-sm outline-none cursor-pointer"
            />
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {loading ? (
             [1,2,3].map(i => <div key={i} className="h-40 glass-panel animate-pulse" />)
        ) : activities.length === 0 ? (
          <div className="col-span-full py-20 bg-slate-800/20 rounded-2xl border-2 border-dashed border-slate-700 flex flex-col items-center justify-center text-slate-500">
             <Filter size={48} className="mb-4 opacity-20" />
             <p>No activities found in this time range.</p>
          </div>
        ) : (
          activities.map(act => (
            <div 
              key={act.id} 
              onClick={() => onSelect(act.id)}
              className="glass-panel p-6 cursor-pointer hover:border-brand-blue/50 hover:bg-slate-800/60 transition-all group"
            >
              <div className="flex justify-between items-start mb-4">
                <span className="text-[10px] font-mono text-slate-500 uppercase tracking-widest">{act.id}</span>
                <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                  act.status === 'done' ? 'bg-brand-green/20 text-brand-green' : 'bg-brand-blue/20 text-brand-blue'
                }`}>
                  {act.status.toUpperCase()}
                </span>
              </div>
              <h3 className="font-bold text-lg mb-2 group-hover:text-brand-blue transition-colors leading-tight">
                {act.name}
              </h3>
              
              {act.ms_total > 0 && (
                <div className="mt-4">
                  <div className="flex justify-between text-[10px] font-bold text-slate-500 mb-1 uppercase tracking-tighter">
                    <span>Milestones</span>
                    <span>{act.ms_achieved} / {act.ms_total}</span>
                  </div>
                  <div className="h-1 w-full bg-slate-800 rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-brand-blue transition-all duration-1000" 
                      style={{ width: `${(act.ms_achieved / act.ms_total) * 100}%` }}
                    />
                  </div>
                </div>
              )}

              <div className="flex items-center justify-between mt-6">
                <span className="text-xs text-slate-500 italic">
                  Created {format(new Date(act.created_at), 'MMM d, HH:mm')}
                </span>
                <ArrowRight size={18} className="text-slate-700 group-hover:text-brand-blue translate-x-0 group-hover:translate-x-1 transition-all" />
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

export default ActivityList
