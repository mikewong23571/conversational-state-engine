import React from 'react';
import { IntentSummary } from '../hooks/useConfirmationFlow';
import EnhancedImpactAnalysis, { type EnhancedImpactAnalysisData } from './EnhancedImpactAnalysis';

interface IntentConfirmationProps {
  intent: IntentSummary;
  onConfirm: () => void;
  onCancel: () => void;
  loading?: boolean;
  preliminaryImpact?: EnhancedImpactAnalysisData; // 初步影响分析
}

export const IntentConfirmation: React.FC<IntentConfirmationProps> = ({
  intent,
  onConfirm,
  onCancel,
  loading = false,
  preliminaryImpact
}) => {
  const getActionColor = (action: string) => {
    switch (action.toLowerCase()) {
      case 'add': return 'text-green-700 bg-green-50';
      case 'delete': case 'remove': return 'text-red-700 bg-red-50';
      case 'modify': case 'replace': case 'edit': return 'text-blue-700 bg-blue-50';
      case 'move': return 'text-purple-700 bg-purple-50';
      default: return 'text-gray-700 bg-gray-50';
    }
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'text-green-600';
    if (confidence >= 0.6) return 'text-yellow-600';
    return 'text-red-600';
  };

  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      <div className="mb-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-2">确认您的意图</h2>
        <p className="text-sm text-gray-600">
          请确认我们对您请求的理解是否正确。您可以修改或取消。
        </p>
      </div>

      <div className="space-y-4 mb-6">
        {/* 操作类型 */}
        <div className="flex items-center space-x-3">
          <span className="text-sm font-medium text-gray-500 w-20">操作:</span>
          <span className={`px-3 py-1 rounded-full text-sm font-medium ${getActionColor(intent.action)}`}>
            {intent.action.toUpperCase()}
          </span>
        </div>

        {/* 目标路径 */}
        <div className="flex items-start space-x-3">
          <span className="text-sm font-medium text-gray-500 w-20 mt-1">目标:</span>
          <span className="text-sm font-mono text-gray-700 bg-gray-50 px-2 py-1 rounded">
            {intent.target_path}
          </span>
        </div>

        {/* 值 */}
        {intent.value !== undefined && (
          <div className="flex items-start space-x-3">
            <span className="text-sm font-medium text-gray-500 w-20 mt-1">值:</span>
            <div className="flex-1">
              <pre className="text-sm text-gray-700 bg-gray-50 p-3 rounded max-h-32 overflow-y-auto">
                {typeof intent.value === 'object'
                  ? JSON.stringify(intent.value, null, 2)
                  : String(intent.value)}
              </pre>
            </div>
          </div>
        )}

        {/* 原因 */}
        <div className="flex items-start space-x-3">
          <span className="text-sm font-medium text-gray-500 w-20 mt-1">原因:</span>
          <span className="text-sm text-gray-700 flex-1">
            {intent.reason}
          </span>
        </div>

        {/* 置信度 */}
        <div className="flex items-center space-x-3">
          <span className="text-sm font-medium text-gray-500 w-20">置信度:</span>
          <span className={`text-sm font-medium ${getConfidenceColor(intent.confidence)}`}>
            {Math.round(intent.confidence * 100)}%
          </span>
          <div className="flex-1 bg-gray-200 rounded-full h-2">
            <div
              className={`h-2 rounded-full transition-all duration-300 ${
                intent.confidence >= 0.8 ? 'bg-green-500' :
                intent.confidence >= 0.6 ? 'bg-yellow-500' : 'bg-red-500'
              }`}
              style={{ width: `${intent.confidence * 100}%` }}
            />
          </div>
        </div>
      </div>

      {/* 提示信息 */}
        {intent.confidence < 0.8 ? (
          <div className="mb-6 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
            <div className="flex items-start">
              <div className="text-yellow-600 text-sm">
                ⚠️ 置信度较低，建议仔细核对意图理解是否正确。
              </div>
            </div>
          </div>
        ) : null}

      {/* 初步影响分析 */}
        {preliminaryImpact ? (
          <div className="mb-6">
            <h3 className="text-lg font-medium text-gray-900 mb-3">初步影响分析</h3>
            <EnhancedImpactAnalysis impact={preliminaryImpact} />
          </div>
        ) : null}

      {/* 操作按钮 */}
      <div className="flex justify-between items-center pt-4 border-t border-gray-200">
        <button
          onClick={onCancel}
          disabled={loading}
          className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50"
        >
          取消
        </button>

        <div className="flex space-x-3">
          <button
            onClick={onCancel}
            disabled={loading}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50"
          >
            修改意图
          </button>
          <button
            onClick={onConfirm}
            disabled={loading}
            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? '处理中...' : '确认意图'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default IntentConfirmation;
