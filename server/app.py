"""
FastAPI application for Conversational State Engine
"""
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List, Dict, Any
import json
import sqlite3
import uuid
from datetime import datetime
import jsonpatch
from contextlib import contextmanager

from models import (
    IntentionSet, State, PatchProposal, ImpactAnalysis,
    Commit, Session, Patch, Conflict
)
from conflicts import create_default_detector
from renderer_incremental import create_renderer
from analyzer import MockAnalyzer

# 初始化FastAPI应用
app = FastAPI(title="Conversational State Engine", version="0.1.0")

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 数据库连接管理
@contextmanager
def get_db():
    conn = sqlite3.connect("state_engine.db")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

# 初始化数据库
def init_db():
    """初始化数据库表"""
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                current_version TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS states (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                version TEXT NOT NULL,
                schema_version TEXT NOT NULL,
                data TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id),
                UNIQUE(session_id, version)
            );
            
            CREATE TABLE IF NOT EXISTS draft_intentions (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                data TEXT NOT NULL,
                status TEXT DEFAULT 'draft',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            );
            
            CREATE TABLE IF NOT EXISTS patch_proposals (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                intention_set_id TEXT,
                patches TEXT NOT NULL,
                impact_analysis TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id),
                FOREIGN KEY (intention_set_id) REFERENCES draft_intentions(id)
            );
            
            CREATE TABLE IF NOT EXISTS commits (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                parent_version TEXT NOT NULL,
                new_version TEXT NOT NULL,
                patches TEXT NOT NULL,
                reverse_patches TEXT NOT NULL,
                author TEXT,
                message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            );
            
            CREATE TABLE IF NOT EXISTS artifacts (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                version TEXT NOT NULL,
                type TEXT NOT NULL,
                content TEXT NOT NULL,
                url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            );
        """)
        conn.commit()

# 启动时初始化数据库
init_db()

# 初始化组件
conflict_detector = create_default_detector()
analyzer = MockAnalyzer()
markdown_renderer = create_renderer("markdown")
csv_renderer = create_renderer("csv")

# ========== API端点实现 ==========

@app.get("/sessions/{sid}/state")
async def get_state(sid: str, paths: Optional[str] = Query(None)):
    """获取会话的当前状态（支持切片）"""
    with get_db() as conn:
        # 获取会话
        session = conn.execute(
            "SELECT * FROM sessions WHERE session_id = ?", (sid,)
        ).fetchone()
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # 获取当前版本的状态
        state_row = conn.execute(
            "SELECT * FROM states WHERE session_id = ? AND version = ?",
            (sid, session["current_version"])
        ).fetchone()
        
        if not state_row:
            raise HTTPException(status_code=404, detail="State not found")
        
        state_data = json.loads(state_row["data"])
        
        # 如果指定了paths，进行切片
        if paths:
            # TODO: 实现路径切片逻辑
            pass
        
        return State(
            version=state_row["version"],
            schema_version=state_row["schema_version"],
            data=state_data
        )

@app.post("/sessions/{sid}/intents")
async def draft_intents(sid: str, intention_set: IntentionSet):
    """保存意图草稿"""
    intention_set_id = f"int_{uuid.uuid4().hex[:8]}"
    
    with get_db() as conn:
        # 验证会话存在
        session = conn.execute(
            "SELECT * FROM sessions WHERE session_id = ?", (sid,)
        ).fetchone()
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # 保存意图草稿
        conn.execute(
            "INSERT INTO draft_intentions (id, session_id, data) VALUES (?, ?, ?)",
            (intention_set_id, sid, intention_set.model_dump_json())
        )
        conn.commit()
    
    return {
        "intention_set_id": intention_set_id,
        "status": "draft"
    }

@app.post("/sessions/{sid}/patch-proposals")
async def propose_patches(sid: str, intention_set_id: str):
    """根据意图生成补丁提案和影响分析"""
    proposal_id = f"pp_{uuid.uuid4().hex[:8]}"
    
    with get_db() as conn:
        # 获取意图草稿
        intention_row = conn.execute(
            "SELECT * FROM draft_intentions WHERE id = ? AND session_id = ?",
            (intention_set_id, sid)
        ).fetchone()
        
        if not intention_row:
            raise HTTPException(status_code=404, detail="Intention set not found")
        
        intentions = IntentionSet.model_validate_json(intention_row["data"])
        
        # 获取当前状态
        session = conn.execute(
            "SELECT * FROM sessions WHERE session_id = ?", (sid,)
        ).fetchone()
        
        state_row = conn.execute(
            "SELECT * FROM states WHERE session_id = ? AND version = ?",
            (sid, session["current_version"])
        ).fetchone()
        
        current_state = json.loads(state_row["data"])
        
        # 生成patches
        patches = []
        for intent in intentions.items:
            if intent.action == "add":
                patches.append({
                    "op": "add",
                    "path": intent.target_path,
                    "value": intent.value
                })
            elif intent.action == "modify":
                patches.append({
                    "op": "replace",
                    "path": intent.target_path,
                    "value": intent.value
                })
            elif intent.action == "delete":
                patches.append({
                    "op": "remove",
                    "path": intent.target_path
                })
        
        # 冲突检测和影响分析
        full_state = {
            "version": state_row["version"],
            "schema_version": state_row["schema_version"],
            "data": current_state
        }
        conflicts = conflict_detector.detect_with_patches(full_state, patches)
        
        # 确定风险级别
        risk_level = "low"
        if any(c.severity == "high" for c in conflicts):
            risk_level = "high"
        elif any(c.severity == "medium" for c in conflicts):
            risk_level = "medium"
        
        # 识别受影响的路径
        affected_paths = []
        for patch in patches:
            affected_paths.append(patch["path"])
        
        impact_analysis = ImpactAnalysis(
            affected_paths=affected_paths,
            risk_level=risk_level,
            semantic_conflicts=conflicts
        )
        
        # 保存提案
        proposal = PatchProposal(
            proposal_id=proposal_id,
            patches=[Patch(**p) for p in patches],
            impact_analysis=impact_analysis
        )
        
        conn.execute(
            """INSERT INTO patch_proposals 
               (id, session_id, intention_set_id, patches, impact_analysis) 
               VALUES (?, ?, ?, ?, ?)""",
            (proposal_id, sid, intention_set_id, 
             json.dumps(patches), impact_analysis.model_dump_json())
        )
        conn.commit()
    
    return proposal

@app.post("/sessions/{sid}/confirm")
async def confirm_stage(
    sid: str,
    stage: str,
    proposal_id: str,
    accept_patch_indices: Optional[List[int]] = None,
    apply_auto_fixes: bool = False
):
    """渐进式确认"""
    with get_db() as conn:
        # 获取提案
        proposal_row = conn.execute(
            "SELECT * FROM patch_proposals WHERE id = ? AND session_id = ?",
            (proposal_id, sid)
        ).fetchone()
        
        if not proposal_row:
            raise HTTPException(status_code=404, detail="Proposal not found")
        
        # 根据阶段更新状态
        if stage == "intent":
            status = "intent_confirmed"
        elif stage == "change":
            status = "change_confirmed"
            # TODO: 根据accept_patch_indices过滤patches
        elif stage == "side_effect":
            status = "ready_to_commit"
            # TODO: 应用auto_fixes
        else:
            raise HTTPException(status_code=400, detail="Invalid stage")
        
        # 更新提案状态
        conn.execute(
            "UPDATE patch_proposals SET status = ? WHERE id = ?",
            (status, proposal_id)
        )
        conn.commit()
    
    return {
        "stage": stage,
        "status": status
    }

@app.post("/sessions/{sid}/commit")
async def commit_changes(sid: str, proposal_id: str, message: Optional[str] = None):
    """提交变更"""
    commit_id = f"c_{uuid.uuid4().hex[:8]}"
    
    with get_db() as conn:
        # 获取提案
        proposal_row = conn.execute(
            "SELECT * FROM patch_proposals WHERE id = ? AND session_id = ?",
            (proposal_id, sid)
        ).fetchone()
        
        if not proposal_row:
            raise HTTPException(status_code=404, detail="Proposal not found")
        
        patches = json.loads(proposal_row["patches"])
        
        # 获取当前状态
        session = conn.execute(
            "SELECT * FROM sessions WHERE session_id = ?", (sid,)
        ).fetchone()
        
        state_row = conn.execute(
            "SELECT * FROM states WHERE session_id = ? AND version = ?",
            (sid, session["current_version"])
        ).fetchone()
        
        current_state = json.loads(state_row["data"])
        
        # 应用patches
        try:
            patch_obj = jsonpatch.JsonPatch(patches)
            new_state = patch_obj.apply(current_state)
            
            # 计算反向patches（用于撤销）
            reverse_patch = jsonpatch.make_patch(new_state, current_state)
            reverse_patches = list(reverse_patch)
            
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to apply patches: {str(e)}")
        
        # 生成新版本号
        current_version_num = int(session["current_version"][1:])
        new_version = f"v{current_version_num + 1}"
        
        # 保存新状态
        conn.execute(
            "INSERT INTO states (session_id, version, schema_version, data) VALUES (?, ?, ?, ?)",
            (sid, new_version, state_row["schema_version"], json.dumps(new_state))
        )
        
        # 保存commit
        conn.execute(
            """INSERT INTO commits 
               (id, session_id, parent_version, new_version, patches, reverse_patches, message) 
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (commit_id, sid, session["current_version"], new_version,
             json.dumps(patches), json.dumps(reverse_patches), message)
        )
        
        # 更新会话的当前版本
        conn.execute(
            "UPDATE sessions SET current_version = ?, updated_at = CURRENT_TIMESTAMP WHERE session_id = ?",
            (new_version, sid)
        )
        
        # 生成artifacts
        full_new_state = {
            "version": new_version,
            "schema_version": state_row["schema_version"],
            "data": new_state
        }
        
        # 增量渲染Markdown
        markdown_content = markdown_renderer.render_incremental(
            full_new_state, patches, "requirements.md"
        )
        
        # 渲染CSV
        csv_content = csv_renderer.render_acceptance_criteria(full_new_state)
        
        # 保存artifacts
        md_artifact_id = f"art_{uuid.uuid4().hex[:8]}"
        csv_artifact_id = f"art_{uuid.uuid4().hex[:8]}"
        
        conn.execute(
            "INSERT INTO artifacts (id, session_id, version, type, content) VALUES (?, ?, ?, ?, ?)",
            (md_artifact_id, sid, new_version, "markdown", markdown_content)
        )
        
        conn.execute(
            "INSERT INTO artifacts (id, session_id, version, type, content) VALUES (?, ?, ?, ?, ?)",
            (csv_artifact_id, sid, new_version, "csv", csv_content)
        )
        
        conn.commit()
    
    return {
        "commit_id": commit_id,
        "version": new_version,
        "artifacts": {
            "items": [
                {"id": md_artifact_id, "type": "markdown", "url": f"/artifacts/{md_artifact_id}"},
                {"id": csv_artifact_id, "type": "csv", "url": f"/artifacts/{csv_artifact_id}"}
            ]
        }
    }

