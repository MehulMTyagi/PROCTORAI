import { useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  ArrowLeft,
  Camera,
  CheckCircle2,
  Expand,
  MonitorUp,
  Radio,
  RotateCw,
  Save,
  ScanFace,
  Send,
  ShieldCheck,
  UserRoundX,
  UsersRound,
  Wifi,
  WifiOff,
} from "lucide-react";
import "./styles.css";
import Preflight, { type ReadinessCheck, type ReadinessKey, type CheckStatus } from "./Preflight";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";
const AI_ENGINE_BASE = import.meta.env.VITE_AI_ENGINE_URL ?? "http://127.0.0.1:8765";
const TUNNEL_BYPASS_HEADERS = { "bypass-tunnel-reminder": "1" };

type User = { id: string; email: string; full_name: string; role: string };
type Assessment = {
  id: string;
  title: string;
  description: string | null;
  status: string;
  duration_minutes: number | null;
};
type Question = {
  id: string;
  prompt: string;
  question_type: string;
  options: { id: string; label: string }[] | null;
  correct_answer: string | null;
  points: number;
  display_order: number;
};
type AssessmentDetail = Assessment & { questions: Question[] };
type Attempt = {
  id: string;
  assessment_id: string;
  status: string;
  score: number | null;
  answers: Answer[];
};
type Answer = {
  id: string;
  question_id: string;
  answer_text: string | null;
  selected_option: string | null;
  score_awarded: number | null;
};
type IntegrityEvent = {
  id: string;
  event_type: string;
  status: string;
  priority_score: number;
};
type AiModelInfo = {
  name: string;
  version: string;
  detector: string;
  cascade_path?: string | null;
};
type AiEventCandidate = {
  event_type: "FACE_ABSENT" | "MULTIPLE_PERSONS";
  severity: "HIGH";
  confidence: number;
  priority_score: number;
  metadata: Record<string, unknown>;
};
type AiFrameResponse = {
  face_count: number;
  state: {
    consecutive_absent_frames: number;
    consecutive_multiple_frames: number;
    normal_frames: number;
    samples_analyzed: number;
  };
  events: AiEventCandidate[];
  model: AiModelInfo;
};
type Session = { token: string; user: User };
type PendingOperation = {
  id: string;
  kind: "ANSWER" | "EVENT" | "HEARTBEAT";
  path: string;
  method: "POST";
  body: Record<string, unknown>;
  label: string;
  queued_at: string;
  status: "queued" | "retrying" | "failed";
};

class ApiError extends Error {
  status?: number;
  retriable: boolean;

  constructor(message: string, status?: number, retriable = false) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.retriable = retriable;
  }
}

const initialChecks: ReadinessCheck[] = [
  { key: "backend", label: "Assessment connection", status: "pending", detail: "Not checked" },
  { key: "camera", label: "Camera", status: "pending", detail: "Not checked" },
  { key: "microphone", label: "Microphone", status: "pending", detail: "Not checked" },
  { key: "sidecar", label: "Local monitoring", status: "pending", detail: "Not checked" },
  { key: "fullscreen", label: "Fullscreen", status: "pending", detail: "Not entered" },
];

async function api<T>(path: string, options: RequestInit = {}, simulateOffline = false): Promise<T> {
  if (simulateOffline) throw new ApiError("Simulated network offline", undefined, true);

  const response = await fetch(`${API_BASE}${path}`, {
    signal: AbortSignal.timeout(8000),
    ...options,
    headers: { "Content-Type": "application/json", ...TUNNEL_BYPASS_HEADERS, ...options.headers },
  });
  if (!response.ok) {
    const message = await response.text();
    throw new ApiError(message || `Request failed with status ${response.status}`, response.status, response.status >= 500);
  }
  return response.json() as Promise<T>;
}

function errorMessage(error: unknown, fallback: string) {
  return error instanceof Error ? error.message : fallback;
}

function shouldQueueOperation(error: unknown) {
  return !(error instanceof ApiError) || error.retriable;
}

async function login(): Promise<Session> {
  const auth = await api<{ access_token: string; user: User }>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email: "candidate@example.com", password: "password123" }),
  });
  return { token: auth.access_token, user: auth.user };
}

