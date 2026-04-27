import React, { useState, useEffect, useRef } from 'react'
import axios from 'axios'
import mermaid from 'mermaid'
import { RefreshCcw, Info, CheckCircle, XCircle, Search, FileText, Play, Pause, SkipForward, Send, Radio, GitBranch, Settings } from 'lucide-react'
import EventTimeline from './EventTimeline'
import MilestoneTracker from './components/MilestoneTracker'

// Initialize Mermaid
mermaid.initialize({
  startOnLoad: false,
  theme: 'dark',
  securityLevel: 'loose',
  themeVariables: {
    primaryColor: '#1e293b',
    primaryTextColor: '#f8fafc',
    primaryBorderColor: '#334155',
    lineColor: '#64748b',
    secondaryColor: '#334155',
    tertiaryColor: '#1e293b'
  }
})

function BlueprintGraph({ activityId }) {
  const [data, setData] = useState({ nodes: [], edges: [] })
  const [selectedTask, setSelectedTask] = useState(null)
  const [loading, setLoading] = useState(false)
  const [userInstruction, setUserInstruction] = useState("")
  const [pendingPlans, setPendingPlans] = useState([])
  const [autoAdvance, setAutoAdvance] = useState(true)
  const mermaidRef = useRef(null)

  const handleSubmitInstruction = async () => {
    if (!userInstruction.trim()) return
    try {
      await axios.post(`/api/activity/${activityId}/instruction`, { instruction: userInstruction })
      setUserInstruction("")
      fetchGraph()
    } catch (e) { console.error("Failed to submit instruction", e) }
  }

  const handleActivatePlanner = async () => {
    try {
      await axios.post(`/api/activity/${activityId}/activate_planner`)
      alert("Architect/Planner activated. Checking board...")
    } catch (e) { console.error("Activation failed", e); alert("Failed to activate planner") }
  }

  const handleStep = async () => {
    try {
      const resp = await axios.post(`/api/system/step`)
      if (resp.data.status === 'idle') {
        alert("System is stable. No pending events.")
      } else {
        console.log("Processed event:", resp.data.processed)
        fetchGraph()
      }
    } catch (e) { console.error("Step failed", e); alert("Failed to step engine") }
  }

  const fetchSettings = async () => {
    try {
      const resp = await axios.get('/api/system/settings')
      setAutoAdvance(resp.data.auto_advance)
    } catch (e) { console.error("Failed to fetch settings", e) }
  }

  const handleToggleAutoAdvance = async () => {
    const newVal = !autoAdvance
    try {
      await axios.post('/api/system/settings', null, { params: { auto_advance: newVal } })
      setAutoAdvance(newVal)
    } catch (e) { console.error("Failed to update settings", e) }
  }

  const fetchGraph = async () => {
    setLoading(true)
    try {
      const resp = await axios.get(`/api/activity/${activityId}/graph`)
      setData(resp.data)
      renderMermaid(resp.data)
      
      const plansResp = await axios.get(`/api/blueprints?activity_id=${activityId}&status=pending`)
      setPendingPlans(plansResp.data)
    } catch (err) {
      console.error("Graph fetch failed", err)
    }
    setLoading(false)
  }

  const renderMermaid = async (graphData) => {
    // Check if mermaid is available from import or global
    const m = mermaid || window.mermaid
    if (graphData.nodes.length === 0 || !m) {
      console.warn("Mermaid not available or no nodes to render")
      return
    }
    
    // Generate Mermaid Syntax
    let code = "graph TD\n"
    
    // Define Classes at the top
    code += `  classDef awaiting fill:#f59e0b,stroke:#fcd34d,stroke-width:2px,color:#fff\n`
    code += `  classDef done fill:#10b981,stroke:#059669,stroke-width:1px,color:#fff\n`
    code += `  classDef ready fill:#3b82f6,stroke:#2563eb,stroke-width:1px,color:#fff\n`
    code += `  classDef blocked fill:#ef4444,stroke:#dc2626,stroke-width:2px,color:#fff\n`

    // All nodes rendered uniformly
    graphData.nodes.forEach(node => {
      let className = ""
      if (node.status === 'awaiting_approval') {
        className = "awaiting"
      } else if (node.status === 'done' || node.status === 'code_done') {
        className = "done"
      } else if (node.status === 'ready' || node.status === 'in_progress' || node.status === 'active') {
        className = "ready"
      } else if (node.status === 'blocked' || node.status === 'failed') {
        className = "blocked"
      }
      
      // Escape special characters in label
      const safeLabel = node.label.replace(/\n/g, "<br/>").replace(/"/g, "&quot;")
      
      // Use quotes around node ID if it contains special chars, though alphanumeric+underscore is usually fine
      code += `  ${node.id}["${safeLabel}"]\n`
      if (className) {
        code += `  class ${node.id} ${className}\n`
      }
    })
    
    // Define Edges
    graphData.edges.forEach(edge => {
      code += `  ${edge.from} --> ${edge.to}\n`
    })
    
    try {
       // Unique ID for SVG generation to avoid collisions
       const { svg } = await m.render('blueprint-svg-' + Date.now(), code)
       if (mermaidRef.current) {
         mermaidRef.current.innerHTML = svg
         
         // Attach click listeners to SVG nodes
         const nodes = mermaidRef.current.querySelectorAll('.node')
         nodes.forEach(nodeEl => {
           nodeEl.style.cursor = 'pointer'
           nodeEl.onclick = () => {
             // Extract task ID from the element ID or classes
             const nodeId = graphData.nodes.find(n => nodeEl.id.includes(n.id))?.id
             if (nodeId) {
                const task = graphData.nodes.find(n => n.id === nodeId)
                if (task) setSelectedTask(task)
             }
           }
         })
       }
    } catch (e) {
      console.error("Mermaid Render Error", e)
    }
  }

  useEffect(() => {
    fetchGraph()
    fetchSettings()
    const interval = setInterval(fetchGraph, 5000)
    return () => clearInterval(interval)
  }, [activityId])

  const handleApprovePlan = async (planId) => {
    try {
      await axios.post(`/api/blueprint/${planId}/approve`)
      fetchGraph()
      alert("Plan approved!")
    } catch (e) { alert("Approval failed") }
  }

  const handleRejectPlan = async (planId) => {
    try {
      await axios.post(`/api/blueprint/${planId}/reject`)
      fetchGraph()
    } catch (e) { alert("Rejection failed") }
  }

  return (
    <div className="relative flex flex-col gap-6">
      {/* Tool Bar & Cockpit */}
      <div className="flex flex-col gap-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <h2 className="text-lg font-bold text-slate-400">BLUEPRINT TOPOLOGY</h2>
            <div className="flex items-center gap-3 px-3 py-1.5 rounded-full text-[10px] font-bold tracking-widest border border-slate-600 bg-slate-800 text-slate-300">
              <Radio size={12} />
              MANUAL OVERSIGHT
            </div>
          </div>
          
          <div className="flex items-center gap-3">
            {/* Contextual Controller */}
            <div className="flex items-center bg-slate-900 border border-slate-700/50 rounded-xl p-1 shadow-2xl">
               
               <button 
                onClick={handleActivatePlanner}
                className="flex items-center gap-2 px-4 py-2 bg-indigo-600/20 text-indigo-400 hover:bg-indigo-600/30 rounded-lg font-bold text-xs uppercase tracking-tighter transition-all duration-300"
               >
                 <Settings size={14} /> Activate Planner
               </button>

               <div className="h-6 w-[1px] bg-slate-700/50 mx-2" />

               {/* VALVE CONTROLS */}
               <div className="flex items-center gap-1 bg-slate-950/50 p-1 rounded-lg border border-slate-800">
                 <button 
                  onClick={handleToggleAutoAdvance}
                  title={autoAdvance ? "Pause Auto-Advance" : "Resume Auto-Advance"}
                  className={`p-2 rounded-md transition-all ${autoAdvance ? 'bg-brand-blue text-white shadow-lg' : 'text-slate-500 hover:text-slate-300'}`}
                 >
                   {autoAdvance ? <Play size={14} fill="currentColor" /> : <Pause size={14} fill="currentColor" />}
                 </button>
                 
                 <button 
                  onClick={handleStep}
                  disabled={autoAdvance}
                  title="Step Engine"
                  className={`p-2 rounded-md transition-all ${autoAdvance ? 'opacity-20 cursor-not-allowed' : 'text-slate-300 hover:bg-slate-800 hover:text-white'}`}
                 >
                   <SkipForward size={14} fill="currentColor" />
                 </button>
               </div>

               <div className="h-6 w-[1px] bg-slate-700/50 mx-2" />
               
               {/* BROADCAST FIELD */}
               <div className="flex items-center px-4 bg-slate-950/30 rounded-lg border border-transparent focus-within:border-slate-600 transition-all">
                  <span className="text-slate-600 font-mono text-[10px] mr-2">{"CMD>"}</span>
                  <input 
                    type="text" 
                    placeholder="Broadcast instruction..."
                    value={userInstruction}
                    onChange={(e) => setUserInstruction(e.target.value)}
                    className="bg-transparent border-none text-xs focus:ring-0 w-64 text-slate-100 placeholder:text-slate-600 font-medium py-2 outline-none"
                    onKeyDown={(e) => e.key === 'Enter' && handleSubmitInstruction()}
                  />
                  <button 
                    onClick={handleSubmitInstruction}
                    className="ml-2 p-2 text-brand-blue hover:text-white transition-all hover:scale-110 active:scale-95"
                  >
                    <Send size={16} />
                  </button>
               </div>
            </div>

            <button 
              onClick={fetchGraph}
              disabled={loading}
              className="flex items-center gap-2 px-4 py-3 bg-slate-800 hover:bg-slate-700 rounded-xl border border-slate-700 transition-all text-sm font-bold shadow-lg"
            >
              <RefreshCcw size={16} className={`${loading ? 'animate-spin' : ''}`} />
              Sync
            </button>
          </div>
        </div>
      </div>

      {/* Pending Plans Notification */}
      {pendingPlans.length > 0 && (
        <div className="flex flex-col gap-4 animate-in fade-in slide-in-from-top duration-500">
           {pendingPlans.map(plan => (
             <div key={plan.id} className="bg-amber-500/10 border border-amber-500/30 rounded-2xl p-6 flex items-center justify-between shadow-2xl backdrop-blur-md">
                <div className="flex items-center gap-4">
                   <div className="w-12 h-12 bg-amber-500/20 rounded-full flex items-center justify-center text-amber-500">
                      <RefreshCcw size={24} className="animate-spin-slow" />
                   </div>
                   <div>
                      <h3 className="text-amber-100 font-bold text-lg">{plan.title}</h3>
                      <p className="text-amber-500/60 text-xs font-mono uppercase tracking-widest mt-1">
                        PROPOSED BLUEPRINT MODIFICATION • {plan.id}
                      </p>
                   </div>
                </div>
                <div className="flex items-center gap-3">
                   <button 
                    onClick={() => handleRejectPlan(plan.id)}
                    className="px-6 py-2.5 rounded-xl border border-amber-500/20 text-amber-500 hover:bg-amber-500/10 transition-all font-bold text-xs uppercase tracking-widest"
                   >
                     Reject
                   </button>
                   <button 
                    onClick={() => handleApprovePlan(plan.id)}
                    className="px-8 py-2.5 bg-amber-500 hover:bg-amber-400 text-slate-950 rounded-xl transition-all font-bold text-xs uppercase tracking-widest shadow-lg shadow-amber-900/40"
                   >
                     Review & Approve
                   </button>
                </div>
             </div>
           ))}
        </div>
      )}

      {/* Graph Canvas */}
      <div className="glass-panel min-h-[500px] flex items-center justify-center overflow-auto p-12">
        {data.nodes.length > 0 ? (
          <div ref={mermaidRef} id="graphDiv" className="w-full flex justify-center" />
        ) : (
          <div className="flex flex-col items-center gap-4 opacity-30">
             <GitBranch size={48} />
             <p className="text-sm font-medium italic tracking-widest uppercase">No Active Topology Detected</p>
          </div>
        )}
      </div>

      {/* Milestones & Timeline */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1">
          <MilestoneTracker activityId={activityId} />
        </div>
        <div className="lg:col-span-2">
          <EventTimeline activityId={activityId} />
        </div>
      </div>

      {/* Side Detail Panel (Drawer) */}
      {selectedTask && (
        <div className="fixed inset-y-0 right-0 w-[450px] bg-slate-900 border-l border-slate-700 shadow-2xl z-50 flex flex-col transform transition-transform duration-300">
           <div className="p-8 flex-1 overflow-y-auto">
             <div className="flex justify-between items-start mb-8">
               <div>
                 <span className="text-[10px] font-mono text-slate-500 uppercase tracking-widest block mb-1">TASK DETAILS</span>
                 <h3 className="text-2xl font-bold italic">{selectedTask.id}</h3>
               </div>
               <button onClick={() => setSelectedTask(null)} className="text-slate-500 hover:text-white">
                 <XCircle size={24} />
               </button>
             </div>

             <div className="space-y-8">
                <section>
                  <h4 className="flex items-center gap-2 text-brand-blue font-bold text-sm mb-3 uppercase tracking-tight">
                    <Search size={16} /> Iteration Goal
                  </h4>
                  <div className="bg-slate-800/50 p-4 rounded-xl border border-slate-700 text-sm leading-relaxed text-slate-200 italic">
                    {selectedTask.goal}
                  </div>
                </section>

                <section>
                   <h4 className="flex items-center gap-2 text-slate-400 font-bold text-sm mb-3 uppercase tracking-tight">
                    <FileText size={16} /> Audit Status
                  </h4>
                  <div className="grid grid-cols-2 gap-4 text-xs font-mono">
                     <div className="bg-slate-800 p-3 rounded-lg border border-slate-700">
                       <span className="text-slate-500 block mb-1 uppercase">State</span>
                       <span className="text-slate-100">{selectedTask.status.toUpperCase()}</span>
                     </div>
                     <div className="bg-slate-800 p-3 rounded-lg border border-slate-700">
                       <span className="text-slate-500 block mb-1 uppercase">Approved</span>
                       <span className={selectedTask.is_approved ? 'text-brand-green' : 'text-brand-red'}>
                         {selectedTask.is_approved ? 'YES' : 'NO'}
                       </span>
                     </div>
                  </div>
                </section>
             </div>
           </div>

           {/* Actions */}
           <div className="p-8 bg-slate-950/50 border-t border-slate-700 flex gap-4">
              <button 
                onClick={() => setSelectedTask(null)}
                className="flex-1 bg-slate-800 hover:bg-slate-700 text-slate-300 font-bold py-4 rounded-xl border border-slate-600 transition-all"
              >
                CLOSE
              </button>
           </div>
        </div>
      )}
    </div>
  )
}

export default BlueprintGraph
