"""
Incremental renderer for efficient artifact generation
"""
from typing import Dict, List, Set, Any, Optional
from datetime import datetime
import hashlib
import json
from jinja2 import Template, Environment, FileSystemLoader
import os

class IncrementalRenderer:
    """增量渲染器，只重新渲染受影响的片段"""
    
    def __init__(self, template_dir: str = "templates"):
        self.cache: Dict[str, str] = {}  # fragment_id -> rendered_content
        self.checksums: Dict[str, str] = {}  # fragment_id -> content_hash
        self.dependencies: Dict[str, Set[str]] = {}  # path -> affected_fragment_ids
        
        # Jinja2环境
        if os.path.exists(template_dir):
            self.env = Environment(loader=FileSystemLoader(template_dir))
        else:
            self.env = Environment()
        
        # 初始化依赖映射
        self._init_dependencies()
    
    def _init_dependencies(self):
        """初始化路径到片段的依赖映射"""
        # 基础映射规则
        self.dependencies = {
            "/stories": {"story_list", "summary"},
            "/stories/*": {"story_list", "story_detail"},
            "/glossary": {"glossary", "summary"},
            "/glossary/*": {"glossary"},
            "/metadata": {"header", "summary"},
        }
    
    def render_incremental(self, state: dict, patches: List[dict], 
                          template_name: str = "requirements.md") -> str:
        """增量渲染：只重新渲染受patches影响的片段"""
        
        # 1. 识别受影响的片段
        affected_fragments = self._get_affected_fragments(patches)
        
        # 2. 重新渲染受影响的片段
        for fragment_id in affected_fragments:
            content = self._render_fragment(state, fragment_id, template_name)
            
            # 计算内容hash
            content_hash = hashlib.md5(content.encode()).hexdigest()
            
            # 只有内容真正改变时才更新缓存
            if self.checksums.get(fragment_id) != content_hash:
                self.cache[fragment_id] = content
                self.checksums[fragment_id] = content_hash
        
        # 3. 组装完整输出
        return self._assemble(template_name, state)
    
    def _get_affected_fragments(self, patches: List[dict]) -> Set[str]:
        """根据patches确定受影响的片段"""
        affected = set()
        
        for patch in patches:
            path = patch.get("path", "")
            
            # 匹配依赖规则
            for pattern, fragments in self.dependencies.items():
                if self._path_matches(path, pattern):
                    affected.update(fragments)
        
        return affected
    
    def _path_matches(self, path: str, pattern: str) -> bool:
        """检查路径是否匹配模式"""
        if pattern.endswith("/*"):
            # 通配符匹配
            prefix = pattern[:-2]
            return path.startswith(prefix)
        else:
            # 精确匹配或前缀匹配
            return path == pattern or path.startswith(pattern + "/")
    
    def _render_fragment(self, state: dict, fragment_id: str, 
                        template_name: str) -> str:
        """渲染单个片段"""
        
        # 片段渲染器映射
        fragment_renderers = {
            "header": self._render_header,
            "summary": self._render_summary,
            "story_list": self._render_story_list,
            "story_detail": self._render_story_detail,
            "glossary": self._render_glossary,
        }
        
        renderer = fragment_renderers.get(fragment_id, self._render_default)
        return renderer(state)
    
    def _render_header(self, state: dict) -> str:
        """渲染文档头部"""
        metadata = state.get("metadata", {})
        version = state.get("version", "unknown")
        
        return f"""# 需求规格说明书
        
**版本**: {version}  
**更新时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**项目**: {metadata.get('project', 'Unknown Project')}

---

"""
    
    def _render_summary(self, state: dict) -> str:
        """渲染摘要统计"""
        stories = state.get("data", {}).get("stories", [])
        
        # 按优先级统计
        priority_count = {"P0": 0, "P1": 0, "P2": 0}
        for story in stories:
            priority = story.get("priority", "P2")
            priority_count[priority] = priority_count.get(priority, 0) + 1
        
        return f"""## 摘要

- **需求总数**: {len(stories)}
- **P0需求**: {priority_count['P0']}
- **P1需求**: {priority_count['P1']}
- **P2需求**: {priority_count['P2']}

---

"""
    
    def _render_story_list(self, state: dict) -> str:
        """渲染用户故事列表"""
        stories = state.get("data", {}).get("stories", [])
        
        if not stories:
            return "## 用户故事\n\n*暂无用户故事*\n\n"
        
        content = "## 用户故事\n\n"
        
        # 按优先级分组
        for priority in ["P0", "P1", "P2"]:
            priority_stories = [s for s in stories if s.get("priority") == priority]
            if priority_stories:
                content += f"### {priority} 级需求\n\n"
                for story in priority_stories:
                    content += f"- **{story.get('key', 'NO-KEY')}**: {story.get('title', '无标题')}\n"
                content += "\n"
        
        return content
    
    def _render_story_detail(self, state: dict) -> str:
        """渲染用户故事详情"""
        stories = state.get("data", {}).get("stories", [])
        
        if not stories:
            return ""
        
        content = "## 需求详情\n\n"
        
        for story in stories:
            content += f"### {story.get('key', 'NO-KEY')}: {story.get('title', '无标题')}\n\n"
            
            # 基本信息
            content += f"**优先级**: {story.get('priority', 'P2')}  \n"
            
            if story.get('platform'):
                content += f"**平台**: {', '.join(story.get('platform', []))}  \n"
            
            if story.get('dependencies'):
                content += f"**依赖**: {', '.join(story.get('dependencies', []))}  \n"
            
            # 验收标准
            criteria = story.get('acceptance_criteria', [])
            if criteria:
                content += "\n**验收标准**:\n"
                for criterion in criteria:
                    content += f"- {criterion}\n"
            
            content += "\n---\n\n"
        
        return content
    
    def _render_glossary(self, state: dict) -> str:
        """渲染术语表"""
        glossary = state.get("data", {}).get("glossary", [])
        
        if not glossary:
            return "## 术语表\n\n*暂无术语定义*\n\n"
        
        content = "## 术语表\n\n"
        
        for term in glossary:
            content += f"- **{term.get('term', '')}**: {term.get('definition', '')}\n"
        
        content += "\n"
        return content
    
    def _render_default(self, state: dict) -> str:
        """默认渲染器"""
        return ""
    
    def _assemble(self, template_name: str, state: dict) -> str:
        """组装所有片段为完整文档"""
        
        # 定义片段顺序
        fragment_order = [
            "header",
            "summary",
            "story_list",
            "story_detail",
            "glossary"
        ]
        
        # 组装内容
        full_content = ""
        for fragment_id in fragment_order:
            if fragment_id in self.cache:
                full_content += self.cache[fragment_id]
            else:
                # 首次渲染
                content = self._render_fragment(state, fragment_id, template_name)
                self.cache[fragment_id] = content
                self.checksums[fragment_id] = hashlib.md5(content.encode()).hexdigest()
                full_content += content
        
        return full_content
    
    def clear_cache(self):
        """清空渲染缓存"""
        self.cache.clear()
        self.checksums.clear()
    
    def get_cache_stats(self) -> dict:
        """获取缓存统计信息"""
        return {
            "cached_fragments": len(self.cache),
            "total_size": sum(len(c) for c in self.cache.values()),
            "fragments": list(self.cache.keys())
        }

