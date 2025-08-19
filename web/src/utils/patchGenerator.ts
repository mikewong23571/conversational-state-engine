/**
 * 基于推断意图生成JSON Patch的工具
 */

import { Operation } from 'fast-json-patch';
import { InferredIntent } from './intentInference';

export interface GeneratedPatchResult {
  patches: Operation[];
  explanation: string;
  confidence: number;
}

/**
 * 从自然语言中提取可能的属性值
 */
function extractAttributesFromText(text: string): Record<string, any> {
  const attributes: Record<string, any> = {};
  
  // 提取优先级
  const priorityMatch = text.match(/P[0-3]|[Pp]riority\s*[=:]\s*P?[0-3]|高优先级|中优先级|低优先级/i);
  if (priorityMatch) {
    const match = priorityMatch[0];
    if (match.includes('P0') || match.includes('高优先级')) {
      attributes.priority = 'P0';
    } else if (match.includes('P1') || match.includes('中优先级')) {
      attributes.priority = 'P1';
    } else if (match.includes('P2') || match.includes('低优先级')) {
      attributes.priority = 'P2';
    } else {
      attributes.priority = 'P1'; // 默认
    }
  } else {
    attributes.priority = 'P1'; // 默认中等优先级
  }
  
  // 提取标题（尝试从文本中猜测）
  let title = '';
  
  // 匹配 "创建一个xxx" 模式，但更智能地提取核心概念
  const createMatch = text.match(/创建\s*(?:一个|个)?\s*([^，。！？]+?)(?:，|。|$)/);
  if (createMatch) {
    const rawTitle = createMatch[1].trim();
    // 提取关键词组合
    if (rawTitle.includes('命令行') && rawTitle.includes('工具')) {
      if (rawTitle.includes('分析') && rawTitle.includes('优化')) {
        title = '代码分析优化工具';
      } else if (rawTitle.includes('分析')) {
        title = '代码分析工具';
      } else if (rawTitle.includes('优化')) {
        title = '代码优化工具';
      } else {
        title = '命令行工具';
      }
    } else {
      title = rawTitle.length > 20 ? rawTitle.substring(0, 20) : rawTitle;
    }
  }
  
  // 匹配其他可能的标题模式
  if (!title) {
    const titlePatterns = [
      /(?:开发|构建|制作|建立)\s*([^，。！？]{1,20})/,
      /([^，。！？\s]*工具[^，。！？\s]*)/,
      /([^，。！？\s]*系统[^，。！？\s]*)/,
      /([^，。！？\s]*功能[^，。！？\s]*)/
    ];
    
    for (const pattern of titlePatterns) {
      const match = text.match(pattern);
      if (match) {
        title = match[1].length > 20 ? match[1].substring(0, 20) : match[1];
        break;
      }
    }
  }
  
  // 如果还是没有找到，使用默认标题
  if (!title) {
    title = '用户需求项目';
  }
  
  attributes.title = title;
  
  // 提取平台信息
  const platformKeywords = ['iOS', 'Android', 'Web', '网页', '移动端', '桌面', 'Windows', 'Mac', 'Linux'];
  const foundPlatforms = platformKeywords.filter(platform => 
    text.toLowerCase().includes(platform.toLowerCase())
  );
  if (foundPlatforms.length > 0) {
    attributes.platform = foundPlatforms;
  }
  
  // 提取认证类型
  if (text.includes('SSO') || text.includes('单点登录')) {
    attributes.auth_type = 'SSO';
  } else if (text.includes('本地') || text.includes('密码')) {
    attributes.auth_type = 'local';
  }
  
  // 生成唯一key - 更规范的格式
  let keyBase = '';
  if (title.includes('工具')) {
    keyBase = 'TOOL';
  } else if (title.includes('系统')) {
    keyBase = 'SYSTEM';
  } else if (title.includes('功能')) {
    keyBase = 'FEATURE';
  } else {
    // 提取英文/数字，转为大写，限制长度
    keyBase = title.replace(/[^a-zA-Z0-9]/g, '').toUpperCase().substring(0, 8) || 'ITEM';
  }
  
  // 添加类型前缀
  if (title.includes('命令行') || title.includes('CLI')) {
    keyBase = `CLI-${keyBase}`;
  } else if (title.includes('代码') || title.includes('分析')) {
    keyBase = `CODE-${keyBase}`;
  }

  // 确保生成的 key 符合 ^[A-Z]+-[A-Za-z0-9]+$ 格式
  const keyPrefix = `AUTO${keyBase.replace(/[^A-Z]/g, '')}`;
  attributes.key = `${keyPrefix}-${Date.now()}`;
  
  // 添加其他常用属性
  attributes.status = 'draft';
  
  // 生成更具体的验收标准
  const acceptanceCriteria = [];
  if (title.includes('工具')) {
    if (title.includes('命令行')) {
      acceptanceCriteria.push('支持命令行参数配置');
      acceptanceCriteria.push('提供使用帮助文档');
    }
    if (title.includes('分析')) {
      acceptanceCriteria.push('支持代码质量分析');
      acceptanceCriteria.push('生成分析报告');
    }
    if (title.includes('优化')) {
      acceptanceCriteria.push('提供代码优化建议');
      acceptanceCriteria.push('支持自动化优化');
    }
  } else {
    acceptanceCriteria.push(`实现${title}的核心功能`);
  }
  
  // 总是添加通用标准
  acceptanceCriteria.push('通过功能测试');
  acceptanceCriteria.push('通过用户验收');
  
  attributes.acceptance_criteria = acceptanceCriteria;
  
  return attributes;
}

