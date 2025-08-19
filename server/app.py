"""
FastAPI application for Conversational State Engine
"""

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import jsonpatch

# Load environment variables from .env file
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

from domains.dialogue.analyzer import LLMAnalyzer, MockAnalyzer
from domains.rendering.incremental import create_renderer
from domains.state.conflicts import ConflictResolver, create_default_detector
from domains.state.models import (
    Commit,
    CommitRequest,
    ConfirmChangesRequest,
    ConfirmIntentRequest,
    ConfirmSideEffectsRequest,
    Conflict,
    ImpactAnalysis,
    IntentionSet,
    Patch,
    PatchProposal,
    PatchProposalRequest,
    Session,
    State,
)

from .auth import (
    Token,
    User,
    UserCreate,
    UserLogin,
    authenticate_user,
    check_session_access,
    create_access_token,
    create_user,
    get_current_user,
    grant_session_access,
    init_auth_db,
    require_permission,
)
from .context_slicer import ContextSlicer, SliceConfig
from .validation import schema_validator

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
        conn.executescript(
            """
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
                selected_patch_indices TEXT DEFAULT '[]',
                applied_auto_fixes TEXT DEFAULT '{}',
                stage_confirmations TEXT DEFAULT '{}',
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
        """
        )
        conn.commit()


# 启动时初始化数据库
init_db()
init_auth_db()

# 初始化组件
conflict_detector = create_default_detector()
# 尝试使用OpenAI兼容分析器，否则降级到Mock
import os

llm_provider = os.getenv("CSE_LLM_PROVIDER", "mock")
if llm_provider.lower() == "openai" and (
    os.getenv("OPENAI_API_KEY") or os.getenv("CSE_API_KEY")
):
    # 支持OpenAI兼容的API提供商
    analyzer_kwargs = {}
    if os.getenv("CSE_MODEL"):
        analyzer_kwargs["model"] = os.getenv("CSE_MODEL")
    if os.getenv("CSE_BASE_URL") or os.getenv("OPENAI_BASE_URL"):
        analyzer_kwargs["base_url"] = os.getenv("CSE_BASE_URL") or os.getenv(
            "OPENAI_BASE_URL"
        )
    if os.getenv("CSE_API_KEY"):
        analyzer_kwargs["api_key"] = os.getenv("CSE_API_KEY")

    analyzer = LLMAnalyzer.create("openai", **analyzer_kwargs)
    print(f"✅ LLM Analyzer initialized with provider: {llm_provider}")
else:
    print(
        "Using mock analyzer (set CSE_LLM_PROVIDER=openai and OPENAI_API_KEY/CSE_API_KEY to use OpenAI-compatible API)"
    )
    analyzer = MockAnalyzer()

markdown_renderer = create_renderer("markdown")
csv_renderer = create_renderer("csv")
context_slicer = ContextSlicer()
conflict_resolver = ConflictResolver()

# ========== 认证端点 ==========


@app.post("/auth/register", response_model=dict)
async def register(user_data: UserCreate):
    """注册新用户"""
    try:
        user = create_user(user_data)
        return {
            "message": "User created successfully",
            "user_id": user.user_id,
            "email": user.email,
            "role": user.role,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user: {str(e)}",
        )


@app.post("/auth/login", response_model=Token)
async def login(user_credentials: UserLogin):
    """用户登录"""
    user = authenticate_user(user_credentials.email, user_credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": user.user_id, "email": user.email, "role": user.role},
        expires_delta=access_token_expires,
    )

    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/auth/me", response_model=User)
async def get_me(current_user: User = Depends(get_current_user)):
    """获取当前用户信息"""
    return current_user


# ========== API端点实现 ==========


