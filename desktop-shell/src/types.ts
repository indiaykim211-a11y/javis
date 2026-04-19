export type Snapshot = {
  generatedAt: string;
  app: {
    name: string;
    ui: string;
    engine: string;
  };
  project: {
    summary: string;
    targetOutcome: string;
    steps: string[];
  };
  assistant: {
    badge: string;
    headline: string;
    summary: string;
    nextAction: string;
  };
  surface: {
    stateKey: string;
    projectLabel: string;
    badgeLabel: string;
    title: string;
    summary: string;
    reason: string;
    nextAction: string;
    progressLabel: string;
    detailLabel: string;
    riskLabel: string;
    actions: Array<{
      id: string;
      label: string;
      enabled: boolean;
      emphasis: string;
    }>;
  };
  runtime: {
    savedAt: string;
    progress: {
      current: number;
      total: number;
      ratio: number;
    };
    currentStep: string;
    lastCapturePath: string | null;
    lastTargetTitle: string;
    lockStatus: string;
    operatorPaused: boolean;
    operatorPauseReason: string;
    autoRunning: boolean;
  };
  codex: {
    strategyPresetId: string;
    automationModeId: string;
    deepIntegrationModeId: string;
    liveOpsProfileId: string;
  };
  queue: Array<{
    index: number;
    total: number;
    title: string;
    status: string;
    displayLine: string;
  }>;
  promptPreview: {
    hasStep: boolean;
    isComplete: boolean;
    stepIndex: number | null;
    stepTitle: string;
    source: string;
    excerpt: string;
    generatedPrompt: string;
    draftPrompt: string;
  };
  signals: Array<{
    label: string;
    value: string;
    tone: string;
  }>;
  deckSections: Array<{
    id: string;
    title: string;
    value: string;
    description: string;
    tone: string;
  }>;
  recentProjects: Array<{
    title: string;
    savedAt: string;
    progress: {
      current: number;
      total: number;
    };
    lastCapturePath: string;
  }>;
};

export type ActionResponse = {
  ok: boolean;
  actionId: string;
  message: string;
  payload?: Record<string, unknown>;
  snapshot?: Snapshot;
};

export type ControlDeckOption = {
  id: string;
  title: string;
  summary: string;
};

export type JudgmentStudio = {
  engineModeId: string;
  modelName: string;
  confidenceThreshold: number;
  maxHistoryItems: number;
  modeOptions: ControlDeckOption[];
  timeline: string;
  historyLines: string[];
  lastResult: {
    decision: string;
    reason: string;
    confidence: number;
    riskLevel: string;
    messageToUser: string;
    source: string;
    evaluatedAt: string;
    validationNotes: string[];
  };
};

export type VisualStudio = {
  targetModeId: string;
  captureScopeId: string;
  retentionHintId: string;
  sensitiveContentRisk: string;
  expectedPage: string;
  expectedSignalsText: string;
  disallowedSignalsText: string;
  observationFocusText: string;
  observedNotesText: string;
  targetModeOptions: ControlDeckOption[];
  captureScopeOptions: ControlDeckOption[];
  retentionOptions: ControlDeckOption[];
  timeline: string;
  historyLines: string[];
  lastResult: {
    targetLabel: string;
    contradictionLevel: string;
    decisionHint: string;
    messageToUser: string;
    observedSummary: string;
    evaluatedAt: string;
  };
};

export type VoiceStudio = {
  languageCode: string;
  autoBriefEnabled: boolean;
  confirmationEnabled: boolean;
  spokenFeedbackEnabled: boolean;
  ambientReadyEnabled: boolean;
  microphoneName: string;
  speakerName: string;
  timeline: string;
  historyLines: string[];
  lastResult: {
    transcriptText: string;
    intentId: string;
    actionStatus: string;
    messageToUser: string;
    spokenBriefingText: string;
    evaluatedAt: string;
  };
};

export type DeepIntegrationStudio = {
  selectedModeId: string;
  appServerReadinessId: string;
  cloudTriggerReadinessId: string;
  desktopFallbackAllowed: boolean;
  appServerNotes: string;
  cloudTriggerNotes: string;
  handoffNotes: string;
  modeOptions: ControlDeckOption[];
  readinessOptions: ControlDeckOption[];
  capabilityRegistry: string;
  crossSurfaceHandoff: string;
  observabilityReport: string;
};

export type ControlDeck = {
  projectEditor: {
    projectSummary: string;
    targetOutcome: string;
    stepsText: string;
    stepCount: number;
    nextStepIndex: number;
  };
  operationsEditor: {
    codexStrategy: {
      selectedPresetId: string;
      selectedModeId: string;
      customInstruction: string;
      presetOptions: ControlDeckOption[];
      modeOptions: ControlDeckOption[];
    };
    automation: {
      pollIntervalSec: number;
      dryRun: boolean;
    };
    liveOps: {
      selectedProfileId: string;
      reportCadenceId: string;
      reentryModeId: string;
      operatorNote: string;
      profileOptions: ControlDeckOption[];
      cadenceOptions: ControlDeckOption[];
      reentryOptions: ControlDeckOption[];
    };
  };
  promptWorkbench: {
    hasStep: boolean;
    stepIndex: number | null;
    stepTitle: string;
    source: string;
    generatedPrompt: string;
    draftPrompt: string;
    isDirty: boolean;
  };
  intelligenceStudio: {
    judgment: JudgmentStudio;
    visual: VisualStudio;
    voice: VoiceStudio;
    deepIntegration: DeepIntegrationStudio;
  };
  runbooks: {
    launchPrompt: string;
    runbook: string;
    runboard: string;
    shiftBrief: string;
  };
  recentProjects: Array<{
    index: number;
    title: string;
    targetOutcome: string;
    savedAt: string;
    progress: {
      current: number;
      total: number;
    };
    lastCapturePath: string;
  }>;
};

export type ControlDeckResponse = {
  ok: boolean;
  kind: string;
  message: string;
  snapshot?: Snapshot;
  controlDeck?: ControlDeck;
};

export type ActivityEntry = {
  timestamp: string;
  message: string;
  tone: string;
};

export type WorkspaceBundle = {
  generatedAt: string;
  snapshot: Snapshot;
  controlDeck: ControlDeck;
  activityFeed: ActivityEntry[];
};
