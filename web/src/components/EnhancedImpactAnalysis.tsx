import React, { useState } from 'react';

interface EnhancedConflict {
  type: string;
  rule: string;
  severity: 'low' | 'medium' | 'high';
  message: string;
  suggestion?: {
    description: string;
    auto_fix: boolean;
    patches?: any[];
  };
  affected_paths: string[];
  examples?: string[];
}

interface EnhancedImpactAnalysis {
  affected_paths: string[];
  risk_level: 'low' | 'medium' | 'high';
  semantic_conflicts: EnhancedConflict[];
  suggested_alternatives?: any[];
  risk_explanation?: string;
  dependency_analysis?: {
    breaking_changes: string[];
    cascading_effects: string[];
    validation_warnings: string[];
  };
}

interface EnhancedImpactAnalysisProps {
  impact: EnhancedImpactAnalysis;
  onApplySuggestion?: (conflictIndex: number) => void;
}

export const EnhancedImpactAnalysis: React.FC<EnhancedImpactAnalysisProps> = ({
  impact,
  onApplySuggestion
}) => {
  const [expandedConflict, setExpandedConflict] = useState<number | null>(null);
  const [showDependencies, setShowDependencies] = useState(false);

  const getRiskLevelDetails = (level: 'low' | 'medium' | 'high') => {
    switch (level) {
      case 'high':
        return {
          color: 'text-red-600 bg-red-50 border-red-200',
          icon: '🚨',
          description: '高风险：可能导致系统功能异常或数据不一致'
        };
      case 'medium':
        return {
          color: 'text-yellow-600 bg-yellow-50 border-yellow-200',
          icon: '⚠️',
          description: '中等风险：需要注意，可能影响部分功能'
        };
      case 'low':
        return {
          color: 'text-blue-600 bg-blue-50 border-blue-200',
          icon: 'ℹ️',
          description: '低风险：影响较小，建议评估后执行'
        };
    }
  };

  const getSeverityBadge = (severity: 'low' | 'medium' | 'high') => {
    const colors = {
      high: 'bg-red-100 text-red-800',
      medium: 'bg-yellow-100 text-yellow-800',
      low: 'bg-blue-100 text-blue-800'
    };
    return `px-2 py-1 text-xs font-medium rounded-full ${colors[severity]}`;
  };

  const riskDetails = getRiskLevelDetails(impact.risk_level);

  return (
    <div className="space-y-6">
      {/* 风险等级总览 */}
      <div className={`p-4 rounded-lg border ${riskDetails.color}`}>
        <div className="flex items-start space-x-3">
          <span className="text-xl">{riskDetails.icon}</span>
          <div className="flex-1">
            <div className="text-sm font-medium mb-1">
              风险等级: {impact.risk_level.toUpperCase()}
            </div>
            <div className="text-sm">
              {impact.risk_explanation || riskDetails.description}
            </div>
            {impact.affected_paths.length > 0 && (
              <div className="mt-2">
                <div className="text-xs font-medium text-gray-600 mb-1">
                  受影响的路径 ({impact.affected_paths.length}):
                </div>
                <div className="flex flex-wrap gap-1">
                  {impact.affected_paths.slice(0, 3).map((path, index) => (
                    <span key={index} className="text-xs bg-white px-2 py-1 rounded font-mono">
                      {path}
                    </span>
                  ))}
                  {impact.affected_paths.length > 3 && (
                    <span className="text-xs text-gray-500">
                      +{impact.affected_paths.length - 3} more...
                    </span>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 语义冲突详情 */}
      {impact.semantic_conflicts.length > 0 && (
        <div className="space-y-4">
          <h3 className="text-lg font-medium text-gray-900">
            检测到的冲突 ({impact.semantic_conflicts.length})
          </h3>
          
          {impact.semantic_conflicts.map((conflict, index) => (
            <div key={index} className="border border-gray-200 rounded-lg overflow-hidden">
              <div 
                className="p-4 bg-gray-50 cursor-pointer hover:bg-gray-100"
                onClick={() => setExpandedConflict(expandedConflict === index ? null : index)}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <span className={getSeverityBadge(conflict.severity)}>
                      {conflict.severity.toUpperCase()}
                    </span>
                    <span className="font-medium text-gray-900">
                      {conflict.rule}
                    </span>
                  </div>
                  <div className="flex items-center space-x-2">
                    {conflict.suggestion?.auto_fix && (
                      <span className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded">
                        AUTO-FIX
                      </span>
                    )}
                    <span className="text-gray-400">
                      {expandedConflict === index ? '▼' : '▶'}
                    </span>
                  </div>
                </div>
                <div className="mt-1 text-sm text-gray-600">
                  {conflict.message}
                </div>
              </div>

              {expandedConflict === index && (
                <div className="p-4 bg-white border-t border-gray-200">
                  {/* 受影响路径 */}
                  {conflict.affected_paths.length > 0 && (
                    <div className="mb-4">
                      <div className="text-sm font-medium text-gray-700 mb-2">
                        受影响的路径:
                      </div>
                      <div className="space-y-1">
                        {conflict.affected_paths.map((path, pathIndex) => (
                          <div key={pathIndex} className="text-xs font-mono bg-gray-100 px-2 py-1 rounded">
                            {path}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* 示例 */}
                  {conflict.examples && conflict.examples.length > 0 && (
                    <div className="mb-4">
                      <div className="text-sm font-medium text-gray-700 mb-2">
                        示例场景:
                      </div>
                      <div className="space-y-1">
                        {conflict.examples.map((example, exampleIndex) => (
                          <div key={exampleIndex} className="text-sm text-gray-600 italic">
                            • {example}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* 建议修复 */}
                  {conflict.suggestion && (
                    <div className="p-3 bg-blue-50 rounded-lg">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="text-sm font-medium text-blue-900 mb-1">
                            💡 建议修复
                          </div>
                          <div className="text-sm text-blue-800">
                            {conflict.suggestion.description}
                          </div>
                          {conflict.suggestion.patches && (
                            <div className="mt-2 text-xs text-blue-700">
                              将应用 {conflict.suggestion.patches.length} 个补丁修复此问题
                            </div>
                          )}
                        </div>
                        {onApplySuggestion && conflict.suggestion.auto_fix && (
                          <button
                            onClick={() => onApplySuggestion(index)}
                            className="ml-3 px-3 py-1 text-xs font-medium text-white bg-blue-600 rounded hover:bg-blue-700"
                          >
                            应用修复
                          </button>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* 依赖分析 */}
      {impact.dependency_analysis && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-medium text-gray-900">依赖影响分析</h3>
            <button
              onClick={() => setShowDependencies(!showDependencies)}
              className="text-sm text-blue-600 hover:text-blue-800"
            >
              {showDependencies ? '隐藏详情' : '显示详情'}
            </button>
          </div>

          {showDependencies && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* 破坏性变更 */}
              {impact.dependency_analysis.breaking_changes.length > 0 && (
                <div className="p-3 bg-red-50 rounded-lg border border-red-200">
                  <div className="text-sm font-medium text-red-900 mb-2">
                    ⚠️ 破坏性变更
                  </div>
                  <div className="space-y-1">
                    {impact.dependency_analysis.breaking_changes.map((change, index) => (
                      <div key={index} className="text-xs text-red-700">
                        • {change}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* 级联效应 */}
              {impact.dependency_analysis.cascading_effects.length > 0 && (
                <div className="p-3 bg-yellow-50 rounded-lg border border-yellow-200">
                  <div className="text-sm font-medium text-yellow-900 mb-2">
                    🔄 级联效应
                  </div>
                  <div className="space-y-1">
                    {impact.dependency_analysis.cascading_effects.map((effect, index) => (
                      <div key={index} className="text-xs text-yellow-700">
                        • {effect}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* 验证警告 */}
              {impact.dependency_analysis.validation_warnings.length > 0 && (
                <div className="p-3 bg-blue-50 rounded-lg border border-blue-200">
                  <div className="text-sm font-medium text-blue-900 mb-2">
                    ℹ️ 验证警告
                  </div>
                  <div className="space-y-1">
                    {impact.dependency_analysis.validation_warnings.map((warning, index) => (
                      <div key={index} className="text-xs text-blue-700">
                        • {warning}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* 替代方案 */}
      {impact.suggested_alternatives && impact.suggested_alternatives.length > 0 && (
        <div className="space-y-4">
          <h3 className="text-lg font-medium text-gray-900">建议的替代方案</h3>
          <div className="space-y-3">
            {impact.suggested_alternatives.map((alternative, index) => (
              <div key={index} className="p-3 bg-green-50 rounded-lg border border-green-200">
                <div className="text-sm font-medium text-green-900">
                  💡 方案 {index + 1}
                </div>
                <div className="text-sm text-green-800 mt-1">
                  {typeof alternative === 'string' ? alternative : JSON.stringify(alternative)}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 无冲突状态 */}
      {impact.semantic_conflicts.length === 0 && (
        <div className="p-4 bg-green-50 rounded-lg border border-green-200">
          <div className="flex items-center space-x-2 text-green-700">
            <span className="text-lg">✅</span>
            <span className="text-sm font-medium">
              未检测到语义冲突，变更可以安全执行
            </span>
          </div>
        </div>
      )}
    </div>
  );
};

export default EnhancedImpactAnalysis;