@app.post("/sessions/{sid}/analyze")
async def analyze_message(
    sid: str,
    request: Dict[str, str],  # {"message": "user input"}
    auto_apply: bool = Query(default=False),
    current_user: User = Depends(get_current_user),
):
    """使用LLM分析用户消息并生成意图"""
    # Check session access
    check_session_access(sid, current_user)

    message = request.get("message", "")
    if not message.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Message cannot be empty"
        )

    with get_db() as conn:
        # 获取当前状态
        session = conn.execute(
            "SELECT * FROM sessions WHERE session_id = ?", (sid,)
        ).fetchone()

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        state_row = conn.execute(
            "SELECT * FROM states WHERE session_id = ? AND version = ?",
            (sid, session["current_version"]),
        ).fetchone()

        if not state_row:
            raise HTTPException(status_code=404, detail="State not found")

        current_state = json.loads(state_row["data"])

        # 使用ContextSlicer预处理状态以提供更相关的上下文
        context_slices = context_slicer.slice_state({"data": current_state}, message)

        # 提取最相关的上下文数据
        relevant_context = {}
        for slice_obj in context_slices[:3]:  # 使用前3个最相关的切片
            relevant_context[slice_obj.path] = slice_obj.data

        # 使用LLM分析器
        try:
            if hasattr(analyzer, "analyze") and hasattr(analyzer.analyze, "__call__"):
                # 如果是异步方法
                if hasattr(analyzer, "client") and analyzer.client:
                    intention_set = await analyzer.analyze(message, relevant_context)
                else:
                    # 同步Mock分析器
                    intention_set = analyzer.analyze(message, relevant_context)
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Analyzer not properly initialized",
                )
        except Exception as e:
            print(f"Analysis error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to analyze message: {str(e)}",
            )

    result = {
        "message": message,
        "intentions": intention_set.model_dump(),
        "analyzer_type": (
            "openai" if hasattr(analyzer, "client") and analyzer.client else "mock"
        ),
        "context_analysis": {
            "slices_used": len(context_slices),
            "relevant_paths": list(relevant_context.keys()),
            "top_slices": [
                {
                    "id": slice_obj.id,
                    "path": slice_obj.path,
                    "importance": slice_obj.importance_score,
                    "size": slice_obj.size,
                }
                for slice_obj in context_slices[:3]
            ],
        },
    }

    # If auto_apply is True, automatically progress through the pipeline
    if auto_apply:
        try:
            # Check write permission for auto-apply
            if "write" not in current_user.permissions:
                result["auto_apply_error"] = "Insufficient permissions for auto-apply"
                return result

            # Save intention draft
            intention_set_id = f"int_{uuid.uuid4().hex[:8]}"
            conn.execute(
                "INSERT INTO draft_intentions (id, session_id, data) VALUES (?, ?, ?)",
                (intention_set_id, sid, intention_set.model_dump_json()),
            )
            conn.commit()

            # Generate patches
            patches = []
            for intent in intention_set.items:
                if intent.action == "add":
                    patches.append(
                        {"op": "add", "path": intent.target_path, "value": intent.value}
                    )
                elif intent.action == "modify":
                    patches.append(
                        {
                            "op": "replace",
                            "path": intent.target_path,
                            "value": intent.value,
                        }
                    )
                elif intent.action == "delete":
                    patches.append({"op": "remove", "path": intent.target_path})

            # Conflict detection
            full_state = {
                "version": state_row["version"],
                "schema_version": state_row["schema_version"],
                "data": current_state,
            }
            conflicts = conflict_detector.detect_with_patches(full_state, patches)

            # Create patch proposal
            proposal_id = f"pp_{uuid.uuid4().hex[:8]}"
            risk_level = "low"
            if any(c.severity == "high" for c in conflicts):
                risk_level = "high"
            elif any(c.severity == "medium" for c in conflicts):
                risk_level = "medium"

            affected_paths = [patch["path"] for patch in patches]
            impact_analysis = ImpactAnalysis(
                affected_paths=affected_paths,
                risk_level=risk_level,
                semantic_conflicts=conflicts,
            )

            conn.execute(
                """INSERT INTO patch_proposals
                   (id, session_id, intention_set_id, patches, impact_analysis)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    proposal_id,
                    sid,
                    intention_set_id,
                    json.dumps(patches),
                    impact_analysis.model_dump_json(),
                ),
            )
            conn.commit()

            # Auto-confirm all stages if no high-severity conflicts
            if risk_level != "high":
                # Stage 1: Confirm intent
                stage_confirmations = {
                    "intent_confirmed": True,
                    "intent_confirmed_at": datetime.utcnow().isoformat(),
                    "intent_confirmed_by": current_user.user_id,
                    "changes_confirmed": True,
                    "changes_confirmed_at": datetime.utcnow().isoformat(),
                    "changes_confirmed_by": current_user.user_id,
                    "selected_patches_count": len(patches),
                    "side_effects_confirmed": True,
                    "side_effects_confirmed_at": datetime.utcnow().isoformat(),
                    "side_effects_confirmed_by": current_user.user_id,
                    "auto_fixes_applied": False,
                }

                conn.execute(
                    """UPDATE patch_proposals
                       SET status = 'ready_to_commit', stage_confirmations = ?
                       WHERE id = ?""",
                    (json.dumps(stage_confirmations), proposal_id),
                )

                # Apply patches and commit
                commit_id = f"c_{uuid.uuid4().hex[:8]}"

                try:
                    patch_obj = jsonpatch.JsonPatch(patches)
                    new_state = patch_obj.apply(current_state)
                    reverse_patch = jsonpatch.make_patch(new_state, current_state)
                    reverse_patches = list(reverse_patch)
                except Exception as e:
                    result["auto_apply_error"] = f"Failed to apply patches: {str(e)}"
                    return result

                # Generate new version
                current_version_num = int(session["current_version"][1:])
                new_version = f"v{current_version_num + 1}"

                # Save new state
                conn.execute(
                    "INSERT INTO states (session_id, version, schema_version, data) VALUES (?, ?, ?, ?)",
                    (
                        sid,
                        new_version,
                        state_row["schema_version"],
                        json.dumps(new_state),
                    ),
                )

                # Save commit
                conn.execute(
                    """INSERT INTO commits
                       (id, session_id, parent_version, new_version, patches, reverse_patches, message)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        commit_id,
                        sid,
                        session["current_version"],
                        new_version,
                        json.dumps(patches),
                        json.dumps(reverse_patches),
                        f"Auto-applied: {message}",
                    ),
                )

                # Update session version
                conn.execute(
                    "UPDATE sessions SET current_version = ?, updated_at = CURRENT_TIMESTAMP WHERE session_id = ?",
                    (new_version, sid),
                )

                # Generate artifacts
                full_new_state = {
                    "version": new_version,
                    "schema_version": state_row["schema_version"],
                    "data": new_state,
                }

                markdown_content = markdown_renderer.render_incremental(
                    full_new_state, patches, "requirements.md"
                )
                csv_content = csv_renderer.render_acceptance_criteria(full_new_state)

                md_artifact_id = f"art_{uuid.uuid4().hex[:8]}"
                csv_artifact_id = f"art_{uuid.uuid4().hex[:8]}"

                conn.execute(
                    "INSERT INTO artifacts (id, session_id, version, type, content) VALUES (?, ?, ?, ?, ?)",
                    (md_artifact_id, sid, new_version, "markdown", markdown_content),
                )

                conn.execute(
                    "INSERT INTO artifacts (id, session_id, version, type, content) VALUES (?, ?, ?, ?, ?)",
                    (csv_artifact_id, sid, new_version, "csv", csv_content),
                )

                conn.commit()

                result.update(
                    {
                        "auto_applied": True,
                        "commit_id": commit_id,
                        "new_version": new_version,
                        "artifacts": [
                            {"id": md_artifact_id, "type": "markdown"},
                            {"id": csv_artifact_id, "type": "csv"},
                        ],
                        "conflicts_detected": len(conflicts),
                        "risk_level": risk_level,
                    }
                )
            else:
                result.update(
                    {
                        "auto_applied": False,
                        "proposal_id": proposal_id,
                        "conflicts_detected": len(conflicts),
                        "risk_level": risk_level,
                        "message": "High-risk conflicts detected, manual confirmation required",
                    }
                )

        except Exception as e:
            print(f"Auto-apply error: {e}")
            result["auto_apply_error"] = str(e)

    return result


