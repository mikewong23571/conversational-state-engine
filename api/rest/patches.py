# mypy: ignore-errors

import json
import uuid
from datetime import datetime
from typing import Any

import jsonpatch
from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies import (
    conflict_detector,
    conflict_resolver,
    csv_renderer,
    markdown_renderer,
)
from domains.auth import User, get_current_user
from domains.state.models import (
    CommitRequest,
    ConfirmChangesRequest,
    ConfirmIntentRequest,
    ConfirmSideEffectsRequest,
    ImpactAnalysis,
    IntentionSet,
    Patch,
    PatchProposal,
    PatchProposalRequest,
)
from domains.state.validation import schema_validator
from shared.database import get_db

router = APIRouter(prefix="/sessions/{sid}", tags=["patches"])


@router.post("/patch-proposals")
async def propose_patches(
    sid: str,
    request: PatchProposalRequest,
    current_user: User = Depends(get_current_user),
):
    if "write" not in current_user.permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions. Required: write",
        )
    proposal_id = f"pp_{uuid.uuid4().hex[:8]}"
    intention_set_id = request.intention_set_id
    with get_db() as conn:
        intention_row = conn.execute(
            "SELECT * FROM draft_intentions WHERE id = ? AND session_id = ?",
            (intention_set_id, sid),
        ).fetchone()
        if not intention_row:
            raise HTTPException(status_code=404, detail="Intention set not found")
        intentions = IntentionSet.model_validate_json(intention_row["data"])
        session = conn.execute(
            "SELECT * FROM sessions WHERE session_id = ?", (sid,)
        ).fetchone()
        state_row = conn.execute(
            "SELECT * FROM states WHERE session_id = ? AND version = ?",
            (sid, session["current_version"]),
        ).fetchone()
        current_state = json.loads(state_row["data"])
        patches: list[dict[str, Any]] = []
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
        patches_for_detection = []
        for p in patches:
            prefixed = p.copy()
            prefixed["path"] = f"/data{p['path']}"
            patches_for_detection.append(prefixed)
        full_state = {
            "version": state_row["version"],
            "schema_version": state_row["schema_version"],
            "data": current_state,
        }
        conflicts = conflict_detector.detect_with_patches(
            full_state, patches_for_detection
        )
        patch_validation = schema_validator.validate_patches(patches)
        if not patch_validation.is_valid:
            print(f"Patch validation warnings: {patch_validation.errors}")
        auto_fix_patches: list[dict[str, Any]] = []
        if conflicts:
            try:
                auto_fixes = conflict_resolver.suggest_fixes(conflicts, full_state)
                auto_fix_patches = conflict_resolver.prioritize_fixes(auto_fixes)
                if auto_fix_patches:
                    fix_validation = schema_validator.validate_patches(auto_fix_patches)
                    if not fix_validation.is_valid:
                        print(f"Auto-fix validation warnings: {fix_validation.errors}")
                        auto_fix_patches = [
                            p
                            for i, p in enumerate(auto_fix_patches)
                            if not any(
                                f"patch[{i}]" in err.get("path", "")
                                for err in fix_validation.errors
                            )
                        ]
            except Exception as e:  # pragma: no cover - unexpected errors
                print(f"Error generating auto-fixes: {e}")
                auto_fix_patches = []
        risk_level = "low"
        if any(c.severity == "high" for c in conflicts):
            risk_level = "high"
        elif any(c.severity == "medium" for c in conflicts):
            risk_level = "medium"
        affected_paths = [p["path"] for p in patches]
        impact_analysis = ImpactAnalysis(
            affected_paths=affected_paths,
            risk_level=risk_level,
            semantic_conflicts=conflicts,
        )
        proposal = PatchProposal(
            proposal_id=proposal_id,
            patches=[Patch(**p) for p in patches],
            impact_analysis=impact_analysis,
        )
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


@router.post("/confirm-intent")
async def confirm_intent_stage(
    sid: str,
    request: ConfirmIntentRequest,
    current_user: User = Depends(get_current_user),
):
    if "write" not in current_user.permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions. Required: write",
        )
    proposal_id = request.proposal_id
    with get_db() as conn:
        proposal_row = conn.execute(
            "SELECT * FROM patch_proposals WHERE id = ? AND session_id = ?",
            (proposal_id, sid),
        ).fetchone()
        if not proposal_row:
            raise HTTPException(status_code=404, detail="Proposal not found")
        stage_confirmations = json.loads(proposal_row["stage_confirmations"] or "{}")
        stage_confirmations["intent_confirmed"] = True
        stage_confirmations["intent_confirmed_at"] = datetime.utcnow().isoformat()
        stage_confirmations["intent_confirmed_by"] = current_user.user_id
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


