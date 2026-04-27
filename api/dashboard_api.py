from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List
from .db import execute_query, execute_mutation
from . import engine
import json

router = APIRouter(prefix="/api")

@router.get("/activities")
async def get_activities(
    start: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end: Optional[str] = Query(None, description="End date (YYYY-MM-DD)")
):
    """List activities with optional date filtering."""
    sql = """
        SELECT a.id, a.name, a.status, a.priority, a.created_at, 
               COUNT(m.id) as ms_total, 
               COUNT(m.id) FILTER (WHERE m.status = 'Achieved') as ms_achieved 
        FROM activities a
        LEFT JOIN milestones m ON a.id = m.activity_id
    """
    params = []
    
    where_clauses = []
    if start:
        where_clauses.append("a.created_at >= %s")
        params.append(start)
    if end:
        where_clauses.append("a.created_at < (%s::date + 1)")
        params.append(end)
        
    if where_clauses:
        sql += " WHERE " + " AND ".join(where_clauses)
    
    sql += " GROUP BY a.id ORDER BY a.created_at DESC"
    
    try:
        results = execute_query(sql, tuple(params))
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/activity/{activity_id}/graph")
async def get_activity_graph(activity_id: str):
    """Returns task nodes and edges for Mermaid visualization."""
    sql = """
        SELECT id, module_id, module_iteration_goal, status, depends_on
        FROM tasks
        WHERE activity_id = %s
    """
    try:
        tasks = execute_query(sql, (activity_id,))
        if not tasks:
            return {"nodes": [], "edges": []}
            
        nodes = []
        edges = []
        
        for t in tasks:
            # Node metadata
            nodes.append({
                "id": t['id'],
                "label": f"{t['id']}\n({t['module_id']})",
                "status": t['status'],

                "goal": t['module_iteration_goal']
            })
            
            # Edges from depends_on
            deps = t['depends_on'] or []
            for dep_id in deps:
                edges.append({"from": dep_id, "to": t['id']})
                
        return {"nodes": nodes, "edges": edges}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/activity/{activity_id}/details")