@app.get("/sessions/{sid}/context-slices")
async def get_context_slices(
    sid: str,
    intent: Optional[str] = Query(None),
    max_slices: int = Query(default=10, le=50),
    current_user: User = Depends(get_current_user),
):
    """获取智能上下文切片"""
    # Check session access
    check_session_access(sid, current_user)

    with get_db() as conn:
        # 获取会话和状态
        session = conn.execute(
            "SELECT * FROM sessions WHERE session_id = ?", (sid,)
        ).fetchone()

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        state_row = conn.execute(
            "SELECT * FROM states WHERE session_id = ? AND version = ?",
            (sid, session["current_version"]),
        ).fetchone()

        if not state_row:
            raise HTTPException(status_code=404, detail="State not found")

        state_data = json.loads(state_row["data"])

        # 构建完整状态
        full_state = {
            "version": state_row["version"],
            "schema_version": state_row["schema_version"],
            "data": state_data,
        }

        # 生成智能切片
        slices = context_slicer.slice_state(full_state, intent)

        return {
            "session_id": sid,
            "version": state_row["version"],
            "intent": intent,
            "total_slices": len(slices),
            "returned_slices": min(len(slices), max_slices),
            "slices": [
                {
                    "id": slice_obj.id,
                    "path": slice_obj.path,
                    "size": slice_obj.size,
                    "importance_score": slice_obj.importance_score,
                    "metadata": slice_obj.metadata,
                    "dependencies": slice_obj.dependencies,
                    "data": slice_obj.data,
                }
                for slice_obj in slices[:max_slices]
            ],
        }


@app.get("/sessions/{sid}/state")
async def get_state(
    sid: str,
    paths: Optional[str] = Query(None),
    intent: Optional[str] = Query(None),
    slice_mode: bool = Query(default=False),
    current_user: User = Depends(get_current_user),
):
    """获取会话的当前状态（支持智能切片）"""
    # Check session access
    check_session_access(sid, current_user)
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
            (sid, session["current_version"]),
        ).fetchone()

        if not state_row:
            raise HTTPException(status_code=404, detail="State not found")

        state_data = json.loads(state_row["data"])

        # 构建完整状态对象
        full_state = {
            "version": state_row["version"],
            "schema_version": state_row["schema_version"],
            "data": state_data,
        }

        # 智能切片处理
        if slice_mode:
            # 使用ContextSlicer进行智能切片
            slices = context_slicer.slice_state(full_state, intent)

            # 返回切片信息和最相关的数据
            return {
                "session_id": sid,
                "version": state_row["version"],
                "schema_version": state_row["schema_version"],
                "slicing_enabled": True,
                "slice_count": len(slices),
                "slices": [
                    {
                        "id": slice_obj.id,
                        "path": slice_obj.path,
                        "size": slice_obj.size,
                        "importance_score": slice_obj.importance_score,
                        "metadata": slice_obj.metadata,
                        "dependencies": slice_obj.dependencies,
                        "data": slice_obj.data,
                    }
                    for slice_obj in slices[:10]  # 只返回前10个最重要的切片
                ],
                "intent_analyzed": intent or "No intent provided",
            }

        # 传统路径过滤处理
        elif paths:
            # 支持多个路径，用逗号分隔
            path_list = [p.strip() for p in paths.split(",")]
            filtered_data = {}

            for path in path_list:
                try:
                    # 使用ContextSlicer的路径解析功能
                    path_value = context_slicer._get_path_value(state_data, path)
                    if path_value is not None:
                        # 将路径转换为嵌套字典结构
                        _set_path_value(filtered_data, path, path_value)
                except Exception as e:
                    print(f"Error filtering path {path}: {e}")
                    continue

            return State(
                version=state_row["version"],
                schema_version=state_row["schema_version"],
                data=filtered_data if filtered_data else state_data,
            )

        # 默认返回完整状态
        return State(
            version=state_row["version"],
            schema_version=state_row["schema_version"],
            data=state_data,
        )


