import React, { useState, useRef, useEffect } from 'react';
import { parseUserInput, CommandResult, getCommandHelp } from '../utils/commandParser';

interface CommandInputProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: (value: string) => void;
  loading?: boolean;
  placeholder?: string;
}

export const CommandInput: React.FC<CommandInputProps> = ({
  value,
  onChange,
  onSubmit,
  loading = false,
  placeholder = "Enter your intent or use commands like /add, /edit, /del..."
}) => {
  const [showHelp, setShowHelp] = useState(false);
  const [parseResult, setParseResult] = useState<CommandResult | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // 解析输入内容
  useEffect(() => {
    if (value.trim()) {
      const result = parseUserInput(value);
      setParseResult(result);
    } else {
      setParseResult(null);
    }
  }, [value]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (value.trim() && !loading) {
      onSubmit(value);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    // Ctrl+Enter 或 Cmd+Enter 提交
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault();
      handleSubmit(e);
    }

    // 显示/隐藏帮助
    if (e.key === 'F1' || (e.ctrlKey && e.key === '/')) {
      e.preventDefault();
      setShowHelp(!showHelp);
    }
  };

  const insertCommand = (command: string) => {
    onChange(command);
    textareaRef.current?.focus();
  };

  const getInputStyle = () => {
    if (!parseResult) return '';

    if (parseResult.type === 'command') {
      return 'border-blue-300 bg-blue-50';
    } else {
      return 'border-gray-300 bg-white';
    }
  };

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-lg font-semibold">Enter your intent</h2>
        <div className="flex items-center space-x-2">
          <button
            type="button"
            onClick={() => setShowHelp(!showHelp)}
            className="text-sm text-blue-600 hover:text-blue-800"
            title="Show command help (F1)"
          >
            {showHelp ? 'Hide Help' : 'Show Help'}
          </button>
          <span className="text-xs text-gray-500">Ctrl+Enter to submit</span>
        </div>
      </div>

      {/* 解析结果指示器 */}
      {parseResult && (
        <div className="mb-3">
          {parseResult.type === 'command' ? (
            <div className="flex items-center space-x-2 text-sm">
              <span className="px-2 py-1 bg-blue-100 text-blue-700 rounded text-xs font-medium">
                COMMAND
              </span>
              <span className="text-gray-600">
                {parseResult.command?.action.toUpperCase()} → {parseResult.command?.target}
              </span>
            </div>
          ) : (
            <div className="flex items-center space-x-2 text-sm">
              <span className="px-2 py-1 bg-gray-100 text-gray-700 rounded text-xs font-medium">
                NATURAL LANGUAGE
              </span>
              <span className="text-gray-600">Will be processed by AI</span>
            </div>
          )}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="relative">
          <textarea
            ref={textareaRef}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            className={`w-full p-3 border rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none transition-colors ${getInputStyle()}`}
            rows={4}
            disabled={loading}
          />
        </div>

        {/* 快速命令按钮 */}
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => insertCommand('/add story key= priority=P0 title="" reason=""')}
            className="text-xs px-2 py-1 bg-green-100 text-green-700 rounded hover:bg-green-200"
          >
            /add story
          </button>
          <button
            type="button"
            onClick={() => insertCommand('/edit story key= set priority=')}
            className="text-xs px-2 py-1 bg-blue-100 text-blue-700 rounded hover:bg-blue-200"
          >
            /edit story
          </button>
          <button
            type="button"
            onClick={() => insertCommand('/del story key=')}
            className="text-xs px-2 py-1 bg-red-100 text-red-700 rounded hover:bg-red-200"
          >
            /del story
          </button>
          <button
            type="button"
            onClick={() => insertCommand('/set stories[key=].auth_type=')}
            className="text-xs px-2 py-1 bg-purple-100 text-purple-700 rounded hover:bg-purple-200"
          >
            /set path
          </button>
        </div>

        <div className="flex justify-between items-center">
          <div className="text-sm text-gray-500">
            {parseResult?.type === 'command'
              ? `Structured command (confidence: ${parseResult.command?.confidence || 1})`
              : 'Natural language input'
            }
          </div>
          <button
            type="submit"
            disabled={!value.trim() || loading}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400"
          >
            {loading ? 'Processing...' : 'Submit'}
          </button>
        </div>
      </form>

      {/* 帮助面板 */}
      {showHelp && (
        <div className="mt-4 p-4 bg-gray-50 rounded-lg border">
          <h3 className="font-medium text-gray-900 mb-2">Command Help</h3>
          <pre className="text-xs text-gray-700 whitespace-pre-wrap font-mono">
            {getCommandHelp()}
          </pre>

          <div className="mt-3 text-xs text-gray-600">
            <p><strong>Tips:</strong></p>
            <ul className="ml-4 mt-1 space-y-1">
              <li>• Commands are processed with 100% confidence</li>
              <li>• Natural language is processed by AI with variable confidence</li>
              <li>• Use Ctrl+Enter to submit quickly</li>
              <li>• Press F1 or Ctrl+/ to toggle help</li>
            </ul>
          </div>
        </div>
      )}
    </div>
  );
};

export default CommandInput;
