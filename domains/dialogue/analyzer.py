"""
Mock analyzer for dialogue to intention conversion
"""

import json
import re
import time
from typing import Any, Dict, List, Optional

from domains.state.models import Action, Intention, IntentionSet


class MockAnalyzer:
    """Mock分析器，用规则和模板处理对话"""

    def __init__(self):
        # 命令模式正则
        self.command_patterns = {
            "add": re.compile(r"/add\s+(\w+)(?:\s+(.+))?"),
            "edit": re.compile(r"/edit\s+(\S+)\s+(.+)"),
            "delete": re.compile(r"/delete\s+(\S+)"),
            "move": re.compile(r"/move\s+(\S+)\s+to\s+(\S+)"),
            "set": re.compile(r"/set\s+(\S+)\s+(.+)"),
        }

        # 自然语言关键词映射
        self.keywords = {
            "add": ["新增", "添加", "创建", "加入", "增加"],
            "modify": ["修改", "更改", "更新", "编辑", "调整"],
            "delete": ["删除", "移除", "去掉", "取消"],
            "priority": ["优先级", "P0", "P1", "P2", "紧急", "重要"],
            "story": ["故事", "需求", "功能", "story"],
            "acceptance": ["验收", "标准", "条件", "要求"],
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
                            "key": parsed_params.get(
                                "key", f"STORY-{self._generate_id()}"
                            ),
                            "title": parsed_params.get("title", "待定标题"),
                            "priority": parsed_params.get("priority", "P2"),
                            "acceptance_criteria": parsed_params.get("acceptance", []),
                        }

                        intentions.append(
                            Intention(
                                action=Action.add,
                                target_path="/stories/-",
                                value=value,
                                reason=parsed_params.get("reason"),
                                confidence=0.95,
                            )
                        )

                elif action == "edit":
                    path = match.group(1)
                    value = match.group(2)

                    intentions.append(
                        Intention(
                            action=Action.modify,
                            target_path=path,
                            value=self._parse_value(value),
                            confidence=0.95,
                        )
                    )

                elif action == "delete":
                    path = match.group(1)

                    intentions.append(
                        Intention(
                            action=Action.delete, target_path=path, confidence=0.95
                        )
                    )

                break

        return IntentionSet(items=intentions)

    def _parse_natural_language(
        self, message: str, state: Dict[str, Any]
    ) -> IntentionSet:
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
        if (
            "故事" in message_lower
            or "需求" in message_lower
            or "story" in message_lower
        ):
            # 提取故事相关信息
            story_data = self._extract_story_info(message)

            if action == "add":
                intentions.append(
                    Intention(
                        action=Action.add,
                        target_path="/stories/-",
                        value=story_data,
                        reason=f"用户请求: {message[:50]}...",
                        confidence=0.7,
                    )
                )
            elif action == "modify":
                # 需要确定要修改的故事
                # 这里简化处理，假设修改第一个故事
                intentions.append(
                    Intention(
                        action=Action.modify,
                        target_path="/stories/0",
                        value=story_data,
                        reason=f"用户请求: {message[:50]}...",
                        confidence=0.6,
                    )
                )

        return IntentionSet(items=intentions, notes="通过自然语言分析提取，置信度较低")

    def _extract_story_info(self, message: str) -> Dict[str, Any]:
        """从消息中提取故事信息"""
        story = {
            "key": f"STORY-{self._generate_id()}",
            "title": "待定标题",
            "priority": "P2",
            "acceptance_criteria": [],
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
            if value.startswith("[") and value.endswith("]"):
                # 数组
                value = value[1:-1].split(",")
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


class OpenAIAnalyzer:
    """OpenAI兼容API分析器 - 支持OpenAI、vLLM、Ollama、DeepSeek等"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-3.5-turbo",
        base_url: Optional[str] = None,
    ):
        import os

        self.api_key = (
            api_key or os.getenv("OPENAI_API_KEY") or os.getenv("CSE_API_KEY")
        )
        self.model = model or os.getenv("CSE_MODEL", "gpt-3.5-turbo")
        self.base_url = (
            base_url or os.getenv("OPENAI_BASE_URL") or os.getenv("CSE_BASE_URL")
        )
        self.mock_analyzer = MockAnalyzer()  # 降级方案

        if self.api_key:
            try:
                import os

                from openai import OpenAI

                # 清理代理设置
                proxy_vars = [
                    "http_proxy",
                    "https_proxy",
                    "HTTP_PROXY",
                    "HTTPS_PROXY",
                    "ALL_PROXY",
                    "all_proxy",
                ]
                for var in proxy_vars:
                    if var in os.environ:
                        del os.environ[var]

                # 支持自定义base_url用于OpenAI兼容的API提供商
                client_kwargs = {"api_key": self.api_key, "http_client": None}
                if self.base_url:
                    client_kwargs["base_url"] = self.base_url
                    print(f"Using OpenAI-compatible API at: {self.base_url}")
                else:
                    print("Using OpenAI official API")

                self.client = OpenAI(**client_kwargs)
                print(f"Model: {self.model}")

            except ImportError:
                print("OpenAI package not installed, falling back to mock")
                self.client = None
            except Exception as e:
                print(f"Failed to initialize OpenAI client: {e}")
                self.client = None
        else:
            print(
                "No API key provided (set OPENAI_API_KEY or CSE_API_KEY), using mock analyzer"
            )
            self.client = None

    async def analyze(self, message: str, state: Dict[str, Any]) -> IntentionSet:
        """使用OpenAI分析消息"""

        if not self.client:
            print("📝 LLM Call: Using Mock Analyzer (no client available)")
            return self.mock_analyzer.analyze(message, state)

        # 构建few-shot prompt
        prompt = self._build_few_shot_prompt(message, state)

        # Log the LLM call
        print(f"\n🤖 LLM Call Started")
        print(f"   Model: {self.model}")
        print(f"   Message: {message[:100]}{'...' if len(message) > 100 else ''}")
        print(f"   State stories count: {len(state.get('stories', []))}")
        print(f"   Prompt length: {len(prompt)} characters")

        try:
            start_time = time.time()

            # 调用OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at analyzing user requirements and extracting structured intentions for state modification. Always respond with valid JSON.",
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=1000,
                temperature=0.1,
            )

            end_time = time.time()
            latency = end_time - start_time

            # 解析响应
            content = response.choices[0].message.content
            intentions = self._parse_llm_response(content)

            # Log the LLM response
            print(f"✅ LLM Call Completed")
            print(f"   Latency: {latency:.2f}s")
            print(f"   Response ID: {response.id}")
            print(f"   Model used: {response.model}")
            print(f"   Usage: {response.usage}")
            print(f"   Raw response length: {len(content)} characters")
            print(f"   Parsed intentions: {len(intentions.items)} items")
            print(
                f"   Response preview: {content[:200]}{'...' if len(content) > 200 else ''}"
            )

            # Log detailed prompt and response for debugging
            print(f"\n📋 Full Prompt:")
            print(f"   {prompt}")
            print(f"\n📋 Full Response:")
            print(f"   {content}")
            print(f"\n{'='*60}\n")

            return intentions
        except Exception as e:
            # 降级到Mock分析器
            print(f"❌ LLM Call Failed: {e}")
            print(f"   Falling back to Mock Analyzer")
            return self.mock_analyzer.analyze(message, state)

    def _build_few_shot_prompt(self, message: str, state: Dict[str, Any]) -> str:
        """构建包含few-shot示例的prompt"""
        return f"""
I need to analyze user messages and extract structured intentions for state modification.

SCHEMA:
- stories: array of user stories
  - key: unique identifier (format: PREFIX-DESCRIPTION)
  - title: story title
  - priority: P0 (critical), P1 (high), P2 (medium)
  - acceptance_criteria: array of strings
  - dependencies: array of story keys
  - auth_type: "password" | "sso" | "biometric" (for auth stories)
  - platform: array of platforms if applicable

CURRENT STATE:
- {len(state.get('stories', []))} existing stories
- Priority distribution: {self._count_priorities(state) or 'Unknown'}

EXAMPLES:

User: "Add a user login story with biometric authentication support"
Response:
{{
  "items": [
    {{
      "action": "add",
      "target_path": "/stories/-",
      "value": {{
        "key": "AUTH-Login",
        "title": "User Login with Biometric Authentication",
        "priority": "P1",
        "acceptance_criteria": [
          "User can log in with username/password",
          "User can log in with biometric authentication",
          "Failed login attempts are tracked"
        ],
        "auth_type": "biometric"
      }},
      "reason": "User requested login functionality with biometric support",
      "confidence": 0.9
    }}
  ]
}}

User: "Update AUTH-Login to be P0 priority and add SSO support"
Response:
{{
  "items": [
    {{
      "action": "modify",
      "target_path": "/stories/0/priority",
      "value": "P0",
      "reason": "User requested priority upgrade to P0",
      "confidence": 0.95
    }},
    {{
      "action": "modify",
      "target_path": "/stories/0/auth_type",
      "value": "sso",
      "reason": "User requested SSO authentication support",
      "confidence": 0.9
    }},
    {{
      "action": "modify",
      "target_path": "/stories/0/acceptance_criteria/-",
      "value": "User can log in via SSO provider",
      "reason": "Adding SSO acceptance criteria",
      "confidence": 0.85
    }}
  ]
}}

User: "Remove the user registration story"
Response:
{{
  "items": [
    {{
      "action": "delete",
      "target_path": "/stories/1",
      "reason": "User requested removal of registration story",
      "confidence": 0.9
    }}
  ]
}}

NOW ANALYZE:

User Message: {message}

Extract the intentions as JSON (JSON only, no explanation):
"""

    def _count_priorities(self, state: Dict[str, Any]) -> str:
        """统计优先级分布"""
        stories = state.get("stories", []) or []
        counts = {"P0": 0, "P1": 0, "P2": 0}
        for story in stories:
            p = story.get("priority", "P2")
            if p not in counts:
                p = "P2"  # Default to P2 if unknown priority
            counts[p] = counts.get(p, 0) + 1

        # Ensure all values are integers before formatting
        p0_count = counts.get("P0", 0) or 0
        p1_count = counts.get("P1", 0) or 0
        p2_count = counts.get("P2", 0) or 0

        return f"P0:{p0_count}, P1:{p1_count}, P2:{p2_count}"

    def _parse_llm_response(self, response: str) -> IntentionSet:
        """解析LLM响应"""
        print(f"\n🔍 Parsing LLM Response...")

        # 清理响应
        response = response.strip()
        print(f"   Response length: {len(response)} chars")

        # 提取JSON部分
        json_start = response.find("{")
        json_end = response.rfind("}") + 1

        print(f"   JSON start: {json_start}, JSON end: {json_end}")

        if json_start >= 0 and json_end > json_start:
            json_str = response[json_start:json_end]
            print(f"   Extracted JSON length: {len(json_str)} chars")

            try:
                data = json.loads(json_str)
                print(f"   ✅ JSON parsed successfully")
                print(f"   Data keys: {list(data.keys())}")

                # 验证数据格式
                if "items" not in data:
                    data["items"] = []
                    print(f"   ⚠️  Added missing 'items' key")

                print(f"   Items count: {len(data['items'])}")

                # 转换action字符串为Action枚举
                for i, item in enumerate(data["items"]):
                    if "action" in item:
                        action_str = item["action"].lower()
                        original_action = item["action"]
                        if action_str == "add":
                            item["action"] = Action.add
                        elif action_str == "modify" or action_str == "update":
                            item["action"] = Action.modify
                        elif action_str == "delete" or action_str == "remove":
                            item["action"] = Action.delete
                        print(f"   Item {i}: {original_action} → {item['action']}")

                intention_set = IntentionSet(**data)
                print(f"   ✅ IntentionSet created successfully")
                return intention_set

            except json.JSONDecodeError as e:
                print(f"   ❌ JSON decode error: {e}")
                print(f"   Raw response: {response}")
                error_msg = str(e) if e else "Unknown JSON decode error"
                return IntentionSet(
                    items=[], notes=f"Failed to parse LLM response: {error_msg}"
                )
            except Exception as e:
                print(f"   ❌ Data validation error: {e}")
                print(f"   Parsed data: {data}")
                error_msg = str(e) if e else "Unknown validation error"
                return IntentionSet(
                    items=[], notes=f"Data validation error: {error_msg}"
                )

        # 解析失败，返回空集
        print(f"   ❌ No JSON found in response")
        return IntentionSet(items=[], notes="No JSON found in LLM response")


class LLMAnalyzer:
    """LLM分析器工厂类"""

    @staticmethod
    def create(provider: str = "openai", **kwargs) -> "OpenAIAnalyzer":
        """创建LLM分析器实例"""
        if provider.lower() == "openai":
            return OpenAIAnalyzer(**kwargs)
        elif provider.lower() == "mock":
            return MockAnalyzer()
        else:
            print(f"Unknown provider {provider}, falling back to mock")
            return MockAnalyzer()