@router.post("/confirm-changes")
async def confirm_changes_stage(
    sid: str,
    request: ConfirmChangesRequest,
    current_user: User = Depends(get_current_user),
):
    if "write" not in current_user.permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions. Required: write",
        )
    proposal_id = request.proposal_id
    selected_patch_indices = request.selected_patch_indices
    with get_db() as conn:
        proposal_row = conn.execute(
            "SELECT * FROM patch_proposals WHERE id = ? AND session_id = ?",
            (proposal_id, sid),
        ).fetchone()
        if not proposal_row:
            raise HTTPException(status_code=404, detail="Proposal not found")
        stage_confirmations = json.loads(proposal_row["stage_confirmations"] or "{}")
        if not stage_confirmations.get("intent_confirmed"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Must confirm intent stage first",
            )
        patches = json.loads(proposal_row["patches"])
        if selected_patch_indices is not None:
            selected_patches = [
                patches[i] for i in selected_patch_indices if i < len(patches)
            ]
        else:
            selected_patches = patches
            selected_patch_indices = list(range(len(patches)))
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
        stage_confirmations["changes_confirmed"] = True
        stage_confirmations["changes_confirmed_at"] = datetime.utcnow().isoformat()
        stage_confirmations["changes_confirmed_by"] = current_user.user_id
        stage_confirmations["selected_patches_count"] = len(selected_patches)
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


@router.post("/confirm-side-effects")
async def confirm_side_effects_stage(
    sid: str,
    request: ConfirmSideEffectsRequest,
    current_user: User = Depends(get_current_user),
):
    if "write" not in current_user.permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions. Required: write",
        )
    proposal_id = request.proposal_id
    apply_auto_fixes = request.apply_auto_fixes
    with get_db() as conn:
        proposal_row = conn.execute(
            "SELECT * FROM patch_proposals WHERE id = ? AND session_id = ?",
            (proposal_id, sid),
        ).fetchone()
        if not proposal_row:
            raise HTTPException(status_code=404, detail="Proposal not found")
        stage_confirmations = json.loads(proposal_row["stage_confirmations"] or "{}")
        if not stage_confirmations.get("changes_confirmed"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Must confirm changes stage first",
            )
        auto_fixes: dict[str, Any] = {}
        if apply_auto_fixes:
            selected_indices = json.loads(
                proposal_row["selected_patch_indices"] or "[]"
            )
            patches = json.loads(proposal_row["patches"])
            selected_patches = [
                patches[i] for i in selected_indices if i < len(patches)
            ]
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
            conflicts = conflict_detector.detect_with_patches(
                full_state, selected_patches
            )
            for conflict in conflicts:
                if hasattr(conflict, "auto_fix") and conflict.auto_fix:
                    auto_fixes[conflict.path] = conflict.auto_fix
        stage_confirmations["side_effects_confirmed"] = True
        stage_confirmations["side_effects_confirmed_at"] = datetime.utcnow().isoformat()
        stage_confirmations["side_effects_confirmed_by"] = current_user.user_id
        stage_confirmations["auto_fixes_applied"] = apply_auto_fixes
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


@router.post("/commit")
async def commit_changes(
    sid: str,
    request: CommitRequest,
    current_user: User = Depends(get_current_user),
):
    if "write" not in current_user.permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions. Required: write",
        )
    proposal_id = request.proposal_id
    message = request.message
    commit_id = f"c_{uuid.uuid4().hex[:8]}"
    with get_db() as conn:
        proposal_row = conn.execute(
            "SELECT * FROM patch_proposals WHERE id = ? AND session_id = ?",
            (proposal_id, sid),
        ).fetchone()
        if not proposal_row:
            raise HTTPException(status_code=404, detail="Proposal not found")
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
        all_patches = json.loads(proposal_row["patches"])
        selected_indices = json.loads(proposal_row["selected_patch_indices"] or "[]")
        if selected_indices:
            patches = [all_patches[i] for i in selected_indices if i < len(all_patches)]
        else:
            patches = all_patches
        auto_fixes = json.loads(proposal_row["applied_auto_fixes"] or "{}")
        if auto_fixes:
            for path, fix_value in auto_fixes.items():
                patches.append({"op": "replace", "path": path, "value": fix_value})
        session = conn.execute(
            "SELECT * FROM sessions WHERE session_id = ?", (sid,)
        ).fetchone()
        state_row = conn.execute(
            "SELECT * FROM states WHERE session_id = ? AND version = ?",
            (sid, session["current_version"]),
        ).fetchone()
        current_state = json.loads(state_row["data"])
        try:
            patch_obj = jsonpatch.JsonPatch(patches)
            new_state = patch_obj.apply(current_state)
            reverse_patch = jsonpatch.make_patch(new_state, current_state)
            reverse_patches = list(reverse_patch)
        except Exception as e:
            raise HTTPException(
                status_code=400, detail=f"Failed to apply patches: {str(e)}"
            ) from e
        current_version_num = int(session["current_version"][1:])
        new_version = f"v{current_version_num + 1}"
        conn.execute(
            "INSERT INTO states (session_id, version, schema_version, data) VALUES (?, ?, ?, ?)",
            (sid, new_version, state_row["schema_version"], json.dumps(new_state)),
        )
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
        conn.execute(
            "UPDATE sessions SET current_version = ?, updated_at = CURRENT_TIMESTAMP WHERE session_id = ?",
            (new_version, sid),
        )
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
