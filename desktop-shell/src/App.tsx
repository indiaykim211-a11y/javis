import { startTransition, useEffect, useState } from "react";

import { mockSnapshot } from "./mockSnapshot";
import type {
  ActionResponse,
  ActivityEntry,
  ControlDeck,
  ControlDeckOption,
  ControlDeckResponse,
  Snapshot,
  WorkspaceBundle,
} from "./types";

type DeckTab = "project" | "operations" | "prompt" | "intelligence" | "activity" | "recent";

type ProjectFormState = {
  projectSummary: string;
  targetOutcome: string;
  stepsText: string;
};

type OperationsFormState = {
  selectedPresetId: string;
  selectedModeId: string;
  customInstruction: string;
  pollIntervalSec: number;
  dryRun: boolean;
  selectedProfileId: string;
  reportCadenceId: string;
  reentryModeId: string;
  operatorNote: string;
};

type IntelligenceFormState = {
  judgmentEngineModeId: string;
  judgmentModelName: string;
  judgmentConfidenceThreshold: number;
  judgmentMaxHistoryItems: number;
  visualTargetModeId: string;
  visualCaptureScopeId: string;
  visualRetentionHintId: string;
  visualSensitiveContentRisk: string;
  visualExpectedPage: string;
  visualExpectedSignalsText: string;
  visualDisallowedSignalsText: string;
  visualObservationFocusText: string;
  visualObservedNotesText: string;
  voiceLanguageCode: string;
  voiceAutoBriefEnabled: boolean;
  voiceConfirmationEnabled: boolean;
  voiceSpokenFeedbackEnabled: boolean;
  voiceAmbientReadyEnabled: boolean;
  voiceMicrophoneName: string;
  voiceSpeakerName: string;
  deepSelectedModeId: string;
  deepAppServerReadinessId: string;
  deepCloudTriggerReadinessId: string;
  deepDesktopFallbackAllowed: boolean;
  deepAppServerNotes: string;
  deepCloudTriggerNotes: string;
  deepHandoffNotes: string;
};

const deckTabs: Array<{ id: DeckTab; label: string; caption: string }> = [
  { id: "project", label: "프로젝트", caption: "요약 · 목표 · 단계" },
  { id: "operations", label: "운영", caption: "전략 · cadence · runbook" },
  { id: "prompt", label: "프롬프트", caption: "현재 단계 workbench" },
  { id: "intelligence", label: "Intelligence", caption: "판단 · 시각 · 음성 · 통합" },
  { id: "activity", label: "활동 피드", caption: "저장 · 전송 · 오류 흐름" },
  { id: "recent", label: "최근 세션", caption: "복원 · 재진입" },
];

function formatSavedAt(value: string): string {
  if (!value) {
    return "저장 기록 없음";
  }
  return value.replace("T", " ");
}

function findOption(options: ControlDeckOption[], selectedId: string): ControlDeckOption | undefined {
  return options.find((option) => option.id === selectedId);
}

function projectFormFromDeck(deck: ControlDeck): ProjectFormState {
  return {
    projectSummary: deck.projectEditor.projectSummary,
    targetOutcome: deck.projectEditor.targetOutcome,
    stepsText: deck.projectEditor.stepsText,
  };
}

function operationsFormFromDeck(deck: ControlDeck): OperationsFormState {
  return {
    selectedPresetId: deck.operationsEditor.codexStrategy.selectedPresetId,
    selectedModeId: deck.operationsEditor.codexStrategy.selectedModeId,
    customInstruction: deck.operationsEditor.codexStrategy.customInstruction,
    pollIntervalSec: deck.operationsEditor.automation.pollIntervalSec,
    dryRun: deck.operationsEditor.automation.dryRun,
    selectedProfileId: deck.operationsEditor.liveOps.selectedProfileId,
    reportCadenceId: deck.operationsEditor.liveOps.reportCadenceId,
    reentryModeId: deck.operationsEditor.liveOps.reentryModeId,
    operatorNote: deck.operationsEditor.liveOps.operatorNote,
  };
}

function intelligenceFormFromDeck(deck: ControlDeck): IntelligenceFormState {
  const judgment = deck.intelligenceStudio.judgment;
  const visual = deck.intelligenceStudio.visual;
  const voice = deck.intelligenceStudio.voice;
  const deep = deck.intelligenceStudio.deepIntegration;

  return {
    judgmentEngineModeId: judgment.engineModeId,
    judgmentModelName: judgment.modelName,
    judgmentConfidenceThreshold: judgment.confidenceThreshold,
    judgmentMaxHistoryItems: judgment.maxHistoryItems,
    visualTargetModeId: visual.targetModeId,
    visualCaptureScopeId: visual.captureScopeId,
    visualRetentionHintId: visual.retentionHintId,
    visualSensitiveContentRisk: visual.sensitiveContentRisk,
    visualExpectedPage: visual.expectedPage,
    visualExpectedSignalsText: visual.expectedSignalsText,
    visualDisallowedSignalsText: visual.disallowedSignalsText,
    visualObservationFocusText: visual.observationFocusText,
    visualObservedNotesText: visual.observedNotesText,
    voiceLanguageCode: voice.languageCode,
    voiceAutoBriefEnabled: voice.autoBriefEnabled,
    voiceConfirmationEnabled: voice.confirmationEnabled,
    voiceSpokenFeedbackEnabled: voice.spokenFeedbackEnabled,
    voiceAmbientReadyEnabled: voice.ambientReadyEnabled,
    voiceMicrophoneName: voice.microphoneName,
    voiceSpeakerName: voice.speakerName,
    deepSelectedModeId: deep.selectedModeId,
    deepAppServerReadinessId: deep.appServerReadinessId,
    deepCloudTriggerReadinessId: deep.cloudTriggerReadinessId,
    deepDesktopFallbackAllowed: deep.desktopFallbackAllowed,
    deepAppServerNotes: deep.appServerNotes,
    deepCloudTriggerNotes: deep.cloudTriggerNotes,
    deepHandoffNotes: deep.handoffNotes,
  };
}

function isProjectDirty(form: ProjectFormState, deck: ControlDeck | null): boolean {
  if (!deck) {
    return false;
  }
  return (
    form.projectSummary !== deck.projectEditor.projectSummary ||
    form.targetOutcome !== deck.projectEditor.targetOutcome ||
    form.stepsText !== deck.projectEditor.stepsText
  );
}

function isOperationsDirty(form: OperationsFormState, deck: ControlDeck | null): boolean {
  if (!deck) {
    return false;
  }
  const next = deck.operationsEditor;
  return (
    form.selectedPresetId !== next.codexStrategy.selectedPresetId ||
    form.selectedModeId !== next.codexStrategy.selectedModeId ||
    form.customInstruction !== next.codexStrategy.customInstruction ||
    form.pollIntervalSec !== next.automation.pollIntervalSec ||
    form.dryRun !== next.automation.dryRun ||
    form.selectedProfileId !== next.liveOps.selectedProfileId ||
    form.reportCadenceId !== next.liveOps.reportCadenceId ||
    form.reentryModeId !== next.liveOps.reentryModeId ||
    form.operatorNote !== next.liveOps.operatorNote
  );
}

function isPromptDirty(draftPrompt: string, deck: ControlDeck | null): boolean {
  if (!deck) {
    return false;
  }
  return draftPrompt !== deck.promptWorkbench.draftPrompt;
}

function isIntelligenceDirty(form: IntelligenceFormState, deck: ControlDeck | null): boolean {
  if (!deck) {
    return false;
  }
  const judgment = deck.intelligenceStudio.judgment;
  const visual = deck.intelligenceStudio.visual;
  const voice = deck.intelligenceStudio.voice;
  const deep = deck.intelligenceStudio.deepIntegration;

  return (
    form.judgmentEngineModeId !== judgment.engineModeId ||
    form.judgmentModelName !== judgment.modelName ||
    form.judgmentConfidenceThreshold !== judgment.confidenceThreshold ||
    form.judgmentMaxHistoryItems !== judgment.maxHistoryItems ||
    form.visualTargetModeId !== visual.targetModeId ||
    form.visualCaptureScopeId !== visual.captureScopeId ||
    form.visualRetentionHintId !== visual.retentionHintId ||
    form.visualSensitiveContentRisk !== visual.sensitiveContentRisk ||
    form.visualExpectedPage !== visual.expectedPage ||
    form.visualExpectedSignalsText !== visual.expectedSignalsText ||
    form.visualDisallowedSignalsText !== visual.disallowedSignalsText ||
    form.visualObservationFocusText !== visual.observationFocusText ||
    form.visualObservedNotesText !== visual.observedNotesText ||
    form.voiceLanguageCode !== voice.languageCode ||
    form.voiceAutoBriefEnabled !== voice.autoBriefEnabled ||
    form.voiceConfirmationEnabled !== voice.confirmationEnabled ||
    form.voiceSpokenFeedbackEnabled !== voice.spokenFeedbackEnabled ||
    form.voiceAmbientReadyEnabled !== voice.ambientReadyEnabled ||
    form.voiceMicrophoneName !== voice.microphoneName ||
    form.voiceSpeakerName !== voice.speakerName ||
    form.deepSelectedModeId !== deep.selectedModeId ||
    form.deepAppServerReadinessId !== deep.appServerReadinessId ||
    form.deepCloudTriggerReadinessId !== deep.cloudTriggerReadinessId ||
    form.deepDesktopFallbackAllowed !== deep.desktopFallbackAllowed ||
    form.deepAppServerNotes !== deep.appServerNotes ||
    form.deepCloudTriggerNotes !== deep.cloudTriggerNotes ||
    form.deepHandoffNotes !== deep.handoffNotes
  );
}

