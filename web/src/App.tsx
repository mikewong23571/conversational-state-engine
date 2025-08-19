import React, { useState, useEffect } from 'react';
import DiffPanel from './components/DiffPanel';
import IntentConfirmation from './components/IntentConfirmation';
import SideEffectAnalysis from './components/SideEffectAnalysis';
import CommandInput from './components/CommandInput';
import { Operation } from 'fast-json-patch';
import { useConfirmationFlow, type IntentSummary } from './hooks/useConfirmationFlow';
import { parseUserInput } from './utils/commandParser';
import { inferIntentFromText, validateInferredIntent, suggestCommand } from './utils/intentInference';
import { generatePatchesFromIntent, validateGeneratedPatches } from './utils/patchGenerator';
import { testPatches, suggestPatchFix } from './utils/patchTester';

type Patch = Operation;

interface Suggestion {
  description: string;
  auto_fix: boolean;
  patches?: Patch[];
}

interface Conflict {
  type: string;
  rule: string;
  severity: 'low' | 'medium' | 'high';
  message: string;
  suggestion?: Suggestion;
  affected_paths: string[];
  examples?: string[];
}

interface ImpactAnalysis {
  affected_paths: string[];
  risk_level: 'low' | 'medium' | 'high';
  semantic_conflicts: Conflict[];
  suggested_alternatives?: unknown[];
  risk_explanation?: string;
  dependency_analysis?: {
    breaking_changes: string[];
    cascading_effects: string[];
    validation_warnings: string[];
  };
}

interface Artifact {
  type?: string;
  url?: string;
  [key: string]: unknown;
}

interface SessionState {
  id: string;
  state: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

interface API {
  baseUrl: string;

  createSession(): Promise<SessionState>;

  getSessionState(sessionId: string): Promise<Record<string, unknown>>;

  submitIntent(sessionId: string, message: string): Promise<{
    intentions: unknown[];
    patches: Patch[];
    impact: ImpactAnalysis;
  }>;

  confirmPatches(sessionId: string, patchIndices: number[]): Promise<{
    success: boolean;
    new_state: Record<string, unknown>;
    applied_patches: Patch[];
  }>;

  commitState(sessionId: string): Promise<{
    success: boolean;
    artifacts: Artifact[];
  }>;
}

class APIClient implements API {
  baseUrl: string;
  private token: string | null = null;

  constructor(baseUrl: string = 'http://localhost:8000') {
    this.baseUrl = baseUrl;
  }

  async register(email: string, password: string, full_name?: string): Promise<{ access_token: string; token_type: string }> {
    const response = await fetch(`${this.baseUrl}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password, full_name, role: 'editor' })
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Registration failed');
    }
    const data = await response.json();
    this.token = data.access_token;
    return data;
  }

  async login(email: string, password: string): Promise<{ access_token: string; token_type: string }> {
    const response = await fetch(`${this.baseUrl}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Login failed');
    }
    const data = await response.json();
    this.token = data.access_token;
    return data;
  }

  private getAuthHeaders(): Record<string, string> {
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }
    return headers;
  }

  async createSession(): Promise<SessionState> {
    // Create session
    const createResponse = await fetch(`${this.baseUrl}/sessions`, {
      method: 'POST',
      headers: this.getAuthHeaders()
    });
    if (!createResponse.ok) throw new Error('Failed to create session');

    const sessionData = await createResponse.json();
    const sessionId = sessionData.session_id;

    // Get session state
    const stateResponse = await fetch(`${this.baseUrl}/sessions/${sessionId}/state`, {
      headers: this.getAuthHeaders()
    });
    if (!stateResponse.ok) throw new Error('Failed to get session state');

    const stateData = await stateResponse.json();

    return {
      id: sessionId,
      state: stateData,
      created_at: stateData.created_at,
      updated_at: stateData.created_at
    };
  }