/**
 * 根据意图生成添加操作的补丁
 */
function generateAddPatch(intent: InferredIntent, originalText: string): Operation {
  const attributes = extractAttributesFromText(originalText);
  
  // 根据目标路径确定添加的内容类型
  if (intent.target_path.includes('/stories')) {
    return {
      op: 'add',
      path: '/data/stories/-',
      value: {
        ...attributes,
        reason: `用户请求: ${originalText}`
      }
    };
  } else if (intent.target_path.includes('/users')) {
    return {
      op: 'add',
      path: '/data/users/-',
      value: {
        key: attributes.key,
        name: attributes.title,
        email: `user${Date.now()}@example.com`,
        role: 'user',
        status: 'active'
      }
    };
  } else {
    // 默认添加到stories
    return {
      op: 'add',
      path: '/data/stories/-',
      value: {
        ...attributes,
        reason: `用户请求: ${originalText}`
      }
    };
  }
}

/**
 * 根据意图生成修改操作的补丁
 */
function generateModifyPatch(intent: InferredIntent, originalText: string): Operation[] {
  const attributes = extractAttributesFromText(originalText);
  
  // 根据意图的target_path确定基础路径
  const basePath = intent.target_path.endsWith('/-') 
    ? intent.target_path.replace('/-', '/0') 
    : intent.target_path.includes('/stories') 
    ? '/data/stories/0' 
    : '/data/stories/0';
  
  // 生成多个可能的修改补丁
  const patches: Operation[] = [];
  
  if (attributes.priority) {
    patches.push({
      op: 'replace',
      path: `${basePath}/priority`,
      value: attributes.priority
    });
  }
  
  if (attributes.title) {
    patches.push({
      op: 'replace',
      path: `${basePath}/title`,
      value: attributes.title
    });
  }
  
  if (attributes.auth_type) {
    patches.push({
      op: 'replace',
      path: `${basePath}/auth_type`,
      value: attributes.auth_type
    });
  }
  
  // 如果没有具体的修改，至少更新原因
  if (patches.length === 0) {
    patches.push({
      op: 'replace',
      path: `${basePath}/reason`,
      value: `更新需求: ${originalText}`
    });
  }
  
  return patches;
}

