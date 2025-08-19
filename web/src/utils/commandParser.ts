/**
 * 命令通道解析器
 * 支持结构化命令语法，如：
 * /add story key=AUTH-Login priority=P0 platform=[iOS,Android] reason="移动端+生物识别"
 * /edit story key=AUTH-Login set priority=P1
 * /del story key=AUTH-Old
 * /set stories[$key==AUTH-Login].auth_type=SSO
 */

export interface CommandResult {
  type: 'command' | 'natural_language';
  command?: ParsedCommand;
  original: string;
}

export interface ParsedCommand {
  action: 'add' | 'edit' | 'delete' | 'set' | 'move';
  target: string;
  properties: Record<string, any>;
  reason?: string;
  confidence: number;
}

// 命令正则表达式
const COMMAND_PATTERNS = {
  add: /^\/add\s+(\w+)(?:\s+(.+))?$/,
  edit: /^\/edit\s+(\w+)(?:\s+(.+))?$/,
  del: /^\/del\s+(\w+)(?:\s+(.+))?$/,
  delete: /^\/delete\s+(\w+)(?:\s+(.+))?$/,
  set: /^\/set\s+(.+)$/,
  move: /^\/move\s+(\w+)(?:\s+(.+))?$/
};

/**
 * 解析键值对参数
 * 支持格式：key=value key="quoted value" key=[array,values] reason="reason text"
 */
function parseKeyValuePairs(input: string): Record<string, any> {
  const result: Record<string, any> = {};

  // 正则匹配 key=value, key="value", key=[array]
  const kvRegex = /(\w+)=(?:"([^"]*)"|(\[[^\]]*\])|([^\s]+))/g;
  let match;

  while ((match = kvRegex.exec(input)) !== null) {
    const key = match[1];
    const quotedValue = match[2];
    const arrayValue = match[3];
    const simpleValue = match[4];

    if (quotedValue !== undefined) {
      result[key] = quotedValue;
    } else if (arrayValue !== undefined) {
      // 解析数组 [item1,item2,item3]
      const arrayContent = arrayValue.slice(1, -1); // 移除 [ ]
      result[key] = arrayContent.split(',').map(item => item.trim());
    } else if (simpleValue !== undefined) {
      // 尝试解析为数字或保持字符串
      if (/^\d+$/.test(simpleValue)) {
        result[key] = parseInt(simpleValue, 10);
      } else if (/^\d*\.\d+$/.test(simpleValue)) {
        result[key] = parseFloat(simpleValue);
      } else if (simpleValue === 'true' || simpleValue === 'false') {
        result[key] = simpleValue === 'true';
      } else {
        result[key] = simpleValue;
      }
    }
  }

  return result;
}

/**
 * 生成目标路径
 */
function generateTargetPath(action: string, target: string, properties: Record<string, any>): string {
  switch (action) {
    case 'add':
      if (target === 'story') {
        return '/stories/-'; // 添加到数组末尾
      }
      return `/${target}/-`;

    case 'edit':
    case 'delete':
      if (target === 'story' && properties.key) {
        return `/stories/[key=${properties.key}]`; // 通过key查找
      }
      return `/${target}/0`; // 默认第一个

    case 'set':
      return target; // set命令中target就是完整路径

    case 'move':
      return `/${target}/0`; // 默认实现

    default:
      return `/${target}`;
  }
}

/**
 * 解析单个命令
 */
function parseCommand(input: string): ParsedCommand | null {
  const trimmed = input.trim();

  // 检查每种命令模式
  for (const [action, pattern] of Object.entries(COMMAND_PATTERNS)) {
    const match = trimmed.match(pattern);
    if (match) {
      const target = match[1];
      const params = match[2] || '';

      // 解析参数
      const properties = parseKeyValuePairs(params);
      const reason = properties.reason;
      delete properties.reason; // reason不是属性

      // 生成目标路径
      const targetPath = generateTargetPath(action, target, properties);

      return {
        action: action === 'del' || action === 'delete' ? 'delete' : action as any,
        target: targetPath,
        properties,
        reason,
        confidence: 1.0 // 命令解析置信度为100%
      };
    }
  }

  return null;
}

/**
 * 主解析函数
 */
export function parseUserInput(input: string): CommandResult {
  const trimmed = input.trim();

  // 检查是否是命令
  if (trimmed.startsWith('/')) {
    const command = parseCommand(trimmed);
    if (command) {
      return {
        type: 'command',
        command,
        original: input
      };
    }
  }

  // 不是命令或解析失败，返回自然语言
  return {
    type: 'natural_language',
    original: input
  };
}

/**
 * 获取命令帮助信息
 */
export function getCommandHelp(): string {
  return `
支持的命令格式：

/add <类型> [参数...]
  添加新项目
  示例: /add story key=AUTH-Login priority=P0 title="用户登录" reason="新增登录功能"

/edit <类型> [选择器] set [参数...]
  编辑现有项目
  示例: /edit story key=AUTH-Login set priority=P1 title="用户登录v2"

/del <类型> [选择器]
  删除项目
  示例: /del story key=AUTH-Old

/set <路径>=<值>
  设置特定路径的值
  示例: /set stories[key=AUTH-Login].auth_type=SSO

参数格式：
- 简单值: key=value
- 字符串: key="quoted value"
- 数组: key=[item1,item2,item3]
- 原因: reason="解释说明"
`;
}

/**
 * 验证命令语法
 */
export function validateCommand(command: ParsedCommand): { valid: boolean; errors: string[] } {
  const errors: string[] = [];

  if (!command.action) {
    errors.push('Missing action');
  }

  if (!command.target) {
    errors.push('Missing target');
  }

  // 特定验证
  if (command.action === 'add' && Object.keys(command.properties).length === 0) {
    errors.push('Add command requires at least one property');
  }

  if (command.action === 'edit' && Object.keys(command.properties).length === 0) {
    errors.push('Edit command requires at least one property to change');
  }

  return {
    valid: errors.length === 0,
    errors
  };
}