def _set_path_value(target: Dict[str, Any], path: str, value: Any):
    """在目标字典中设置路径值"""
    if path == "/" or not path:
        return

    parts = path.strip("/").split("/")
    current = target

    for i, part in enumerate(parts[:-1]):
        if part not in current:
            current[part] = {}
        current = current[part]

    if parts:
        current[parts[-1]] = value


@app.post("/sessions/{sid}/intents")
async def draft_intents(
    sid: str,
    intention_set: IntentionSet,
    current_user: User = Depends(get_current_user),
):
    """保存意图草稿"""
    # Check write permission
    if "write" not in current_user.permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions. Required: write",
        )

    # Validate intention set schema
    validation_result = schema_validator.validate_intentions(intention_set.dict())
    if not validation_result.is_valid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": "Intention validation failed",
                "validation_errors": validation_result.to_dict(),
            },
        )

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
            (intention_set_id, sid, intention_set.model_dump_json()),
        )
        conn.commit()

    return {"intention_set_id": intention_set_id, "status": "draft"}


@app.post("/sessions/{sid}/patch-proposals")
async def propose_patches(
    sid: str,
    request: PatchProposalRequest,
    current_user: User = Depends(get_current_user),
):
    """根据意图生成补丁提案和影响分析"""
    # Check write permission
    if "write" not in current_user.permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions. Required: write",
        )

    proposal_id = f"pp_{uuid.uuid4().hex[:8]}"

    intention_set_id = request.intention_set_id

    with get_db() as conn:
        # 获取意图草稿
        intention_row = conn.execute(
            "SELECT * FROM draft_intentions WHERE id = ? AND session_id = ?",
            (intention_set_id, sid),
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
            (sid, session["current_version"]),
        ).fetchone()

        current_state = json.loads(state_row["data"])

        # 生成patches
        patches = []
        for intent in intentions.items:
            if intent.action == "add":
                patches.append(
                    {"op": "add", "path": intent.target_path, "value": intent.value}
                )
            elif intent.action == "modify":
                patches.append(
                    {"op": "replace", "path": intent.target_path, "value": intent.value}
                )
            elif intent.action == "delete":
                patches.append({"op": "remove", "path": intent.target_path})

        # 为冲突检测添加 /data 前缀
        patches_for_detection = []
        for p in patches:
            prefixed = p.copy()
            prefixed["path"] = f"/data{p['path']}"
            patches_for_detection.append(prefixed)

        # 冲突检测和影响分析
        full_state = {
            "version": state_row["version"],
            "schema_version": state_row["schema_version"],
            "data": current_state,
        }
        conflicts = conflict_detector.detect_with_patches(
            full_state, patches_for_detection
        )

        # Validate generated patches
        patch_validation = schema_validator.validate_patches(patches)
        if not patch_validation.is_valid:
            # Log validation errors but continue (patches might still be applicable)
            print(f"Patch validation warnings: {patch_validation.errors}")

        # 生成自动修复建议
        auto_fix_patches = []
        if conflicts:
            try:
                auto_fixes = conflict_resolver.suggest_fixes(conflicts, full_state)
                auto_fix_patches = conflict_resolver.prioritize_fixes(auto_fixes)

                # Validate auto-fix patches
                if auto_fix_patches:
                    fix_validation = schema_validator.validate_patches(auto_fix_patches)
                    if not fix_validation.is_valid:
                        print(f"Auto-fix validation warnings: {fix_validation.errors}")
                        # Filter out invalid auto-fixes
                        auto_fix_patches = [
                            p
                            for i, p in enumerate(auto_fix_patches)
                            if not any(
                                f"patch[{i}]" in err.get("path", "")
                                for err in fix_validation.errors
                            )
                        ]

            except Exception as e:
                print(f"Error generating auto-fixes: {e}")
                auto_fix_patches = []

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
            semantic_conflicts=conflicts,
        )

        # 保存提案
        proposal = PatchProposal(
            proposal_id=proposal_id,
            patches=[Patch(**p) for p in patches],
            impact_analysis=impact_analysis,
        )

        # Store auto-fix patches in the applied_auto_fixes field
        conn.execute(
            """INSERT INTO patch_proposals
               (id, session_id, intention_set_id, patches, impact_analysis, applied_auto_fixes)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                proposal_id,
                sid,
                intention_set_id,
                json.dumps(patches),
                impact_analysis.model_dump_json(),
                json.dumps(auto_fix_patches),
            ),
        )
        conn.commit()

    # Enhanced response with conflict resolution information
    response = proposal.model_dump()
    response.update(
        {
            "conflicts_detected": len(conflicts),
            "auto_fix_patches": auto_fix_patches,
            "conflict_resolution": {
                "total_fixes_available": len(auto_fix_patches),
                "high_priority_fixes": len(
                    [
                        f
                        for f in auto_fix_patches
                        if any(
                            keyword in f.get("reason", "").lower()
                            for keyword in ["priority", "auth", "dependency"]
                        )
                    ]
                ),
                "resolution_summary": f"Generated {len(auto_fix_patches)} automatic fixes for {len(conflicts)} detected conflicts",
            },
        }
    )

    return response


@app.post("/sessions/{sid}/resolve-conflicts")
async def resolve_conflicts(
    sid: str,
    proposal_id: str,
    apply_fixes: bool = Query(default=False),
    current_user: User = Depends(get_current_user),
):
    """获取冲突解决方案并可选择性应用自动修复"""
    # Check write permission
    if "write" not in current_user.permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions. Required: write",
        )

    with get_db() as conn:
        # 获取提案
        proposal_row = conn.execute(
            "SELECT * FROM patch_proposals WHERE id = ? AND session_id = ?",
            (proposal_id, sid),
        ).fetchone()

        if not proposal_row:
            raise HTTPException(status_code=404, detail="Proposal not found")

        # 获取当前状态
        session = conn.execute(
            "SELECT * FROM sessions WHERE session_id = ?", (sid,)
        ).fetchone()

        state_row = conn.execute(
            "SELECT * FROM states WHERE session_id = ? AND version = ?",
            (sid, session["current_version"]),
        ).fetchone()

        current_state = json.loads(state_row["data"])
        full_state = {
            "version": state_row["version"],
            "schema_version": state_row["schema_version"],
            "data": current_state,
        }

        # 重新分析冲突以确保最新状态
        patches = json.loads(proposal_row["patches"])
        conflicts = conflict_detector.detect_with_patches(full_state, patches)

        # 生成修复建议
        auto_fixes = conflict_resolver.suggest_fixes(conflicts, full_state)
        prioritized_fixes = conflict_resolver.prioritize_fixes(auto_fixes)

        if apply_fixes and prioritized_fixes:
            # 应用自动修复到提案中
            updated_patches = patches + prioritized_fixes

            # 更新提案中的修复信息
            conn.execute(
                "UPDATE patch_proposals SET applied_auto_fixes = ? WHERE id = ?",
                (json.dumps(prioritized_fixes), proposal_id),
            )

            # 重新检测冲突以验证修复效果
            remaining_conflicts = conflict_detector.detect_with_patches(
                full_state, updated_patches
            )

            conn.commit()

            return {
                "proposal_id": proposal_id,
                "conflicts_before_fix": len(conflicts),
                "conflicts_after_fix": len(remaining_conflicts),
                "fixes_applied": len(prioritized_fixes),
                "applied_fixes": prioritized_fixes,
                "remaining_conflicts": [
                    {
                        "type": c.type,
                        "severity": c.severity,
                        "message": c.message,
                        "path": c.path,
                    }
                    for c in remaining_conflicts
                ],
                "resolution_success": len(remaining_conflicts) < len(conflicts),
                "updated_patches": updated_patches,
            }
        else:
            # 仅返回修复建议，不应用
            return {
                "proposal_id": proposal_id,
                "conflicts_detected": len(conflicts),
                "available_fixes": len(prioritized_fixes),
                "conflicts": [
                    {
                        "type": c.type,
                        "severity": c.severity,
                        "message": c.message,
                        "path": c.path,
                        "suggestion": c.suggestion,
                    }
                    for c in conflicts
                ],
                "suggested_fixes": prioritized_fixes,
                "fix_summary": {
                    "high_priority": len(
                        [
                            f
                            for f in prioritized_fixes
                            if any(
                                kw in f.get("reason", "").lower()
                                for kw in ["priority", "auth", "dependency"]
                            )
                        ]
                    ),
                    "structural": len(
                        [
                            f
                            for f in prioritized_fixes
                            if "structural" in f.get("reason", "").lower()
                        ]
                    ),
                    "timeline": len(
                        [
                            f
                            for f in prioritized_fixes
                            if "timeline" in f.get("reason", "").lower()
                        ]
                    ),
                },
            }


@app.post("/sessions/{sid}/validate-state")
async def validate_session_state(
    sid: str, current_user: User = Depends(get_current_user)
):
    """Comprehensive state validation with business rules"""
    # Check session access
    check_session_access(sid, current_user)

    with get_db() as conn:
        # Get current state
        session = conn.execute(
            "SELECT * FROM sessions WHERE session_id = ?", (sid,)
        ).fetchone()

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        state_row = conn.execute(
            "SELECT * FROM states WHERE session_id = ? AND version = ?",
            (sid, session["current_version"]),
        ).fetchone()

        if not state_row:
            raise HTTPException(status_code=404, detail="State not found")

        # Construct full state for validation
        full_state = {
            "version": state_row["version"],
            "schema_version": state_row["schema_version"],
            "data": json.loads(state_row["data"]),
        }

        # Run comprehensive validation
        validation_result = schema_validator.validate_state(full_state)

        return {
            "session_id": sid,
            "version": state_row["version"],
            "validation_timestamp": datetime.utcnow().isoformat(),
            "validation_result": validation_result.to_dict(),
            "overall_health": {
                "status": (
                    "healthy" if validation_result.is_valid else "issues_detected"
                ),
                "error_count": len(validation_result.errors),
                "warning_count": len(validation_result.warnings),
                "suggestion_count": len(validation_result.suggestions),
            },
            "recommendations": {
                "critical_fixes_needed": len(
                    [
                        e
                        for e in validation_result.errors
                        if e.get("severity") == "error"
                    ]
                ),
                "optimization_opportunities": len(validation_result.suggestions),
                "business_rule_compliance": validation_result.is_valid,
            },
        }


@app.post("/validate/intentions")
async def validate_intentions_endpoint(
    intentions: Dict[str, Any], current_user: User = Depends(get_current_user)
):
    """Standalone intention validation endpoint"""
    validation_result = schema_validator.validate_intentions(intentions)

    return {
        "validation_result": validation_result.to_dict(),
        "validated_at": datetime.utcnow().isoformat(),
        "recommendations": {
            "can_proceed": validation_result.is_valid,
            "issues_to_address": len(validation_result.errors),
            "suggestions_available": len(validation_result.suggestions),
        },
    }


@app.post("/validate/patches")
async def validate_patches_endpoint(
    patches: List[Dict[str, Any]], current_user: User = Depends(get_current_user)
):
    """Standalone patch validation endpoint"""
    validation_result = schema_validator.validate_patches(patches)

    return {
        "validation_result": validation_result.to_dict(),
        "patch_count": len(patches),
        "validated_at": datetime.utcnow().isoformat(),
        "safety_assessment": {
            "safe_to_apply": validation_result.is_valid,
            "destructive_operations": len(
                [p for p in patches if p.get("op") == "remove"]
            ),
            "requires_review": not validation_result.is_valid
            or any(p.get("op") in ["remove", "move"] for p in patches),
        },
    }


@app.post("/sessions/{sid}/confirm-intent")
async def confirm_intent_stage(
    sid: str,
    request: ConfirmIntentRequest,
    current_user: User = Depends(get_current_user),
):
    """第一阶段：确认意图理解"""
    # Check write permission
    if "write" not in current_user.permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions. Required: write",
        )

    proposal_id = request.proposal_id

    with get_db() as conn:
        # 获取提案
        proposal_row = conn.execute(
            "SELECT * FROM patch_proposals WHERE id = ? AND session_id = ?",
            (proposal_id, sid),
        ).fetchone()

        if not proposal_row:
            raise HTTPException(status_code=404, detail="Proposal not found")

        # 解析当前阶段确认
        stage_confirmations = json.loads(proposal_row["stage_confirmations"] or "{}")
        stage_confirmations["intent_confirmed"] = True
        stage_confirmations["intent_confirmed_at"] = datetime.utcnow().isoformat()
        stage_confirmations["intent_confirmed_by"] = current_user.user_id

        # 更新状态
        conn.execute(
            """UPDATE patch_proposals
               SET status = 'intent_confirmed', stage_confirmations = ?
               WHERE id = ?""",
            (json.dumps(stage_confirmations), proposal_id),
        )
        conn.commit()

    return {
        "stage": "intent",
        "status": "confirmed",
        "next_stage": "change",
        "message": "Intent confirmed. Proceed to review specific changes.",
    }


@app.post("/sessions/{sid}/confirm-changes")
async def confirm_changes_stage(
    sid: str,
    request: ConfirmChangesRequest,
    current_user: User = Depends(get_current_user),
):
    """第二阶段：确认具体变更"""
    # Check write permission
    if "write" not in current_user.permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions. Required: write",
        )

    proposal_id = request.proposal_id
    selected_patch_indices = request.selected_patch_indices

    with get_db() as conn:
        # 获取提案
        proposal_row = conn.execute(
            "SELECT * FROM patch_proposals WHERE id = ? AND session_id = ?",
            (proposal_id, sid),
        ).fetchone()

        if not proposal_row:
            raise HTTPException(status_code=404, detail="Proposal not found")

        # 检查前一阶段是否已确认
        stage_confirmations = json.loads(proposal_row["stage_confirmations"] or "{}")
        if not stage_confirmations.get("intent_confirmed"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Must confirm intent stage first",
            )

        # 处理补丁选择
        patches = json.loads(proposal_row["patches"])
        if selected_patch_indices is not None:
            # 过滤选中的patches
            selected_patches = [
                patches[i] for i in selected_patch_indices if i < len(patches)
            ]
        else:
            # 默认选择所有patches
            selected_patches = patches
            selected_patch_indices = list(range(len(patches)))

        # 重新进行冲突分析（只针对选中的patches）
        session = conn.execute(
            "SELECT * FROM sessions WHERE session_id = ?", (sid,)
        ).fetchone()

        state_row = conn.execute(
            "SELECT * FROM states WHERE session_id = ? AND version = ?",
            (sid, session["current_version"]),
        ).fetchone()

        current_state = json.loads(state_row["data"])
        full_state = {
            "version": state_row["version"],
            "schema_version": state_row["schema_version"],
            "data": current_state,
        }

        conflicts = conflict_detector.detect_with_patches(full_state, selected_patches)

        # 更新阶段确认
        stage_confirmations["changes_confirmed"] = True
        stage_confirmations["changes_confirmed_at"] = datetime.utcnow().isoformat()
        stage_confirmations["changes_confirmed_by"] = current_user.user_id
        stage_confirmations["selected_patches_count"] = len(selected_patches)

        # 更新状态和选中的patches
        conn.execute(
            """UPDATE patch_proposals
               SET status = 'changes_confirmed',
                   stage_confirmations = ?,
                   selected_patch_indices = ?
               WHERE id = ?""",
            (
                json.dumps(stage_confirmations),
                json.dumps(selected_patch_indices),
                proposal_id,
            ),
        )
        conn.commit()

    return {
        "stage": "changes",
        "status": "confirmed",
        "selected_patches": len(selected_patches),
        "conflicts_detected": len(conflicts),
        "next_stage": "side_effects",
        "message": f"Selected {len(selected_patches)} patches for application. Proceed to review side effects.",
    }


@app.post("/sessions/{sid}/confirm-side-effects")
async def confirm_side_effects_stage(
    sid: str,
    request: ConfirmSideEffectsRequest,
    current_user: User = Depends(get_current_user),
):
    """第三阶段：确认副作用并应用自动修复"""
    # Check write permission
    if "write" not in current_user.permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions. Required: write",
        )

    proposal_id = request.proposal_id
    apply_auto_fixes = request.apply_auto_fixes

    with get_db() as conn:
        # 获取提案
        proposal_row = conn.execute(
            "SELECT * FROM patch_proposals WHERE id = ? AND session_id = ?",
            (proposal_id, sid),
        ).fetchone()

        if not proposal_row:
            raise HTTPException(status_code=404, detail="Proposal not found")

        # 检查前面阶段是否已确认
        stage_confirmations = json.loads(proposal_row["stage_confirmations"] or "{}")
        if not stage_confirmations.get("changes_confirmed"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Must confirm changes stage first",
            )

        auto_fixes = {}

        if apply_auto_fixes:
            # 获取选中的patches
            selected_indices = json.loads(
                proposal_row["selected_patch_indices"] or "[]"
            )
            patches = json.loads(proposal_row["patches"])
            selected_patches = [
                patches[i] for i in selected_indices if i < len(patches)
            ]

            # 获取当前状态
            session = conn.execute(
                "SELECT * FROM sessions WHERE session_id = ?", (sid,)
            ).fetchone()

            state_row = conn.execute(
                "SELECT * FROM states WHERE session_id = ? AND version = ?",
                (sid, session["current_version"]),
            ).fetchone()

            current_state = json.loads(state_row["data"])
            full_state = {
                "version": state_row["version"],
                "schema_version": state_row["schema_version"],
                "data": current_state,
            }

            # 检测冲突并生成自动修复
            conflicts = conflict_detector.detect_with_patches(
                full_state, selected_patches
            )

            for conflict in conflicts:
                if hasattr(conflict, "auto_fix") and conflict.auto_fix:
                    auto_fixes[conflict.path] = conflict.auto_fix

        # 更新阶段确认
        stage_confirmations["side_effects_confirmed"] = True
        stage_confirmations["side_effects_confirmed_at"] = datetime.utcnow().isoformat()
        stage_confirmations["side_effects_confirmed_by"] = current_user.user_id
        stage_confirmations["auto_fixes_applied"] = apply_auto_fixes

        # 更新状态
        conn.execute(
            """UPDATE patch_proposals
               SET status = 'ready_to_commit',
                   stage_confirmations = ?,
                   applied_auto_fixes = ?
               WHERE id = ?""",
            (json.dumps(stage_confirmations), json.dumps(auto_fixes), proposal_id),
        )
        conn.commit()

    return {
        "stage": "side_effects",
        "status": "confirmed",
        "auto_fixes_applied": len(auto_fixes),
        "next_stage": "commit",
        "message": f"Side effects confirmed. Applied {len(auto_fixes)} auto-fixes. Ready to commit.",
    }


@app.get("/sessions/{sid}/proposals/{proposal_id}/status")
async def get_proposal_status(
    sid: str, proposal_id: str, current_user: User = Depends(get_current_user)
):
    """获取提案的当前确认状态"""
    # Check session access
    check_session_access(sid, current_user)

    with get_db() as conn:
        proposal_row = conn.execute(
            "SELECT * FROM patch_proposals WHERE id = ? AND session_id = ?",
            (proposal_id, sid),
        ).fetchone()

        if not proposal_row:
            raise HTTPException(status_code=404, detail="Proposal not found")

        stage_confirmations = json.loads(proposal_row["stage_confirmations"] or "{}")
        selected_indices = json.loads(proposal_row["selected_patch_indices"] or "[]")
        auto_fixes = json.loads(proposal_row["applied_auto_fixes"] or "{}")

        # 确定当前阶段
        current_stage = "intent"
        if stage_confirmations.get("intent_confirmed"):
            current_stage = "changes"
            if stage_confirmations.get("changes_confirmed"):
                current_stage = "side_effects"
                if stage_confirmations.get("side_effects_confirmed"):
                    current_stage = "ready_to_commit"

        return {
            "proposal_id": proposal_id,
            "status": proposal_row["status"],
            "current_stage": current_stage,
            "stage_confirmations": stage_confirmations,
            "selected_patch_count": (
                len(selected_indices)
                if selected_indices
                else len(json.loads(proposal_row["patches"]))
            ),
            "auto_fixes_count": len(auto_fixes),
            "created_at": proposal_row["created_at"],
        }


@app.post("/sessions/{sid}/commit")
async def commit_changes(
    sid: str, request: CommitRequest, current_user: User = Depends(get_current_user)
):
    """提交变更（需要完成三阶段确认）"""
    # Check write permission
    if "write" not in current_user.permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions. Required: write",
        )

    proposal_id = request.proposal_id
    message = request.message

    commit_id = f"c_{uuid.uuid4().hex[:8]}"

    with get_db() as conn:
        # 获取提案
        proposal_row = conn.execute(
            "SELECT * FROM patch_proposals WHERE id = ? AND session_id = ?",
            (proposal_id, sid),
        ).fetchone()

        if not proposal_row:
            raise HTTPException(status_code=404, detail="Proposal not found")

        # 检查是否完成了三阶段确认
        stage_confirmations = json.loads(proposal_row["stage_confirmations"] or "{}")
        if not all(
            [
                stage_confirmations.get("intent_confirmed"),
                stage_confirmations.get("changes_confirmed"),
                stage_confirmations.get("side_effects_confirmed"),
            ]
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Must complete all three confirmation stages before committing",
            )

        # 获取选中的patches
        all_patches = json.loads(proposal_row["patches"])
        selected_indices = json.loads(proposal_row["selected_patch_indices"] or "[]")

        if selected_indices:
            patches = [all_patches[i] for i in selected_indices if i < len(all_patches)]
        else:
            patches = all_patches

        # 应用自动修复
        auto_fixes = json.loads(proposal_row["applied_auto_fixes"] or "{}")
        if auto_fixes:
            for path, fix_value in auto_fixes.items():
                patches.append({"op": "replace", "path": path, "value": fix_value})

        # 获取当前状态
        session = conn.execute(
            "SELECT * FROM sessions WHERE session_id = ?", (sid,)
        ).fetchone()

        state_row = conn.execute(
            "SELECT * FROM states WHERE session_id = ? AND version = ?",
            (sid, session["current_version"]),
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
            raise HTTPException(
                status_code=400, detail=f"Failed to apply patches: {str(e)}"
            )

        # 生成新版本号
        current_version_num = int(session["current_version"][1:])
        new_version = f"v{current_version_num + 1}"

        # 保存新状态
        conn.execute(
            "INSERT INTO states (session_id, version, schema_version, data) VALUES (?, ?, ?, ?)",
            (sid, new_version, state_row["schema_version"], json.dumps(new_state)),
        )

        # 保存commit
        conn.execute(
            """INSERT INTO commits
               (id, session_id, parent_version, new_version, patches, reverse_patches, message)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                commit_id,
                sid,
                session["current_version"],
                new_version,
                json.dumps(patches),
                json.dumps(reverse_patches),
                message,
            ),
        )

        # 更新会话的当前版本
        conn.execute(
            "UPDATE sessions SET current_version = ?, updated_at = CURRENT_TIMESTAMP WHERE session_id = ?",
            (new_version, sid),
        )

        # 生成artifacts
        full_new_state = {
            "version": new_version,
            "schema_version": state_row["schema_version"],
            "data": new_state,
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
            (md_artifact_id, sid, new_version, "markdown", markdown_content),
        )

        conn.execute(
            "INSERT INTO artifacts (id, session_id, version, type, content) VALUES (?, ?, ?, ?, ?)",
            (csv_artifact_id, sid, new_version, "csv", csv_content),
        )

        conn.commit()

    return {
        "commit_id": commit_id,
        "version": new_version,
        "artifacts": {
            "items": [
                {
                    "id": md_artifact_id,
                    "type": "markdown",
                    "url": f"/artifacts/{md_artifact_id}",
                },
                {
                    "id": csv_artifact_id,
                    "type": "csv",
                    "url": f"/artifacts/{csv_artifact_id}",
                },
            ]
        },
    }


