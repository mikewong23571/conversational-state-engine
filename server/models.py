"""
Data models for the Conversational State Engine
"""
from enum import Enum
from typing import List, Optional, Any, Dict, Union
from pydantic import BaseModel, Field
try:
    from pydantic import validator, root_validator  # Pydantic v1
except ImportError:
    from pydantic import field_validator as validator, model_validator  # Pydantic v2
    def root_validator(**kwargs):
        return model_validator(mode='before')
from typing import Annotated

# Pydantic v2 compatible string types with validation
JsonPointer = Annotated[str, Field(pattern=r'^(/[^/]*)+$')]
OptionalString = Annotated[str, Field(min_length=1, max_length=500)]
EvidenceString = Annotated[str, Field(max_length=1000)]
ConstrainedFloat = Annotated[float, Field(ge=0.0, le=1.0)]
StoryKey = Annotated[str, Field(pattern=r'^[A-Z]+-[A-Za-z0-9]+$')]
StoryTitle = Annotated[str, Field(min_length=1, max_length=200)]
CriteriaString = Annotated[str, Field(min_length=1, max_length=500)]
PatchPath = Annotated[str, Field(pattern=r'^(/[^/]*)*$')]
VersionString = Annotated[str, Field(pattern=r'^v\d+$')]
SchemaVersionString = Annotated[str, Field(pattern=r'^\d+\.\d+\.\d+$')]
NotesString = Annotated[str, Field(max_length=1000)]
from datetime import datetime
import re
import json

class Action(str, Enum):
    add = "add"
    modify = "modify" 
    delete = "delete"
    move = "move"
    set = "set"

class Intention(BaseModel):
    action: Action
    target_path: JsonPointer  # RFC6901 JSON Pointer validation
    value: Optional[Any] = None
    reason: Optional[OptionalString] = None
    confidence: ConstrainedFloat = 0.8
    evidence: Optional[EvidenceString] = None  # 原文片段或命中规则

    @validator('target_path')
    def validate_json_pointer(cls, v):
        """Validate RFC6901 JSON Pointer format"""
        if not v.startswith('/'):
            raise ValueError('JSON Pointer must start with /')
        
        # Check for invalid characters
        if '//' in v:
            raise ValueError('JSON Pointer cannot contain empty path segments')
        
        return v
    
    @validator('value')
    def validate_value_for_action(cls, v, values):
        """Validate value is appropriate for the action"""
        action = values.get('action')
        if action == Action.delete and v is not None:
            raise ValueError('Delete actions should not have a value')
        elif action in [Action.add, Action.modify, Action.set] and v is None:
            raise ValueError(f'{action} actions require a value')
        return v
    
    @root_validator(skip_on_failure=True)
    def validate_intention_consistency(cls, values):
        """Validate overall intention consistency"""
        action = values.get('action')
        target_path = values.get('target_path', '')
        confidence = values.get('confidence', 0)
        
        # High confidence operations should have evidence
        if confidence > 0.9 and not values.get('evidence'):
            values['evidence'] = f'High confidence {action} operation'
        
        # Validate path patterns for specific actions
        if action == Action.add and target_path.endswith('/-'):
            # Array append operation
            pass
        elif action == Action.move and not values.get('reason'):
            raise ValueError('Move operations require a reason')
        
        return values

class IntentionSet(BaseModel):
    items: List[Intention] = Field(default_factory=list, min_length=0, max_length=50)
    notes: Optional[NotesString] = None

    @validator('items')
    def validate_intention_conflicts(cls, v):
        """Check for conflicting intentions within the set"""
        paths = {}
        for intention in v:
            path = intention.target_path
            if path in paths:
                # Check if actions conflict
                existing_action = paths[path]
                if existing_action == Action.delete and intention.action != Action.delete:
                    raise ValueError(f'Cannot {intention.action} on path {path} after delete')
                elif intention.action == Action.delete and existing_action != Action.delete:
                    raise ValueError(f'Cannot delete path {path} after {existing_action}')
            paths[path] = intention.action
        return v
    
    @root_validator(skip_on_failure=True)
    def validate_set_consistency(cls, values):
        """Validate consistency across the intention set"""
        items = values.get('items', [])
        if not items:
            return values
        
        # Check for logical consistency
        high_confidence_count = sum(1 for item in items if item.confidence > 0.9)
        if high_confidence_count == 0 and len(items) > 0:
            # At least one intention should have reasonable confidence
            current_notes = values.get('notes', '') or ''
            values['notes'] = (current_notes + ' Note: Low confidence intentions.').strip()
        
        return values

class PatchOp(str, Enum):
    add = "add"
    remove = "remove"  
    replace = "replace"
    move = "move"
    copy = "copy"
    test = "test"

