/**
 * 意图推断工具
 * 从自然语言中推断用户的操作意图
 */

export interface InferredIntent {
  action: 'add' | 'modify' | 'delete' | 'move' | 'set';
  target_path: string;
  confidence: number;
  reasoning: string;
}

// 关键词映射
const ACTION_KEYWORDS = {
  add: [
    '创建', '添加', '新建', '增加', '建立', '制作', '开发', '构建',
    'create', 'add', 'new', 'build', 'make', 'develop', 'establish'
  ],
  modify: [
    '修改', '更新', '改变', '调整', '优化', '改进', '变更', '编辑',
    'modify', 'update', 'change', 'edit', 'improve', 'optimize', 'adjust'
  ],
  delete: [
    '删除', '移除', '去掉', '清除', '取消', '撤销',
    'delete', 'remove', 'clear', 'cancel', 'eliminate'
  ],
  move: [
    '移动', '转移', '迁移', '重新排列',
    'move', 'transfer', 'relocate', 'rearrange'
  ],
  set: [
    '设置', '配置', '指定', '定义',
    'set', 'configure', 'define', 'specify'
  ]
};

// 目标类型关键词
const TARGET_KEYWORDS = {
  story: ['故事', '需求', 'story', 'requirement', 'feature'],
  tool: ['工具', 'tool', '命令行', 'cli', '脚本', 'script'],
  config: ['配置', 'config', 'setting', '设置'],
  user: ['用户', 'user', '账户', 'account'],
  auth: ['认证', '登录', 'auth', 'login', '权限', 'permission']
};

/**
 * 从文本中推断操作类型
 */
function inferAction(text: string): { action: string; confidence: number; reasoning: string } {
  const lowerText = text.toLowerCase();
  const scores: Record<string, { score: number; matches: string[] }> = {};

  // 计算每种操作的得分
  for (const [action, keywords] of Object.entries(ACTION_KEYWORDS)) {
    scores[action] = { score: 0, matches: [] };

    for (const keyword of keywords) {
      if (lowerText.includes(keyword.toLowerCase())) {
        scores[action].score += 1;
        scores[action].matches.push(keyword);
      }
    }
  }

  // 找到得分最高的操作
  const sortedActions = Object.entries(scores)
    .sort(([,a], [,b]) => b.score - a.score)
    .filter(([,data]) => data.score > 0);

  if (sortedActions.length === 0) {
    // 默认为modify，但置信度很低
    return {
      action: 'modify',
      confidence: 0.3,
      reasoning: '无法识别明确的操作关键词，默认为修改操作'
    };
  }

  const [bestAction, bestData] = sortedActions[0];
  const confidence = Math.min(0.9, 0.5 + bestData.score * 0.2); // 基础0.5 + 关键词加成

  return {
    action: bestAction,
    confidence,
    reasoning: `检测到关键词: ${bestData.matches.join(', ')}`
  };
}

/**
 * 从文本中推断目标路径
 */
function inferTargetPath(text: string, action: string): { path: string; confidence: number } {
  const lowerText = text.toLowerCase();

  // 检测目标类型
  for (const [targetType, keywords] of Object.entries(TARGET_KEYWORDS)) {
    for (const keyword of keywords) {
      if (lowerText.includes(keyword.toLowerCase())) {
        const basePath =
          targetType === 'story' || targetType === 'tool'
            ? '/stories'
            : `/${targetType}`;
        const path = action === 'add' ? `${basePath}/-` : `${basePath}/0`;

        return {
          path,
          confidence: 0.8
        };
      }
    }
  }

  // 默认假设是故事相关
  const defaultPath = action === 'add' ? '/stories/-' : '/stories/0';
  return {
    path: defaultPath,
    confidence: 0.4
  };
}

/**
 * 主要的意图推断函数
 */
export function inferIntentFromText(text: string): InferredIntent {
  const actionResult = inferAction(text);
  const targetResult = inferTargetPath(text, actionResult.action);

  // 综合置信度
  const overallConfidence = (actionResult.confidence + targetResult.confidence) / 2;

  return {
    action: actionResult.action as any,
    target_path: targetResult.path,
    confidence: overallConfidence,
    reasoning: `${actionResult.reasoning}; 推断目标: ${targetResult.path}`
  };
}

/**
 * 验证推断结果的合理性
 */
export function validateInferredIntent(intent: InferredIntent, _originalText: string): {
  valid: boolean;
  issues: string[];
  suggestions: string[];
} {
  const issues: string[] = [];
  const suggestions: string[] = [];

  // 检查置信度
  if (intent.confidence < 0.5) {
    issues.push('意图推断置信度较低');
    suggestions.push('建议使用结构化命令获得更准确的结果');
  }

  // 检查操作与目标的匹配性
  if (intent.action === 'add' && !intent.target_path.endsWith('/-')) {
    issues.push('添加操作的目标路径应该以 /- 结尾');
  }

  if (intent.action === 'delete' && intent.target_path.endsWith('/-')) {
    issues.push('删除操作不能指向数组末尾');
  }

  return {
    valid: issues.length === 0,
    issues,
    suggestions
  };
}

/**
 * 为用户提供命令建议
 */
export function suggestCommand(intent: InferredIntent, originalText: string): string {
  const { action, target_path } = intent;

  if (target_path.includes('/stories')) {
    const baseCommand = action === 'add' ? '/add story' :
                       action === 'modify' ? '/edit story' :
                       action === 'delete' ? '/del story' :
                       `/set ${target_path}`;

    if (action === 'add') {
      return `${baseCommand} key=NEW-TOOL priority=P1 title="命令行工具" reason="优化代码工具"`;
    } else if (action === 'modify') {
      return `${baseCommand} key=EXISTING-KEY set title="新标题"`;
    } else if (action === 'delete') {
      return `${baseCommand} key=TARGET-KEY`;
    }
  }

  return `/add story key=AUTO-${Date.now()} title="基于用户输入" reason="${originalText.slice(0, 50)}"`;
}