class MarkdownRenderer(IncrementalRenderer):
    """Markdown格式渲染器"""
    
    def render_to_markdown(self, state: dict) -> str:
        """渲染为Markdown格式"""
        return self._assemble("requirements.md", state)

class CSVRenderer:
    """CSV格式渲染器（用于验收用例）"""
    
    def render_acceptance_criteria(self, state: dict) -> str:
        """渲染验收标准为CSV格式"""
        import csv
        import io
        
        stories = state.get("data", {}).get("stories", [])
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # 写入表头
        writer.writerow(["Story Key", "Title", "Priority", "Criterion", "Status"])
        
        # 写入数据
        for story in stories:
            key = story.get("key", "")
            title = story.get("title", "")
            priority = story.get("priority", "P2")
            
            criteria = story.get("acceptance_criteria", [])
            if criteria:
                for criterion in criteria:
                    writer.writerow([key, title, priority, criterion, "待验证"])
            else:
                writer.writerow([key, title, priority, "无验收标准", "待补充"])
        
        return output.getvalue()

# 渲染器工厂
def create_renderer(format_type: str = "markdown") -> Any:
    """根据格式类型创建渲染器"""
    renderers = {
        "markdown": MarkdownRenderer,
        "csv": CSVRenderer,
    }
    
    renderer_class = renderers.get(format_type, MarkdownRenderer)
    return renderer_class()