class Patch(BaseModel):
    op: PatchOp
    path: PatchPath  # RFC6901 JSON Pointer
    value: Optional[Any] = None
    from_path: Optional[PatchPath] = Field(None, alias="from")

    @validator('path')
    def validate_patch_path(cls, v):
        """Validate JSON Pointer format for patch path"""
        if not v.startswith('/') and v != '':
            raise ValueError('Patch path must be empty or start with /')
        return v
    
    @validator('value')
    def validate_value_for_op(cls, v, values):
        """Validate value is appropriate for the operation"""
        op = values.get('op')
        if op in [PatchOp.add, PatchOp.replace, PatchOp.test] and v is None:
            raise ValueError(f'Operation {op} requires a value')
        elif op in [PatchOp.remove, PatchOp.move, PatchOp.copy] and v is not None:
            # These operations should not have values (move/copy use from_path)
            pass
        return v
    
    @root_validator(skip_on_failure=True)
    def validate_patch_consistency(cls, values):
        """Validate patch operation consistency"""
        op = values.get('op')
        from_path = values.get('from_path')
        
        if op in [PatchOp.move, PatchOp.copy] and not from_path:
            raise ValueError(f'Operation {op} requires from_path')
        elif op not in [PatchOp.move, PatchOp.copy] and from_path:
            raise ValueError(f'Operation {op} should not have from_path')
        
        return values

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

class PatchProposalRequest(BaseModel):
    intention_set_id: str

class PatchProposal(BaseModel):
    proposal_id: str
    patches: List[Patch]
    impact_analysis: ImpactAnalysis
    preview_diff: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=datetime.now)

class Priority(str, Enum):
    P0 = "P0"  # Critical
    P1 = "P1"  # High
    P2 = "P2"  # Medium

class AuthType(str, Enum):
    password = "password"
    sso = "sso"
    biometric = "biometric"

class Story(BaseModel):
    """Story/requirement validation model"""
    key: StoryKey  # Format: PREFIX-IDENTIFIER
    title: StoryTitle
    priority: Priority = Priority.P2
    acceptance_criteria: List[CriteriaString] = Field(default_factory=list)
    dependencies: List[StoryKey] = Field(default_factory=list)
    auth_type: Optional[AuthType] = None
    platform: Optional[List[str]] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    
    @validator('acceptance_criteria')
    def validate_acceptance_criteria(cls, v):
        """Ensure unique acceptance criteria"""
        if len(v) != len(set(v)):
            raise ValueError('Acceptance criteria must be unique')
        return v
    
    @validator('dependencies')
    def validate_dependencies(cls, v):
        """Ensure unique dependencies"""
        if len(v) != len(set(v)):
            raise ValueError('Dependencies must be unique')
        return v
    
    @root_validator(skip_on_failure=True)
    def validate_story_consistency(cls, values):
        """Validate story-level consistency"""
        start_date = values.get('start_date')
        end_date = values.get('end_date')
        
        if start_date and end_date and start_date >= end_date:
            raise ValueError('end_date must be after start_date')
        
        # Validate auth_type consistency with acceptance criteria
        auth_type = values.get('auth_type')
        criteria = values.get('acceptance_criteria', [])
        criteria_text = ' '.join(criteria).lower()
        
        if auth_type == AuthType.sso and 'password' in criteria_text:
            raise ValueError('SSO auth_type conflicts with password-related acceptance criteria')
        elif auth_type == AuthType.password and 'sso' in criteria_text:
            raise ValueError('Password auth_type conflicts with SSO-related acceptance criteria')
        
        return values

class StateData(BaseModel):
    """Validation model for state data"""
    stories: List[Story] = Field(default_factory=list)
    glossary: List[Dict[str, str]] = Field(default_factory=list)
    
    @validator('stories')
    def validate_story_keys_unique(cls, v):
        """Ensure story keys are unique"""
        keys = [story.key for story in v]
        if len(keys) != len(set(keys)):
            raise ValueError('Story keys must be unique')
        return v
    
    @validator('stories')
    def validate_story_dependencies(cls, v):
        """Validate story dependencies exist"""
        story_keys = {story.key for story in v}
        
        for story in v:
            for dep in story.dependencies:
                if dep not in story_keys:
                    raise ValueError(f'Story {story.key} depends on non-existent story {dep}')
        
        # Check for circular dependencies (simple check)
        def has_circular_dependency(story_key, visited=None):
            if visited is None:
                visited = set()
            if story_key in visited:
                return True
            visited.add(story_key)
            
            story = next((s for s in v if s.key == story_key), None)
            if story:
                for dep in story.dependencies:
                    if has_circular_dependency(dep, visited.copy()):
                        return True
            return False
        
        for story in v:
            if has_circular_dependency(story.key):
                raise ValueError(f'Circular dependency detected involving story {story.key}')
        
        return v

class State(BaseModel):
    version: VersionString  # Format: v1, v2, v3...
    schema_version: SchemaVersionString  # Semantic versioning
    data: StateData
    created_at: datetime = Field(default_factory=datetime.now)
    
    @validator('version')
    def validate_version_format(cls, v):
        """Validate version follows semantic format"""
        if not re.match(r'^v\d+$', v):
            raise ValueError('Version must follow format: v1, v2, v3, etc.')
        return v

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
