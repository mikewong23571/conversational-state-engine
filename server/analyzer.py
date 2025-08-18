"""
Mock analyzer for dialogue to intention conversion
"""
import re
from typing import List, Dict, Any, Optional
from models import IntentionSet, Intention, Action

class MockAnalyzer:
    """Mock分析器，用规则和模板处理对话"""
    
    def __init__(self):
        # 命令模式正则
        self.command_patterns = {
            "add": re.compile(r"/add\s+(\w+)(?:\s+(.+))?"),
            "edit": re.compile(r"/edit\s+(\S+)\s+(.+)"),
            "delete": re.compile(r"/delete\s+(\S+)"),
            "move": re.compile(r"/move\s+(\S+)\s+to\s+(\S+)"),
            "set": re.compile(r"/set\s+(\S+)\s+(.+)")
        }
        
        # 自然语言关键词映射
        self.keywords = {
            "add": ["新增", "添加", "创建", "加入", "增加"],
            "modify": ["修改", "更改", "更新", "编辑", "调整"],
            "delete": ["删除", "移除", "去掉", "取消"],
            "priority": ["优先级", "P0", "P1", "P2", "紧急", "重要"],
            "story": ["故事", "需求", "功能", "story"],
            "acceptance": ["验收", "标准", "条件", "要求"]
        }
    
    def analyze(self, message: str, state: Dict[str, Any]) -> IntentionSet:
        """分析消息，提取意图"""
        
        # 首先尝试命令模式
        if message.startswith("/"):
            return self._parse_command(message)
        
        # 否则使用自然语言分析
        return self._parse_natural_language(message, state)
    
    def _parse_command(self, message: str) -> IntentionSet:
        """解析命令格式的消息"""
        intentions = []
        
        # 检查各种命令模式
        for action, pattern in self.command_patterns.items():
            match = pattern.match(message)
            if match:
                if action == "add":
                    entity_type = match.group(1)
                    params = match.group(2) if match.group(2) else ""
                    
                    # 解析参数
                    parsed_params = self._parse_params(params)
                    
                    if entity_type == "story":
                        value = {
                            "key": parsed_params.get("key", f"STORY-{self._generate_id()}"),
                            "title": parsed_params.get("title", "待定标题"),
                            "priority": parsed_params.get("priority", "P2"),
                            "acceptance_criteria": parsed_params.get("acceptance", [])
                        }
                        
                        intentions.append(Intention(
                            action=Action.add,
                            target_path="/stories/-",
                            value=value,
                            reason=parsed_params.get("reason"),
                            confidence=0.95
                        ))
                
                elif action == "edit":
                    path = match.group(1)
                    value = match.group(2)
                    
                    intentions.append(Intention(
                        action=Action.modify,
                        target_path=path,
                        value=self._parse_value(value),
                        confidence=0.95
                    ))
                
                elif action == "delete":
                    path = match.group(1)
                    
                    intentions.append(Intention(
                        action=Action.delete,
                        target_path=path,
                        confidence=0.95
                    ))
                
                break
        
        return IntentionSet(items=intentions)
    
    def _parse_natural_language(self, message: str, state: Dict[str, Any]) -> IntentionSet:
        """解析自然语言消息"""
        intentions = []
        message_lower = message.lower()
        
        # 检测动作类型
        action = None
        for act, keywords in self.keywords.items():
            if any(kw in message_lower for kw in keywords):
                if act in ["add", "modify", "delete"]:
                    action = act
                    break
        
        if not action:
            # 默认为添加
            action = "add"
        
        # 提取实体信息
        if "故事" in message_lower or "需求" in message_lower or "story" in message_lower:
            # 提取故事相关信息
            story_data = self._extract_story_info(message)
            
            if action == "add":
                intentions.append(Intention(
                    action=Action.add,
                    target_path="/stories/-",
                    value=story_data,
                    reason=f"用户请求: {message[:50]}...",
                    confidence=0.7
                ))
            elif action == "modify":
                # 需要确定要修改的故事
                # 这里简化处理，假设修改第一个故事
                intentions.append(Intention(
                    action=Action.modify,
                    target_path="/stories/0",
                    value=story_data,
                    reason=f"用户请求: {message[:50]}...",
                    confidence=0.6
                ))
        
        return IntentionSet(items=intentions, notes="通过自然语言分析提取，置信度较低")
    
    def _extract_story_info(self, message: str) -> Dict[str, Any]:
        """从消息中提取故事信息"""
        story = {
            "key": f"STORY-{self._generate_id()}",
            "title": "待定标题",
            "priority": "P2",
            "acceptance_criteria": []
        }
        
        message_lower = message.lower()
        
        # 提取优先级
        if "p0" in message_lower or "紧急" in message_lower:
            story["priority"] = "P0"
        elif "p1" in message_lower or "重要" in message_lower:
            story["priority"] = "P1"
        elif "p2" in message_lower:
            story["priority"] = "P2"
        
        # 提取标题（简化处理）
        if "登录" in message:
            story["title"] = "用户登录功能"
            story["key"] = "AUTH-Login"
        elif "注册" in message:
            story["title"] = "用户注册功能"
            story["key"] = "AUTH-Register"
        
        # 提取验收标准
        criteria = []
        if "生物识别" in message or "指纹" in message or "面部" in message:
            criteria.append("支持生物识别认证")
        if "失败" in message and "锁定" in message:
            # 尝试提取锁定规则
            import re
            match = re.search(r"失败(\d+)次.*锁定(\d+)", message)
            if match:
                criteria.append(f"失败{match.group(1)}次锁定{match.group(2)}分钟")
            else:
                criteria.append("包含失败锁定机制")
        if "移动" in message or "iOS" in message_lower or "android" in message_lower:
            story["platform"] = ["iOS", "Android"]
            criteria.append("支持移动端")
        
        # 提取依赖
        if "依赖" in message:
            # 简化处理：查找类似 AUTH-XXX 的模式
            import re
            deps = re.findall(r"[A-Z]+-[A-Z0-9]+", message)
            if deps:
                story["dependencies"] = deps
        
        if criteria:
            story["acceptance_criteria"] = criteria
        
        return story
    
    def _parse_params(self, params_str: str) -> Dict[str, Any]:
        """解析参数字符串"""
        params = {}
        
        # 简单的 key=value 解析
        import re
        pattern = re.compile(r'(\w+)=([^\s]+|\[.*?\]|".*?")')
        
        for match in pattern.finditer(params_str):
            key = match.group(1)
            value = match.group(2)
            
            # 处理不同类型的值
            if value.startswith('[') and value.endswith(']'):
                # 数组
                value = value[1:-1].split(',')
            elif value.startswith('"') and value.endswith('"'):
                # 字符串
                value = value[1:-1]
            
            params[key] = value
        
        # 查找 reason
        reason_match = re.search(r'reason="([^"]+)"', params_str)
        if reason_match:
            params["reason"] = reason_match.group(1)
        
        return params
    
    def _parse_value(self, value_str: str) -> Any:
        """解析值字符串"""
        # 尝试解析为JSON
        import json
        try:
            return json.loads(value_str)
        except:
            # 如果不是JSON，返回原始字符串
            return value_str
    
    def _generate_id(self) -> str:
        """生成随机ID"""
        import random
        return str(random.randint(100, 999))

