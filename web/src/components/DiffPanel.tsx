import React, { useMemo, useState, useCallback } from 'react';
import { applyPatch } from 'fast-json-patch';

interface Patch {
  op: 'add' | 'remove' | 'replace' | 'move' | 'copy' | 'test';
  path: string;
  value?: any;
  from?: string;
}

interface Conflict {
  type: string;
  rule: string;
  severity: 'low' | 'medium' | 'high';
  message: string;
  suggestion?: any;
}

interface ImpactAnalysis {
  affected_paths: string[];
  risk_level: 'low' | 'medium' | 'high';
  semantic_conflicts: Conflict[];
  suggested_alternatives?: any[];
}

interface DiffPanelProps {
  currentState: any;
  proposedPatches: Patch[];
  impact: ImpactAnalysis;
  onConfirm: (selectedIndices: number[]) => void;
  onReject: () => void;
}

export const DiffPanel: React.FC<DiffPanelProps> = ({
  currentState,
  proposedPatches,
  impact,
  onConfirm,
  onReject
}) => {
  const [selected, setSelected] = useState<boolean[]>(
    proposedPatches.map(() => true)
  );
  
  const [viewMode, setViewMode] = useState<'list' | 'json' | 'side-by-side'>('list');

  // 计算预览状态
  const previewState = useMemo(() => {
    try {
      let nextState = JSON.parse(JSON.stringify(currentState));
      
      proposedPatches.forEach((patch, idx) => {
        if (selected[idx]) {
          nextState = applyPatch(nextState, [patch], false, false).newDocument;
        }
      });
      
      return nextState;
    } catch (error) {
      console.error('Failed to apply patches:', error);
      return currentState;
    }
  }, [currentState, proposedPatches, selected]);

  // 按操作类型分组patches
  const groupedPatches = useMemo(() => {
    const groups: Record<string, Array<{patch: Patch, index: number}>> = {
      add: [],
      modify: [],
      delete: [],
      other: []
    };
    
    proposedPatches.forEach((patch, index) => {
      const group = patch.op === 'add' ? 'add' :
                   patch.op === 'replace' ? 'modify' :
                   patch.op === 'remove' ? 'delete' : 'other';
      groups[group].push({ patch, index });
    });
    
    return groups;
  }, [proposedPatches]);

  const toggleSelection = useCallback((index: number) => {
    const newSelected = [...selected];
    newSelected[index] = !newSelected[index];
    setSelected(newSelected);
  }, [selected]);

  const selectAll = useCallback(() => {
    setSelected(proposedPatches.map(() => true));
  }, [proposedPatches]);

  const selectNone = useCallback(() => {
    setSelected(proposedPatches.map(() => false));
  }, [proposedPatches]);

  const handleConfirm = useCallback(() => {
    const selectedIndices = selected
      .map((isSelected, idx) => isSelected ? idx : -1)
      .filter(idx => idx >= 0);
    onConfirm(selectedIndices);
  }, [selected, onConfirm]);

  const getRiskColor = (level: string) => {
    switch (level) {
      case 'high': return 'text-red-600 bg-red-50';
      case 'medium': return 'text-yellow-600 bg-yellow-50';
      case 'low': return 'text-green-600 bg-green-50';
      default: return 'text-gray-600 bg-gray-50';
    }
  };

  const getOpColor = (op: string) => {
    switch (op) {
      case 'add': return 'text-green-700';
      case 'remove': return 'text-red-700';
      case 'replace': return 'text-blue-700';
      case 'move': return 'text-purple-700';
      default: return 'text-gray-700';
    }
  };

  return (
    <div className="flex flex-col h-full bg-white rounded-lg shadow-lg">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold text-gray-900">变更预览</h2>
          <div className="flex items-center space-x-2">
            <span className={`px-3 py-1 rounded-full text-sm font-medium ${getRiskColor(impact.risk_level)}`}>
              风险: {impact.risk_level.toUpperCase()}
            </span>
            <div className="flex space-x-2">
              <button
                onClick={() => setViewMode('list')}
                className={`px-3 py-1 text-sm rounded ${viewMode === 'list' ? 'bg-blue-100 text-blue-700' : 'text-gray-600'}`}
              >
                列表
              </button>
              <button
                onClick={() => setViewMode('json')}
                className={`px-3 py-1 text-sm rounded ${viewMode === 'json' ? 'bg-blue-100 text-blue-700' : 'text-gray-600'}`}
              >
                JSON
              </button>
              <button
                onClick={() => setViewMode('side-by-side')}
                className={`px-3 py-1 text-sm rounded ${viewMode === 'side-by-side' ? 'bg-blue-100 text-blue-700' : 'text-gray-600'}`}
              >
                对比
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="flex-1 flex overflow-hidden">
        {/* Left Panel - Patches List */}
        <div className="w-1/3 border-r border-gray-200 overflow-y-auto">
          <div className="p-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-medium text-gray-900">变更列表</h3>
              <div className="flex space-x-2">
                <button
                  onClick={selectAll}
                  className="text-xs text-blue-600 hover:text-blue-800"
                >
                  全选
                </button>
                <button
                  onClick={selectNone}
                  className="text-xs text-blue-600 hover:text-blue-800"
                >
                  清空
                </button>
              </div>
            </div>

            {/* Grouped patches */}
            {Object.entries(groupedPatches).map(([group, items]) => {
              if (items.length === 0) return null;
              
              return (
                <div key={group} className="mb-4">
                  <h4 className="text-sm font-medium text-gray-600 mb-2 capitalize">
                    {group === 'add' ? '新增' : 
                     group === 'modify' ? '修改' : 
                     group === 'delete' ? '删除' : '其他'} ({items.length})
                  </h4>
                  <div className="space-y-2">
                    {items.map(({ patch, index }) => (
                      <label
                        key={index}
                        className="flex items-start p-2 rounded hover:bg-gray-50 cursor-pointer"
                      >
                        <input
                          type="checkbox"
                          checked={selected[index]}
                          onChange={() => toggleSelection(index)}
                          className="mt-1 mr-3"
                        />
                        <div className="flex-1">
                          <div className="flex items-center">
                            <span className={`text-xs font-mono ${getOpColor(patch.op)}`}>
                              {patch.op.toUpperCase()}
                            </span>
                            <span className="ml-2 text-sm text-gray-700 font-mono">
                              {patch.path}
                            </span>
                          </div>
                          {patch.value && (
                            <div className="mt-1 text-xs text-gray-500 truncate">
                              {typeof patch.value === 'object' 
                                ? JSON.stringify(patch.value).substring(0, 50) + '...'
                                : String(patch.value)}
                            </div>
                          )}
                        </div>
                      </label>
                    ))}
                  </div>
                </div>
              );
            })}

            {/* Conflicts */}
            {impact.semantic_conflicts.length > 0 && (
              <div className="mt-6">
                <h4 className="text-sm font-medium text-gray-600 mb-2">
                  检测到的问题 ({impact.semantic_conflicts.length})
                </h4>
                <div className="space-y-2">
                  {impact.semantic_conflicts.map((conflict, idx) => (
                    <div
                      key={idx}
                      className={`p-3 rounded-lg ${
                        conflict.severity === 'high' ? 'bg-red-50 border border-red-200' :
                        conflict.severity === 'medium' ? 'bg-yellow-50 border border-yellow-200' :
                        'bg-blue-50 border border-blue-200'
                      }`}
                    >
                      <div className="flex items-start">
                        <span className={`text-xs font-medium ${
                          conflict.severity === 'high' ? 'text-red-700' :
                          conflict.severity === 'medium' ? 'text-yellow-700' :
                          'text-blue-700'
                        }`}>
                          {conflict.rule}
                        </span>
                      </div>
                      <p className="mt-1 text-sm text-gray-700">{conflict.message}</p>
                      {conflict.suggestion && (
                        <div className="mt-2 text-xs text-gray-600">
                          建议: {JSON.stringify(conflict.suggestion)}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Right Panel - Preview */}
        <div className="flex-1 overflow-y-auto">
          {viewMode === 'list' && (
            <div className="p-6">
              <h3 className="font-medium text-gray-900 mb-4">预览结果</h3>
              <div className="space-y-4">
                {/* 显示主要变更内容 */}
                <div className="bg-gray-50 rounded-lg p-4">
                  <pre className="text-sm text-gray-700 whitespace-pre-wrap">
                    {JSON.stringify(previewState, null, 2)}
                  </pre>
                </div>
              </div>
            </div>
          )}

          {viewMode === 'json' && (
            <div className="p-6">
              <h3 className="font-medium text-gray-900 mb-4">JSON Diff</h3>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <h4 className="text-sm font-medium text-gray-600 mb-2">当前状态</h4>
                  <div className="bg-gray-50 rounded-lg p-4 h-96 overflow-y-auto">
                    <pre className="text-xs text-gray-700">
                      {JSON.stringify(currentState, null, 2)}
                    </pre>
                  </div>
                </div>
                <div>
                  <h4 className="text-sm font-medium text-gray-600 mb-2">预览状态</h4>
                  <div className="bg-blue-50 rounded-lg p-4 h-96 overflow-y-auto">
                    <pre className="text-xs text-gray-700">
                      {JSON.stringify(previewState, null, 2)}
                    </pre>
                  </div>
                </div>
              </div>
            </div>
          )}

          {viewMode === 'side-by-side' && (
            <div className="p-6">
              <h3 className="font-medium text-gray-900 mb-4">并排对比</h3>
              <div className="bg-yellow-50 rounded-lg p-4">
                <p className="text-sm text-yellow-700">
                  完整的并排对比视图需要集成专门的diff库（如react-diff-viewer）
                </p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Footer */}
      <div className="px-6 py-4 border-t border-gray-200 bg-gray-50">
        <div className="flex items-center justify-between">
          <div className="text-sm text-gray-600">
            已选择 {selected.filter(s => s).length} / {proposedPatches.length} 项变更
          </div>
          <div className="flex space-x-3">
            <button
              onClick={onReject}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
            >
              取消
            </button>
            <button
              onClick={handleConfirm}
              disabled={!selected.some(s => s)}
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
            >
              确认所选变更
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DiffPanel;