@app.get("/sessions/{sid}/artifacts")
async def list_artifacts(sid: str, version: Optional[str] = None):
    """列出artifacts"""
    with get_db() as conn:
        if version:
            artifacts = conn.execute(
                "SELECT id, type, created_at FROM artifacts WHERE session_id = ? AND version = ?",
                (sid, version)
            ).fetchall()
        else:
            artifacts = conn.execute(
                "SELECT id, type, version, created_at FROM artifacts WHERE session_id = ?",
                (sid,)
            ).fetchall()
        
        items = []
        for art in artifacts:
            items.append({
                "id": art["id"],
                "type": art["type"],
                "url": f"/artifacts/{art['id']}",
                "version": art.get("version"),
                "created_at": art["created_at"]
            })
    
    return {"items": items}

@app.post("/sessions")
async def create_session():
    """创建新会话"""
    session_id = f"sess_{uuid.uuid4().hex[:8]}"
    
    # 初始状态
    initial_state = {
        "stories": [],
        "glossary": []
    }
    
    with get_db() as conn:
        # 创建会话
        conn.execute(
            "INSERT INTO sessions (session_id, current_version) VALUES (?, ?)",
            (session_id, "v1")
        )
        
        # 创建初始状态
        conn.execute(
            "INSERT INTO states (session_id, version, schema_version, data) VALUES (?, ?, ?, ?)",
            (session_id, "v1", "1.0.0", json.dumps(initial_state))
        )
        
        conn.commit()
    
    return {
        "session_id": session_id,
        "version": "v1"
    }

@app.get("/")
async def root():
    """API根路径"""
    return {
        "name": "Conversational State Engine",
        "version": "0.1.0",
        "docs": "/docs"
    }

# 健康检查
@app.get("/health")
async def health_check():
    return {"status": "healthy"}
