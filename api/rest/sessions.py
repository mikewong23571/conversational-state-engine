"""Session management REST endpoints."""

import json
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.dependencies import context_slicer
from domains.auth import (
    User,
    check_session_access,
    get_current_user,
    grant_session_access,
)
from domains.state.models import State, StateData
from shared.database import get_db

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("/", response_model=dict)
async def create_session(
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    if "write" not in current_user.permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions. Required: write",
        )
    session_id = f"sess_{uuid.uuid4().hex[:8]}"
    initial_state: dict[str, list[Any]] = {"stories": [], "glossary": []}
    with get_db() as conn:
        conn.execute(
            "INSERT INTO sessions (session_id, current_version) VALUES (?, ?)",
            (session_id, "v1"),
        )
        conn.execute(
            "INSERT INTO states (session_id, version, schema_version, data) VALUES (?, ?, ?, ?)",
            (session_id, "v1", "1.0.0", json.dumps(initial_state)),
        )
        conn.commit()
    grant_session_access(session_id, current_user.user_id, "write")
    return {"session_id": session_id, "version": "v1"}


@router.get("/{sid}/state", response_model=State)
async def get_state(
    sid: str,
    paths: str | None = Query(None),
    intent: str | None = Query(None),
    slice_mode: bool = Query(default=False),
    current_user: User = Depends(get_current_user),
) -> State | dict[str, Any]:
    check_session_access(sid, current_user)
    with get_db() as conn:
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
        full_state = {
            "version": state_row["version"],
            "schema_version": state_row["schema_version"],
            "data": state_data,
        }
        if slice_mode:
            slices = context_slicer.slice_state(full_state, intent or "")
            return {
                "session_id": sid,
                "version": state_row["version"],
                "schema_version": state_row["schema_version"],
                "slicing_enabled": True,
                "slice_count": len(slices),
                "slices": [
                    {
                        "id": s.id,
                        "path": s.path,
                        "data": s.data,
                        "metadata": s.metadata,
                        "dependencies": s.dependencies,
                        "size": s.size,
                        "importance_score": s.importance_score,
                    }
                    for s in slices[:10]
                ],
                "intent_analyzed": intent or "No intent provided",
            }
        elif paths:
            path_list = [p.strip() for p in paths.split(",")]
            filtered_data: dict[str, Any] = {}
            for path in path_list:
                try:
                    path_value = context_slicer._get_path_value(state_data, path)
                    if path_value is not None:
                        _set_path_value(filtered_data, path, path_value)
                except Exception:
                    continue
            final_data = filtered_data if filtered_data else state_data
            state_data_obj = StateData.model_validate(final_data)
            return State(
                version=state_row["version"],
                schema_version=state_row["schema_version"],
                data=state_data_obj,
            )
        state_data_obj = StateData.model_validate(state_data)
        return State(
            version=state_row["version"],
            schema_version=state_row["schema_version"],
            data=state_data_obj,
        )


def _set_path_value(target: dict[str, Any], path: str, value: Any) -> None:
    if path == "/" or not path:
        return
    parts = path.strip("/").split("/")
    current = target
    for part in parts[:-1]:
        if part not in current:
            current[part] = {}
        current = current[part]
    if parts:
        current[parts[-1]] = value
