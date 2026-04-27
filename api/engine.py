from __future__ import annotations

import logging
import json
import os
import httpx
from typing import Optional, List, Dict, Any
from .db import execute_query, execute_mutation, db_transaction
from .supervisor import agent_supervisor

logger = logging.getLogger("smart_task.engine")

# 事件类型常量
EVENT_TASK_COMPLETED = "task_completed"
EVENT_TASK_READY = "task_ready"
EVENT_TASK_ASSIGNED = "task_assigned"
EVENT_TASK_FAILED = "task_failed"
EVENT_HUMAN_INSTRUCTION = "human_instruction"
EVENT_PLAN_APPROVED = "plan_approved"

SETTINGS_FILE = "runtime_settings.json"

def get_auto_advance() -> bool:
    """从 runtime_settings.json 读取自动推进设置。"""
    if not os.path.exists(SETTINGS_FILE):
        return True  # 默认为开启
    try:
        with open(SETTINGS_FILE, "r") as f:
            settings = json.load(f)
            return settings.get("auto_advance", True)
    except Exception:
        return True

def set_auto_advance(value: bool):
    """保存自动推进设置。"""
    settings = {"auto_advance": value}
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f)

def emit_event(
    event_type: str,
    source: str = "system",
    payload: Dict[str, Any] = None,
    activity_id: str = None,
    task_id: str = None,
    resource_id: str = None,
    connection=None
) -> int:
    """向事件总线写入新事件。"""
    query = """
        INSERT INTO events (event_type, source, payload, activity_id, task_id, resource_id, status)
        VALUES (%s, %s, %s, %s, %s, %s, 'pending')
        RETURNING id
    """
    params = (
        event_type,
        source,
        json.dumps(payload or {}),
        activity_id,
        task_id,
        resource_id
    )
    
    res = execute_query(query, params, connection=connection)
    return res[0]['id']

def step(connection=None) -> Optional[Dict[str, Any]]:
    """物理步进：处理总线中最早的一条 pending 事件。"""
    # 查找并锁定最早的待处理事件
    query = "SELECT * FROM events WHERE status = 'pending' ORDER BY id LIMIT 1 FOR UPDATE SKIP LOCKED"
    events = execute_query(query, connection=connection)
    
    if not events:
        return None
        
    event = events[0]
    event_id = event['id']
    event_type = event['event_type']
    
    logger.info(f"Engine processing event {event_id} ({event_type})")
    
    try:
        summary = _handle_event(event, connection=connection)
        
        # 标记为已解决
        execute_mutation(
            "UPDATE events SET status = 'resolved', resolved_at = CURRENT_TIMESTAMP WHERE id = %s",
            (event_id,),
            connection=connection
        )
        
        return {
            "event_id": event_id,
            "type": event_type,
            "summary": summary
        }
    except Exception as e:
        logger.error(f"Engine failed to process event {event_id}: {e}")
        # 记录错误并标记失败
        execute_mutation(
            "UPDATE events SET status = 'failed', payload = payload || %s::jsonb WHERE id = %s",
            (json.dumps({"error": str(e)}), event_id),
            connection=connection
        )
        raise e

def run_to_stable(connection=None) -> List[Dict[str, Any]]:
    """因果冲刷：循环执行 step() 直到队列清空。"""
    results = []
    
    if connection:
        # 在外部提供的连接（事务）中执行
        while True:
            res = step(connection=connection)
            if not res:
                break
            results.append(res)
    else:
        # 开启新事务执行
        with db_transaction() as conn:
            while True:
                res = step(connection=conn)
                if not res:
                    break
                results.append(res)
                
    return results

def _handle_event(event: Dict[str, Any], connection=None) -> str:
    """根据事件类型分发处理逻辑。"""
    etype = event['event_type']
    
    if etype == EVENT_TASK_COMPLETED:
        return _handle_task_completed(event, connection)
    elif etype == EVENT_TASK_READY:
        return _handle_task_ready(event, connection)
    elif etype == EVENT_PLAN_APPROVED:
        return "Plan approved, waiting for external execution or next step."
    else:
        return f"Acknowledged event {etype}, no deterministic action required."

