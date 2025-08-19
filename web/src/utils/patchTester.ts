/**
 * 补丁测试工具 - 用于验证生成的补丁是否能正确应用
 */

import { Operation, applyPatch } from 'fast-json-patch';

export interface PatchTestResult {
  success: boolean;
  error?: string;
  resultState?: unknown;
  originalState: unknown;
  patch: Operation;
}

/**
 * 测试单个补丁是否能正确应用
 */
export function testPatch(state: unknown, patch: Operation): PatchTestResult {
  const testState = JSON.parse(JSON.stringify(state));

  // 如果补丁路径缺少 /data 前缀，补上以适配完整状态
  const normalizedPatch = patch.path.startsWith('/data')
    ? patch
    : { ...patch, path: `/data${patch.path}` };

  try {
    console.log('🧪 Testing patch:', normalizedPatch);
    console.log('🧪 Initial state:', JSON.stringify(testState, null, 2));

    const result = applyPatch(testState, [normalizedPatch], false, false);

    console.log('✅ Patch test successful');
    console.log('🧪 Result state:', JSON.stringify(result.newDocument, null, 2));

    return {
      success: true,
      resultState: result.newDocument,
      originalState: state,
      patch: normalizedPatch
    };
  } catch (error) {
    console.error('❌ Patch test failed:', error);
    console.error('❌ Failed patch:', patch);
    console.error('❌ Test state:', JSON.stringify(testState, null, 2));

    return {
      success: false,
      error: error instanceof Error ? error.message : String(error),
      originalState: state,
      patch: normalizedPatch
    };
  }
}

/**
 * 测试多个补丁的顺序应用
 */
export function testPatches(state: unknown, patches: Operation[]): {
  success: boolean;
  results: PatchTestResult[];
  finalState?: unknown;
} {
  let currentState = JSON.parse(JSON.stringify(state));
  const results: PatchTestResult[] = [];

  for (let i = 0; i < patches.length; i++) {
    const result = testPatch(currentState, patches[i]);
    results.push(result);

    if (!result.success) {
      return {
        success: false,
        results
      };
    }

    currentState = result.resultState;
  }

  return {
    success: true,
    results,
    finalState: currentState
  };
}

/**
 * 验证状态结构是否支持给定的补丁路径
 */
export function validatePatchPath(state: unknown, path: string): {
  valid: boolean;
  issue?: string;
  suggestion?: string;
} {
  try {
    const fullPath = path.startsWith('/data') ? path : `/data${path}`;
    const pathParts = fullPath.split('/').filter(part => part !== '');
      let current: unknown = state;

    for (let i = 0; i < pathParts.length; i++) {
      const part = pathParts[i];

      // 处理数组索引
      if (part === '-') {
        // 添加到数组末尾，检查前一个是否是数组
        if (!Array.isArray(current)) {
          return {
            valid: false,
            issue: `Path ${fullPath}: 尝试添加到非数组对象`,
            suggestion: `确保路径 /${pathParts.slice(0, i).join('/')} 指向一个数组`
          };
        }
        break; // - 总是在路径末尾
      } else if (/^\d+$/.test(part)) {
        // 数组索引
        const index = parseInt(part);
        if (!Array.isArray(current)) {
          return {
            valid: false,
            issue: `Path ${fullPath}: 尝试访问非数组的索引 ${index}`,
            suggestion: `确保路径 /${pathParts.slice(0, i).join('/')} 指向一个数组`
          };
        }
        if (index >= current.length) {
          return {
            valid: false,
            issue: `Path ${fullPath}: 索引 ${index} 超出数组长度 ${current.length}`,
            suggestion: `使用有效的索引 (0-${current.length-1}) 或使用 '-' 添加到末尾`
          };
        }
          current = current[index];
      } else {
        // 对象属性
        if (current === null || typeof current !== 'object') {
          return {
            valid: false,
            issue: `Path ${fullPath}: 尝试访问非对象的属性 ${part}`,
            suggestion: `确保路径 /${pathParts.slice(0, i).join('/')} 指向一个对象`
          };
        }

        // 对于中间路径，属性必须存在
        if (i < pathParts.length - 1 && !(part in current)) {
          return {
            valid: false,
            issue: `Path ${fullPath}: 中间路径属性 ${part} 不存在`,
            suggestion: `确保属性 ${part} 存在于状态中`
          };
        }

          current = (current as Record<string, unknown>)[part];
      }
    }

    return { valid: true };
  } catch (error) {
    return {
      valid: false,
      issue: `路径验证异常: ${error}`,
      suggestion: '检查路径格式是否正确'
    };
  }
}

/**
 * 为常见错误提供修复建议
 */
export function suggestPatchFix(state: unknown, patch: Operation, error: string): string[] {
  const suggestions: string[] = [];

  // 检查路径
  const pathValidation = validatePatchPath(state, patch.path);
  if (!pathValidation.valid) {
    suggestions.push(`路径问题: ${pathValidation.issue}`);
    if (pathValidation.suggestion) {
      suggestions.push(`建议: ${pathValidation.suggestion}`);
    }
  }

  // 检查操作类型
  if (patch.op === 'add') {
    if (!('value' in patch)) {
      suggestions.push('ADD操作缺少value属性');
    }

    if (patch.path.endsWith('/-')) {
      const arrayPath = patch.path.substring(0, patch.path.length - 2);
      const arrayValidation = validatePatchPath(state, arrayPath);
      if (!arrayValidation.valid) {
        suggestions.push(`目标数组路径无效: ${arrayPath}`);
      }
    }
  }

  if (patch.op === 'replace') {
    if (!('value' in patch)) {
      suggestions.push('REPLACE操作缺少value属性');
    }
  }

  // 检查常见的结构问题
  if (error.includes('undefined') || error.includes('null')) {
    suggestions.push('目标路径可能指向undefined或null值');
    suggestions.push('检查状态结构是否与补丁路径匹配');
  }

  return suggestions;
}
