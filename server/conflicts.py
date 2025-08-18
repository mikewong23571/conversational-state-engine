"""
Conflict detection engine with structural and logical rules
"""
from dataclasses import dataclass
from typing import Callable, List, Dict, Any, Optional
from models import Conflict
import jsonpatch
import json

@dataclass
class Rule:
    """规则定义"""
    name: str
    severity: str
    check: Callable[[dict], List[Conflict]]
    description: str = ""

class ConflictDetector:
    """冲突检测器"""
    
    def __init__(self, rules: List[Rule]):
        self.rules = rules
        
    def detect(self, candidate: dict) -> List[Conflict]:
        """检测候选状态中的所有冲突"""
        conflicts = []
        for rule in self.rules:
            conflicts.extend(rule.check(candidate))
        return conflicts
    
    def detect_with_patches(self, current_state: dict, patches: List[dict]) -> List[Conflict]:
        """先应用patches到当前状态，然后检测冲突"""
        try:
            # 应用patches得到候选状态
            candidate = self._apply_patches(current_state, patches)
            return self.detect(candidate)
        except Exception as e:
            # 如果patches本身有问题，返回结构性错误
            return [Conflict(
                type="structural",
                rule="patch_application",
                severity="high",
                message=f"Failed to apply patches: {str(e)}"
            )]
    
    def _apply_patches(self, state: dict, patches: List[dict]) -> dict:
        """应用JSON patches到状态"""
        state_copy = json.loads(json.dumps(state))  # 深拷贝
        patch = jsonpatch.JsonPatch(patches)
        return patch.apply(state_copy)

# ========== 业务规则实现 ==========

def auth_method_conflict(state: dict) -> List[Conflict]:
    """检测认证方法冲突：SSO与本地密码要求互斥"""
    conflicts = []
    stories = state.get("data", {}).get("stories", [])
    
    for story in stories:
        if story.get("auth_type") == "SSO":
            # 检查验收标准中是否有本地密码相关要求
            criteria = story.get("acceptance_criteria", [])
            for criterion in criteria:
                if "local_password" in str(criterion).lower() or "本地密码" in str(criterion):
                    conflicts.append(Conflict(
                        type="logical",
                        rule="auth_method_conflict",
                        severity="high",
                        message=f"Story '{story.get('key')}': SSO与本地密码要求互斥",
                        suggestion={
                            "action": "remove_phrase",
                            "target": "local_password",
                            "from": f"/stories/{stories.index(story)}/acceptance_criteria"
                        }
                    ))
    return conflicts

def dependency_order(state: dict) -> List[Conflict]:
    """检测依赖优先级：被依赖的story优先级不能低于依赖方"""
    conflicts = []
    stories = state.get("data", {}).get("stories", [])
    
    # 构建key到优先级的映射
    key_to_priority = {s.get("key"): s.get("priority", "P2") for s in stories}
    priority_rank = {"P0": 0, "P1": 1, "P2": 2}
    
    for story in stories:
        story_key = story.get("key")
        story_priority = story.get("priority", "P2")
        story_rank = priority_rank.get(story_priority, 2)
        
        for dep_key in story.get("dependencies", []):
            dep_priority = key_to_priority.get(dep_key, "P2")
            dep_rank = priority_rank.get(dep_priority, 2)
            
            if dep_rank > story_rank:
                conflicts.append(Conflict(
                    type="logical",
                    rule="dependency_order",
                    severity="medium",
                    message=f"Story '{story_key}' (优先级{story_priority}) 依赖于 '{dep_key}' (优先级{dep_priority})",
                    suggestion={
                        "action": "bump_priority",
                        "target": dep_key,
                        "to": story_priority
                    }
                ))
    return conflicts

def timeline_consistency(state: dict) -> List[Conflict]:
    """检测时间线一致性：结束日期必须晚于开始日期"""
    conflicts = []
    stories = state.get("data", {}).get("stories", [])
    
    for story in stories:
        start_date = story.get("start_date")
        end_date = story.get("end_date")
        
        if start_date and end_date:
            # 简单字符串比较（假设ISO格式）
            if end_date < start_date:
                conflicts.append(Conflict(
                    type="logical",
                    rule="timeline_consistency",
                    severity="high",
                    message=f"Story '{story.get('key')}': 结束日期早于开始日期",
                    suggestion={
                        "action": "swap_dates",
                        "start_date": end_date,
                        "end_date": start_date
                    }
                ))
    return conflicts

