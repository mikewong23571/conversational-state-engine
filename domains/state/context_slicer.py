# mypy: ignore-errors

"""
ContextSlicer for intelligent state slicing and context management
"""

import json
from dataclasses import dataclass
from typing import Any


@dataclass
class SliceConfig:
    """切片配置"""

    max_depth: int = 3
    max_size: int = 1000  # 最大节点数
    include_patterns: list[str] = None
    exclude_patterns: list[str] = None
    priority_fields: list[str] = None

    def __post_init__(self):
        if self.include_patterns is None:
            self.include_patterns = ["/stories", "/metadata", "/glossary"]
        if self.exclude_patterns is None:
            self.exclude_patterns = ["/history", "/temp"]
        if self.priority_fields is None:
            self.priority_fields = ["key", "title", "priority", "dependencies"]


@dataclass
class ContextSlice:
    """上下文切片"""

    id: str
    path: str
    data: Any
    metadata: dict[str, Any]
    dependencies: list[str]  # 依赖的其他切片ID
    size: int
    importance_score: float


class ContextSlicer:
    """智能状态切片器"""

    def __init__(self, config: SliceConfig = None):
        self.config = config or SliceConfig()
        self.slice_cache: dict[str, ContextSlice] = {}

    def slice_state(
        self, state: dict[str, Any], intent: str = None
    ) -> list[ContextSlice]:
        """根据意图对状态进行智能切片"""
        # 1. 分析意图，确定相关路径
        relevant_paths = self._analyze_intent(intent) if intent else []

        # 2. 生成切片候选
        candidates = self._generate_slice_candidates(state, relevant_paths)

        # 3. 评估和排序切片
        ranked_slices = self._rank_slices(candidates, intent)

        # 4. 应用大小限制
        final_slices = self._apply_size_limits(ranked_slices)

        # 缓存结果
        for slice_obj in final_slices:
            self.slice_cache[slice_obj.id] = slice_obj

        return final_slices

    def _analyze_intent(self, intent: str) -> list[str]:
        """分析意图，提取相关路径"""
        if not intent:
            return []

        relevant_paths = []
        intent_lower = intent.lower()

        # 关键词到路径的映射
        path_mapping = {
            "story": ["/stories"],
            "需求": ["/stories"],
            "功能": ["/stories"],
            "metadata": ["/metadata"],
            "glossary": ["/glossary"],
            "术语": ["/glossary"],
            "依赖": ["/stories/*/dependencies"],
            "priority": ["/stories/*/priority"],
            "优先级": ["/stories/*/priority"],
            "acceptance": ["/stories/*/acceptance_criteria"],
            "验收": ["/stories/*/acceptance_criteria"],
        }

        for keyword, paths in path_mapping.items():
            if keyword in intent_lower:
                relevant_paths.extend(paths)

        # 如果没有匹配的关键词，返回默认包含的路径
        if not relevant_paths:
            relevant_paths = self.config.include_patterns

        return list(set(relevant_paths))

    def _generate_slice_candidates(
        self, state: dict[str, Any], relevant_paths: list[str]
    ) -> list[ContextSlice]:
        """生成切片候选"""
        candidates = []

        # 基于相关路径生成切片
        for path_pattern in relevant_paths:
            path_slices = self._slice_by_path_pattern(state, path_pattern)
            candidates.extend(path_slices)

        # 基于数据类型生成切片
        type_slices = self._slice_by_data_types(state)
        candidates.extend(type_slices)

        # 基于依赖关系生成切片
        dep_slices = self._slice_by_dependencies(state)
        candidates.extend(dep_slices)

        return candidates

    def _slice_by_path_pattern(
        self, state: dict[str, Any], pattern: str
    ) -> list[ContextSlice]:
        """根据路径模式生成切片"""
        slices = []

        if pattern.endswith("/*"):
            # 通配符模式：处理数组
            base_path = pattern[:-2]
            base_data = self._get_path_value(state, base_path)

            if isinstance(base_data, list):
                for i, item in enumerate(base_data):
                    slice_path = f"{base_path}/{i}"
                    slice_data = self._extract_slice_data(item, max_depth=2)

                    slice_obj = ContextSlice(
                        id=f"path_{slice_path.replace('/', '_')}",
                        path=slice_path,
                        data=slice_data,
                        metadata={
                            "type": "path_wildcard",
                            "pattern": pattern,
                            "index": i,
                        },
                        dependencies=self._find_dependencies(slice_data),
                        size=self._calculate_size(slice_data),
                        importance_score=self._calculate_importance(slice_data),
                    )
                    slices.append(slice_obj)
        else:
            # 精确路径模式
            slice_data = self._get_path_value(state, pattern)
            if slice_data is not None:
                slice_obj = ContextSlice(
                    id=f"path_{pattern.replace('/', '_')}",
                    path=pattern,
                    data=slice_data,
                    metadata={"type": "path_exact", "pattern": pattern},
                    dependencies=self._find_dependencies(slice_data),
                    size=self._calculate_size(slice_data),
                    importance_score=self._calculate_importance(slice_data),
                )
                slices.append(slice_obj)

        return slices

    def _slice_by_data_types(self, state: dict[str, Any]) -> list[ContextSlice]:
        """根据数据类型生成切片"""
        slices = []

        # 提取所有stories
        stories = self._get_path_value(state, "/stories")
        if isinstance(stories, list):
            for i, story in enumerate(stories):
                # 按优先级分组
                priority = story.get("priority", "P2")
                slice_obj = ContextSlice(
                    id=f"priority_{priority}_story_{i}",
                    path=f"/stories/{i}",
                    data={
                        "key": story.get("key"),
                        "title": story.get("title"),
                        "priority": priority,
                        "dependencies": story.get("dependencies", []),
                    },
                    metadata={
                        "type": "priority_group",
                        "priority": priority,
                        "story_index": i,
                    },
                    dependencies=story.get("dependencies", []),
                    size=4,  # 固定大小
                    importance_score=self._get_priority_score(priority),
                )
                slices.append(slice_obj)

        return slices

    def _slice_by_dependencies(self, state: dict[str, Any]) -> list[ContextSlice]:
        """根据依赖关系生成切片"""
        slices = []
        stories = self._get_path_value(state, "/stories")

        if not isinstance(stories, list):
            return slices

        # 构建依赖图
        dep_graph = {}
        for i, story in enumerate(stories):
            key = story.get("key")
            if key:
                dep_graph[key] = {
                    "index": i,
                    "deps": story.get("dependencies", []),
                    "story": story,
                }

        # 找出独立的依赖链
        processed = set()
        for key, _node in dep_graph.items():
            if key in processed:
                continue

            # 收集依赖链
            chain = self._collect_dependency_chain(key, dep_graph, processed)
            if len(chain) > 1:
                chain_data = []
                for chain_key in chain:
                    if chain_key in dep_graph:
                        chain_data.append(dep_graph[chain_key]["story"])

                slice_obj = ContextSlice(
                    id=f"dep_chain_{'_'.join(chain)}",
                    path="/stories",
                    data=chain_data,
                    metadata={
                        "type": "dependency_chain",
                        "chain": chain,
                        "length": len(chain),
                    },
                    dependencies=[],
                    size=len(chain_data) * 5,  # 估算大小
                    importance_score=len(chain) * 0.8,  # 依赖链越长越重要
                )
                slices.append(slice_obj)

        return slices

    def _collect_dependency_chain(
        self, start_key: str, dep_graph: dict[str, Any], processed: set[str]
    ) -> list[str]:
        """收集依赖链"""
        chain = []
        current = start_key

        while current and current not in processed:
            processed.add(current)
            chain.append(current)

            # 找到依赖当前key的其他节点
            dependents = []
            for key, node in dep_graph.items():
                if current in node["deps"] and key not in processed:
                    dependents.append(key)

            # 简化处理：只取第一个依赖者
            if dependents:
                current = dependents[0]
            else:
                break

        return chain

    def _rank_slices(
        self, slices: list[ContextSlice], intent: str = None
    ) -> list[ContextSlice]:
        """对切片进行评分和排序"""
        # 计算综合得分
        for slice_obj in slices:
            # 基础重要性分数
            score = slice_obj.importance_score

            # 意图相关性加分
            if intent:
                relevance = self._calculate_intent_relevance(slice_obj, intent)
                score += relevance * 0.5

            # 大小惩罚（越大得分越低）
            size_penalty = min(slice_obj.size / 100, 1.0) * 0.3
            score -= size_penalty

            # 依赖复杂度加分
            if slice_obj.dependencies:
                score += len(slice_obj.dependencies) * 0.1

            slice_obj.importance_score = max(0, score)

        # 按得分排序
        return sorted(slices, key=lambda x: x.importance_score, reverse=True)

    def _calculate_intent_relevance(
        self, slice_obj: ContextSlice, intent: str
    ) -> float:
        """计算切片与意图的相关性"""
        if not intent:
            return 0

        intent_lower = intent.lower()
        relevance = 0

        # 检查路径相关性
        if "/stories" in slice_obj.path and any(
            word in intent_lower for word in ["story", "需求", "功能"]
        ):
            relevance += 0.8
        if "/glossary" in slice_obj.path and any(
            word in intent_lower for word in ["术语", "glossary"]
        ):
            relevance += 0.6
        if "priority" in slice_obj.path and any(
            word in intent_lower for word in ["priority", "优先级"]
        ):
            relevance += 0.7

        # 检查数据内容相关性
        data_str = json.dumps(slice_obj.data, default=str).lower()
        for keyword in ["p0", "p1", "p2", "登录", "注册", "认证"]:
            if keyword in intent_lower and keyword in data_str:
                relevance += 0.5

        return min(relevance, 1.0)

    def _apply_size_limits(self, slices: list[ContextSlice]) -> list[ContextSlice]:
        """应用大小限制"""
        final_slices = []
        total_size = 0

        for slice_obj in slices:
            if total_size + slice_obj.size <= self.config.max_size:
                final_slices.append(slice_obj)
                total_size += slice_obj.size
            else:
                # 尝试对大切片进行进一步分割
                if slice_obj.size > 100:  # 只对较大的切片进行分割
                    sub_slices = self._split_large_slice(slice_obj)
                    for sub_slice in sub_slices:
                        if total_size + sub_slice.size <= self.config.max_size:
                            final_slices.append(sub_slice)
                            total_size += sub_slice.size
                        else:
                            break
                break

        return final_slices

    def _split_large_slice(self, slice_obj: ContextSlice) -> list[ContextSlice]:
        """分割大切片"""
        if isinstance(slice_obj.data, list) and len(slice_obj.data) > 5:
            # 分割大数组
            mid = len(slice_obj.data) // 2
            return [
                ContextSlice(
                    id=f"{slice_obj.id}_part1",
                    path=slice_obj.path,
                    data=slice_obj.data[:mid],
                    metadata={**slice_obj.metadata, "part": 1, "total_parts": 2},
                    dependencies=slice_obj.dependencies,
                    size=mid,
                    importance_score=slice_obj.importance_score * 0.8,
                ),
                ContextSlice(
                    id=f"{slice_obj.id}_part2",
                    path=slice_obj.path,
                    data=slice_obj.data[mid:],
                    metadata={**slice_obj.metadata, "part": 2, "total_parts": 2},
                    dependencies=slice_obj.dependencies,
                    size=len(slice_obj.data) - mid,
                    importance_score=slice_obj.importance_score * 0.6,
                ),
            ]

        return [slice_obj]

    # ===== 辅助方法 =====

    def _get_path_value(self, data: Any, path: str) -> Any:
        """根据路径获取值（支持简单的JSON Pointer）"""
        if path == "/":
            return data

        parts = path.strip("/").split("/")
        current = data

        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            elif isinstance(current, list) and part.isdigit():
                current = current[int(part)]
            else:
                return None

        return current

    def _extract_slice_data(self, data: Any, max_depth: int = 3) -> Any:
        """提取切片数据（限制深度）"""
        if max_depth <= 0:
            return str(type(data))

        if isinstance(data, dict):
            result = {}
            for key, value in data.items():
                if key in self.config.priority_fields:
                    result[key] = value
                elif len(result) < 10:  # 限制字段数量
                    result[key] = self._extract_slice_data(value, max_depth - 1)
            return result
        elif isinstance(data, list):
            return [
                self._extract_slice_data(item, max_depth - 1) for item in data[:5]
            ]  # 限制列表长度
        else:
            return data

    def _find_dependencies(self, data: Any) -> list[str]:
        """查找数据中的依赖"""
        dependencies = []

        if isinstance(data, dict):
            deps = data.get("dependencies", [])
            if isinstance(deps, list):
                dependencies.extend(deps)

            # 查找类似 AUTH-XXX 的模式
            for value in data.values():
                if isinstance(value, str):
                    import re

                    found_deps = re.findall(r"[A-Z]+-[A-Z0-9]+", value)
                    dependencies.extend(found_deps)

        return list(set(dependencies))

    def _calculate_size(self, data: Any) -> int:
        """计算数据大小（估算节点数）"""
        if isinstance(data, dict):
            return len(data) + sum(self._calculate_size(v) for v in data.values())
        elif isinstance(data, list):
            return len(data) + sum(self._calculate_size(item) for item in data)
        else:
            return 1

    def _calculate_importance(self, data: Any) -> float:
        """计算数据的重要性分数"""
        score = 0.5  # 基础分数

        if isinstance(data, dict):
            # 优先级加分
            priority = data.get("priority", "")
            score += self._get_priority_score(priority)

            # 关键字段加分
            if data.get("key"):
                score += 0.3
            if data.get("title"):
                score += 0.2
            if data.get("acceptance_criteria"):
                score += 0.2

        return min(score, 1.0)

    def _get_priority_score(self, priority: str) -> float:
        """获取优先级分数"""
        priority_scores = {"P0": 1.0, "P1": 0.7, "P2": 0.4}
        return priority_scores.get(priority.upper(), 0.4)

    def get_slice(self, slice_id: str) -> ContextSlice | None:
        """获取缓存的切片"""
        return self.slice_cache.get(slice_id)

    def clear_cache(self):
        """清空缓存"""
        self.slice_cache.clear()


# ===== 使用示例 =====


def example_usage():
    """使用示例"""
    # 示例状态
    sample_state = {
        "metadata": {"project": "CSE Demo", "version": "1.0"},
        "data": {
            "stories": [
                {
                    "key": "AUTH-Login",
                    "title": "用户登录功能",
                    "priority": "P0",
                    "dependencies": ["AUTH-Register"],
                    "acceptance_criteria": ["支持生物识别认证", "失败3次锁定30分钟"],
                },
                {
                    "key": "AUTH-Register",
                    "title": "用户注册功能",
                    "priority": "P1",
                    "dependencies": [],
                    "acceptance_criteria": ["邮箱验证", "密码强度要求"],
                },
            ],
            "glossary": [{"term": "SSO", "definition": "单点登录"}],
        },
    }

    # 创建切片器
    slicer = ContextSlicer()

    # 切分状态
    intent = "添加一个新的P0级登录故事，要求支持生物识别认证"
    slices = slicer.slice_state(sample_state, intent)

    print(f"生成了 {len(slices)} 个切片:")
    for slice_obj in slices:
        print(
            f"- {slice_obj.id}: 重要性={slice_obj.importance_score:.2f}, 大小={slice_obj.size}"
        )


if __name__ == "__main__":
    example_usage()