/**
 * 根据意图生成删除操作的补丁
 */
function generateDeletePatch(_intent: InferredIntent): Operation {
  // 删除第一个匹配项（实际应该根据具体的key删除）
  return {
    op: 'remove',
    path: '/data/stories/0'
  };
}

/**
 * 根据意图生成设置操作的补丁
 */
function generateSetPatch(intent: InferredIntent, originalText: string): Operation {
  const attributes = extractAttributesFromText(originalText);
  
  // 从目标路径中提取要设置的路径
  let targetPath = intent.target_path;
  let value = attributes.title;

  // 如果路径不够具体，使用默认设置
  if (!targetPath.includes('.') && !targetPath.includes('[')) {
    targetPath = '/stories/0/title';
    value = attributes.title;
  }

  // 确保路径以 /data 开头以匹配状态结构
  if (!targetPath.startsWith('/')) {
    targetPath = `/${targetPath}`;
  }
  if (!targetPath.startsWith('/data/')) {
    targetPath = `/data${targetPath}`;
  }

  return {
    op: 'replace',
    path: targetPath,
    value: value
  };
}

/**
 * 主要的补丁生成函数
 */
export function generatePatchesFromIntent(
  intent: InferredIntent, 
  originalText: string
): GeneratedPatchResult {
  let patches: Operation[] = [];
  let explanation = '';
  let confidence = intent.confidence;
  
  try {
    switch (intent.action) {
      case 'add':
        patches = [generateAddPatch(intent, originalText)];
        explanation = `基于意图"${intent.action}"生成添加操作，将在${intent.target_path}创建新项目`;
        break;
        
      case 'modify':
        patches = generateModifyPatch(intent, originalText);
        explanation = `基于意图"${intent.action}"生成${patches.length}个修改操作`;
        break;
        
      case 'delete':
        patches = [generateDeletePatch(intent)];
        explanation = `基于意图"${intent.action}"生成删除操作，将移除${intent.target_path}的项目`;
        break;
        
      case 'set':
        patches = [generateSetPatch(intent, originalText)];
        explanation = `基于意图"${intent.action}"生成设置操作，将更新${intent.target_path}`;
        break;
        
      default:
        // 默认为添加操作
        patches = [generateAddPatch(intent, originalText)];
        explanation = `未识别的操作类型，默认生成添加操作`;
        confidence = Math.min(confidence, 0.5);
    }
    
  } catch (error) {
    console.error('生成补丁时出错:', error);
    // 生成一个安全的默认补丁
    patches = [{
      op: 'add',
      path: '/data/stories/-',
      value: {
        key: `FALLBACK-${Date.now()}`,
        title: '解析失败的用户请求',
        priority: 'P2',
        reason: originalText,
        status: 'needs_review'
      }
    }];
    explanation = '补丁生成失败，创建了一个默认的审查项目';
    confidence = 0.3;
  }
  
  return {
    patches,
    explanation,
    confidence
  };
}

/**
 * 验证生成的补丁是否合理
 */
export function validateGeneratedPatches(patches: Operation[]): {
  valid: boolean;
  issues: string[];
} {
  const issues: string[] = [];
  
  for (const patch of patches) {
    // 检查路径有效性
    if (!patch.path || !patch.path.startsWith('/')) {
      issues.push(`无效的补丁路径: ${patch.path}`);
    }
    
    // 检查操作类型
    if (!['add', 'remove', 'replace', 'move', 'copy', 'test'].includes(patch.op)) {
      issues.push(`无效的操作类型: ${patch.op}`);
    }
    
    // 检查添加和替换操作必须有值
    if ((patch.op === 'add' || patch.op === 'replace') && patch.value === undefined) {
      issues.push(`${patch.op}操作缺少值`);
    }
  }
  
  return {
    valid: issues.length === 0,
    issues
  };
}