function App() {
  const [snapshot, setSnapshot] = useState<Snapshot>(mockSnapshot);
  const [controlDeck, setControlDeck] = useState<ControlDeck | null>(null);
  const [activityFeed, setActivityFeed] = useState<ActivityEntry[]>([]);
  const [lastWorkspaceSync, setLastWorkspaceSync] = useState("");
  const [connected, setConnected] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isActing, setIsActing] = useState(false);
  const [bridgeMessage, setBridgeMessage] = useState("web shell action bridge가 아직 실행되지 않았습니다.");
  const [briefingText, setBriefingText] = useState("");
  const [summaryText, setSummaryText] = useState("");
  const [isDeckOpen, setIsDeckOpen] = useState(false);
  const [activeDeckTab, setActiveDeckTab] = useState<DeckTab>("project");
  const [isDeckBusy, setIsDeckBusy] = useState(false);
  const [projectForm, setProjectForm] = useState<ProjectFormState>({
    projectSummary: "",
    targetOutcome: "",
    stepsText: "",
  });
  const [operationsForm, setOperationsForm] = useState<OperationsFormState>({
    selectedPresetId: "",
    selectedModeId: "",
    customInstruction: "",
    pollIntervalSec: 8,
    dryRun: true,
    selectedProfileId: "",
    reportCadenceId: "",
    reentryModeId: "",
    operatorNote: "",
  });
  const [promptDraft, setPromptDraft] = useState("");
  const [intelligenceForm, setIntelligenceForm] = useState<IntelligenceFormState>({
    judgmentEngineModeId: "",
    judgmentModelName: "",
    judgmentConfidenceThreshold: 0.6,
    judgmentMaxHistoryItems: 8,
    visualTargetModeId: "",
    visualCaptureScopeId: "",
    visualRetentionHintId: "",
    visualSensitiveContentRisk: "",
    visualExpectedPage: "",
    visualExpectedSignalsText: "",
    visualDisallowedSignalsText: "",
    visualObservationFocusText: "",
    visualObservedNotesText: "",
    voiceLanguageCode: "ko-KR",
    voiceAutoBriefEnabled: true,
    voiceConfirmationEnabled: true,
    voiceSpokenFeedbackEnabled: true,
    voiceAmbientReadyEnabled: false,
    voiceMicrophoneName: "",
    voiceSpeakerName: "",
    deepSelectedModeId: "",
    deepAppServerReadinessId: "",
    deepCloudTriggerReadinessId: "",
    deepDesktopFallbackAllowed: true,
    deepAppServerNotes: "",
    deepCloudTriggerNotes: "",
    deepHandoffNotes: "",
  });

  const apiBaseUrl = window.javisDesktop?.getApiBaseUrl?.() ?? "http://127.0.0.1:8765";

  const applyWorkspaceBundle = (bundle: WorkspaceBundle) => {
    const previousDeck = controlDeck;
    const keepProjectForm = isProjectDirty(projectForm, previousDeck);
    const keepOperationsForm = isOperationsDirty(operationsForm, previousDeck);
    const keepPromptDraft = isPromptDirty(promptDraft, previousDeck);
    const keepIntelligenceForm = isIntelligenceDirty(intelligenceForm, previousDeck);

    setSnapshot(bundle.snapshot);
    setControlDeck(bundle.controlDeck);
    setActivityFeed(bundle.activityFeed);
    setLastWorkspaceSync(bundle.generatedAt);

    if (!previousDeck || !keepProjectForm) {
      setProjectForm(projectFormFromDeck(bundle.controlDeck));
    }
    if (!previousDeck || !keepOperationsForm) {
      setOperationsForm(operationsFormFromDeck(bundle.controlDeck));
    }
    if (!previousDeck || !keepPromptDraft) {
      setPromptDraft(bundle.controlDeck.promptWorkbench.draftPrompt);
    }
    if (!previousDeck || !keepIntelligenceForm) {
      setIntelligenceForm(intelligenceFormFromDeck(bundle.controlDeck));
    }
  };

  const loadWorkspace = async () => {
    setIsRefreshing(true);
    try {
      const response = await fetch(`${apiBaseUrl}/api/workspace`);
      if (!response.ok) {
        throw new Error(`workspace request failed: ${response.status}`);
      }
      const bundle = (await response.json()) as WorkspaceBundle;
      startTransition(() => {
        applyWorkspaceBundle(bundle);
      });
      setConnected(true);
      setErrorMessage("");
    } catch (error) {
      setConnected(false);
      setErrorMessage(error instanceof Error ? error.message : "unknown error");
    } finally {
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    void loadWorkspace();
    const timer = window.setInterval(() => {
      void loadWorkspace();
    }, 10000);
    return () => {
      window.clearInterval(timer);
    };
  }, []);

  useEffect(() => {
    if (!isDeckOpen) {
      return;
    }
    void loadWorkspace();
  }, [isDeckOpen]);

  const runAction = async (actionId: string) => {
    if (actionId === "open_settings") {
      setIsDeckOpen((current) => !current);
      setBridgeMessage("Control Deck workspace를 열었습니다.");
      return;
    }

    setIsActing(true);
    try {
      const response = await fetch(`${apiBaseUrl}/api/action`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ actionId }),
      });

      const result = (await response.json()) as ActionResponse;
      if (!response.ok || !result.ok) {
        throw new Error(result.message || `action failed: ${response.status}`);
      }

      if (result.snapshot) {
        startTransition(() => {
          setSnapshot(result.snapshot as Snapshot);
        });
      }
      setConnected(true);
      setBridgeMessage(result.message);
      setErrorMessage("");

      const payload = result.payload ?? {};
      const maybeBriefing = payload.briefing;
      const maybeSummary = payload.summary;
      if (typeof maybeBriefing === "string") {
        setBriefingText(maybeBriefing);
      }
      if (typeof maybeSummary === "string") {
        setSummaryText(maybeSummary);
      }

      void loadWorkspace();
    } catch (error) {
      setBridgeMessage("액션 실행에 실패했습니다.");
      setErrorMessage(error instanceof Error ? error.message : "unknown error");
    } finally {
      setIsActing(false);
    }
  };

  const submitControlDeck = async (body: Record<string, unknown>) => {
    setIsDeckBusy(true);
    try {
      const response = await fetch(`${apiBaseUrl}/api/control-deck`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(body),
      });
      const result = (await response.json()) as ControlDeckResponse;
      if (!response.ok || !result.ok) {
        throw new Error(result.message || `control deck failed: ${response.status}`);
      }
      if (result.snapshot) {
        startTransition(() => {
          setSnapshot(result.snapshot as Snapshot);
        });
      }
      if (result.controlDeck) {
        startTransition(() => {
          setControlDeck(result.controlDeck as ControlDeck);
        });
      }
      setConnected(true);
      setBridgeMessage(result.message);
      setErrorMessage("");
      await loadWorkspace();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "unknown error");
      setBridgeMessage("Control Deck 저장에 실패했습니다.");
    } finally {
      setIsDeckBusy(false);
    }
  };

  const saveProjectEditor = async () => {
    await submitControlDeck({
      kind: "project",
      project: projectForm,
    });
  };

  const saveOperationsEditor = async () => {
    await submitControlDeck({
      kind: "operations",
      operations: {
        codexStrategy: {
          selectedPresetId: operationsForm.selectedPresetId,
          selectedModeId: operationsForm.selectedModeId,
          customInstruction: operationsForm.customInstruction,
        },
        automation: {
          pollIntervalSec: operationsForm.pollIntervalSec,
          dryRun: operationsForm.dryRun,
        },
        liveOps: {
          selectedProfileId: operationsForm.selectedProfileId,
          reportCadenceId: operationsForm.reportCadenceId,
          reentryModeId: operationsForm.reentryModeId,
          operatorNote: operationsForm.operatorNote,
        },
      },
    });
  };

  const savePromptDraft = async () => {
    await submitControlDeck({
      kind: "prompt",
      action: "save",
      draftPrompt: promptDraft,
    });
  };

  const resetPromptDraft = async () => {
    await submitControlDeck({
      kind: "prompt",
      action: "reset",
    });
  };

  const saveIntelligenceEditor = async () => {
    await submitControlDeck({
      kind: "intelligence",
      intelligence: {
        judgment: {
          engineModeId: intelligenceForm.judgmentEngineModeId,
          modelName: intelligenceForm.judgmentModelName,
          confidenceThreshold: intelligenceForm.judgmentConfidenceThreshold,
          maxHistoryItems: intelligenceForm.judgmentMaxHistoryItems,
        },
        visual: {
          targetModeId: intelligenceForm.visualTargetModeId,
          captureScopeId: intelligenceForm.visualCaptureScopeId,
          retentionHintId: intelligenceForm.visualRetentionHintId,
          sensitiveContentRisk: intelligenceForm.visualSensitiveContentRisk,
          expectedPage: intelligenceForm.visualExpectedPage,
          expectedSignalsText: intelligenceForm.visualExpectedSignalsText,
          disallowedSignalsText: intelligenceForm.visualDisallowedSignalsText,
          observationFocusText: intelligenceForm.visualObservationFocusText,
          observedNotesText: intelligenceForm.visualObservedNotesText,
        },
        voice: {
          languageCode: intelligenceForm.voiceLanguageCode,
          autoBriefEnabled: intelligenceForm.voiceAutoBriefEnabled,
          confirmationEnabled: intelligenceForm.voiceConfirmationEnabled,
          spokenFeedbackEnabled: intelligenceForm.voiceSpokenFeedbackEnabled,
          ambientReadyEnabled: intelligenceForm.voiceAmbientReadyEnabled,
          microphoneName: intelligenceForm.voiceMicrophoneName,
          speakerName: intelligenceForm.voiceSpeakerName,
        },
        deepIntegration: {
          selectedModeId: intelligenceForm.deepSelectedModeId,
          appServerReadinessId: intelligenceForm.deepAppServerReadinessId,
          cloudTriggerReadinessId: intelligenceForm.deepCloudTriggerReadinessId,
          desktopFallbackAllowed: intelligenceForm.deepDesktopFallbackAllowed,
          appServerNotes: intelligenceForm.deepAppServerNotes,
          cloudTriggerNotes: intelligenceForm.deepCloudTriggerNotes,
          handoffNotes: intelligenceForm.deepHandoffNotes,
        },
      },
    });
  };

  const restoreRecentProject = async (recentIndex: number) => {
    await submitControlDeck({
      kind: "recent_project",
      recentIndex,
    });
  };

  const progressPercent = Math.max(8, Math.round(snapshot.runtime.progress.ratio * 100));
  const deckStatus = isDeckBusy ? "SYNCING" : controlDeck ? "READY" : "LOCKED";
  const promptWorkbench = controlDeck?.promptWorkbench;
  const strategyOptions = controlDeck?.operationsEditor.codexStrategy;
  const liveOpsOptions = controlDeck?.operationsEditor.liveOps;
  const selectedPreset = strategyOptions
    ? findOption(strategyOptions.presetOptions, operationsForm.selectedPresetId)
    : undefined;
  const selectedMode = strategyOptions
    ? findOption(strategyOptions.modeOptions, operationsForm.selectedModeId)
    : undefined;
  const selectedProfile = liveOpsOptions
    ? findOption(liveOpsOptions.profileOptions, operationsForm.selectedProfileId)
    : undefined;
  const selectedCadence = liveOpsOptions
    ? findOption(liveOpsOptions.cadenceOptions, operationsForm.reportCadenceId)
    : undefined;
  const selectedReentry = liveOpsOptions
    ? findOption(liveOpsOptions.reentryOptions, operationsForm.reentryModeId)
    : undefined;
  const intelligenceStudio = controlDeck?.intelligenceStudio;
  const selectedJudgmentMode = intelligenceStudio
    ? findOption(intelligenceStudio.judgment.modeOptions, intelligenceForm.judgmentEngineModeId)
    : undefined;
  const selectedVisualTarget = intelligenceStudio
    ? findOption(intelligenceStudio.visual.targetModeOptions, intelligenceForm.visualTargetModeId)
    : undefined;
  const selectedVisualScope = intelligenceStudio
    ? findOption(intelligenceStudio.visual.captureScopeOptions, intelligenceForm.visualCaptureScopeId)
    : undefined;
  const selectedVisualRetention = intelligenceStudio
    ? findOption(intelligenceStudio.visual.retentionOptions, intelligenceForm.visualRetentionHintId)
    : undefined;
  const selectedDeepMode = intelligenceStudio
    ? findOption(intelligenceStudio.deepIntegration.modeOptions, intelligenceForm.deepSelectedModeId)
    : undefined;
  const selectedAppServerReadiness = intelligenceStudio
    ? findOption(intelligenceStudio.deepIntegration.readinessOptions, intelligenceForm.deepAppServerReadinessId)
    : undefined;
  const selectedCloudTriggerReadiness = intelligenceStudio
    ? findOption(intelligenceStudio.deepIntegration.readinessOptions, intelligenceForm.deepCloudTriggerReadinessId)
    : undefined;

  const projectDirty = isProjectDirty(projectForm, controlDeck);
  const operationsDirty = isOperationsDirty(operationsForm, controlDeck);
  const promptDirty = isPromptDirty(promptDraft, controlDeck);
  const intelligenceDirty = isIntelligenceDirty(intelligenceForm, controlDeck);
  const dirtyBadges = [
    projectDirty ? "PROJECT DRAFT" : null,
    operationsDirty ? "OPS DRAFT" : null,
    promptDirty ? "PROMPT DRAFT" : null,
    intelligenceDirty ? "INTEL DRAFT" : null,
  ].filter(Boolean) as string[];

  return (
    <div className="shell">
      <div className="shell__noise" />

      <header className="topbar">
        <div className="brand">
          <p className="eyebrow">JAVIS // LIVE SYNC WORKSPACE</p>
          <h1>실시간에 가깝게 동기화되는 Codex 운영 어시스턴트</h1>
          <p className="brand__summary">
            Phase 6에서는 판단, 시각, 음성, 딥 인티그레이션 설정까지 웹에서 다루는 Intelligence Studio를 엽니다.
          </p>
        </div>

        <div className="topbar__controls">
          <div className="status-strip">
            <span className={`pill ${connected ? "pill--good" : "pill--warn"}`}>
              {connected ? "ENGINE LINKED" : "DEMO SNAPSHOT"}
            </span>
            <span className="pill">{snapshot.surface.badgeLabel.toUpperCase()}</span>
            <span className="pill">{snapshot.codex.automationModeId.toUpperCase()}</span>
            <span className={`pill ${snapshot.runtime.autoRunning ? "pill--good" : ""}`}>
              {snapshot.runtime.autoRunning ? "AUTO LOOP" : "MANUAL MODE"}
            </span>
            <span className={`pill ${deckStatus === "READY" ? "pill--good" : deckStatus === "SYNCING" ? "pill--warn" : ""}`}>
              DECK {deckStatus}
            </span>
            <span className="pill">SYNC {formatSavedAt(lastWorkspaceSync || snapshot.generatedAt)}</span>
          </div>

          <div className="topbar__actions">
            <button className="ghost-button" onClick={() => void runAction("open_settings")} type="button">
              {isDeckOpen ? "Close Control Deck" : "Open Control Deck"}
            </button>
            <button className="ghost-button" onClick={() => void loadWorkspace()} type="button">
              {isRefreshing ? "Refreshing..." : "Refresh Workspace"}
            </button>
          </div>
        </div>
      </header>

      <main className="dashboard">
        <section className="hero card">
          <div className="hero__visual">
            <div className="hero__orb">
              <div className="hero__orb-core" />
              <div className="hero__orb-ring hero__orb-ring--one" />
              <div className="hero__orb-ring hero__orb-ring--two" />
            </div>
            <div className="hero__metrics">
              <div className="metric">
                <span>Progress</span>
                <strong>{snapshot.surface.progressLabel}</strong>
              </div>
              <div className="metric">
                <span>Risk</span>
                <strong>{snapshot.surface.riskLabel}</strong>
              </div>
              <div className="metric">
                <span>Workspace sync</span>
                <strong>{formatSavedAt(lastWorkspaceSync || snapshot.generatedAt)}</strong>
              </div>
            </div>
          </div>

          <div className="hero__content">
            <span className="hero__badge">{snapshot.surface.badgeLabel}</span>
            <h2>{snapshot.surface.title}</h2>
            <p className="hero__summary">{snapshot.surface.summary}</p>

            <div className="hero__detail-grid">
              <div className="detail-card">
                <span className="meta-label">왜 이런 상태인가</span>
                <strong>{snapshot.surface.reason}</strong>
              </div>
              <div className="detail-card">
                <span className="meta-label">지금 가장 좋은 다음 행동</span>
                <strong>{snapshot.surface.nextAction}</strong>
              </div>
            </div>
          </div>
        </section>

        <section className="column column--signals">
          <article className="card card--mission">
            <div className="card__header">
              <span className="card__eyebrow">Mission Brief</span>
              <span className="card__tag">{snapshot.app.engine.toUpperCase()}</span>
            </div>
            <h3>{snapshot.project.summary || "프로젝트 요약이 아직 없습니다."}</h3>
            <p>{snapshot.project.targetOutcome || "목표 결과를 입력하면 이 카드가 더 선명해집니다."}</p>
          </article>

          <article className="card card--signals-board">
            <div className="card__header">
              <span className="card__eyebrow">System Signals</span>
              <span className="card__tag">LIVE</span>
            </div>
            <div className="signal-stack">
              {snapshot.signals.map((signal) => (
                <div key={signal.label} className="signal-row">
                  <div>
                    <span className="signal-row__label">{signal.label}</span>
                    <strong>{signal.value}</strong>
                  </div>
                  <span className={`signal-dot signal-dot--${signal.tone}`} />
                </div>
              ))}
            </div>
          </article>

          <article className="card card--snapshot">
            <div className="card__header">
              <span className="card__eyebrow">Snapshot</span>
              <span className="card__tag">
                {snapshot.runtime.progress.current}/{snapshot.runtime.progress.total}
              </span>
            </div>
            <div className="meter">
              <div className="meter__fill" style={{ width: `${progressPercent}%` }} />
            </div>
            <p className="muted">저장 시각: {formatSavedAt(snapshot.runtime.savedAt)}</p>
            <p className="muted">{snapshot.surface.detailLabel}</p>
          </article>
        </section>

        <section className="column column--focus">
          <article className="card card--timeline">
            <div className="card__header">
              <span className="card__eyebrow">Operational Timeline</span>
              <span className="card__tag">PHASE 6</span>
            </div>
            <div className="timeline">
              {snapshot.queue.length === 0 ? (
                <p className="muted">단계 목록이 비어 있습니다. Control Deck 프로젝트 탭에서 마스터플랜을 먼저 넣어 주세요.</p>
              ) : (
                snapshot.queue.map((item) => (
                  <div key={`${item.title}-${item.index}`} className={`timeline__item timeline__item--${item.status}`}>
                    <div className="timeline__index">{item.index + 1}</div>
                    <div>
                      <p className="timeline__title">{item.title}</p>
                      <p className="timeline__caption">{item.displayLine}</p>
                    </div>
                  </div>
                ))
              )}
            </div>
          </article>

          <article className="card card--prompt">
            <div className="card__header">
              <span className="card__eyebrow">Prompt Preview</span>
              <span className="card__tag">{snapshot.promptPreview.source.toUpperCase()}</span>
            </div>
            <h3>{snapshot.promptPreview.stepTitle || "아직 선택된 단계가 없습니다."}</h3>
            <p>{snapshot.promptPreview.excerpt || "프롬프트 미리보기가 아직 비어 있습니다."}</p>
          </article>
        </section>

        <section className="column column--ops">
          <article className="card card--dock">
            <div className="card__header">
              <span className="card__eyebrow">Action Dock</span>
              <span className="card__tag">LIVE BRIDGE</span>
            </div>
            <div className="dock">
              {snapshot.surface.actions.map((action) => (
                <button
                  key={action.id}
                  className={`dock__button dock__button--${action.emphasis}`}
                  disabled={!action.enabled || isActing}
                  onClick={() => void runAction(action.id)}
                  type="button"
                >
                  <span>{action.label}</span>
                  <small>{action.id}</small>
                </button>
              ))}

              <button className="dock__button dock__button--utility" disabled={isActing} onClick={() => void runAction("start_auto")} type="button">
                <span>감시</span>
                <small>start_auto</small>
              </button>

              <button className="dock__button dock__button--utility" disabled={isActing} onClick={() => void runAction("refresh_windows")} type="button">
                <span>창 확인</span>
                <small>refresh_windows</small>
              </button>
            </div>
          </article>

          <article className="card card--bridge-status">
            <div className="card__header">
              <span className="card__eyebrow">Bridge Status</span>
              <span className={`card__tag ${connected ? "card__tag--good" : "card__tag--warn"}`}>
                {connected ? "CONNECTED" : "WAITING"}
              </span>
            </div>
            <p className="muted">
              {connected
                ? "workspace bundle과 action bridge를 함께 읽고 있습니다."
                : "지금은 fallback snapshot을 사용 중입니다. `python -m app.api.server`를 실행하면 실제 상태가 연결됩니다."}
            </p>
            <p className="bridge-line">{bridgeMessage}</p>
            {errorMessage ? <p className="error-line">{errorMessage}</p> : null}
          </article>

          <article className="card card--bridge-output">
            <div className="card__header">
              <span className="card__eyebrow">Bridge Output</span>
              <span className="card__tag">{isActing ? "RUNNING" : "IDLE"}</span>
            </div>
            <div className="bridge-output">
              <p>{briefingText || summaryText || "브리핑 또는 상태 요약이 여기에 표시됩니다."}</p>
            </div>
          </article>

          <article className="card card--feed">
            <div className="card__header">
              <span className="card__eyebrow">Ops Feed</span>
              <span className="card__tag">{activityFeed.length}</span>
            </div>
            <div className="activity-list activity-list--compact">
              {activityFeed.length === 0 ? (
                <p className="muted">아직 운영 로그가 없습니다.</p>
              ) : (
                activityFeed.slice(0, 5).map((entry, index) => (
                  <div key={`${entry.timestamp}-${index}`} className={`activity-item activity-item--${entry.tone}`}>
                    <div className="activity-item__meta">
                      <span>{entry.timestamp || "방금"}</span>
                    </div>
                    <p>{entry.message}</p>
                  </div>
                ))
              )}
            </div>
          </article>

          <article className="card card--recent">
            <div className="card__header">
              <span className="card__eyebrow">Recent Projects</span>
              <span className="card__tag">{snapshot.recentProjects.length}</span>
            </div>
            <div className="recent-list">
              {snapshot.recentProjects.length === 0 ? (
                <p className="muted">아직 최근 프로젝트가 없습니다.</p>
              ) : (
                snapshot.recentProjects.map((item) => (
                  <div key={`${item.title}-${item.savedAt}`} className="recent-item">
                    <div>
                      <strong>{item.title}</strong>
                      <span>{formatSavedAt(item.savedAt)}</span>
                    </div>
                    <b>
                      {item.progress.current} / {item.progress.total}
                    </b>
                  </div>
                ))
              )}
            </div>
          </article>
        </section>

        <section className="deck-grid">
          {snapshot.deckSections.map((section) => (
            <article key={section.id} className="card deck-card">
              <div className="card__header">
                <span className="card__eyebrow">{section.title}</span>
                <span className={`card__tag card__tag--${section.tone}`}>{section.tone.toUpperCase()}</span>
              </div>
              <h3>{section.value}</h3>
              <p>{section.description}</p>
            </article>
          ))}
        </section>
      </main>

      {isDeckOpen ? (
        <div className="drawer-backdrop" onClick={() => setIsDeckOpen(false)} role="presentation">
          <aside className="drawer card drawer--workspace" onClick={(event) => event.stopPropagation()}>
            <div className="drawer__shell">
              <div className="drawer__nav">
                <div className="drawer__nav-head">
                  <span className="card__eyebrow">Control Deck</span>
                  <strong>Live Sync Workspace</strong>
                  <p>프로젝트 편집과 운영 설정 사이를 왔다 갔다 할 때도 자동 동기화가 draft를 함부로 덮어쓰지 않습니다.</p>
                </div>

                <div className="drawer__nav-tabs">
                  {deckTabs.map((tab) => (
                    <button
                      key={tab.id}
                      className={`drawer__nav-button ${activeDeckTab === tab.id ? "drawer__nav-button--active" : ""}`}
                      onClick={() => setActiveDeckTab(tab.id)}
                      type="button"
                    >
                      <span>{tab.label}</span>
                      <small>{tab.caption}</small>
                    </button>
                  ))}
                </div>
              </div>

              <div className="drawer__panel">
                <div className="drawer__panel-head">
                  <div>
                    <span className="card__eyebrow">Workspace Beta</span>
                    <h2>Control Deck Workspace</h2>
                    <p>workspace bundle로 snapshot, deck, activity를 함께 읽고, 편집 중인 영역은 local draft를 우선 보존합니다.</p>
                  </div>
                  <div className="drawer__panel-actions">
                    {dirtyBadges.length > 0 ? (
                      dirtyBadges.map((badge) => (
                        <span key={badge} className="pill pill--warn">
                          {badge}
                        </span>
                      ))
                    ) : (
                      <span className="pill pill--good">ALL CLEAN</span>
                    )}
                    <span className={`pill ${deckStatus === "READY" ? "pill--good" : deckStatus === "SYNCING" ? "pill--warn" : ""}`}>
                      {deckStatus}
                    </span>
                    <button className="ghost-button ghost-button--small" onClick={() => void loadWorkspace()} type="button">
                      {isRefreshing || isDeckBusy ? "Syncing..." : "Reload Workspace"}
                    </button>
                    <button className="ghost-button ghost-button--small" onClick={() => setIsDeckOpen(false)} type="button">
                      Close
                    </button>
                  </div>
                </div>

                <div className={`sync-banner ${dirtyBadges.length > 0 ? "sync-banner--warn" : "sync-banner--good"}`}>
                  <strong>{dirtyBadges.length > 0 ? "로컬 편집 보존 중" : "workspace 자동 동기화 정상"}</strong>
                  <p>
                    {dirtyBadges.length > 0
                      ? "현재 수정 중인 섹션은 자동 새로고침이 바로 덮어쓰지 않습니다. 저장하거나 원문으로 되돌리면 다시 깨끗한 동기화 상태로 돌아갑니다."
                      : `마지막 workspace sync: ${formatSavedAt(lastWorkspaceSync || snapshot.generatedAt)}`}
                  </p>
                </div>

                {activeDeckTab === "project" ? (
                  <div className="workspace-grid">
                    <label className="form-field form-field--full">
                      <span className="meta-label">Project Summary</span>
                      <textarea
                        value={projectForm.projectSummary}
                        onChange={(event) =>
                          setProjectForm((current) => ({ ...current, projectSummary: event.target.value }))
                        }
                      />
                    </label>

                    <label className="form-field form-field--full">
                      <span className="meta-label">Target Outcome</span>
                      <textarea
                        value={projectForm.targetOutcome}
                        onChange={(event) =>
                          setProjectForm((current) => ({ ...current, targetOutcome: event.target.value }))
                        }
                      />
                    </label>

                    <label className="form-field form-field--full">
                      <span className="meta-label">Steps / Masterplan</span>
                      <textarea
                        className="form-field__textarea--steps"
                        value={projectForm.stepsText}
                        onChange={(event) =>
                          setProjectForm((current) => ({ ...current, stepsText: event.target.value }))
                        }
                      />
                    </label>

                    <div className="workspace-stats form-field--full">
                      <div className="stat-chip">
                        <span>단계 수</span>
                        <strong>{controlDeck?.projectEditor.stepCount ?? 0}</strong>
                      </div>
                      <div className="stat-chip">
                        <span>다음 인덱스</span>
                        <strong>{(controlDeck?.projectEditor.nextStepIndex ?? 0) + 1}</strong>
                      </div>
                      <div className="stat-chip">
                        <span>현재 진행</span>
                        <strong>{snapshot.surface.progressLabel}</strong>
                      </div>
                    </div>

                    <div className="workspace-actions form-field--full">
                      <button
                        className="panel-button panel-button--primary"
                        disabled={!controlDeck || isDeckBusy}
                        onClick={() => void saveProjectEditor()}
                        type="button"
                      >
                        프로젝트 계획 저장
                      </button>
                      <p>단계 목록을 저장하면 timeline, prompt preview, launch-ready prompt가 즉시 다시 계산됩니다.</p>
                    </div>
                  </div>
                ) : null}

                {activeDeckTab === "operations" ? (
                  <div className="workspace-grid">
                    <label className="form-field">
                      <span className="meta-label">Codex Preset</span>
                      <select
                        value={operationsForm.selectedPresetId}
                        onChange={(event) =>
                          setOperationsForm((current) => ({ ...current, selectedPresetId: event.target.value }))
                        }
                      >
                        {(strategyOptions?.presetOptions ?? []).map((option) => (
                          <option key={option.id} value={option.id}>
                            {option.title}
                          </option>
                        ))}
                      </select>
                      <small>{selectedPreset?.summary ?? "현재 프로젝트에 맞는 운영 시나리오를 고릅니다."}</small>
                    </label>

                    <label className="form-field">
                      <span className="meta-label">Automation Mode</span>
                      <select
                        value={operationsForm.selectedModeId}
                        onChange={(event) =>
                          setOperationsForm((current) => ({ ...current, selectedModeId: event.target.value }))
                        }
                      >
                        {(strategyOptions?.modeOptions ?? []).map((option) => (
                          <option key={option.id} value={option.id}>
                            {option.title}
                          </option>
                        ))}
                      </select>
                      <small>{selectedMode?.summary ?? "same thread / thread automation / project automation 경로를 고릅니다."}</small>
                    </label>

                    <label className="form-field">
                      <span className="meta-label">Poll Interval (sec)</span>
                      <input
                        type="number"
                        min={1}
                        max={3600}
                        value={operationsForm.pollIntervalSec}
                        onChange={(event) =>
                          setOperationsForm((current) => ({
                            ...current,
                            pollIntervalSec: Number(event.target.value || 0),
                          }))
                        }
                      />
                      <small>live sync와 별개로 Python 자동 감시가 다시 움직일 때의 poll cadence입니다.</small>
                    </label>

                    <div className="form-field form-field--toggle">
                      <span className="meta-label">Dry Run</span>
                      <label className="toggle-row">
                        <input
                          checked={operationsForm.dryRun}
                          onChange={(event) =>
                            setOperationsForm((current) => ({ ...current, dryRun: event.target.checked }))
                          }
                          type="checkbox"
                        />
                        <span>{operationsForm.dryRun ? "실제 전송 없이 미리보기만" : "실제 전송 허용"}</span>
                      </label>
                      <small>실사용 초반에는 dry run 유지 후, 충분히 믿어질 때 실제 전송으로 내리는 편이 안전합니다.</small>
                    </div>

                    <label className="form-field form-field--full">
                      <span className="meta-label">Follow-up Memo</span>
                      <textarea
                        value={operationsForm.customInstruction}
                        onChange={(event) =>
                          setOperationsForm((current) => ({ ...current, customInstruction: event.target.value }))
                        }
                      />
                    </label>

                    <label className="form-field">
                      <span className="meta-label">Live Ops Profile</span>
                      <select
                        value={operationsForm.selectedProfileId}
                        onChange={(event) =>
                          setOperationsForm((current) => ({ ...current, selectedProfileId: event.target.value }))
                        }
                      >
                        {(liveOpsOptions?.profileOptions ?? []).map((option) => (
                          <option key={option.id} value={option.id}>
                            {option.title}
                          </option>
                        ))}
                      </select>
                      <small>{selectedProfile?.summary ?? "운영 성향을 고릅니다."}</small>
                    </label>

                    <label className="form-field">
                      <span className="meta-label">Report Cadence</span>
                      <select
                        value={operationsForm.reportCadenceId}
                        onChange={(event) =>
                          setOperationsForm((current) => ({ ...current, reportCadenceId: event.target.value }))
                        }
                      >
                        {(liveOpsOptions?.cadenceOptions ?? []).map((option) => (
                          <option key={option.id} value={option.id}>
                            {option.title}
                          </option>
                        ))}
                      </select>
                      <small>{selectedCadence?.summary ?? "언제 운영 브리프를 남길지 정합니다."}</small>
                    </label>

                    <label className="form-field">
                      <span className="meta-label">Re-entry Mode</span>
                      <select
                        value={operationsForm.reentryModeId}
                        onChange={(event) =>
                          setOperationsForm((current) => ({ ...current, reentryModeId: event.target.value }))
                        }
                      >
                        {(liveOpsOptions?.reentryOptions ?? []).map((option) => (
                          <option key={option.id} value={option.id}>
                            {option.title}
                          </option>
                        ))}
                      </select>
                      <small>{selectedReentry?.summary ?? "결과를 어디서 다시 읽고 이어갈지 정합니다."}</small>
                    </label>

                    <label className="form-field form-field--full">
                      <span className="meta-label">Operator Note</span>
                      <textarea
                        value={operationsForm.operatorNote}
                        onChange={(event) =>
                          setOperationsForm((current) => ({ ...current, operatorNote: event.target.value }))
                        }
                      />
                    </label>

                    <div className="workspace-actions form-field--full">
                      <button
                        className="panel-button panel-button--primary"
                        disabled={!controlDeck || isDeckBusy}
                        onClick={() => void saveOperationsEditor()}
                        type="button"
                      >
                        운영 설정 저장
                      </button>
                      <p>저장하면 launch prompt, runbook, runboard, shift brief가 현재 선택값 기준으로 즉시 새로 계산됩니다.</p>
                    </div>

                    <div className="runbook-grid form-field--full">
                      <article className="runbook-card">
                        <div className="card__header">
                          <span className="card__eyebrow">Launch-ready Prompt</span>
                          <span className="card__tag">COPY SOURCE</span>
                        </div>
                        <pre>{controlDeck?.runbooks.launchPrompt || "아직 launch prompt를 불러오지 못했습니다."}</pre>
                      </article>

                      <article className="runbook-card">
                        <div className="card__header">
                          <span className="card__eyebrow">Runbook / Handoff</span>
                          <span className="card__tag">OPERATIONS</span>
                        </div>
                        <pre>{controlDeck?.runbooks.runbook || "운영 런북이 아직 없습니다."}</pre>
                      </article>

                      <article className="runbook-card">
                        <div className="card__header">
                          <span className="card__eyebrow">Automation Runboard</span>
                          <span className="card__tag">LIVE</span>
                        </div>
                        <pre>{controlDeck?.runbooks.runboard || "runboard 데이터가 아직 없습니다."}</pre>
                      </article>

                      <article className="runbook-card">
                        <div className="card__header">
                          <span className="card__eyebrow">Shift Brief</span>
                          <span className="card__tag">RE-ENTRY</span>
                        </div>
                        <pre>{controlDeck?.runbooks.shiftBrief || "shift brief 데이터가 아직 없습니다."}</pre>
                      </article>
                    </div>
                  </div>
                ) : null}

                {activeDeckTab === "prompt" ? (
                  <div className="workspace-grid">
                    {promptWorkbench?.hasStep ? (
                      <>
                        <div className="workspace-stats form-field--full">
                          <div className="stat-chip">
                            <span>현재 단계</span>
                            <strong>{promptWorkbench.stepTitle}</strong>
                          </div>
                          <div className="stat-chip">
                            <span>소스</span>
                            <strong>{promptWorkbench.source}</strong>
                          </div>
                          <div className="stat-chip">
                            <span>상태</span>
                            <strong>{promptDirty ? "local draft" : "clean sync"}</strong>
                          </div>
                        </div>

                        <article className="runbook-card form-field--full">
                          <div className="card__header">
                            <span className="card__eyebrow">Generated Prompt</span>
                            <span className="card__tag">READ ONLY</span>
                          </div>
                          <pre>{controlDeck?.promptWorkbench.generatedPrompt}</pre>
                        </article>

                        <label className="form-field form-field--full">
                          <span className="meta-label">Draft Prompt</span>
                          <textarea
                            className="form-field__textarea--prompt"
                            value={promptDraft}
                            onChange={(event) => setPromptDraft(event.target.value)}
                          />
                        </label>

                        <div className="workspace-actions form-field--full">
                          <button
                            className="panel-button panel-button--primary"
                            disabled={!controlDeck || isDeckBusy}
                            onClick={() => void savePromptDraft()}
                            type="button"
                          >
                            draft 저장
                          </button>
                          <button className="panel-button" disabled={!controlDeck || isDeckBusy} onClick={() => void resetPromptDraft()} type="button">
                            원문으로 되돌리기
                          </button>
                          <p>live sync 중에도 dirty 상태일 땐 local draft를 우선 보존하고, 저장하면 다시 clean sync 상태로 돌아갑니다.</p>
                        </div>
                      </>
                    ) : (
                      <article className="runbook-card form-field--full">
                        <div className="card__header">
                          <span className="card__eyebrow">Prompt Workbench</span>
                          <span className="card__tag">EMPTY</span>
                        </div>
                        <p className="muted">현재 편집 가능한 단계 프롬프트가 없습니다. 프로젝트 계획 저장 후 현재 단계가 생기면 자동으로 준비됩니다.</p>
                      </article>
                    )}
                  </div>
                ) : null}

                {activeDeckTab === "intelligence" ? (
                  <div className="studio-stack">
                    <section className="studio-section">
                      <div className="studio-section__head">
                        <span className="card__eyebrow">Judgment Studio</span>
                        <h3>판단 엔진과 최근 의사결정</h3>
                        <p>continue / pause / ask_user 기준을 조정하고, 최근 판단 결과와 검증 메모를 함께 봅니다.</p>
                      </div>

                      <div className="workspace-grid">
                        <label className="form-field">
                          <span className="meta-label">Engine Mode</span>
                          <select
                            value={intelligenceForm.judgmentEngineModeId}
                            onChange={(event) =>
                              setIntelligenceForm((current) => ({
                                ...current,
                                judgmentEngineModeId: event.target.value,
                              }))
                            }
                          >
                            {(intelligenceStudio?.judgment.modeOptions ?? []).map((option) => (
                              <option key={option.id} value={option.id}>
                                {option.title}
                              </option>
                            ))}
                          </select>
                          <small>{selectedJudgmentMode?.summary ?? "판단 엔진 동작 모드를 고릅니다."}</small>
                        </label>

                        <label className="form-field">
                          <span className="meta-label">Model Name</span>
                          <input
                            type="text"
                            value={intelligenceForm.judgmentModelName}
                            onChange={(event) =>
                              setIntelligenceForm((current) => ({
                                ...current,
                                judgmentModelName: event.target.value,
                              }))
                            }
                          />
                          <small>실제 API 연결 전에도 어떤 모델을 기준으로 운영할지 메모처럼 유지합니다.</small>
                        </label>

                        <label className="form-field">
                          <span className="meta-label">Confidence Threshold</span>
                          <input
                            type="number"
                            min={0}
                            max={1}
                            step={0.05}
                            value={intelligenceForm.judgmentConfidenceThreshold}
                            onChange={(event) =>
                              setIntelligenceForm((current) => ({
                                ...current,
                                judgmentConfidenceThreshold: Number(event.target.value || 0),
                              }))
                            }
                          />
                          <small>현재 기준: {Math.round(intelligenceForm.judgmentConfidenceThreshold * 100)}%</small>
                        </label>

                        <label className="form-field">
                          <span className="meta-label">History Depth</span>
                          <input
                            type="number"
                            min={1}
                            max={20}
                            value={intelligenceForm.judgmentMaxHistoryItems}
                            onChange={(event) =>
                              setIntelligenceForm((current) => ({
                                ...current,
                                judgmentMaxHistoryItems: Number(event.target.value || 1),
                              }))
                            }
                          />
                          <small>최근 판단 이력을 몇 개까지 유지할지 정합니다.</small>
                        </label>

                        <div className="workspace-stats form-field--full">
                          <div className="stat-chip">
                            <span>최근 판단</span>
                            <strong>{intelligenceStudio?.judgment.lastResult.decision || "없음"}</strong>
                          </div>
                          <div className="stat-chip">
                            <span>Confidence</span>
                            <strong>{(intelligenceStudio?.judgment.lastResult.confidence ?? 0).toFixed(2)}</strong>
                          </div>
                          <div className="stat-chip">
                            <span>Risk</span>
                            <strong>{intelligenceStudio?.judgment.lastResult.riskLevel || "unknown"}</strong>
                          </div>
                        </div>

                        <div className="runbook-grid form-field--full">
                          <article className="runbook-card">
                            <div className="card__header">
                              <span className="card__eyebrow">Judgment Timeline</span>
                              <span className="card__tag">LIVE</span>
                            </div>
                            <pre>{intelligenceStudio?.judgment.timeline || "아직 판단 타임라인이 없습니다."}</pre>
                          </article>

                          <article className="runbook-card">
                            <div className="card__header">
                              <span className="card__eyebrow">Validation Notes</span>
                              <span className="card__tag">
                                {intelligenceStudio?.judgment.lastResult.validationNotes.length ?? 0}
                              </span>
                            </div>
                            <pre>
                              {(intelligenceStudio?.judgment.lastResult.validationNotes ?? []).join("\n") ||
                                "검증 메모가 아직 없습니다."}
                            </pre>
                          </article>
                        </div>
                      </div>
                    </section>

                    <section className="studio-section">
                      <div className="studio-section__head">
                        <span className="card__eyebrow">Visual Studio</span>
                        <h3>시각 감독 기준과 최근 시각 근거</h3>
                        <p>Codex 창과 브라우저 화면을 언제, 어떻게 읽을지 정하고 최근 contradiction 결과를 함께 확인합니다.</p>
                      </div>

                      <div className="workspace-grid">
                        <label className="form-field">
                          <span className="meta-label">Target Mode</span>
                          <select
                            value={intelligenceForm.visualTargetModeId}
                            onChange={(event) =>
                              setIntelligenceForm((current) => ({
                                ...current,
                                visualTargetModeId: event.target.value,
                              }))
                            }
                          >
                            {(intelligenceStudio?.visual.targetModeOptions ?? []).map((option) => (
                              <option key={option.id} value={option.id}>
                                {option.title}
                              </option>
                            ))}
                          </select>
                          <small>{selectedVisualTarget?.summary ?? "어떤 화면을 우선 읽을지 정합니다."}</small>
                        </label>

                        <label className="form-field">
                          <span className="meta-label">Capture Scope</span>
                          <select
                            value={intelligenceForm.visualCaptureScopeId}
                            onChange={(event) =>
                              setIntelligenceForm((current) => ({
                                ...current,
                                visualCaptureScopeId: event.target.value,
                              }))
                            }
                          >
                            {(intelligenceStudio?.visual.captureScopeOptions ?? []).map((option) => (
                              <option key={option.id} value={option.id}>
                                {option.title}
                              </option>
                            ))}
                          </select>
                          <small>{selectedVisualScope?.summary ?? "화면 캡처 범위를 조정합니다."}</small>
                        </label>

                        <label className="form-field">
                          <span className="meta-label">Retention Hint</span>
                          <select
                            value={intelligenceForm.visualRetentionHintId}
                            onChange={(event) =>
                              setIntelligenceForm((current) => ({
                                ...current,
                                visualRetentionHintId: event.target.value,
                              }))
                            }
                          >
                            {(intelligenceStudio?.visual.retentionOptions ?? []).map((option) => (
                              <option key={option.id} value={option.id}>
                                {option.title}
                              </option>
                            ))}
                          </select>
                          <small>{selectedVisualRetention?.summary ?? "시각 근거 유지 정책입니다."}</small>
                        </label>

                        <label className="form-field">
                          <span className="meta-label">Sensitive Content Risk</span>
                          <input
                            type="text"
                            value={intelligenceForm.visualSensitiveContentRisk}
                            onChange={(event) =>
                              setIntelligenceForm((current) => ({
                                ...current,
                                visualSensitiveContentRisk: event.target.value,
                              }))
                            }
                          />
                          <small>예: low / medium / high</small>
                        </label>

                        <label className="form-field form-field--full">
                          <span className="meta-label">Expected Page</span>
                          <textarea
                            value={intelligenceForm.visualExpectedPage}
                            onChange={(event) =>
                              setIntelligenceForm((current) => ({
                                ...current,
                                visualExpectedPage: event.target.value,
                              }))
                            }
                          />
                        </label>

                        <label className="form-field">
                          <span className="meta-label">Expected Signals</span>
                          <textarea
                            value={intelligenceForm.visualExpectedSignalsText}
                            onChange={(event) =>
                              setIntelligenceForm((current) => ({
                                ...current,
                                visualExpectedSignalsText: event.target.value,
                              }))
                            }
                          />
                        </label>

                        <label className="form-field">
                          <span className="meta-label">Disallowed Signals</span>
                          <textarea
                            value={intelligenceForm.visualDisallowedSignalsText}
                            onChange={(event) =>
                              setIntelligenceForm((current) => ({
                                ...current,
                                visualDisallowedSignalsText: event.target.value,
                              }))
                            }
                          />
                        </label>

                        <label className="form-field">
                          <span className="meta-label">Observation Focus</span>
                          <textarea
                            value={intelligenceForm.visualObservationFocusText}
                            onChange={(event) =>
                              setIntelligenceForm((current) => ({
                                ...current,
                                visualObservationFocusText: event.target.value,
                              }))
                            }
                          />
                        </label>

                        <label className="form-field">
                          <span className="meta-label">Observed Notes</span>
                          <textarea
                            value={intelligenceForm.visualObservedNotesText}
                            onChange={(event) =>
                              setIntelligenceForm((current) => ({
                                ...current,
                                visualObservedNotesText: event.target.value,
                              }))
                            }
                          />
                        </label>

                        <div className="runbook-grid form-field--full">
                          <article className="runbook-card">
                            <div className="card__header">
                              <span className="card__eyebrow">Visual Timeline</span>
                              <span className="card__tag">EVIDENCE</span>
                            </div>
                            <pre>{intelligenceStudio?.visual.timeline || "아직 시각 타임라인이 없습니다."}</pre>
                          </article>

                          <article className="runbook-card">
                            <div className="card__header">
                              <span className="card__eyebrow">Latest Visual Result</span>
                              <span className="card__tag">
                                {intelligenceStudio?.visual.lastResult.contradictionLevel || "none"}
                              </span>
                            </div>
                            <pre>
                              {[
                                `target: ${intelligenceStudio?.visual.lastResult.targetLabel || "none"}`,
                                `hint: ${intelligenceStudio?.visual.lastResult.decisionHint || "continue"}`,
                                `message: ${intelligenceStudio?.visual.lastResult.messageToUser || "없음"}`,
                                `observed: ${intelligenceStudio?.visual.lastResult.observedSummary || "없음"}`,
                              ].join("\n")}
                            </pre>
                          </article>
                        </div>
                      </div>
                    </section>

                    <section className="studio-section">
                      <div className="studio-section__head">
                        <span className="card__eyebrow">Voice + Integration Studio</span>
                        <h3>음성 동작과 딥 인티그레이션 경계 설정</h3>
                        <p>브리핑/확인 게이트와 App Server, cloud trigger, desktop fallback 경계를 같이 정리합니다.</p>
                      </div>

                      <div className="workspace-grid">
                        <label className="form-field">
                          <span className="meta-label">Language</span>
                          <input
                            type="text"
                            value={intelligenceForm.voiceLanguageCode}
                            onChange={(event) =>
                              setIntelligenceForm((current) => ({
                                ...current,
                                voiceLanguageCode: event.target.value,
                              }))
                            }
                          />
                        </label>

                        <label className="form-field">
                          <span className="meta-label">Microphone</span>
                          <input
                            type="text"
                            value={intelligenceForm.voiceMicrophoneName}
                            onChange={(event) =>
                              setIntelligenceForm((current) => ({
                                ...current,
                                voiceMicrophoneName: event.target.value,
                              }))
                            }
                          />
                        </label>

                        <label className="form-field">
                          <span className="meta-label">Speaker</span>
                          <input
                            type="text"
                            value={intelligenceForm.voiceSpeakerName}
                            onChange={(event) =>
                              setIntelligenceForm((current) => ({
                                ...current,
                                voiceSpeakerName: event.target.value,
                              }))
                            }
                          />
                        </label>

                        <div className="form-field form-field--full">
                          <span className="meta-label">Voice Flags</span>
                          <div className="checkbox-grid">
                            <label className="toggle-row">
                              <input
                                checked={intelligenceForm.voiceAutoBriefEnabled}
                                onChange={(event) =>
                                  setIntelligenceForm((current) => ({
                                    ...current,
                                    voiceAutoBriefEnabled: event.target.checked,
                                  }))
                                }
                                type="checkbox"
                              />
                              <span>자동 브리핑</span>
                            </label>
                            <label className="toggle-row">
                              <input
                                checked={intelligenceForm.voiceConfirmationEnabled}
                                onChange={(event) =>
                                  setIntelligenceForm((current) => ({
                                    ...current,
                                    voiceConfirmationEnabled: event.target.checked,
                                  }))
                                }
                                type="checkbox"
                              />
                              <span>확인 게이트</span>
                            </label>
                            <label className="toggle-row">
                              <input
                                checked={intelligenceForm.voiceSpokenFeedbackEnabled}
                                onChange={(event) =>
                                  setIntelligenceForm((current) => ({
                                    ...current,
                                    voiceSpokenFeedbackEnabled: event.target.checked,
                                  }))
                                }
                                type="checkbox"
                              />
                              <span>음성 피드백</span>
                            </label>
                            <label className="toggle-row">
                              <input
                                checked={intelligenceForm.voiceAmbientReadyEnabled}
                                onChange={(event) =>
                                  setIntelligenceForm((current) => ({
                                    ...current,
                                    voiceAmbientReadyEnabled: event.target.checked,
                                  }))
                                }
                                type="checkbox"
                              />
                              <span>Ambient ready</span>
                            </label>
                          </div>
                        </div>

                        <label className="form-field">
                          <span className="meta-label">Integration Mode</span>
                          <select
                            value={intelligenceForm.deepSelectedModeId}
                            onChange={(event) =>
                              setIntelligenceForm((current) => ({
                                ...current,
                                deepSelectedModeId: event.target.value,
                              }))
                            }
                          >
                            {(intelligenceStudio?.deepIntegration.modeOptions ?? []).map((option) => (
                              <option key={option.id} value={option.id}>
                                {option.title}
                              </option>
                            ))}
                          </select>
                          <small>{selectedDeepMode?.summary ?? "현재 통합 경로를 선택합니다."}</small>
                        </label>

                        <label className="form-field">
                          <span className="meta-label">App Server Readiness</span>
                          <select
                            value={intelligenceForm.deepAppServerReadinessId}
                            onChange={(event) =>
                              setIntelligenceForm((current) => ({
                                ...current,
                                deepAppServerReadinessId: event.target.value,
                              }))
                            }
                          >
                            {(intelligenceStudio?.deepIntegration.readinessOptions ?? []).map((option) => (
                              <option key={option.id} value={option.id}>
                                {option.title}
                              </option>
                            ))}
                          </select>
                          <small>{selectedAppServerReadiness?.summary ?? "App Server 준비 수준입니다."}</small>
                        </label>

                        <label className="form-field">
                          <span className="meta-label">Cloud Trigger Readiness</span>
                          <select
                            value={intelligenceForm.deepCloudTriggerReadinessId}
                            onChange={(event) =>
                              setIntelligenceForm((current) => ({
                                ...current,
                                deepCloudTriggerReadinessId: event.target.value,
                              }))
                            }
                          >
                            {(intelligenceStudio?.deepIntegration.readinessOptions ?? []).map((option) => (
                              <option key={option.id} value={option.id}>
                                {option.title}
                              </option>
                            ))}
                          </select>
                          <small>{selectedCloudTriggerReadiness?.summary ?? "Cloud trigger 준비 수준입니다."}</small>
                        </label>

                        <div className="form-field form-field--toggle">
                          <span className="meta-label">Desktop Fallback</span>
                          <label className="toggle-row">
                            <input
                              checked={intelligenceForm.deepDesktopFallbackAllowed}
                              onChange={(event) =>
                                setIntelligenceForm((current) => ({
                                  ...current,
                                  deepDesktopFallbackAllowed: event.target.checked,
                                }))
                              }
                              type="checkbox"
                            />
                            <span>{intelligenceForm.deepDesktopFallbackAllowed ? "허용" : "차단"}</span>
                          </label>
                          <small>native 경로가 막혔을 때 desktop fallback을 열어둘지 정합니다.</small>
                        </div>

                        <label className="form-field">
                          <span className="meta-label">App Server Notes</span>
                          <textarea
                            value={intelligenceForm.deepAppServerNotes}
                            onChange={(event) =>
                              setIntelligenceForm((current) => ({
                                ...current,
                                deepAppServerNotes: event.target.value,
                              }))
                            }
                          />
                        </label>

                        <label className="form-field">
                          <span className="meta-label">Cloud Trigger Notes</span>
                          <textarea
                            value={intelligenceForm.deepCloudTriggerNotes}
                            onChange={(event) =>
                              setIntelligenceForm((current) => ({
                                ...current,
                                deepCloudTriggerNotes: event.target.value,
                              }))
                            }
                          />
                        </label>

                        <label className="form-field form-field--full">
                          <span className="meta-label">Handoff Notes</span>
                          <textarea
                            value={intelligenceForm.deepHandoffNotes}
                            onChange={(event) =>
                              setIntelligenceForm((current) => ({
                                ...current,
                                deepHandoffNotes: event.target.value,
                              }))
                            }
                          />
                        </label>

                        <div className="runbook-grid form-field--full">
                          <article className="runbook-card">
                            <div className="card__header">
                              <span className="card__eyebrow">Voice Timeline</span>
                              <span className="card__tag">VOICE</span>
                            </div>
                            <pre>{intelligenceStudio?.voice.timeline || "아직 voice timeline이 없습니다."}</pre>
                          </article>

                          <article className="runbook-card">
                            <div className="card__header">
                              <span className="card__eyebrow">Capability Registry</span>
                              <span className="card__tag">INTEGRATION</span>
                            </div>
                            <pre>
                              {intelligenceStudio?.deepIntegration.capabilityRegistry || "registry가 아직 비어 있습니다."}
                            </pre>
                          </article>

                          <article className="runbook-card">
                            <div className="card__header">
                              <span className="card__eyebrow">Cross-surface Handoff</span>
                              <span className="card__tag">HANDOFF</span>
                            </div>
                            <pre>
                              {intelligenceStudio?.deepIntegration.crossSurfaceHandoff ||
                                "handoff bundle이 아직 없습니다."}
                            </pre>
                          </article>

                          <article className="runbook-card">
                            <div className="card__header">
                              <span className="card__eyebrow">Observability Report</span>
                              <span className="card__tag">WATCH</span>
                            </div>
                            <pre>
                              {intelligenceStudio?.deepIntegration.observabilityReport ||
                                "observability report가 아직 없습니다."}
                            </pre>
                          </article>
                        </div>

                        <div className="workspace-actions form-field--full">
                          <button
                            className="panel-button panel-button--primary"
                            disabled={!controlDeck || isDeckBusy}
                            onClick={() => void saveIntelligenceEditor()}
                            type="button"
                          >
                            Intelligence 저장
                          </button>
                          <p>판단/시각/음성/딥 인티그레이션 draft를 한 번에 저장하고, workspace bundle이 새 기준으로 다시 동기화됩니다.</p>
                        </div>
                      </div>
                    </section>
                  </div>
                ) : null}

                {activeDeckTab === "activity" ? (
                  <div className="workspace-grid">
                    <div className="workspace-stats form-field--full">
                      <div className="stat-chip">
                        <span>최근 feed 수</span>
                        <strong>{activityFeed.length}</strong>
                      </div>
                      <div className="stat-chip">
                        <span>현재 loop</span>
                        <strong>{snapshot.runtime.autoRunning ? "auto running" : "manual"}</strong>
                      </div>
                      <div className="stat-chip">
                        <span>마지막 sync</span>
                        <strong>{formatSavedAt(lastWorkspaceSync || snapshot.generatedAt)}</strong>
                      </div>
                    </div>

                    <article className="runbook-card form-field--full">
                      <div className="card__header">
                        <span className="card__eyebrow">Activity Timeline</span>
                        <span className="card__tag">LIVE FEED</span>
                      </div>
                      <div className="activity-list">
                        {activityFeed.length === 0 ? (
                          <p className="muted">아직 activity feed가 없습니다.</p>
                        ) : (
                          activityFeed.map((entry, index) => (
                            <div key={`${entry.timestamp}-${index}`} className={`activity-item activity-item--${entry.tone}`}>
                              <div className="activity-item__meta">
                                <span>{entry.timestamp || "방금"}</span>
                                <span>{entry.tone}</span>
                              </div>
                              <p>{entry.message}</p>
                            </div>
                          ))
                        )}
                      </div>
                    </article>
                  </div>
                ) : null}

                {activeDeckTab === "recent" ? (
                  <div className="workspace-grid">
                    <article className="runbook-card form-field--full">
                      <div className="card__header">
                        <span className="card__eyebrow">Recent Project Re-entry</span>
                        <span className="card__tag">{controlDeck?.recentProjects.length ?? 0}</span>
                      </div>
                      <p className="muted">
                        최근 저장 상태를 현재 세션으로 복원합니다. 복원 후 snapshot, queue, prompt, runbook, activity feed가 한 번에 다시 맞춰집니다.
                      </p>
                    </article>

                    <div className="recent-restore-list form-field--full">
                      {(controlDeck?.recentProjects ?? []).length === 0 ? (
                        <p className="muted">복원 가능한 최근 프로젝트가 아직 없습니다.</p>
                      ) : (
                        controlDeck?.recentProjects.map((item) => (
                          <article key={`${item.index}-${item.savedAt}`} className="recent-restore-card">
                            <div className="recent-restore-card__body">
                              <div>
                                <span className="meta-label">Project {item.index + 1}</span>
                                <strong>{item.title}</strong>
                              </div>
                              <p>{item.targetOutcome || "목표 설명 없음"}</p>
                              <div className="recent-restore-card__meta">
                                <span>저장 시각 {formatSavedAt(item.savedAt)}</span>
                                <span>
                                  진행 {item.progress.current} / {item.progress.total}
                                </span>
                              </div>
                            </div>
                            <button
                              className="panel-button panel-button--primary"
                              disabled={isDeckBusy}
                              onClick={() => void restoreRecentProject(item.index)}
                              type="button"
                            >
                              이 세션으로 복원
                            </button>
                          </article>
                        ))
                      )}
                    </div>
                  </div>
                ) : null}
              </div>
            </div>
          </aside>
        </div>
      ) : null}
    </div>
  );
}

export default App;