def _handle_task_completed(event: Dict[str, Any], connection=None) -> str:
    """处理任务完成：回收资源，并尝试推进 DAG 产生 task_ready 事件。"""
    task_id = event['task_id']
    
    # 1. 资源回收
    assignments = execute_query(
        "SELECT resource_id FROM task_assignments WHERE task_id = %s AND status = 'active'",
        (task_id,),
        connection=connection
    )
    
    res_id = None
    if assignments:
        res_id = assignments[0]['resource_id']
        execute_mutation(
            "UPDATE resources SET is_available = True WHERE id = %s",
            (res_id,),
            connection=connection
        )
        execute_mutation(
            "UPDATE task_assignments SET status = 'completed', completed_at = CURRENT_TIMESTAMP WHERE task_id = %s AND status = 'active'",
            (task_id,),
            connection=connection
        )

    # 2. DAG 推进
    # 查找依赖于此任务且处于 pending 状态的任务
    dependents = execute_query(
        "SELECT id, activity_id, depends_on FROM tasks WHERE %s = ANY(depends_on) AND status = 'pending'",
        (task_id,),
        connection=connection
    )
    
    unlocked_count = 0
    for dep in dependents:
        dep_id = dep['id']
        dependencies = dep['depends_on'] or []
        
        # 检查所有依赖是否都已完成
        unfinished = execute_query(
            "SELECT count(*) as count FROM tasks WHERE id = ANY(%s) AND status != 'done'",
            (dependencies,),
            connection=connection
        )[0]['count']
        
        if unfinished == 0:
            # 解锁任务
            execute_mutation("UPDATE tasks SET status = 'ready' WHERE id = %s", (dep_id,), connection=connection)
            emit_event(
                EVENT_TASK_READY,
                task_id=dep_id,
                activity_id=dep['activity_id'],
                connection=connection
            )
            unlocked_count += 1
            
    return f"Recovered resource {res_id}. Unlocked {unlocked_count} tasks."

def _handle_task_ready(event: Dict[str, Any], connection=None) -> str:
    """处理任务就绪：尝试指派资源并触发 Agent 产生 task_assigned 事件。"""
    task_id = event['task_id']
    
    task_data = execute_query(
        "SELECT t.id, t.module_id, t.module_iteration_goal, m.owner_res_id, t.activity_id "
        "FROM tasks t JOIN modules m ON t.module_id = m.id "
        "WHERE t.id = %s AND t.status = 'ready'",
        (task_id,),
        connection=connection
    )
    
    if not task_data:
        return f"Task {task_id} not ready."
        
    task = task_data[0]
    owner_id = task['owner_res_id']
    
    # 检查资源是否可用
    res_data = execute_query(
        "SELECT id FROM resources WHERE id = %s AND is_available = True",
        (owner_id,),
        connection=connection
    )
    
    if not res_data:
        return f"Resource {owner_id} busy. Task {task_id} stays ready."

    # 执行指派
    execute_mutation("UPDATE tasks SET status = 'in_progress' WHERE id = %s", (task_id,), connection=connection)
    execute_mutation("UPDATE resources SET is_available = False WHERE id = %s", (owner_id,), connection=connection)
    execute_mutation(
        "INSERT INTO task_assignments (task_id, resource_id, status) VALUES (%s, %s, 'active')",
        (task_id, owner_id),
        connection=connection
    )
    
    # 触发外部 Agent
    handle = agent_supervisor.pool.get(owner_id)
    if handle:
        # 支持对象 (PersistentAgentHandle) 或 字典 (Mock)
        h_url = getattr(handle, 'url', None) or handle.get('url')
        h_agent_id = getattr(handle, 'agent_id', None) or handle.get('agent_id')
        _send_agent_request(h_url, h_agent_id, task_id, task['module_iteration_goal'])
    
    emit_event(
        EVENT_TASK_ASSIGNED,
        task_id=task_id,
        resource_id=owner_id,
        activity_id=task['activity_id'],
        connection=connection
    )
    
    return f"Assigned task {task_id} to {owner_id}."

def _send_agent_request(url: str, agent_id: str, session_id: str, text: str):
    """发送 HTTP 请求给 Agent 的 helper 函数。"""
    try:
        with httpx.Client(timeout=5.0) as client:
            client.post(
                f"{url}/run", 
                json={
                    "app_name": agent_id, 
                    "session_id": session_id, 
                    "new_message": {"parts": [{"text": text}]}
                }
            )
    except Exception as e:
        logger.error(f"Agent trigger failed: {e}")
