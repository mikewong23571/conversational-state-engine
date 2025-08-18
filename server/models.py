"""
Data models for the Conversational State Engine
"""
from enum import Enum
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field
from datetime import datetime

class Action(str, Enum):
    add = "add"
    modify = "modify" 
    delete = "delete"
    move = "move"
    set = "set"

class Intention(BaseModel):
    action: Action
    target_path: str  # RFC6901 JSON Pointer
    value: Optional[Any] = None
    reason: Optional[str] = None
    confidence: float = 0.8
    evidence: Optional[str] = None  # 原文片段或命中规则

class IntentionSet(BaseModel):
    items: List[Intention] = Field(default_factory=list)
    notes: Optional[str] = None

class Patch(BaseModel):
    op: str  # add, remove, replace, move, copy, test
    path: str
    value: Optional[Any] = None
    from_path: Optional[str] = Field(None, alias="from")

class Conflict(BaseModel):
    type: str  # structural, logical, semantic
    rule: str
    severity: str  # low, medium, high
    message: str
    suggestion: Optional[Dict[str, Any]] = None

class ImpactAnalysis(BaseModel):
    affected_paths: List[str]
    risk_level: str  # low, medium, high
    semantic_conflicts: List[Conflict] = Field(default_factory=list)
    suggested_alternatives: List[Dict[str, Any]] = Field(default_factory=list)

class PatchProposal(BaseModel):
    proposal_id: str
    patches: List[Patch]
    impact_analysis: ImpactAnalysis
    preview_diff: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=datetime.now)

class State(BaseModel):
    version: str
    schema_version: str
    data: Dict[str, Any]
    created_at: datetime = Field(default_factory=datetime.now)

class Commit(BaseModel):
    commit_id: str
    session_id: str
    parent_version: str
    new_version: str
    patches: List[Patch]
    reverse_patches: List[Patch]
    author: Optional[str] = None
    message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)

class Session(BaseModel):
    session_id: str
    current_version: str
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
