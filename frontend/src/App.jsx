import React, { useState, useEffect } from 'react'
import axios from 'axios'
import ActivityList from './ActivityList'
import BlueprintGraph from './BlueprintGraph'
import { Layout, GitBranch, Terminal } from 'lucide-react'

function App() {
  const [currentActivity, setCurrentActivity] = useState(null)

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const actId = params.get('activityId')
    if (actId) {
      setCurrentActivity(actId)
    }

    const handlePopState = () => {
      const p = new URLSearchParams(window.location.search)
      setCurrentActivity(p.get('activityId'))
    }
    window.addEventListener('popstate', handlePopState)
    return () => window.removeEventListener('popstate', handlePopState)
  }, [])

  useEffect(() => {
    const url = new URL(window.location)
    const existingId = url.searchParams.get('activityId')
    
    if (currentActivity && existingId !== currentActivity) {
      url.searchParams.set('activityId', currentActivity)
      window.history.pushState({}, '', url)
    } else if (!currentActivity && existingId) {
      url.searchParams.delete('activityId')
      window.history.pushState({}, '', url)
    }
  }, [currentActivity])
  
  return (
    <div className="flex flex-col min-h-screen">
      <header className="px-8 py-6 flex items-center justify-between glass-panel border-t-0 border-x-0 rounded-none mb-8">
        <div className="flex items-center gap-3">
          <Layout className="text-brand-blue w-8 h-8" />
          <h1 className="text-2xl font-bold tracking-tight">
            Smart Task <span className="text-brand-blue">Hub</span>
          </h1>
        </div>
        
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2 px-3 py-1 bg-brand-blue/10 text-brand-blue rounded-full text-xs font-semibold">
            <Terminal size={14} />
            PROJECT MANAGEMENT
          </div>
        </div>
      </header>

      <main className="flex-1 px-8 pb-12">
        {!currentActivity ? (
          <ActivityList onSelect={setCurrentActivity} />
        ) : (
          <div className="flex flex-col gap-6">
             <button 
               onClick={() => setCurrentActivity(null)}
               className="self-start text-slate-400 hover:text-white flex items-center gap-2 text-sm transition-colors"
             >
               ← Back to Activity Control
             </button>
             <BlueprintGraph activityId={currentActivity} />
          </div>
        )}
      </main>
    </div>
  )
}

export default App