class LLMAnalyzer:
    """基于LLM的分析器（未来实现）"""
    
    def __init__(self, llm_client):
        self.llm = llm_client
        self.mock_analyzer = MockAnalyzer()  # 降级方案
    
    async def analyze(self, message: str, state: Dict[str, Any]) -> IntentionSet:
        """使用LLM分析消息"""
        
        # 构建prompt
        prompt = self._build_prompt(message, state)
        
        try:
            # 调用LLM
            response = await self.llm.complete(prompt)
            
            # 解析响应
            intentions = self._parse_llm_response(response)
            
            return intentions
        except Exception as e:
            # 降级到Mock分析器
            print(f"LLM analysis failed, falling back to mock: {e}")
            return self.mock_analyzer.analyze(message, state)
    
    def _build_prompt(self, message: str, state: Dict[str, Any]) -> str:
        """构建LLM prompt"""
        return f"""
You are analyzing a user message to extract structured intentions for state modification.

Current State Schema:
- stories: array of user stories
  - key: unique identifier
  - title: story title
  - priority: P0, P1, or P2
  - acceptance_criteria: array of strings
  - dependencies: array of story keys

Current State Summary:
- {len(state.get('stories', []))} stories
- Priorities: {self._count_priorities(state)}

User Message: {message}

Extract the intentions as JSON:
{{
  "items": [
    {{
      "action": "add|modify|delete",
      "target_path": "RFC6901 JSON pointer",
      "value": <new value if applicable>,
      "reason": "why this change",
      "confidence": 0.0-1.0
    }}
  ],
  "notes": "any clarification needed"
}}

Response (JSON only):
"""
    
    def _count_priorities(self, state: Dict[str, Any]) -> str:
        """统计优先级分布"""
        stories = state.get("stories", [])
        counts = {"P0": 0, "P1": 0, "P2": 0}
        for story in stories:
            p = story.get("priority", "P2")
            counts[p] = counts.get(p, 0) + 1
        return f"P0:{counts['P0']}, P1:{counts['P1']}, P2:{counts['P2']}"
    
    def _parse_llm_response(self, response: str) -> IntentionSet:
        """解析LLM响应"""
        import json
        
        # 提取JSON部分
        json_start = response.find('{')
        json_end = response.rfind('}') + 1
        
        if json_start >= 0 and json_end > json_start:
            json_str = response[json_start:json_end]
            try:
                data = json.loads(json_str)
                return IntentionSet(**data)
            except:
                pass
        
        # 解析失败，返回空集
        return IntentionSet(items=[], notes="Failed to parse LLM response")
