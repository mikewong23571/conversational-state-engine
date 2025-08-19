import React from 'react';
import { SideEffectAnalysis as SideEffectData } from '../hooks/useConfirmationFlow';

interface SideEffectAnalysisProps {
  sideEffects: SideEffectData;
  onToggleAutoFix: (index: number) => void;
  onConfirm: () => void;
  onGoBack: () => void;
  loading?: boolean;
}

export const SideEffectAnalysis: React.FC<SideEffectAnalysisProps> = ({
  sideEffects,
  onToggleAutoFix,
  onConfirm,
  onGoBack,
  loading = false
}) => {
  const getSeverityColor = (severity: 'low' | 'medium' | 'high') => {
    switch (severity) {
      case 'high': return 'text-red-700 bg-red-50 border-red-200';
      case 'medium': return 'text-yellow-700 bg-yellow-50 border-yellow-200';
      case 'low': return 'text-blue-700 bg-blue-50 border-blue-200';
    }
  };

  const getSeverityIcon = (severity: 'low' | 'medium' | 'high') => {
    switch (severity) {
      case 'high': return '🚨';
      case 'medium': return '⚠️';
      case 'low': return 'ℹ️';
    }
  };

  const hasHighRiskWarnings = sideEffects.warnings.some(w => w.severity === 'high');
  const enabledAutoFixes = sideEffects.auto_fixes.filter(fix => fix.enabled);

  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      <div className="mb-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-2">副作用分析</h2>
        <p className="text-sm text-gray-600">
          检查您的变更可能产生的副作用和风险。您可以选择应用建议的自动修复。
        </p>
      </div>

      {/* 警告信息 */}
      {sideEffects.warnings.length > 0 && (
        <div className="mb-6">
          <h3 className="text-lg font-medium text-gray-900 mb-3">
            ⚠️ 检测到的风险 ({sideEffects.warnings.length})
          </h3>
          <div className="space-y-3">
            {sideEffects.warnings.map((warning, index) => (
              <div 
                key={index}
                className={`p-4 rounded-lg border ${getSeverityColor(warning.severity)}`}
              >
                <div className="flex items-start space-x-2">
                  <span className="text-lg">{getSeverityIcon(warning.severity)}</span>
                  <div className="flex-1">
                    <div className="text-sm font-medium mb-1">
                      {warning.type}
                    </div>
                    <div className="text-sm">
                      {warning.message}
                    </div>
                  </div>
                  <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                    warning.severity === 'high' ? 'bg-red-100 text-red-800' :
                    warning.severity === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                    'bg-blue-100 text-blue-800'
                  }`}>
                    {warning.severity.toUpperCase()}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 自动修复建议 */}
      {sideEffects.auto_fixes.length > 0 && (
        <div className="mb-6">
          <h3 className="text-lg font-medium text-gray-900 mb-3">
            🔧 建议的自动修复 ({sideEffects.auto_fixes.length})
          </h3>
          <div className="space-y-3">
            {sideEffects.auto_fixes.map((fix, index) => (
              <label 
                key={index}
                className="flex items-start p-4 bg-gray-50 rounded-lg border border-gray-200 hover:bg-gray-100 cursor-pointer"
              >
                <input
                  type="checkbox"
                  checked={fix.enabled}
                  onChange={() => onToggleAutoFix(index)}
                  className="mt-1 mr-3 text-blue-600"
                />
                <div className="flex-1">
                  <div className="text-sm font-medium text-gray-900 mb-1">
                    {fix.description}
                  </div>
                  <div className="text-xs text-gray-600">
                    将应用 {fix.patches.length} 个补丁
                  </div>
                  <details className="mt-2">
                    <summary className="text-xs text-blue-600 cursor-pointer hover:text-blue-800">
                      查看补丁详情
                    </summary>
                    <div className="mt-2 p-2 bg-white rounded border text-xs font-mono">
                      <pre>{JSON.stringify(fix.patches, null, 2)}</pre>
                    </div>
                  </details>
                </div>
              </label>
            ))}
          </div>
          
          {enabledAutoFixes.length > 0 && (
            <div className="mt-3 p-3 bg-green-50 border border-green-200 rounded-lg">
              <div className="text-sm text-green-700">
                ✅ 已选择 {enabledAutoFixes.length} 个自动修复，
                将额外应用 {enabledAutoFixes.reduce((sum, fix) => sum + fix.patches.length, 0)} 个补丁
              </div>
            </div>
          )}
        </div>
      )}

      {/* 无副作用的情况 */}
      {sideEffects.warnings.length === 0 && sideEffects.auto_fixes.length === 0 && (
        <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded-lg">
          <div className="flex items-center space-x-2 text-green-700">
            <span className="text-lg">✅</span>
            <span className="text-sm font-medium">
              未检测到副作用或风险，您的变更可以安全执行。
            </span>
          </div>
        </div>
      )}

      {/* 高风险警告 */}
      {hasHighRiskWarnings && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
          <div className="flex items-start space-x-2">
            <span className="text-lg">🚨</span>
            <div className="text-sm text-red-700">
              <div className="font-medium mb-1">检测到高风险操作</div>
              <div>
                请仔细检查上述警告，确认您了解变更的影响后再继续。
                建议在生产环境中谨慎执行此操作。
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 操作按钮 */}
      <div className="flex justify-between items-center pt-4 border-t border-gray-200">
        <button
          onClick={onGoBack}
          disabled={loading}
          className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50"
        >
          返回修改
        </button>
        
        <button
          onClick={onConfirm}
          disabled={loading}
          className={`px-4 py-2 text-sm font-medium rounded-md disabled:opacity-50 ${
            hasHighRiskWarnings 
              ? 'text-white bg-red-600 hover:bg-red-700' 
              : 'text-white bg-green-600 hover:bg-green-700'
          }`}
        >
          {loading ? '执行中...' : hasHighRiskWarnings ? '确认执行高风险操作' : '确认并执行'}
        </button>
      </div>
    </div>
  );
};

export default SideEffectAnalysis;