async def get_activity_details(activity_id: str):
    """Aggregated stats and metadata for the activity."""
    act_sql = "SELECT * FROM activities WHERE id = %s"
    prog_sql = "SELECT * FROM v_activity_progress WHERE activity_id = %s"
    ms_sql = "SELECT count(*) as total, count(*) FILTER (WHERE status = 'Achieved') as achieved FROM milestones WHERE activity_id = %s"
    
    try:
        act = execute_query(act_sql, (activity_id,))
        try:
            prog = execute_query(prog_sql, (activity_id,))
        except Exception:
            # Fallback if view doesn't exist
            prog = None
        
        milestones = execute_query(ms_sql, (activity_id,))
        ms_stats = milestones[0] if milestones else {"total": 0, "achieved": 0}
        
        if not act:
            raise HTTPException(status_code=404, detail="Activity not found")
            
        return {
            "metadata": act[0],
            "progress": prog[0] if prog else {"completion_percentage": 0},
            "milestone_stats": ms_stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/activity/{activity_id}/milestones")
async def get_activity_milestones(activity_id: str):
    """List all milestones for a specific activity."""
    sql = "SELECT * FROM milestones WHERE activity_id = %s ORDER BY target_date ASC NULLS LAST, created_at ASC"
    try:
        return execute_query(sql, (activity_id,))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/milestone/{milestone_id}/achieve")
async def achieve_milestone(milestone_id: str):
    """Mark a milestone as achieved."""
    sql = "UPDATE milestones SET status = 'Achieved', reached_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP WHERE id = %s"
    try:
        execute_mutation(sql, (milestone_id,))
        # Emit event
        execute_mutation("""
            INSERT INTO events (event_type, source, severity, payload)
            VALUES ('milestone_achieved', 'human', 'normal', %s)
        """, (json.dumps({'milestone_id': milestone_id}),))
        return {"status": "success", "message": f"Milestone {milestone_id} achieved."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- BLUEPRINT MODIFICATION PLANS ---

@router.get("/blueprints")
async def get_blueprints(
    activity_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None)
):
    """List proposed blueprint modification plans."""
    sql = "SELECT id, title, activity_id, status, created_at, proposed_actions FROM blueprint_plans"
    params = []
    where = []
    if activity_id:
        where.append("activity_id = %s")
        params.append(activity_id)
    if status:
        where.append("status = %s")
        params.append(status)
    
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY created_at DESC"
    
    try:
        return execute_query(sql, tuple(params))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/blueprint/{plan_id}/approve")
async def approve_blueprint(plan_id: int):
    """Approve a blueprint plan. This will likely be picked up by the Architect."""
    sql = "UPDATE blueprint_plans SET status = 'approved', updated_at = CURRENT_TIMESTAMP WHERE id = %s"
    try:
        execute_mutation(sql, (plan_id,))
        # Emit an event to notify the Architect to execute
        execute_mutation("""
            INSERT INTO events (event_type, source, severity, payload)
            VALUES ('plan_approved', 'human', 'critical', %s)
        """, (json.dumps({'plan_id': plan_id}),))
        return {"status": "success", "message": f"Plan {plan_id} approved."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/blueprint/{plan_id}/reject")
async def reject_blueprint(plan_id: int):
    """Reject a proposed blueprint plan."""
    sql = "UPDATE blueprint_plans SET status = 'rejected', updated_at = CURRENT_TIMESTAMP WHERE id = %s"
    try:
        execute_mutation(sql, (plan_id,))
        return {"status": "success", "message": f"Plan {plan_id} rejected."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/activity/{activity_id}/activate_planner")
async def activate_planner(activity_id: str):
    """Manually triggers the Planner (PM Agent) to review the activity board."""
    from .supervisor import agent_supervisor
    import threading
    
    # Locate the Project Manager Agent (typically RES-PM-001)
    pm_url = agent_supervisor.get_agent_url("RES-PM-001")
    if not pm_url:
        raise HTTPException(status_code=500, detail="Project Manager agent (RES-PM-001) not found or not running.")
        
    instruction = f"Please review the current events and tasks for activity {activity_id} and propose any necessary blueprint modifications."
    
    # Trigger asynchronously using a simple HTTP call
    from .engine import _send_agent_request
    import threading
    threading.Thread(
        target=_send_agent_request, 
        args=(pm_url, "project_manager", f"plan_{activity_id}", instruction)
    ).start()
    
    return {"status": "success", "message": "Planner activated. Check blueprints for new proposals."}

@router.post("/system/step")
async def trigger_engine_step():
    """Manually process the next pending event in the bus."""
    try:
        result = engine.step()
        if not result:
            return {"status": "idle", "message": "No pending events to process."}
        return {"status": "success", "processed": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/system/settings")
async def get_system_settings():
    """Retrieve current system execution settings."""
    return {
        "auto_advance": engine.get_auto_advance()
    }

@router.post("/system/settings")
async def update_system_settings(auto_advance: bool):
    """Update system execution settings (e.g., toggle Auto/Manual mode)."""
    try:
        engine.set_auto_advance(auto_advance)
        return {"status": "success", "auto_advance": auto_advance}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/activity/{activity_id}/instruction")
async def update_activity_instruction(activity_id: str, instruction: str):
    """Updates user instruction and bumps version and triggers PM via event."""
    sql = """
        UPDATE activities 
        SET user_instruction = %s, 
            instruction_version = instruction_version + 1,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = %s
        RETURNING instruction_version
    """
    try:
        # Use execute_query to get the RETURNING value
        result = execute_query(sql, (instruction, activity_id))
        version = result[0]['instruction_version'] if result else 0
        
        # Emit event directly (human-initiated)
        payload = json.dumps({'instruction': instruction, 'version': version})
        execute_mutation("""
            INSERT INTO events (event_type, source, severity, activity_id, payload)
            VALUES ('human_instruction', 'human', 'critical', %s, %s)
        """, (activity_id, payload))
        
        # Record version so scheduler doesn't double-detect
        execute_mutation("""
            INSERT INTO system_state (key, value) 
            VALUES ('last_human_evt_' || %s, %s)
            ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
        """, (activity_id, str(version)))
        
        return {"status": "success", "version": version}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- EVENT TIMELINE API ---

@router.get("/events")
async def get_events(
    status: Optional[str] = Query(None, description="Filter by status: pending, processing, resolved, dismissed"),
    activity_id: Optional[str] = Query(None, description="Filter by activity"),
    limit: int = Query(50, description="Max results"),
    offset: int = Query(0, description="Offset for pagination")
):
    """Returns the event timeline for the dashboard."""
    sql = "SELECT * FROM events"
    params = []
    where_clauses = []

    if status:
        where_clauses.append("status = %s")
        params.append(status)
    if activity_id:
        where_clauses.append("activity_id = %s")
        params.append(activity_id)
    
    if where_clauses:
        sql += " WHERE " + " AND ".join(where_clauses)
    
    sql += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
    params.extend([limit, offset])
    
    try:
        results = execute_query(sql, tuple(params))
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/events")
async def create_event(
    event_type: str,
    severity: str = Query("normal"),
    activity_id: Optional[str] = Query(None),
    task_id: Optional[str] = Query(None),
    payload: str = Query("{}")
):
    """Human-initiated event creation from the dashboard."""
    try:
        execute_mutation("""
            INSERT INTO events (event_type, source, severity, activity_id, task_id, payload)
            VALUES (%s, 'human', %s, %s, %s, %s)
        """, (event_type, severity, activity_id, task_id, payload))
        return {"status": "success", "message": f"Event '{event_type}' created."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/events/{event_id}/dismiss")
async def dismiss_event(event_id: int):
    """Dismiss (ignore) a pending event."""
    try:
        count = execute_mutation("""
            UPDATE events 
            SET status = 'dismissed', resolved_by = 'human', resolved_at = CURRENT_TIMESTAMP 
            WHERE id = %s AND status = 'pending'
        """, (event_id,))
        if count == 0:
            raise HTTPException(status_code=404, detail="Event not found or already processed")
        return {"status": "success", "message": f"Event #{event_id} dismissed."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

