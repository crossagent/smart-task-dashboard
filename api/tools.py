import os
import json
import logging
from typing import Optional, Any, List
from .db import execute_query, execute_mutation, CustomEncoder, db_transaction
from . import engine

# Import the shared MCP singleton
from .mcp_app import mcp

logger = logging.getLogger("smart_task.task_management.tools")

@mcp.tool()
def query_sql(query: str) -> str:
    """Execute a raw read-only SQL query against the database."""
    upper_query = query.strip().upper()
    if any(upper_query.startswith(verb) for verb in ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE"]):
        return "Error: Only read-only queries (SELECT) are allowed via query_sql."
    try:
        results = execute_query(query)
        if not results: return "No rows returned."
        return json.dumps(results, indent=2, cls=CustomEncoder, ensure_ascii=False)
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def get_database_schema() -> str:
    """Retrieve the structure of all tables in the database."""
    query = """
    SELECT table_name, column_name, data_type, is_nullable
    FROM information_schema.columns
    WHERE table_schema = 'public'
    ORDER BY table_name, ordinal_position;
    """
    try:
        results = execute_query(query)
        schema = {}
        for row in (results or []):
            table = row['table_name']
            if table not in schema: schema[table] = []
            schema[table].append({"column": row['column_name'], "type": row['data_type']})
        return json.dumps(schema, indent=2, ensure_ascii=False)
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def upsert_resource(
    id: str,
    name: str,
    org_role: str,
    resource_type: str = "agent",
    is_available: bool = True,
    status: str = "Available",
    dingtalk_id: Optional[str] = None,
    professional_skill: Optional[str] = None
) -> str:
    """Create or update a record in the resources (compute slots) table."""
    sql = """
        INSERT INTO resources (id, name, org_role, resource_type, is_available, status, dingtalk_id, professional_skill)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id) DO UPDATE SET
            name = EXCLUDED.name,
            org_role = EXCLUDED.org_role,
            resource_type = EXCLUDED.resource_type,
            is_available = EXCLUDED.is_available,
            status = EXCLUDED.status,
            dingtalk_id = EXCLUDED.dingtalk_id,
            professional_skill = EXCLUDED.professional_skill,
            updated_at = CURRENT_TIMESTAMP
    """
    try:
        execute_mutation(sql, (id, name, org_role, resource_type, is_available, status, dingtalk_id, professional_skill))
        return f"Successfully processed resource '{name}' (ID: {id})."
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def upsert_module(
    id: str,
    name: str,
    owner_res_id: str,
    local_path: Optional[str] = None,
    repo_url: Optional[str] = None,
    knowledge_base: Optional[str] = None,
    parent_module_id: Optional[str] = None,
    layer_type: Optional[str] = None,
    entity_type: str = "Code"
) -> str:
    """Create or update a record in the modules (physical entities) table."""
    sql = """
        INSERT INTO modules (id, name, owner_res_id, local_path, repo_url, knowledge_base, parent_module_id, layer_type, entity_type)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id) DO UPDATE SET
            name = EXCLUDED.name,
            owner_res_id = EXCLUDED.owner_res_id,
            local_path = EXCLUDED.local_path,
            repo_url = EXCLUDED.repo_url,
            knowledge_base = EXCLUDED.knowledge_base,
            parent_module_id = EXCLUDED.parent_module_id,
            layer_type = EXCLUDED.layer_type,
            entity_type = EXCLUDED.entity_type,
            updated_at = CURRENT_TIMESTAMP
    """
    try:
        execute_mutation(sql, (id, name, owner_res_id, local_path, repo_url, knowledge_base, parent_module_id, layer_type, entity_type))
        return f"Successfully processed module '{name}' (ID: {id})."
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def upsert_milestone(
    id: str,
    activity_id: str,
    name: str,
    description: Optional[str] = None,
    target_date: Optional[str] = None,
    status: str = "Pending"
) -> str:
    """Create or update a record in the milestones table."""
    sql = """
        INSERT INTO milestones (id, activity_id, name, description, target_date, status)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (id) DO UPDATE SET
            activity_id = EXCLUDED.activity_id,
            name = EXCLUDED.name,
            description = EXCLUDED.description,
            target_date = EXCLUDED.target_date,
            status = EXCLUDED.status,
            updated_at = CURRENT_TIMESTAMP
    """
    try:
        execute_mutation(sql, (id, activity_id, name, description, target_date, status))
        return f"Successfully processed milestone '{name}' (ID: {id})."
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def upsert_activity(
    id: str,
    name: str,
    owner_res_id: str,
    status: str = "Active",
    priority: str = "P1",
    benefit: Optional[str] = None,
    deadline: Optional[str] = None,
    user_instruction: Optional[str] = None
) -> str:
    """Create or update a record in the activities table."""
    sql = """
        INSERT INTO activities (id, name, owner_res_id, status, priority, benefit, deadline, user_instruction)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id) DO UPDATE SET
            name = EXCLUDED.name,
            owner_res_id = EXCLUDED.owner_res_id,
            status = EXCLUDED.status,
            priority = EXCLUDED.priority,
            benefit = EXCLUDED.benefit,
            deadline = EXCLUDED.deadline,
            user_instruction = EXCLUDED.user_instruction,
            updated_at = CURRENT_TIMESTAMP
    """
    try:
        execute_mutation(sql, (id, name, owner_res_id, status, priority, benefit, deadline, user_instruction))
        return f"Successfully processed activity '{name}' (ID: {id})."
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def upsert_task(
    id: str,
    module_id: str,
    module_iteration_goal: str,
    activity_id: Optional[str] = None,
    milestone_id: Optional[str] = None,
    status: str = "pending",
    depends_on: Optional[List[str]] = None,
    estimated_hours: Optional[float] = None
) -> str:
    """Create or update a record in the tasks (state mutations) table."""
    sql = """
        INSERT INTO tasks (id, module_id, module_iteration_goal, activity_id, milestone_id, status, depends_on, estimated_hours)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id) DO UPDATE SET
            module_id = EXCLUDED.module_id,
            module_iteration_goal = EXCLUDED.module_iteration_goal,
            activity_id = EXCLUDED.activity_id,
            milestone_id = EXCLUDED.milestone_id,
            status = EXCLUDED.status,
            depends_on = EXCLUDED.depends_on,
            estimated_hours = EXCLUDED.estimated_hours,
            updated_at = CURRENT_TIMESTAMP
    """
    try:
        execute_mutation(sql, (id, module_id, module_iteration_goal, activity_id, milestone_id, status, depends_on or [], estimated_hours))
        
        # 如果任务直接标记为 ready，发出事件
        if status == 'ready':
            engine.emit_event(
                engine.EVENT_TASK_READY,
                activity_id=activity_id,
                task_id=id
            )
            if engine.get_auto_advance():
                engine.run_to_stable()
                
        return f"Successfully processed task (ID: {id})."
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def assign_task(task_id: str, resource_id: str) -> str:
    """Assign a task to a resource (compute slot) and record it in task_assignments."""
    sql = """
        INSERT INTO task_assignments (task_id, resource_id, assigned_at, status)
        VALUES (%s, %s, CURRENT_TIMESTAMP, 'active')
    """
    try:
        # Also update task status to in_progress if it was ready or pending
        execute_mutation("UPDATE tasks SET status = 'in_progress' WHERE id = %s AND status IN ('ready', 'pending')", (task_id,))
        execute_mutation(sql, (task_id, resource_id))
        return f"Task '{task_id}' assigned to resource '{resource_id}'."
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def get_task_context(task_id: str) -> str:
    """Retrieve full context for a task, including its target module's physical location."""
    query = """
        SELECT 
            t.id, t.module_iteration_goal, t.status as task_status,
            m.name as module_name, m.local_path, m.repo_url, m.knowledge_base,
            a.name as activity_name
        FROM tasks t
        JOIN modules m ON t.module_id = m.id
        LEFT JOIN activities a ON t.activity_id = a.id
        WHERE t.id = %s
    """
    try:
        results = execute_query(query, (task_id,))
        if not results: return f"Error: Task '{task_id}' not found."
        return json.dumps(results[0], indent=2, ensure_ascii=False, cls=CustomEncoder)
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def submit_task_deliverable(task_id: str, status: str, execution_result: str, artifact_data: Optional[str] = None) -> str:
    """Submit the final result and artifact of a task."""
    sql = """
        UPDATE tasks 
        SET status = %s, execution_result = %s, artifact = %s, updated_at = CURRENT_TIMESTAMP 
        WHERE id = %s
    """
    try:
        # 1. 更新任务状态（物理层基础修改）
        execute_mutation(sql, (status, execution_result, artifact_data, task_id))
        
        # 2. 发出事件
        # 先查一下 activity ID 以便填充事件上下文
        task_info = execute_query("SELECT activity_id FROM tasks WHERE id = %s", (task_id,))
        a_id = task_info[0]['activity_id'] if task_info else None
        
        engine.emit_event(
            engine.EVENT_TASK_COMPLETED,
            task_id=task_id,
            payload={
                "status": status,
                "execution_result": execution_result
            },
            activity_id=a_id
        )
        
        # 3. 阀门控制：如果是自动推进模式，立即执行冲刷
        summary = ""
        if engine.get_auto_advance():
            steps = engine.run_to_stable()
            summary = f" Auto-advanced {len(steps)} steps."
            
        return f"Task '{task_id}' submitted with status '{status}'.{summary}"
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def propose_blueprint_plan(
    title: str,
    actions: List[dict],
    activity_id: Optional[str] = None
) -> str:
    """
    Propose a set of blueprint modifications for human review.
    'actions' should be a list of dicts: {op: 'insert'|'update'|'delete', table: str, data: dict, where: dict}
    """
    sql = """
        INSERT INTO blueprint_plans (title, activity_id, proposed_actions, status)
        VALUES (%s, %s, %s, 'pending')
        RETURNING id
    """
    try:
        results = execute_query(sql, (title, activity_id, json.dumps(actions)))
        plan_id = results[0]['id']
        return f"Blueprint modification plan '{title}' proposed (ID: {plan_id}). Awaiting human approval."
    except Exception as e:
        return f"Error: {str(e)}"

def _execute_blueprint_actions(actions: List[dict], conn=None):
    """Executes a list of atomic blueprint modifications."""
    for action in actions:
        op = action.get('op')
        table = action.get('table')
        data = action.get('data', {})
        where = action.get('where', {})

        if op == 'update':
            cols = ", ".join([f"{k} = %s" for k in data.keys()])
            conds = " AND ".join([f"{k} = %s" for k in where.keys()])
            sql = f"UPDATE {table} SET {cols} WHERE {conds}"
            execute_mutation(sql, list(data.values()) + list(where.values()), connection=conn)
        
        elif op == 'insert':
            cols = ", ".join(data.keys())
            placeholders = ", ".join(["%s"] * len(data))
            sql = f"INSERT INTO {table} ({cols}) VALUES ({placeholders})"
            execute_mutation(sql, list(data.values()), connection=conn)
            
        elif op == 'delete':
            conds = " AND ".join([f"{k} = %s" for k in where.keys()])
            sql = f"DELETE FROM {table} WHERE {conds}"
            execute_mutation(sql, list(where.values()), connection=conn)

@mcp.tool()
def execute_approved_plan(plan_id: int) -> str:
    """
    Execute an approved blueprint modification plan. 
    This is called by the Architect agent after receiving a 'plan_approved' event.
    """
    from .db import db_transaction
    
    plan_query = "SELECT * FROM blueprint_plans WHERE id = %s"
    try:
        plan_rows = execute_query(plan_query, (plan_id,))
        if not plan_rows:
            return f"Error: Plan {plan_id} not found."
        
        plan = plan_rows[0]
        if plan['status'] != 'approved':
            return f"Error: Plan {plan_id} is in status '{plan['status']}', not 'approved'."
        
        actions = plan['proposed_actions']
        if isinstance(actions, str):
            actions = json.loads(actions)
            
        with db_transaction() as conn:
            try:
                _execute_blueprint_actions(actions, conn)
                execute_mutation("UPDATE blueprint_plans SET status = 'executed', updated_at = CURRENT_TIMESTAMP WHERE id = %s", (plan_id,), connection=conn)
                
                # 蓝图执行完毕后，触发引擎检查是否有新任务可以开始
                if engine.get_auto_advance():
                    engine.run_to_stable(connection=conn)
                    
                return f"Plan {plan_id} executed successfully."
            except Exception as e:
                # Execution failed - record error and notify agent
                error_msg = str(e)
                execute_mutation("UPDATE blueprint_plans SET status = 'failed_execution', error_message = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s", (error_msg, plan_id), connection=conn)
                return f"Execution of plan {plan_id} failed: {error_msg}. Please review and propose a corrected plan."
                
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def delete_record(table: str, id: str) -> str:
    """Delete a record from allowed tables."""
    allowed = {"resources", "activities", "milestones", "modules", "tasks", "task_assignments", "blueprint_plans"}
    if table not in allowed: return f"Error: Invalid table '{table}'."
    try:
        execute_mutation(f"DELETE FROM {table} WHERE id = %s", (id,))
        return f"Deleted record from '{table}'."
    except Exception as e:
        return f"Error: {str(e)}"


