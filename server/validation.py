"""
Comprehensive schema validation service for the Conversational State Engine
"""

import json
import re
from typing import Any, Dict, List, Optional, Tuple

from pydantic import ValidationError

from domains.state.models import (
    Intention,
    IntentionSet,
    Patch,
    PatchOp,
    State,
    StateData,
    Story,
)


class ValidationResult:
    """Result of validation with errors and warnings"""

    def __init__(self):
        self.is_valid = True
        self.errors: List[Dict[str, Any]] = []
        self.warnings: List[Dict[str, Any]] = []
        self.suggestions: List[Dict[str, Any]] = []

    def add_error(self, path: str, message: str, code: str = "validation_error"):
        """Add a validation error"""
        self.is_valid = False
        self.errors.append(
            {"path": path, "message": message, "code": code, "severity": "error"}
        )

    def add_warning(self, path: str, message: str, code: str = "validation_warning"):
        """Add a validation warning"""
        self.warnings.append(
            {"path": path, "message": message, "code": code, "severity": "warning"}
        )

    def add_suggestion(self, path: str, message: str, fix: Dict[str, Any]):
        """Add a validation suggestion with auto-fix"""
        self.suggestions.append(
            {
                "path": path,
                "message": message,
                "severity": "suggestion",
                "auto_fix": fix,
            }
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format"""
        return {
            "is_valid": self.is_valid,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "suggestion_count": len(self.suggestions),
            "errors": self.errors,
            "warnings": self.warnings,
            "suggestions": self.suggestions,
        }


class SchemaValidator:
    """Enhanced schema validation service"""

    def __init__(self):
        self.business_rules = {
            "priority_dependency_rule": self._validate_priority_dependencies,
            "auth_consistency_rule": self._validate_auth_consistency,
            "timeline_consistency_rule": self._validate_timeline_consistency,
            "story_naming_convention": self._validate_story_naming,
        }

    def validate_state(
        self, state_data: Dict[str, Any], schema_version: str = "1.0.0"
    ) -> ValidationResult:
        """Comprehensive state validation"""
        result = ValidationResult()

        try:
            # Basic Pydantic validation
            if isinstance(state_data, dict) and "data" in state_data:
                # Full state validation
                validated_state = State(**state_data)
                state_data = validated_state.data.dict()
            else:
                # Data-only validation
                validated_data = StateData(**state_data)
                state_data = validated_data.dict()

        except ValidationError as e:
            for error in e.errors():
                path = ".".join(str(p) for p in error["loc"])
                result.add_error(path, error["msg"], error["type"])
            return result

        # Advanced business rule validation
        self._validate_business_rules(state_data, result)

        # Performance and optimization suggestions
        self._generate_optimization_suggestions(state_data, result)

        return result

    def validate_intentions(self, intentions: Dict[str, Any]) -> ValidationResult:
        """Validate intention set"""
        result = ValidationResult()

        try:
            validated_intentions = IntentionSet(**intentions)
        except ValidationError as e:
            for error in e.errors():
                path = ".".join(str(p) for p in error["loc"])
                result.add_error(path, error["msg"], error["type"])
            return result

        # Additional intention-specific validation
        self._validate_intention_patterns(validated_intentions.dict(), result)

        return result

    def validate_patches(self, patches: List[Dict[str, Any]]) -> ValidationResult:
        """Validate patch operations"""
        result = ValidationResult()

        validated_patches = []
        for i, patch_data in enumerate(patches):
            try:
                patch = Patch(**patch_data)
                validated_patches.append(patch)
            except ValidationError as e:
                for error in e.errors():
                    path = f'patch[{i}].{".".join(str(p) for p in error["loc"])}'
                    result.add_error(path, error["msg"], error["type"])

        # Validate patch sequence consistency
        if validated_patches:
            self._validate_patch_sequence(validated_patches, result)

        return result

    def _validate_business_rules(
        self, state_data: Dict[str, Any], result: ValidationResult
    ):
        """Apply business-specific validation rules"""
        for rule_name, rule_func in self.business_rules.items():
            try:
                rule_func(state_data, result)
            except Exception as e:
                result.add_error("business_rules", f"Rule {rule_name} failed: {str(e)}")

    def _validate_priority_dependencies(
        self, state_data: Dict[str, Any], result: ValidationResult
    ):
        """Validate dependencies have equal or higher priority"""
        stories = state_data.get("stories", [])
        story_priorities = {story["key"]: story["priority"] for story in stories}

        priority_order = {"P0": 3, "P1": 2, "P2": 1}

        for story in stories:
            story_priority = priority_order.get(story["priority"], 0)

            for dep_key in story.get("dependencies", []):
                if dep_key in story_priorities:
                    dep_priority = priority_order.get(story_priorities[dep_key], 0)

                    if dep_priority < story_priority:
                        result.add_error(
                            f"stories.{story['key']}.dependencies",
                            f"Dependency {dep_key} has lower priority ({story_priorities[dep_key]}) than dependent story ({story['priority']})",
                            "priority_dependency_conflict",
                        )

                        # Suggest auto-fix
                        result.add_suggestion(
                            f"stories.{story['key']}.dependencies",
                            f"Consider upgrading {dep_key} priority to {story['priority']}",
                            {
                                "op": "replace",
                                "path": f"/stories/{self._find_story_index(stories, dep_key)}/priority",
                                "value": story["priority"],
                            },
                        )

    def _validate_auth_consistency(
        self, state_data: Dict[str, Any], result: ValidationResult
    ):
        """Validate authentication method consistency"""
        stories = state_data.get("stories", [])
        auth_methods = {}

        for i, story in enumerate(stories):
            if "auth_type" in story and story["auth_type"]:
                auth_methods[story["key"]] = story["auth_type"]

            # Check criteria consistency
            criteria_text = " ".join(story.get("acceptance_criteria", [])).lower()
            auth_type = story.get("auth_type")

            if "sso" in criteria_text and auth_type == "password":
                result.add_error(
                    f"stories[{i}].auth_type",
                    "Auth type 'password' conflicts with SSO mentions in acceptance criteria",
                    "authentication_method_conflict",
                )

                result.add_suggestion(
                    f"stories[{i}].auth_type",
                    "Consider changing auth_type to 'sso' or removing SSO from criteria",
                    {
                        "op": "replace",
                        "path": f"/stories/{i}/auth_type",
                        "value": "sso",
                    },
                )

    def _validate_timeline_consistency(
        self, state_data: Dict[str, Any], result: ValidationResult
    ):
        """Validate timeline consistency"""
        stories = state_data.get("stories", [])

        for i, story in enumerate(stories):
            start_date = story.get("start_date")
            end_date = story.get("end_date")

            if start_date and end_date:
                try:
                    from datetime import datetime

                    if isinstance(start_date, str):
                        start_date = datetime.fromisoformat(
                            start_date.replace("Z", "+00:00")
                        )
                    if isinstance(end_date, str):
                        end_date = datetime.fromisoformat(
                            end_date.replace("Z", "+00:00")
                        )

                    if start_date >= end_date:
                        result.add_error(
                            f"stories[{i}].timeline",
                            f"Start date ({start_date}) must be before end date ({end_date})",
                            "timeline_inconsistency",
                        )
                except (ValueError, TypeError) as e:
                    result.add_error(
                        f"stories[{i}].dates",
                        f"Invalid date format: {str(e)}",
                        "date_format_error",
                    )

    def _validate_story_naming(
        self, state_data: Dict[str, Any], result: ValidationResult
    ):
        """Validate story naming conventions"""
        stories = state_data.get("stories", [])

        for i, story in enumerate(stories):
            key = story.get("key", "")
            title = story.get("title", "")

            # Check key format
            if not re.match(r"^[A-Z]+-[A-Za-z0-9]+$", key):
                result.add_warning(
                    f"stories[{i}].key",
                    f"Story key '{key}' doesn't follow recommended format: PREFIX-IDENTIFIER",
                    "naming_convention",
                )

            # Check title length and quality
            if len(title) < 10:
                result.add_warning(
                    f"stories[{i}].title",
                    "Story title is quite short. Consider adding more descriptive details.",
                    "title_too_short",
                )

    def _validate_intention_patterns(
        self, intentions_data: Dict[str, Any], result: ValidationResult
    ):
        """Validate common intention patterns"""
        items = intentions_data.get("items", [])

        # Check for destructive operations without proper confidence
        for i, intention in enumerate(items):
            if intention["action"] == "delete" and intention.get("confidence", 0) < 0.8:
                result.add_warning(
                    f"items[{i}]",
                    "Delete operations should have high confidence (>0.8)",
                    "low_confidence_delete",
                )

            # Check for missing reasons on complex operations
            if intention["action"] in ["move", "modify"] and not intention.get(
                "reason"
            ):
                result.add_warning(
                    f"items[{i}].reason",
                    f"{intention['action'].title()} operations should include a reason",
                    "missing_reason",
                )

    def _validate_patch_sequence(self, patches: List[Patch], result: ValidationResult):
        """Validate patch sequence for conflicts"""
        paths_affected = {}

        for i, patch in enumerate(patches):
            path = patch.path
            op = patch.op

            if path in paths_affected:
                prev_op = paths_affected[path]
                if prev_op == PatchOp.remove and op != PatchOp.add:
                    result.add_error(
                        f"patch[{i}]",
                        f"Cannot {op} on path {path} after it was removed",
                        "patch_sequence_conflict",
                    )

            paths_affected[path] = op

    def _generate_optimization_suggestions(
        self, state_data: Dict[str, Any], result: ValidationResult
    ):
        """Generate performance and optimization suggestions"""
        stories = state_data.get("stories", [])

        # Suggest index optimizations for large datasets
        if len(stories) > 100:
            result.add_suggestion(
                "performance",
                "Large number of stories detected. Consider implementing pagination or indexing.",
                {"recommendation": "implement_pagination", "threshold": 100},
            )

        # Check for redundant acceptance criteria
        criteria_counts = {}
        for story in stories:
            for criterion in story.get("acceptance_criteria", []):
                criteria_counts[criterion] = criteria_counts.get(criterion, 0) + 1

        duplicates = {k: v for k, v in criteria_counts.items() if v > 1}
        if duplicates:
            result.add_suggestion(
                "optimization",
                f"Found {len(duplicates)} duplicated acceptance criteria across stories",
                {
                    "recommendation": "consolidate_criteria",
                    "duplicates": list(duplicates.keys()),
                },
            )

    def _find_story_index(self, stories: List[Dict[str, Any]], key: str) -> int:
        """Find story index by key"""
        for i, story in enumerate(stories):
            if story.get("key") == key:
                return i
        return -1


# Create global validator instance
schema_validator = SchemaValidator()