  async getSessionState(sessionId: string): Promise<Record<string, unknown>> {
    const response = await fetch(`${this.baseUrl}/sessions/${sessionId}/state`, {
      headers: this.getAuthHeaders()
    });
    if (!response.ok) throw new Error('Failed to get session state');
    return response.json();
  }

  async submitIntent(sessionId: string, message: string): Promise<{
    intentions: unknown[];
    patches: Patch[];
    impact: ImpactAnalysis;
  }> {
    const response = await fetch(`${this.baseUrl}/sessions/${sessionId}/analyze`, {
      method: 'POST',
      headers: this.getAuthHeaders(),
      body: JSON.stringify({ message })
    });
    if (!response.ok) throw new Error('Failed to submit intent');
    return response.json();
  }

  async confirmPatches(_sessionId: string, _patchIndices: number[]): Promise<{
    success: boolean;
    new_state: Record<string, unknown>;
    applied_patches: Patch[];
  }> {
    // Note: This endpoint doesn't exist in the backend yet
    // For now, we'll simulate a successful response to allow the flow to continue
    // In a real implementation, this would apply patches without committing
    throw new Error('Patch confirmation endpoint not implemented. Use commit instead.');
  }

  async createIntentionSet(sessionId: string, intentions: unknown): Promise<{intention_set_id: string}> {
    const response = await fetch(`${this.baseUrl}/sessions/${sessionId}/intents`, {
      method: 'POST',
      headers: this.getAuthHeaders(),
      body: JSON.stringify(intentions)
    });
    if (!response.ok) throw new Error('Failed to create intention set');
    return response.json();
  }

  async createPatchProposal(sessionId: string, intentionSetId: string): Promise<{
    proposal_id: string;
    patches: Patch[];
    impact_analysis: ImpactAnalysis;
  }> {
    const response = await fetch(`${this.baseUrl}/sessions/${sessionId}/patch-proposals`, {
      method: 'POST',
      headers: this.getAuthHeaders(),
      body: JSON.stringify({ intention_set_id: intentionSetId })
    });
    if (!response.ok) throw new Error('Failed to create patch proposal');
    return response.json();
  }

  async confirmIntent(sessionId: string, proposalId: string): Promise<unknown> {
    const response = await fetch(`${this.baseUrl}/sessions/${sessionId}/confirm-intent`, {
      method: 'POST',
      headers: this.getAuthHeaders(),
      body: JSON.stringify({ proposal_id: proposalId })
    });
    if (!response.ok) throw new Error('Failed to confirm intent');
    return response.json();
  }

  async confirmChanges(sessionId: string, proposalId: string, selectedIndices: number[]): Promise<unknown> {
    const response = await fetch(`${this.baseUrl}/sessions/${sessionId}/confirm-changes`, {
      method: 'POST',
      headers: this.getAuthHeaders(),
      body: JSON.stringify({
        proposal_id: proposalId,
        selected_patch_indices: selectedIndices
      })
    });
    if (!response.ok) throw new Error('Failed to confirm changes');
    return response.json();
  }

  async confirmSideEffects(sessionId: string, proposalId: string, applyAutoFixes: boolean = false): Promise<unknown> {
    const response = await fetch(`${this.baseUrl}/sessions/${sessionId}/confirm-side-effects`, {
      method: 'POST',
      headers: this.getAuthHeaders(),
      body: JSON.stringify({
        proposal_id: proposalId,
        apply_auto_fixes: applyAutoFixes
      })
    });
    if (!response.ok) throw new Error('Failed to confirm side effects');
    return response.json();
  }

  async commitState(sessionId: string, proposalId?: string): Promise<{
    success: boolean;
    artifacts: Artifact[];
  }> {
    if (!proposalId) {
      throw new Error('Proposal ID required for commit');
    }

    const response = await fetch(`${this.baseUrl}/sessions/${sessionId}/commit`, {
      method: 'POST',
      headers: this.getAuthHeaders(),
      body: JSON.stringify({ proposal_id: proposalId })
    });
    if (!response.ok) throw new Error('Failed to commit state');
    const result = await response.json();

      return {
        success: true,
        artifacts: (result.artifacts?.items || []) as Artifact[],
      };
  }
}