def duplicate_detection(state: dict) -> List[Conflict]:
    """检测重复或相似的stories"""
    conflicts = []
    stories = state.get("data", {}).get("stories", [])
    
    # 简单的重复检测：基于key和title
    seen_keys = set()
    seen_titles = {}
    
    for i, story in enumerate(stories):
        key = story.get("key")
        title = story.get("title", "").lower()
        
        # 检测重复的key
        if key in seen_keys:
            conflicts.append(Conflict(
                type="semantic",
                rule="duplicate_key",
                severity="high",
                message=f"发现重复的story key: '{key}'",
                suggestion={"action": "rename_key", "target": f"/stories/{i}/key"}
            ))
        seen_keys.add(key)
        
        # 检测相似的title
        for prev_title, prev_idx in seen_titles.items():
            if title and prev_title and _string_similarity(title, prev_title) > 0.8:
                conflicts.append(Conflict(
                    type="semantic",
                    rule="similar_story",
                    severity="medium",
                    message=f"Story '{key}' 与 story at index {prev_idx} 标题相似",
                    suggestion={"action": "review_duplicate", "indices": [prev_idx, i]}
                ))
        if title:
            seen_titles[title] = i
    
    return conflicts

def _string_similarity(s1: str, s2: str) -> float:
    """简单的字符串相似度计算（Jaccard系数）"""
    if not s1 or not s2:
        return 0.0
    
    set1 = set(s1.lower().split())
    set2 = set(s2.lower().split())
    
    if not set1 and not set2:
        return 1.0
    if not set1 or not set2:
        return 0.0
    
    intersection = set1 & set2
    union = set1 | set2
    
    return len(intersection) / len(union)

def required_fields_check(state: dict) -> List[Conflict]:
    """检查必填字段"""
    conflicts = []
    stories = state.get("data", {}).get("stories", [])
    
    required_fields = ["key", "title", "acceptance_criteria"]
    
    for i, story in enumerate(stories):
        for field in required_fields:
            value = story.get(field)
            if not value or (isinstance(value, list) and len(value) == 0):
                conflicts.append(Conflict(
                    type="structural",
                    rule="required_field",
                    severity="high",
                    message=f"Story at index {i} 缺少必填字段: '{field}'",
                    suggestion={
                        "action": "add_field",
                        "target": f"/stories/{i}/{field}",
                        "template": _get_field_template(field)
                    }
                ))
    return conflicts

def _get_field_template(field: str) -> Any:
    """获取字段的默认模板值"""
    templates = {
        "key": "STORY-XXX",
        "title": "待定标题",
        "acceptance_criteria": ["待补充验收标准"]
    }
    return templates.get(field, "")

# ========== 创建默认检测器 ==========

def create_default_detector() -> ConflictDetector:
    """创建包含所有默认规则的检测器"""
    rules = [
        Rule("auth_method_conflict", "high", auth_method_conflict, 
             "检测SSO与本地密码要求的互斥"),
        Rule("dependency_order", "medium", dependency_order,
             "检测依赖优先级的合理性"),
        Rule("timeline_consistency", "high", timeline_consistency,
             "检测时间线的一致性"),
        Rule("duplicate_detection", "medium", duplicate_detection,
             "检测重复或相似的stories"),
        Rule("required_fields_check", "high", required_fields_check,
             "检查必填字段的完整性")
    ]
    return ConflictDetector(rules)

# ========== 冲突自动修复建议生成器 ==========

class ConflictResolver:
    """基于冲突生成自动修复patches"""
    
    def suggest_fixes(self, conflicts: List[Conflict]) -> List[dict]:
        """为冲突生成修复patches"""
        fixes = []
        
        for conflict in conflicts:
            suggestion = conflict.suggestion
            if not suggestion:
                continue
            
            action = suggestion.get("action")
            
            if action == "remove_phrase":
                # 移除特定短语
                target = suggestion.get("from")
                phrase = suggestion.get("target")
                # 这里需要更复杂的实现来定位并移除短语
                pass
            
            elif action == "bump_priority":
                # 提升优先级
                target = suggestion.get("target")
                new_priority = suggestion.get("to")
                # 需要找到story并更新优先级
                pass
            
            elif action == "swap_dates":
                # 交换日期
                pass
            
            elif action == "add_field":
                # 添加缺失字段
                target = suggestion.get("target")
                template = suggestion.get("template")
                fixes.append({
                    "op": "add",
                    "path": target,
                    "value": template
                })
        
        return fixes
