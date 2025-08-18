import { useState, useCallback } from 'react';

export interface Command<T> {
  execute: (state: T) => T;
  undo: (state: T) => T;
  description?: string;
}

export interface CommandHistoryState<T> {
  state: T;
  canUndo: boolean;
  canRedo: boolean;
  history: Command<T>[];
  position: number;
}

export function useCommandHistory<T>(
  initialState: T,
  apply: (state: T, patch: any) => T,
  reverse: (state: T, patch: any) => T
) {
  const [state, setState] = useState<T>(initialState);
  const [history, setHistory] = useState<any[]>([]);
  const [position, setPosition] = useState(-1);

  const execute = useCallback((patch: any) => {
    // Apply the patch
    const nextState = apply(state, patch);
    setState(nextState);
    
    // Update history (remove everything after current position)
    const newHistory = history.slice(0, position + 1).concat([patch]);
    setHistory(newHistory);
    setPosition(position + 1);
  }, [state, history, position, apply]);

  const undo = useCallback(() => {
    if (position < 0) return;
    
    const patch = history[position];
    const prevState = reverse(state, patch);
    setState(prevState);
    setPosition(position - 1);
  }, [state, history, position, reverse]);

  const redo = useCallback(() => {
    if (position >= history.length - 1) return;
    
    const patch = history[position + 1];
    const nextState = apply(state, patch);
    setState(nextState);
    setPosition(position + 1);
  }, [state, history, position, apply]);

  const reset = useCallback(() => {
    setState(initialState);
    setHistory([]);
    setPosition(-1);
  }, [initialState]);

  const goto = useCallback((targetPosition: number) => {
    if (targetPosition < -1 || targetPosition >= history.length) return;
    
    let currentState = initialState;
    
    // Replay history up to target position
    for (let i = 0; i <= targetPosition; i++) {
      currentState = apply(currentState, history[i]);
    }
    
    setState(currentState);
    setPosition(targetPosition);
  }, [history, initialState, apply]);

  return {
    state,
    execute,
    undo,
    redo,
    reset,
    goto,
    canUndo: position >= 0,
    canRedo: position < history.length - 1,
    historyLength: history.length,
    position
  };
}

// 更高级的版本，支持命令对象
export function useAdvancedCommandHistory<T>(initialState: T) {
  const [state, setState] = useState<T>(initialState);
  const [history, setHistory] = useState<Command<T>[]>([]);
  const [position, setPosition] = useState(-1);

  const execute = useCallback((command: Command<T>) => {
    // Execute the command
    const nextState = command.execute(state);
    setState(nextState);
    
    // Update history
    const newHistory = history.slice(0, position + 1).concat([command]);
    setHistory(newHistory);
    setPosition(position + 1);
  }, [state, history, position]);

  const undo = useCallback(() => {
    if (position < 0) return;
    
    const command = history[position];
    const prevState = command.undo(state);
    setState(prevState);
    setPosition(position - 1);
  }, [state, history, position]);

  const redo = useCallback(() => {
    if (position >= history.length - 1) return;
    
    const command = history[position + 1];
    const nextState = command.execute(state);
    setState(nextState);
    setPosition(position + 1);
  }, [state, history, position]);

  const getHistoryDescriptions = useCallback(() => {
    return history.map((cmd, idx) => ({
      description: cmd.description || `Command ${idx + 1}`,
      isCurrent: idx === position,
      index: idx
    }));
  }, [history, position]);

  return {
    state,
    execute,
    undo,
    redo,
    canUndo: position >= 0,
    canRedo: position < history.length - 1,
    history: getHistoryDescriptions(),
    goto: (idx: number) => {
      if (idx < -1 || idx >= history.length) return;
      
      let currentState = initialState;
      for (let i = 0; i <= idx; i++) {
        currentState = history[i].execute(currentState);
      }
      setState(currentState);
      setPosition(idx);
    }
  };
}