const App: React.FC = () => {
  const [api] = useState(new APIClient());
  const [session, setSession] = useState<SessionState | null>(null);
  const [currentState, setCurrentState] = useState<Record<string, unknown>>({
    version: "v1",
    schema_version: "1.0.0",
    data: {
      stories: [],
      glossary: []
    }
  });
  const [message, setMessage] = useState('');
  const [proposedPatches, setProposedPatches] = useState<Patch[]>([]);
  const [impact, setImpact] = useState<ImpactAnalysis | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentProposalId, setCurrentProposalId] = useState<string | null>(null);
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [showAuth, setShowAuth] = useState(true);
  const [authMode, setAuthMode] = useState<'login' | 'register'>('login');
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    full_name: ''
  });

  // 渐进式确认流程
  const confirmation = useConfirmationFlow();

  // Artifacts state
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);

  // Debug logging for state changes
  useEffect(() => {
    console.log('Session state changed:', session);
  }, [session]);

  useEffect(() => {
    console.log('isLoggedIn state changed:', isLoggedIn);
  }, [isLoggedIn]);

  useEffect(() => {
    console.log('showAuth state changed:', showAuth);
  }, [showAuth]);

  // Initialize session when user logs in
  useEffect(() => {
    const initializeSession = async () => {
      console.log('initializeSession called from useEffect, isLoggedIn:', isLoggedIn);
      if (!isLoggedIn) return;

      try {
        setLoading(true);
        setError(null);
        console.log('Creating new session...');
        const newSession = await api.createSession();
        console.log('Session created:', newSession);
        console.log('Setting session state...');
        setSession(newSession);
        console.log('Setting current state...');
        setCurrentState(newSession.state);
        console.log('Session state update completed');
      } catch (err: unknown) {
        console.error('Failed to initialize session:', err);
        const error = err as Error;
        if (error.message && error.message.includes('Insufficient permissions')) {
          setError('Your account does not have permission to create sessions. Please register with a different email or contact an administrator.');
        } else {
          setError(`Failed to initialize session: ${error.message}`);
        }
      } finally {
        setLoading(false);
      }
    };

    if (isLoggedIn && !session) {
      console.log('User is logged in but no session exists, initializing...');
      initializeSession();
    }
  }, [isLoggedIn, session, api]);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setLoading(true);
      setError(null);
      console.log('Logging in with:', formData.email);
      await api.login(formData.email, formData.password);
      console.log('Login successful, setting isLoggedIn to true');
      setIsLoggedIn(true);
      setShowAuth(false);
      console.log('Login flow completed, session will be initialized by useEffect');
    } catch (err: unknown) {
      console.error('Login failed:', err);
      const error = err as Error;
      setError(error.message || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setLoading(true);
      setError(null);
      console.log('Registering with:', formData.email);
      await api.register(formData.email, formData.password, formData.full_name);
      console.log('Registration successful, setting isLoggedIn to true');
      setIsLoggedIn(true);
      setShowAuth(false);
      console.log('Registration flow completed, session will be initialized by useEffect');
    } catch (err: unknown) {
      console.error('Registration failed:', err);
      const error = err as Error;
      setError(error.message || 'Registration failed');
    } finally {
      setLoading(false);
    }
  };

  const switchAuthMode = () => {
    setAuthMode(authMode === 'login' ? 'register' : 'login');
    setError(null);
  };

  const handleLogout = () => {
    setIsLoggedIn(false);
    setShowAuth(true);
      setSession(null);
      setCurrentState({});
    setProposedPatches([]);
    setImpact(null);
    setMessage('');
    setFormData({ email: '', password: '', full_name: '' });
    setAuthMode('login');
  };


  const handleSubmit = async (messageInput: string) => {
    if (!messageInput.trim()) return;

    if (!session) {
      console.error('No session found when trying to submit intent');
      setError('No active session. Please refresh the page.');
      return;
    }

    try {
      setLoading(true);
      setError(null);

      // Parse user input to determine if it's a command or natural language
      const parseResult = parseUserInput(messageInput);

        let intent: IntentSummary;
      let patches: Operation[] = [];
      let impact: ImpactAnalysis = { affected_paths: [], risk_level: 'low', semantic_conflicts: [] };

      if (parseResult.type === 'command' && parseResult.command) {
        // Handle structured command
        intent = {
          action: parseResult.command.action,
          target_path: parseResult.command.target,
          value: parseResult.command.properties,
          reason: parseResult.command.reason || `Command: ${parseResult.original}`,
          confidence: parseResult.command.confidence
        };

        // For commands, we can potentially skip API call and generate patches directly
        // But for now, still call API for consistency
        const response = await api.submitIntent(session.id, messageInput);
        patches = response.patches || [];
        impact = response.impact || impact;
      } else {
        // Handle natural language with intelligent intent inference
        const inferredIntent = inferIntentFromText(messageInput);
        const validation = validateInferredIntent(inferredIntent, messageInput);

        try {
          // Generate local patches first to get the value
          const patchResult = generatePatchesFromIntent(inferredIntent, messageInput);
          const patchValue = patchResult.patches.length > 0 && 'value' in patchResult.patches[0]
            ? patchResult.patches[0].value
            : null;

          // Create intention set from inferred intent
          const intentionSet = {
            items: [{
              action: inferredIntent.action,
              target_path: inferredIntent.target_path,
              value: patchValue,
              reason: `${inferredIntent.reasoning} | 用户请求: ${messageInput}`,
              confidence: Math.max(0.1, Math.min(1.0, inferredIntent.confidence)) // Ensure valid range
            }]
          };

          // Create intention set in backend
          console.log('🔧 Creating intention set:', intentionSet);
          const intentionResponse = await api.createIntentionSet(session.id, intentionSet);
          const intentionSetId = intentionResponse.intention_set_id;
          console.log('✅ Created intention set:', intentionSetId);

          // Create patch proposal
          console.log('🔧 Creating patch proposal for intention set:', intentionSetId);
          const proposalResponse = await api.createPatchProposal(session.id, intentionSetId);

          patches = proposalResponse.patches;
          impact = proposalResponse.impact_analysis;
          setCurrentProposalId(proposalResponse.proposal_id);

          console.log('✅ Created patch proposal:', proposalResponse.proposal_id);
          console.log('✅ Backend patches:', patches);
          console.log('✅ Backend impact:', impact);

        } catch (apiError) {
          console.warn('API backend flow failed, using local patch generation:', apiError);

          // Fallback to local patch generation
          const patchResult = generatePatchesFromIntent(inferredIntent, messageInput);
          const patchValidation = validateGeneratedPatches(patchResult.patches);

          if (patchValidation.valid) {
            patches = patchResult.patches;
            console.log('✅ Generated patches locally:', patches);

            // Test patches on current state
            const patchTest = testPatches(currentState, patches);
            if (!patchTest.success) {
              console.error('❌ Patch test failed on current state');
              patchTest.results.forEach((result, idx) => {
                if (!result.success) {
                  console.error(`❌ Patch ${idx} failed:`, result.error);
                  const suggestions = suggestPatchFix(currentState, result.patch, result.error || '');
                  console.error('💡 Suggestions:', suggestions);
                }
              });

              // Use simplified fallback patch
              patches = [{
                op: 'add',
                path: '/data/stories/-',
                value: {
                  key: `SIMPLE-${Date.now()}`,
                  title: '用户需求项目',
                  priority: 'P2',
                  reason: messageInput,
                  status: 'needs_review'
                }
              }];
              console.log('🔄 Using simplified fallback patch:', patches);
            }
          } else {
            console.error('❌ Generated patches validation failed:', patchValidation.issues);
            // Use fallback patches
            patches = [{
              op: 'add',
              path: '/data/stories/-',
              value: {
                key: `MANUAL-${Date.now()}`,
                title: `用户请求: ${messageInput}`,
                priority: 'P2',
                reason: messageInput,
                status: 'needs_review'
              }
            }];
          }

          // No proposal ID for local patches - will skip backend confirmation
          setCurrentProposalId(null);
        }

        intent = {
          action: inferredIntent.action,
          target_path: inferredIntent.target_path,
          value: 'value' in (patches[0] || {}) ? (patches[0] as { value?: unknown }).value : undefined,
          reason: `${inferredIntent.reasoning} | 用户请求: ${messageInput}`,
          confidence: inferredIntent.confidence
        };

        // Add validation warnings to impact if confidence is low
        if (!validation.valid || inferredIntent.confidence < 0.7) {
            const validationConflicts = validation.issues.map(issue => ({
              type: 'intent_inference',
              rule: 'low_confidence_inference',
              severity: 'medium' as const,
              message: issue,
              affected_paths: impact.affected_paths || [],
              suggestion: {
                description: `建议使用命令: ${suggestCommand(inferredIntent, messageInput)}`,
                auto_fix: false
              }
            }));

          impact = {
            ...impact,
            semantic_conflicts: [
              ...(impact.semantic_conflicts || []),
              ...validationConflicts
            ]
          };
        }
      }

      confirmation.actions.startIntentConfirmation(intent);

      // Enhance impact analysis with additional details
      const enhancedImpact = {
        ...impact,
        risk_explanation: impact.risk_level === 'high'
          ? '检测到高风险操作，可能影响现有功能或数据一致性'
          : impact.risk_level === 'medium'
          ? '中等风险操作，建议仔细评估后执行'
          : '低风险操作，对系统影响较小',
        dependency_analysis: {
          breaking_changes: impact.semantic_conflicts?.filter((c: Conflict) => c.severity === 'high')?.map((c: Conflict) => c.message) || [],
          cascading_effects: impact.affected_paths || [],
          validation_warnings: impact.semantic_conflicts?.filter((c: Conflict) => c.severity === 'low')?.map((c: Conflict) => c.message) || []
        },
        semantic_conflicts: impact.semantic_conflicts?.map((conflict: Conflict) => ({
          ...conflict,
          affected_paths: impact.affected_paths || ['/stories'],
          examples: conflict.rule === 'auth_method_conflict'
            ? ['SSO与本地密码认证同时启用', '用户可能无法正确登录']
            : ['数据验证失败', '业务逻辑冲突'],
            suggestion: conflict.rule === 'auth_method_conflict' ? {
              description: '建议禁用本地密码认证，统一使用SSO',
              auto_fix: true,
              patches: [{ op: 'replace', path: '/auth_settings/local_auth', value: false } as Operation]
            } : undefined
        })) || []
      };

      // Store patches and enhanced impact for later stages
      console.log('🔍 Debug - handleSubmit patches:', patches);
      console.log('🔍 Debug - handleSubmit enhancedImpact:', enhancedImpact);

      setProposedPatches(patches);
      setImpact(enhancedImpact);
    } catch (err: unknown) {
      console.error('Failed to process intent:', err);
      setError('Failed to process intent');
    } finally {
      setLoading(false);
    }
  };

  // 渐进式确认流程处理函数
  const handleIntentConfirmed = async () => {
    if (!session) return;

    try {
      setLoading(true);
      setError(null);

      // Call backend intent confirmation only if we have a proposal ID
      if (currentProposalId) {
        await api.confirmIntent(session.id, currentProposalId);
        console.log('✅ Backend intent confirmed for proposal:', currentProposalId);
      } else {
        console.log('📝 Using local patch flow, skipping backend intent confirmation');
      }

      confirmation.actions.confirmIntent();

      // At this point, proposedPatches should have been populated by handleSubmit
      if (proposedPatches.length === 0) {
        console.error('⚠️ No patches available after intent confirmation');
        setError('No changes were generated from your intent. Please try rephrasing your request.');
        return;
      }

      // Set change preview for next stage, falling back to a minimal impact analysis if none exists
      const previewImpact = impact || {
        affected_paths: [],
        risk_level: 'low' as const,
        semantic_conflicts: []
      };

      confirmation.actions.setChangePreview({
        patches: proposedPatches,
        selectedIndices: proposedPatches.map((_, i) => i), // Select all by default
        impact: previewImpact
      });
    } catch (err: unknown) {
      console.error('Failed to confirm intent:', err);
      const error = err as Error;
      setError(`Failed to confirm intent: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleChangesConfirmed = async () => {
    if (!session || !confirmation.state.changes) return;

    try {
      setLoading(true);
      setError(null);

      // Call backend changes confirmation only if we have a proposal ID
      if (currentProposalId) {
        await api.confirmChanges(session.id, currentProposalId, confirmation.state.changes.selectedIndices);
        console.log('✅ Backend changes confirmed for proposal:', currentProposalId);
      } else {
        console.log('📝 Using local patch flow, skipping backend changes confirmation');
      }

      confirmation.actions.confirmChanges();

      // Side effect analysis - in real implementation this would come from API
      const sideEffects = {
        warnings: impact?.semantic_conflicts?.map(conflict => ({
          type: conflict.rule,
          message: conflict.message,
          severity: conflict.severity
        })) || [],
        auto_fixes: [] // TODO: implement auto-fix suggestions
      };

      confirmation.actions.setSideEffectAnalysis(sideEffects);
    } catch (err: unknown) {
      console.error('Failed to confirm changes:', err);
      const error = err as Error;
      setError(`Failed to confirm changes: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleSideEffectsConfirmed = async () => {
    if (!session) return;

    try {
      setLoading(true);
      setError(null);

      // Call backend side effects confirmation only if we have a proposal ID
      if (currentProposalId) {
        await api.confirmSideEffects(session.id, currentProposalId, false);
        console.log('✅ Backend side effects confirmed for proposal:', currentProposalId);
      } else {
        console.log('📝 Using local patch flow, skipping backend side effects confirmation');
      }

      confirmation.actions.confirmSideEffects();

      // Note: Don't reset form immediately - let user see the success state
      // and decide when to commit or make more changes
      setProposedPatches([]);
      setImpact(null);
      setMessage('');

      // Show a message that changes are ready to commit
      console.log('Side effects confirmed. Ready to commit changes.');
    } catch (err: unknown) {
      console.error('Failed to confirm side effects:', err);
      const error = err as Error;
      setError(`Failed to confirm side effects: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleConfirmationCancel = () => {
    confirmation.actions.cancel();
    setProposedPatches([]);
    setImpact(null);
    setMessage('');
    setCurrentProposalId(null);
  };


  const handleCommit = async () => {
    if (!session) {
      setError('No active session');
      return;
    }

    try {
      setLoading(true);
      setError(null);

      if (currentProposalId) {
        // Backend proposal flow
        const response = await api.commitState(session.id, currentProposalId);

        if (response.success) {
          console.log('✅ Backend commit successful. Artifacts generated:', response.artifacts);

          // Reset confirmation flow and proposal
          confirmation.actions.cancel();
          setCurrentProposalId(null);

          // Refresh session state
          const newStateResponse = await api.getSessionState(session.id);
          console.log('🔧 Backend state refresh response:', newStateResponse);
          setCurrentState(newStateResponse);

          // Store artifacts for display
          setArtifacts(response.artifacts);

          // Show success message
          window.alert(`Commit successful! Generated ${response.artifacts.length} artifacts.`);
        } else {
          setError('Backend commit failed');
        }
      } else {
        // Local patch flow - apply patches locally and update state
        console.log('📝 Local commit: applying patches locally');

        // Get the patches from the confirmation state
        const patches = confirmation.state.changes?.patches || [];
        const selectedIndices = confirmation.state.changes?.selectedIndices || [];
        const selectedPatches = selectedIndices.map(i => patches[i]).filter(Boolean);

        if (selectedPatches.length > 0) {
          try {
            // Apply patches to current state using fast-json-patch
            const { applyPatch } = await import('fast-json-patch');
            const updatedState = applyPatch(currentState, selectedPatches, false, false).newDocument;

            // Update the current state in the UI
            setCurrentState(updatedState);

            console.log('✅ Local patches applied successfully');
            console.log('🔧 Updated state:', updatedState);
          } catch (patchError) {
            console.error('❌ Failed to apply local patches:', patchError);
            setError(`Failed to apply local patches: ${patchError}`);
            return;
          }
        }

        confirmation.actions.cancel();

        // Store empty artifacts for display
        setArtifacts([]);

        // Show success message
        window.alert('Local changes applied successfully! (Demo mode - changes not persisted to backend)');
      }
    } catch (err: unknown) {
      console.error('Commit failed:', err);
      const error = err as Error;
      setError(`Commit failed: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  if (showAuth) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="bg-white rounded-lg shadow p-8 max-w-md w-full">
          <h2 className="text-2xl font-bold text-gray-900 mb-6">
            {authMode === 'login' ? 'Login' : 'Register'}
          </h2>

          <form onSubmit={authMode === 'login' ? handleLogin : handleRegister} className="space-y-4">
            {authMode === 'register' && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Full Name</label>
                <input
                  type="text"
                  name="full_name"
                  value={formData.full_name}
                  onChange={handleInputChange}
                  className="w-full p-3 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  required={authMode === 'register'}
                />
              </div>
            )}

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
              <input
                type="email"
                name="email"
                value={formData.email}
                onChange={handleInputChange}
                className="w-full p-3 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
              <input
                type="password"
                name="password"
                value={formData.password}
                onChange={handleInputChange}
                className="w-full p-3 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                required
                minLength={6}
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400"
            >
              {loading
                ? (authMode === 'login' ? 'Logging in...' : 'Registering...')
                : (authMode === 'login' ? 'Login' : 'Register')
              }
            </button>
          </form>

          <div className="mt-4 text-center">
            <button
              type="button"
              onClick={switchAuthMode}
              className="text-blue-600 hover:text-blue-800 text-sm"
            >
              {authMode === 'login'
                ? "Don't have an account? Register"
                : "Already have an account? Login"
              }
            </button>
          </div>

          {error && (
            <div className="mt-4 text-red-600 text-sm">
              {error}
            </div>
          )}
        </div>
      </div>
    );
  }

  if (loading && !session) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-lg">Initializing...</div>
      </div>
    );
  }

  if (error && !session) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="bg-white rounded-lg shadow p-8 max-w-md w-full text-center">
          <div className="text-red-600 mb-4">Error: {error}</div>
          <button
            onClick={handleLogout}
            className="px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700 mr-2"
          >
            Try Again
          </button>
          <button
            onClick={() => {
              handleLogout();
              setAuthMode('register');
            }}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
          >
            Register New Account
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <h1 className="text-2xl font-bold text-gray-900">
              Conversational State Engine
            </h1>
            {session && (
              <div className="flex items-center space-x-4">
                <span className="text-sm text-gray-500">
                  Session: {session.id}
                </span>
                <button
                  onClick={handleCommit}
                  disabled={loading || confirmation.state.stage !== 'completed'}
                  className={`px-4 py-2 rounded-md disabled:bg-gray-400 ${
                    confirmation.state.stage === 'completed'
                      ? 'bg-green-600 text-white hover:bg-green-700'
                      : 'bg-gray-300 text-gray-500'
                  }`}
                  title={confirmation.state.stage !== 'completed' ? 'Complete the confirmation flow first' : 'Commit changes permanently'}
                >
                  {confirmation.state.stage === 'completed' ? 'Commit State' : 'Pending Changes'}
                </button>
                <button
                  onClick={handleLogout}
                  className="px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700"
                >
                  Logout
                </button>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Left Panel - Input & State */}
          <div className="space-y-6">
            {/* Command Input */}
            <CommandInput
              value={message}
              onChange={setMessage}
              onSubmit={handleSubmit}
              loading={loading}
              placeholder="e.g., Add a new story for user login with P0 priority and biometric authentication"
            />

            {/* Current State */}
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-semibold mb-4">Current State</h2>
              <div className="bg-gray-50 rounded p-4 max-h-96 overflow-y-auto">
                <pre className="text-sm text-gray-700 whitespace-pre-wrap">
                  {currentState ? JSON.stringify(currentState, null, 2) : 'No state loaded'}
                </pre>
              </div>
            </div>
          </div>

          {/* Right Panel - Progressive Confirmation */}
          <div className="h-full">
            {confirmation.state.stage === 'intent' && confirmation.state.intent ? (
              <IntentConfirmation
                intent={confirmation.state.intent}
                onConfirm={handleIntentConfirmed}
                onCancel={handleConfirmationCancel}
                loading={loading}
                  preliminaryImpact={impact ?? undefined}
              />
            ) : confirmation.state.stage === 'change' && confirmation.state.changes && currentState ? (
              <DiffPanel
                currentState={currentState}
                proposedPatches={confirmation.state.changes.patches}
                impact={confirmation.state.changes.impact}
                onConfirm={(selectedIndices) => {
                  confirmation.actions.updateSelectedPatches(selectedIndices);
                  handleChangesConfirmed();
                }}
                onReject={() => confirmation.actions.goBack()}
              />
            ) : confirmation.state.stage === 'side_effect' && confirmation.state.sideEffects ? (
              <SideEffectAnalysis
                sideEffects={confirmation.state.sideEffects}
                onToggleAutoFix={confirmation.actions.toggleAutoFix}
                onConfirm={handleSideEffectsConfirmed}
                onGoBack={() => confirmation.actions.goBack()}
                loading={loading}
              />
            ) : confirmation.state.stage === 'completed' ? (
              <div className="bg-white rounded-lg shadow h-full p-6">
                <div className="text-center text-green-600 mb-6">
                  <div className="text-lg mb-2">✅ 变更已成功应用</div>
                  <div className="text-sm">您的变更已提交并生效，可以点击"Commit State"进行最终提交</div>
                </div>

                {artifacts.length > 0 && (
                  <div className="mt-6">
                    <h3 className="text-lg font-semibold text-gray-900 mb-4">生成的产物</h3>
                    <div className="space-y-3">
                      {artifacts.map((artifact, index) => (
                        <div key={index} className="p-3 bg-gray-50 rounded-lg border">
                          <div className="flex items-center justify-between">
                            <div>
                              <div className="text-sm font-medium text-gray-900">
                                {artifact.type || 'Document'}
                              </div>
                              <div className="text-xs text-gray-500">
                                {artifact.url || `artifact-${index + 1}`}
                              </div>
                            </div>
                            <span className="text-xs text-green-600 bg-green-50 px-2 py-1 rounded">
                              Generated
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <div className="mt-6 text-center">
                  <button
                    onClick={() => confirmation.actions.cancel()}
                    className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
                  >
                    开始新的变更
                  </button>
                </div>
              </div>
            ) : (
              <div className="bg-white rounded-lg shadow h-full flex items-center justify-center p-8">
                <div className="text-center text-gray-500">
                  <div className="text-lg mb-2">No proposed changes</div>
                  <div className="text-sm">Submit an intent to see proposed changes here</div>
                </div>
              </div>
            )}
          </div>
        </div>
      </main>

      {/* Error Display */}
      {error && (
        <div className="fixed bottom-4 right-4 bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}
    </div>
  );
};

export default App;
