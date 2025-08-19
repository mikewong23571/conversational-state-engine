"""Intention processing REST endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from domains.auth import User, get_current_user
from domains.state.models import IntentionSet
from domains.state.validation import schema_validator
from shared.database import get_db

router = APIRouter(prefix="/sessions/{sid}", tags=["intentions"])


@router.post("/intents")
async def draft_intents(
    sid: str,
    intention_set: IntentionSet,
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    if "write" not in current_user.permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions. Required: write",
        )
    validation_result = schema_validator.validate_intentions(intention_set.model_dump())
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
        session = conn.execute(
            "SELECT * FROM sessions WHERE session_id = ?", (sid,)
        ).fetchone()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        conn.execute(
            "INSERT INTO draft_intentions (id, session_id, data) VALUES (?, ?, ?)",
            (intention_set_id, sid, intention_set.model_dump_json()),
        )
        conn.commit()
    return {"intention_set_id": intention_set_id, "status": "draft"}
