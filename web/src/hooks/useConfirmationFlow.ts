import { useState, useCallback } from 'react';
import { Operation } from 'fast-json-patch';

export type ConfirmationStage = 'intent' | 'change' | 'side_effect' | 'completed';

export interface IntentSummary {
  action: string;
  target_path: string;
  value?: unknown;
  reason: string;
  confidence: number;
}

export interface ChangePreview {
  patches: Operation[];
  selectedIndices: number[];
  impact: {
    affected_paths: string[];
    risk_level: 'low' | 'medium' | 'high';
    semantic_conflicts: Array<{
      type: string;
      rule: string;
      severity: 'low' | 'medium' | 'high';
      message: string;
      suggestion?: unknown;
    }>;
    suggested_alternatives?: unknown[];
  };
}

export interface SideEffectAnalysis {
  warnings: Array<{
    type: string;
    message: string;
    severity: 'low' | 'medium' | 'high';
  }>;
  auto_fixes: Array<{
    description: string;
    patches: Operation[];
    enabled: boolean;
  }>;
}

export interface ConfirmationState {
  stage: ConfirmationStage;
  intent?: IntentSummary;
  changes?: ChangePreview;
  sideEffects?: SideEffectAnalysis;
  canProceed: boolean;
  canGoBack: boolean;
}

export function useConfirmationFlow() {
  const [state, setState] = useState<ConfirmationState>({
    stage: 'intent',
    canProceed: false,
    canGoBack: false
  });

  const startIntentConfirmation = useCallback((intent: IntentSummary) => {
    setState({
      stage: 'intent',
      intent,
      canProceed: true,
      canGoBack: false
    });
  }, []);

  const confirmIntent = useCallback(() => {
    if (state.stage !== 'intent') return;

    setState(prev => ({
      ...prev,
      stage: 'change',
      canProceed: false, // Will be set when patches are loaded
      canGoBack: true
    }));
  }, [state.stage]);

  const setChangePreview = useCallback((changes: ChangePreview) => {
    setState(prev => ({
      ...prev,
      changes,
      canProceed: changes.selectedIndices.length > 0,
      canGoBack: true
    }));
  }, []);

  const confirmChanges = useCallback(() => {
    if (state.stage !== 'change') return;

    setState(prev => ({
      ...prev,
      stage: 'side_effect',
      canProceed: false, // Will be set when side effects are analyzed
      canGoBack: true
    }));
  }, [state.stage]);

  const setSideEffectAnalysis = useCallback((sideEffects: SideEffectAnalysis) => {
    setState(prev => ({
      ...prev,
      sideEffects,
      canProceed: true,
      canGoBack: true
    }));
  }, []);

  const confirmSideEffects = useCallback(() => {
    if (state.stage !== 'side_effect') return;

    setState(prev => ({
      ...prev,
      stage: 'completed',
      canProceed: false,
      canGoBack: false
    }));
  }, [state.stage]);

  const goBack = useCallback(() => {
    if (!state.canGoBack) return;

    setState(prev => {
      switch (prev.stage) {
        case 'change':
          return {
            ...prev,
            stage: 'intent',
            canProceed: true,
            canGoBack: false
          };
        case 'side_effect':
          return {
            ...prev,
            stage: 'change',
            canProceed: (prev.changes?.selectedIndices.length ?? 0) > 0,
            canGoBack: true
          };
        default:
          return prev;
      }
    });
  }, [state.canGoBack]);

  const cancel = useCallback(() => {
    setState({
      stage: 'intent',
      canProceed: false,
      canGoBack: false
    });
  }, []);

  const updateSelectedPatches = useCallback((selectedIndices: number[]) => {
    setState(prev => ({
      ...prev,
      changes: prev.changes ? {
        ...prev.changes,
        selectedIndices
      } : undefined,
      canProceed: selectedIndices.length > 0
    }));
  }, []);

  const toggleAutoFix = useCallback((index: number) => {
    setState(prev => ({
      ...prev,
      sideEffects: prev.sideEffects ? {
        ...prev.sideEffects,
        auto_fixes: prev.sideEffects.auto_fixes.map((fix, i) =>
          i === index ? { ...fix, enabled: !fix.enabled } : fix
        )
      } : undefined
    }));
  }, []);

  return {
    state,
    actions: {
      startIntentConfirmation,
      confirmIntent,
      setChangePreview,
      confirmChanges,
      setSideEffectAnalysis,
      confirmSideEffects,
      goBack,
      cancel,
      updateSelectedPatches,
      toggleAutoFix
    }
  };
}