@app.get("/sessions/{sid}/artifacts")
async def list_artifacts(
    sid: str,
    version: Optional[str] = None,
    current_user: User = Depends(get_current_user),
):
    """列出artifacts"""
    with get_db() as conn:
        if version:
            artifacts = conn.execute(
                "SELECT id, type, created_at FROM artifacts WHERE session_id = ? AND version = ?",
                (sid, version),
            ).fetchall()
        else:
            artifacts = conn.execute(
                "SELECT id, type, version, created_at FROM artifacts WHERE session_id = ?",
                (sid,),
            ).fetchall()

        items = []
        for art in artifacts:
            items.append(
                {
                    "id": art["id"],
                    "type": art["type"],
                    "url": f"/artifacts/{art['id']}",
                    "version": art.get("version"),
                    "created_at": art["created_at"],
                }
            )

    return {"items": items}


@app.post("/sessions")
async def create_session(current_user: User = Depends(get_current_user)):
    """创建新会话"""
    # Check write permission
    if "write" not in current_user.permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions. Required: write",
        )

    session_id = f"sess_{uuid.uuid4().hex[:8]}"

    # 初始状态
    initial_state = {"stories": [], "glossary": []}

    with get_db() as conn:
        # 创建会话
        conn.execute(
            "INSERT INTO sessions (session_id, current_version) VALUES (?, ?)",
            (session_id, "v1"),
        )

        # 创建初始状态
        conn.execute(
            "INSERT INTO states (session_id, version, schema_version, data) VALUES (?, ?, ?, ?)",
            (session_id, "v1", "1.0.0", json.dumps(initial_state)),
        )

        conn.commit()

    # Grant the creator full access to the session
    grant_session_access(session_id, current_user.user_id, "write")

    return {"session_id": session_id, "version": "v1"}


@app.get("/")
async def root():
    """API根路径"""
    return {"name": "Conversational State Engine", "version": "0.1.0", "docs": "/docs"}


# 健康检查
@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.get("/debug/auth")
async def debug_auth(current_user: User = Depends(get_current_user)):
    return {
        "user_id": current_user.user_id,
        "email": current_user.email,
        "role": current_user.role,
        "permissions": current_user.permissions,
        "has_write": "write" in current_user.permissions,
    }


def main():
    """Entry point for running the server via uv scripts"""
    import uvicorn

    uvicorn.run("server.app:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    main()