function buildOperation(
  kind: PendingOperation["kind"],
  path: string,
  body: Record<string, unknown>,
  label: string,
): PendingOperation {
  return {
    id: crypto.randomUUID(),
    kind,
    path,
    method: "POST",
    body,
    label,
    queued_at: new Date().toISOString(),
    status: "queued",
  };
}

function App() {
  const [session, setSession] = useState<Session | null>(null);
  const [assessments, setAssessments] = useState<Assessment[]>([]);
  const [selected, setSelected] = useState<AssessmentDetail | null>(null);
  const [attempt, setAttempt] = useState<Attempt | null>(null);
  const [draftAnswers, setDraftAnswers] = useState<Record<string, string>>({});
  const [lastEvent, setLastEvent] = useState<IntegrityEvent | null>(null);
  const [readinessChecks, setReadinessChecks] = useState<ReadinessCheck[]>(initialChecks);
  const [consentAccepted, setConsentAccepted] = useState(false);
  const [consentAcceptedAt, setConsentAcceptedAt] = useState<string | null>(null);
  const [fullscreenActive, setFullscreenActive] = useState(Boolean(document.fullscreenElement));
  const [lastHeartbeatAckAt, setLastHeartbeatAckAt] = useState<string | null>(null);
  const [heartbeatGapNotified, setHeartbeatGapNotified] = useState(false);
  const [aiModel, setAiModel] = useState<AiModelInfo | null>(null);
  const [faceMonitor, setFaceMonitor] = useState({
    status: "idle",
    faceCount: null as number | null,
    samplesAnalyzed: 0,
    detail: "Waiting for sidecar",
  });
  const [retryQueue, setRetryQueue] = useState<PendingOperation[]>([]);
  const [simulateOffline, setSimulateOffline] = useState(false);
  const [status, setStatus] = useState("connecting");
  const [error, setError] = useState<string | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const flushingRef = useRef(false);
  const autoEventRef = useRef<Record<string, number>>({});
  const readinessRef = useRef({ consentAccepted, readinessChecks });
  readinessRef.current = { consentAccepted, readinessChecks };

  const authHeaders: Record<string, string> = session
    ? { Authorization: `Bearer ${session.token}` }
    : {};
  const answeredCount = useMemo(
    () => Object.values(draftAnswers).filter((answer) => answer.trim().length > 0).length,
    [draftAnswers],
  );
  const readinessByKey = useMemo(
    () => Object.fromEntries(readinessChecks.map((check) => [check.key, check])),
    [readinessChecks],
  ) as Record<ReadinessKey, ReadinessCheck>;
  const allChecksReady = readinessChecks.every((check) => check.status === "pass");
  const canStartAttempt = Boolean(session && selected && consentAccepted && allChecksReady && status !== "saving");
  const isSubmitted = attempt?.status === "SUBMITTED";
  const monitoringActive = Boolean(attempt && !isSubmitted);
  const sidecarReady = readinessByKey.sidecar?.status === "pass";

  function updateCheck(key: ReadinessKey, nextStatus: CheckStatus, detail: string) {
    setReadinessChecks((current) =>
      current.map((check) => (check.key === key ? { ...check, status: nextStatus, detail } : check)),
    );
  }

  function enqueueOperation(operation: PendingOperation) {
    setRetryQueue((current) => {
      if (operation.kind === "HEARTBEAT" && current.some((queued) => queued.kind === "HEARTBEAT")) {
        return current;
      }
      return [...current, operation];
    });
    setStatus("offline");
  }

  async function executeOperation(operation: PendingOperation, token: string, honorOffline = false) {
    const result = await api<unknown>(
      operation.path,
      {
        method: operation.method,
        headers: { Authorization: `Bearer ${token}` },
        body: JSON.stringify(operation.body),
      },
      honorOffline ? simulateOffline : false,
    );
    if (operation.kind === "EVENT") setLastEvent(result as IntegrityEvent);
    if (operation.kind === "ANSWER") {
      const answer = result as Answer;
      setAttempt((current) => {
        if (!current) return current;
        const existing = current.answers.filter((item) => item.id !== answer.id);
        return { ...current, answers: [...existing, answer] };
      });
    }
    if (operation.kind === "HEARTBEAT") {
      setLastHeartbeatAckAt(new Date().toISOString());
      setHeartbeatGapNotified(false);
    }
  }

  async function flushQueue() {
    if (!session || simulateOffline || flushingRef.current || retryQueue.length === 0) return;
    flushingRef.current = true;
    setStatus("syncing");
    setError(null);
    let failedOperation: PendingOperation | null = null;

    for (const operation of retryQueue) {
      setRetryQueue((current) =>
        current.map((queued) =>
          queued.id === operation.id ? { ...queued, status: "retrying" } : queued,
        ),
      );
      try {
        await executeOperation(operation, session.token);
        setRetryQueue((current) => current.filter((queued) => queued.id !== operation.id));
      } catch (nextError) {
        failedOperation = operation;
        setRetryQueue((current) =>
          current.map((queued) =>
            queued.id === operation.id ? { ...queued, status: "failed" } : queued,
          ),
        );
        setError(errorMessage(nextError, `${operation.label} sync failed.`));
        break;
      }
    }

    flushingRef.current = false;
    setStatus(failedOperation ? "offline" : "ready");
  }

  async function loadAssessments(token: string) {
    const list = await api<Assessment[]>("/assessments", {
      headers: { Authorization: `Bearer ${token}` },
    });
    setAssessments(list);
    if (list[0]) await loadAssessment(list[0].id, token);
  }

  async function loadAssessment(assessmentId: string, token = session?.token) {
    if (!token) return;
    setStatus("loading");
    setError(null);
    try {
      const detail = await api<AssessmentDetail>(`/assessments/${assessmentId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      setSelected(detail);
      setAttempt(null);
      setConsentAccepted(false);
      setConsentAcceptedAt(null);
      setReadinessChecks(initialChecks);
      setDraftAnswers({});
      setLastEvent(null);
      setStatus("ready");
    } catch (nextError) {
      setStatus("error");
      setError(errorMessage(nextError, "Assessment could not be loaded. Please retry."));
    }
  }

  async function connect() {
    setStatus("connecting");
    setError(null);
    try {
      const nextSession = await login();
      setSession(nextSession);
      await loadAssessments(nextSession.token);
      setStatus("ready");
    } catch {
      setSession(null);
      setStatus("error");
      setError("Unable to connect to your assessment service. Please reconnect when the service is available.");
    }
  }

  useEffect(() => { void connect(); }, []);

  useEffect(() => {
    if (!attempt) return;
    const syncRoute = () => {
      window.history.replaceState(null, "", isSubmitted ? "#/submitted" : "#/exam");
    };
    syncRoute();
    document.title = `${isSubmitted ? "Submitted" : "Assessment"} | ProctorAI Candidate`;
    document.getElementById("main-content")?.focus();
    window.scrollTo(0, 0);
    window.addEventListener("hashchange", syncRoute);
    return () => window.removeEventListener("hashchange", syncRoute);
  }, [attempt?.id, isSubmitted]);

  async function sendIntegrityEvent(
    eventType = "APP_FOCUS_LOST",
    metadata: Record<string, unknown> = { source: "candidate-week5-runner", reason: "manual_dummy_event" },
    severity = "MEDIUM",
    priorityScore = 5,
    automatic = false,
  ) {
    if (!attempt || isSubmitted || !session) {
      if (!automatic) setError("Start the assessment attempt before sending a monitoring event.");
      return;
    }

    const now = Date.now();
    if (automatic && now - (autoEventRef.current[eventType] ?? 0) < 5000) return;
    autoEventRef.current[eventType] = now;

    const operation = buildOperation(
      "EVENT",
      `/attempts/${attempt.id}/events`,
      {
        event_type: eventType,
        severity,
        confidence: automatic ? 1 : 0.88,
        priority_score: priorityScore,
        evidence_status: "NOT_REQUIRED",
        metadata: { ...metadata, automatic, queued_from: "candidate-week5-runner" },
      },
      eventType.replaceAll("_", " "),
    );

    setError(null);
    try {
      const event = await api<IntegrityEvent>(
        operation.path,
        {
          method: operation.method,
          headers: authHeaders,
          body: JSON.stringify(operation.body),
        },
        simulateOffline,
      );
      setLastEvent(event);
      if (!simulateOffline) setStatus("ready");
    } catch (nextError) {
      if (shouldQueueOperation(nextError)) {
        enqueueOperation(operation);
      } else {
        setStatus("error");
        setError(errorMessage(nextError, "Monitoring event failed."));
      }
    }
  }

  async function checkSidecarHealth() {
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 8000);
    try {
      const response = await fetch(`${AI_ENGINE_BASE}/health`, {
        headers: TUNNEL_BYPASS_HEADERS,
        signal: controller.signal,
      });
      if (!response.ok) throw new Error("Sidecar returned an error");
      const health = (await response.json()) as { status: string; model: AiModelInfo };
      setAiModel(health.model);
      setFaceMonitor((current) => ({
        ...current,
        detail: `${health.model.detector} ready`,
      }));
      updateCheck("sidecar", health.status === "ok" ? "pass" : "fail", health.status === "ok" ? "Local monitoring is available" : "Local monitoring is not ready. Restart the service and retry.");
      return health.status === "ok";
    } catch {
      setAiModel(null);
      setFaceMonitor((current) => ({ ...current, status: "idle", detail: "Sidecar pending" }));
      updateCheck("sidecar", "fail", "Local monitoring is unavailable. Start the monitoring service and retry.");
      return false;
    } finally {
      window.clearTimeout(timeout);
    }
  }

  function captureFrameDataUrl() {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas || video.readyState < HTMLMediaElement.HAVE_CURRENT_DATA) return null;

    canvas.width = 224;
    canvas.height = 168;
    const context = canvas.getContext("2d");
    if (!context) return null;
    context.drawImage(video, 0, 0, canvas.width, canvas.height);
    return canvas.toDataURL("image/jpeg", 0.62);
  }

  async function analyzeFaceSample(observedFaceCount?: number, source = "camera_sampler") {
    if (!attempt || isSubmitted || !sidecarReady) return;
    const frameDataUrl = observedFaceCount === undefined ? captureFrameDataUrl() : null;
    if (observedFaceCount === undefined && frameDataUrl === null) {
      setFaceMonitor((current) => ({ ...current, status: "waiting", detail: "Waiting for camera frame" }));
      return;
    }

    try {
      const response = await fetch(`${AI_ENGINE_BASE}/analyze-frame`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...TUNNEL_BYPASS_HEADERS },
        body: JSON.stringify({
          session_id: attempt.id,
          frame_data_url: frameDataUrl,
          observed_face_count: observedFaceCount,
          config: {
            absent_frame_threshold: 3,
            multiple_frame_threshold: 2,
            event_cooldown_seconds: 10,
            min_face_size_px: 24,
          },
        }),
      });
      if (!response.ok) throw new Error(await response.text());
      const analysis = (await response.json()) as AiFrameResponse;
      setAiModel(analysis.model);
      setFaceMonitor({
        status: analysis.events.length ? "event" : "detecting",
        faceCount: analysis.face_count,
        samplesAnalyzed: analysis.state.samples_analyzed,
        detail: analysis.events.length
          ? `${analysis.events[0].event_type.replaceAll("_", " ")} candidate`
          : `${analysis.face_count} face${analysis.face_count === 1 ? "" : "s"} detected`,
      });

      for (const event of analysis.events) {
        await sendIntegrityEvent(
          event.event_type,
          {
            ...event.metadata,
            source,
            ai_engine_url: AI_ENGINE_BASE,
            samples_analyzed: analysis.state.samples_analyzed,
          },
          event.severity,
          event.priority_score,
          true,
        );
      }
    } catch (nextError) {
      setFaceMonitor((current) => ({
        ...current,
        status: "error",
        detail: nextError instanceof Error ? nextError.message : "Face analysis failed",
      }));
    }
  }

  async function runFaceDemo(observedFaceCount: number) {
    const samples = observedFaceCount > 1 ? 2 : 3;
    for (let index = 0; index < samples; index += 1) {
      await analyzeFaceSample(observedFaceCount, "manual_face_demo");
    }
  }

  function readinessMetrics() {
    return {
      consent_accepted: consentAccepted,
      consent_accepted_at: consentAcceptedAt,
      consent_version: "candidate-preflight-v1",
      checks: Object.fromEntries(
        readinessChecks.map((check) => [check.key, { status: check.status, detail: check.detail }]),
      ),
      fullscreen_active: fullscreenActive,
      document_hidden: document.hidden,
      retry_queue_depth: retryQueue.length,
      simulated_offline: simulateOffline,
    };
  }

  async function sendHeartbeat(reason: string, attemptId = attempt?.id) {
    if (!attemptId || !session) return;
    const operation = buildOperation(
      "HEARTBEAT",
      `/attempts/${attemptId}/heartbeats`,
      {
        status: simulateOffline ? "DEGRADED" : "OK",
        metrics: { reason, ...readinessMetrics() },
      },
      "Session heartbeat",
    );

    try {
      await executeOperation(operation, session.token, true);
      if (!simulateOffline) setStatus("ready");
    } catch (nextError) {
      if (shouldQueueOperation(nextError)) {
        enqueueOperation(operation);
      } else {
        setStatus("error");
        setError(errorMessage(nextError, "Heartbeat failed."));
      }
    }
  }

  useEffect(() => {
    const handleFullscreenChange = () => {
      const isFullscreen = Boolean(document.fullscreenElement);
      setFullscreenActive(isFullscreen);
      updateCheck(
        "fullscreen",
        isFullscreen ? "pass" : "warning",
        isFullscreen ? "Fullscreen active" : "Fullscreen inactive",
      );
      if (monitoringActive && !isFullscreen) {
        void sendIntegrityEvent("FULLSCREEN_EXIT", { source: "fullscreen_monitor" }, "HIGH", 8, true);
      }
    };

    document.addEventListener("fullscreenchange", handleFullscreenChange);
    return () => document.removeEventListener("fullscreenchange", handleFullscreenChange);
  }, [monitoringActive, session?.token, simulateOffline]);

  useEffect(() => {
    if (!monitoringActive) return;

    const handleFocusLost = () => {
      void sendIntegrityEvent("APP_FOCUS_LOST", { source: "focus_monitor" }, "MEDIUM", 5, true);
    };
    const handleVisibility = () => {
      if (document.hidden) handleFocusLost();
    };

    window.addEventListener("blur", handleFocusLost);
    document.addEventListener("visibilitychange", handleVisibility);
    return () => {
      window.removeEventListener("blur", handleFocusLost);
      document.removeEventListener("visibilitychange", handleVisibility);
    };
  }, [monitoringActive, session?.token, simulateOffline]);

  useEffect(() => {
    if (!monitoringActive) return;
    void sendHeartbeat("periodic");
    const interval = window.setInterval(() => void sendHeartbeat("periodic"), 10000);
    return () => window.clearInterval(interval);
  }, [
    monitoringActive,
    session?.token,
    consentAccepted,
    fullscreenActive,
    readinessChecks,
    retryQueue.length,
    simulateOffline,
  ]);

  useEffect(() => {
    if (!monitoringActive || heartbeatGapNotified) return;
    const interval = window.setInterval(() => {
      if (!lastHeartbeatAckAt) return;
      const elapsedMs = Date.now() - new Date(lastHeartbeatAckAt).getTime();
      if (elapsedMs > 15000) {
        setHeartbeatGapNotified(true);
        void sendIntegrityEvent(
          "HEARTBEAT_GAP",
          { source: "heartbeat_monitor", elapsed_ms: elapsedMs },
          "HIGH",
          9,
          true,
        );
      }
    }, 5000);
    return () => window.clearInterval(interval);
  }, [monitoringActive, heartbeatGapNotified, lastHeartbeatAckAt, session?.token, simulateOffline]);

  useEffect(() => {
    if (!monitoringActive || !sidecarReady || !navigator.mediaDevices?.getUserMedia) {
      return;
    }

    let cancelled = false;
    navigator.mediaDevices
      .getUserMedia({ video: { width: 320, height: 240 }, audio: false })
      .then((stream) => {
        if (cancelled) {
          stream.getTracks().forEach((track) => track.stop());
          return;
        }
        streamRef.current = stream;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          void videoRef.current.play();
        }
        setFaceMonitor((current) => ({ ...current, status: "camera", detail: "Camera sampler active" }));
      })
      .catch(() => {
        setFaceMonitor((current) => ({ ...current, status: "warning", detail: "Camera stream unavailable" }));
      });

    return () => {
      cancelled = true;
      streamRef.current?.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    };
  }, [monitoringActive, sidecarReady]);

  useEffect(() => {
    if (!monitoringActive || !sidecarReady) return;
    const interval = window.setInterval(() => void analyzeFaceSample(), 3000);
    return () => window.clearInterval(interval);
  }, [monitoringActive, sidecarReady, attempt?.id]);

  useEffect(() => {
    if (retryQueue.length > 0 && !simulateOffline) {
      const interval = window.setInterval(() => void flushQueue(), 4000);
      void flushQueue();
      return () => window.clearInterval(interval);
    }
  }, [retryQueue.length, simulateOffline, session?.token]);

  async function runReadinessChecks() {
    setStatus("checking");
    setError(null);
    updateCheck("backend", "pending", "Checking assessment connection...");
    updateCheck("sidecar", "pending", "Checking local monitoring...");

    try {
      const health = await api<{ status: string }>("/health", {}, simulateOffline);
      updateCheck(
        "backend",
        health.status === "ok" ? "pass" : "fail",
        health.status === "ok" ? "Assessment service is available" : "Assessment service is not ready. Retry in a moment.",
      );
    } catch {
      updateCheck("backend", "fail", "Assessment service is unavailable. Check your connection and retry.");
    }

    await checkSidecarHealth();

    updateCheck(
      "fullscreen",
      document.fullscreenElement ? "pass" : "warning",
      document.fullscreenElement ? "Fullscreen active" : "Fullscreen inactive",
    );
    setStatus("ready");
  }

  async function startAttempt() {
    if (!selected) return;
    if (!canStartAttempt || !document.fullscreenElement) {
      setError("Complete consent and all requirement checks, including fullscreen, before starting.");
      return;
    }

    setStatus("saving");
    setError(null);
    try {
      const health = await api<{ status: string }>("/health", {}, simulateOffline).catch(() => null);
      if (health?.status !== "ok") {
        updateCheck("backend", "fail", "Assessment service is unavailable. Check your connection and retry.");
        throw new Error("The assessment connection changed. Repeat the system check before starting.");
      }
      if (!(await checkSidecarHealth())) {
        throw new Error("Local monitoring is unavailable. Repeat the system check before starting.");
      }
      if (!document.fullscreenElement) throw new Error("Restore fullscreen before starting the assessment.");
      if (!readinessRef.current.consentAccepted || readinessRef.current.readinessChecks.some((check) => check.status !== "pass")) {
        throw new Error("A requirement changed. Complete the remaining checks before starting.");
      }
      const started = await api<{ attempt_id: string; status: string }>(
        "/attempts/start",
        {
          method: "POST",
          headers: authHeaders,
          body: JSON.stringify({ assessment_id: selected.id }),
        },
        simulateOffline,
      );
      const detail = await api<Attempt>(
        `/attempts/${started.attempt_id}`,
        { headers: authHeaders },
        simulateOffline,
      );
      setAttempt(detail);
      setDraftAnswers(
        Object.fromEntries(
          detail.answers.map((answer) => [
            answer.question_id,
            answer.selected_option ?? answer.answer_text ?? "",
          ]),
        ),
      );
      setStatus("ready");
      if (detail.status !== "SUBMITTED") void sendHeartbeat("attempt_started", started.attempt_id);
    } catch (nextError) {
      setStatus("error");
      setError(errorMessage(nextError, "Attempt start failed."));
    }
  }

  async function saveAnswer(question: Question, value: string) {
    if (!attempt || isSubmitted || !session) return;
    setDraftAnswers((current) => ({ ...current, [question.id]: value }));

    const operation = buildOperation(
      "ANSWER",
      `/attempts/${attempt.id}/answers`,
      {
        question_id: question.id,
        selected_option: question.question_type === "MCQ" ? value : null,
        answer_text: question.question_type === "SHORT_ANSWER" ? value : null,
      },
      `Answer ${question.display_order}`,
    );

    try {
      await executeOperation(operation, session.token, true);
      if (!simulateOffline) setStatus("ready");
    } catch (nextError) {
      if (shouldQueueOperation(nextError)) {
        enqueueOperation(operation);
      } else {
        setStatus("error");
        setError(errorMessage(nextError, "Answer save failed."));
      }
    }
  }

  async function submitAttempt() {
    if (!attempt) return;
    if (retryQueue.length > 0) {
      setError("Queued answers or monitoring events must sync before submission.");
      return;
    }

    setStatus("saving");
    setError(null);
    try {
      const result = await api<{ status: string; score: number; answers: Answer[] }>(
        `/attempts/${attempt.id}/submit`,
        { method: "POST", headers: authHeaders },
        simulateOffline,
      );
      setAttempt((current) =>
        current ? { ...current, status: result.status, score: result.score, answers: result.answers } : current,
      );
      setStatus("ready");
    } catch (nextError) {
      setStatus("error");
      setError(errorMessage(nextError, "Submit failed."));
    }
  }

  async function requestFullscreen() {
    setError(null);
    try {
      await document.documentElement.requestFullscreen();
    } catch (nextError) {
      updateCheck("fullscreen", "fail", "Fullscreen could not be enabled. Use a supported desktop browser and retry.");
      setError(nextError instanceof Error ? nextError.message : "Fullscreen request failed.");
    }
  }

  return (
    <div className="candidate-shell">
      <a className="skip-link" href="#main-content" onClick={(event) => { event.preventDefault(); document.getElementById("main-content")?.focus(); }}>Skip to main content</a>
      <header className="app-header">
        <div className="brand">
          <ShieldCheck size={28} aria-hidden="true" />
          <span>ProctorAI</span>
          <span className="portal-label">Candidate portal</span>
        </div>
        <div className={`network ${simulateOffline ? "offline" : status}`} aria-live="polite">
          {simulateOffline ? <WifiOff size={16} aria-hidden="true" /> : <Wifi size={16} aria-hidden="true" />}
          {simulateOffline ? "offline demo" : status}
        </div>
      </header>

      {error ? <div className="error-panel" role="alert">{error}</div> : null}

      {!attempt ? <Preflight
        assessments={assessments}
        selected={selected}
        questionCount={selected?.questions.length ?? 0}
        checks={readinessChecks}
        consent={consentAccepted}
        connected={Boolean(session)}
        busy={["connecting", "loading", "checking", "saving"].includes(status)}
        onSelect={loadAssessment}
        onReconnect={connect}
        onConsent={(accepted) => { setConsentAccepted(accepted); setConsentAcceptedAt(accepted ? new Date().toISOString() : null); }}
        onCheck={updateCheck}
        onSystemCheck={runReadinessChecks}
        onFullscreen={requestFullscreen}
        onStart={startAttempt}
      /> : <main id="main-content" tabIndex={-1} className="active-session">
      <section className="assessment-band">
        <div>
          <p className="eyebrow">Candidate Session</p>
          <h1>{isSubmitted ? "Assessment submitted" : selected?.title}</h1>
          <span>{selected?.duration_minutes ?? 0} minutes | {selected?.status ?? "PENDING"}</span>
        </div>
        <div className="band-actions">
          {isSubmitted ? <button onClick={() => { setAttempt(null); setConsentAccepted(false); setConsentAcceptedAt(null); setReadinessChecks(initialChecks); setDraftAnswers({}); setLastHeartbeatAckAt(null); window.location.hash = "/assessments"; }}>
            <ArrowLeft size={18} aria-hidden="true" />Back to assessments
          </button> : <button onClick={requestFullscreen} disabled={fullscreenActive}>
            <Expand size={18} aria-hidden="true" />
            {fullscreenActive ? "Fullscreen active" : "Restore fullscreen"}
          </button>}
        </div>
      </section>

      {!isSubmitted && <section className="status-grid">
        <div className="status-tile">
          <Camera size={22} aria-hidden="true" />
          <span>Camera</span>
          <strong>{readinessByKey.camera?.status === "pass" ? "Ready" : "Check"}</strong>
        </div>
        <div className="status-tile">
          <MonitorUp size={22} aria-hidden="true" />
          <span>Monitoring</span>
          <strong>{monitoringActive ? "Active" : "Pending"}</strong>
        </div>
        <div className="status-tile">
          <CheckCircle2 size={22} aria-hidden="true" />
          <span>Progress</span>
          <strong>{answeredCount}/{selected?.questions.length ?? 0}</strong>
        </div>
        <div className="status-tile">
          <Radio size={22} aria-hidden="true" />
          <span>Heartbeat</span>
          <strong>{lastHeartbeatAckAt ? "Synced" : "Waiting"}</strong>
        </div>
        <div className="status-tile">
          <ScanFace size={22} aria-hidden="true" />
          <span>Face AI</span>
          <strong>{sidecarReady ? faceMonitor.status : "Pending"}</strong>
        </div>
      </section>}

      {!isSubmitted && <section className="sync-strip" aria-label="Network and retry state">
        <label className="switch-control">
          <input
            checked={simulateOffline}
            onChange={(event) => setSimulateOffline(event.target.checked)}
            type="checkbox"
          />
          <span>Simulate network outage</span>
        </label>
        <div>
          <strong>{retryQueue.length}</strong>
          <span> queued operation{retryQueue.length === 1 ? "" : "s"}</span>
        </div>
        <button onClick={flushQueue} disabled={simulateOffline || retryQueue.length === 0}>
          <RotateCw size={17} aria-hidden="true" />
          Retry Sync
        </button>
      </section>}

      <section className="exam-surface">
        <div className="question-block">
          <div className="runner-header">
            <div>
              <span>{isSubmitted ? "Submission receipt" : "Assessment"}</span>
              <h2>{isSubmitted ? "Your submitted answers" : `${answeredCount} of ${selected?.questions.length ?? 0} answered`}</h2>
            </div>
            <button onClick={submitAttempt} disabled={!attempt || isSubmitted || retryQueue.length > 0 || status === "saving"}>
              <Save size={18} aria-hidden="true" />
              Submit
            </button>
          </div>

          {selected?.questions.length ? (
            <div className="question-list">
              {selected.questions.map((question, index) => (
                <article className="question-card" key={question.id}>
                  <span>Question {index + 1} | {question.points} points</span>
                  <h3>{question.prompt}</h3>
                  {question.question_type === "MCQ" && question.options ? (
                    <div className="option-grid">
                      {question.options.map((option) => (
                        <button
                          className={draftAnswers[question.id] === option.id ? "selected" : ""}
                          disabled={!attempt || isSubmitted}
                          key={option.id}
                          onClick={() => saveAnswer(question, option.id)}
                        >
                          {option.label}
                        </button>
                      ))}
                    </div>
                  ) : (
                    <textarea
                      aria-label={`Answer for question ${index + 1}`}
                      disabled={!attempt || isSubmitted}
                      value={draftAnswers[question.id] ?? ""}
                      onChange={(event) =>
                        setDraftAnswers((current) => ({ ...current, [question.id]: event.target.value }))
                      }
                      onBlur={(event) => saveAnswer(question, event.target.value)}
                    />
                  )}
                </article>
              ))}
            </div>
          ) : (
            <div className="empty-state">No questions are available yet</div>
          )}
        </div>

        <aside className="event-card">
          <span>Submission</span>
          <strong>{isSubmitted ? `Score ${attempt?.score ?? 0}` : "Not Submitted"}</strong>
          <small>{isSubmitted ? "Objective questions scored automatically" : "Autosave runs per answer"}</small>
          {!isSubmitted && <>
          <span>Face Monitor</span>
          <strong>
            {faceMonitor.faceCount === null ? "No Sample" : `${faceMonitor.faceCount} Face${faceMonitor.faceCount === 1 ? "" : "s"}`}
          </strong>
          <small>
            {aiModel ? `${aiModel.name} | ${faceMonitor.samplesAnalyzed} samples` : faceMonitor.detail}
          </small>
          <div className="face-actions">
            <button onClick={() => runFaceDemo(0)} disabled={!monitoringActive || !sidecarReady}>
              <UserRoundX size={17} aria-hidden="true" />
              Face Absent
            </button>
            <button onClick={() => runFaceDemo(2)} disabled={!monitoringActive || !sidecarReady}>
              <UsersRound size={17} aria-hidden="true" />
              Multiple People
            </button>
          </div>
          <span>Last Event</span>
          <strong>{lastEvent ? lastEvent.event_type.replaceAll("_", " ") : "None"}</strong>
          <small>{lastEvent ? `${lastEvent.status} | Priority ${lastEvent.priority_score}` : "Ready"}</small>
          <span>Retry Queue</span>
          <strong>{retryQueue.length ? `${retryQueue.length} Pending` : "Clear"}</strong>
          <small>{retryQueue[0] ? `${retryQueue[0].label} | ${retryQueue[0].status}` : "All local operations synced"}</small>
          <button onClick={() => sendIntegrityEvent()} disabled={!monitoringActive}>
            <Send size={17} aria-hidden="true" />
            Send Test Event
          </button>
          <video ref={videoRef} aria-label="Local face monitor preview" muted playsInline />
          <canvas ref={canvasRef} aria-hidden="true" />
          </>}
        </aside>
      </section>
      </main>}
    </div>
  );
}

createRoot(document.getElementById("root")!).render(<App />);
