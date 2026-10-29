import { useEffect, useMemo, useRef, useState } from "react";
import type { FormEvent } from "react";
import { createRoot } from "react-dom/client";
import {
  BookOpen,
  CircleHelp,
  LayoutDashboard,
  ShieldCheck,
  Wifi,
  WifiOff,
} from "lucide-react";
import "./styles.css";
import "./portal.css";
import "./legibility.css";
import AssessmentsPage from "./AssessmentsPage";
import LoginPage from "./LoginPage";
import IdentityEnrollmentPage from "./IdentityEnrollmentPage";
import SetupPage from "./SetupPage";
import TestPage from "./TestPage";
import { CandidateHelp, CandidateHome } from "./PortalPages";
import { RollingEvidenceRecorder } from "./evidenceRecorder";
import { enabled, requiredCheck, requirements } from "./proctoring";
import {
  parseRoute,
  routeHash,
  type AiFrameResponse,
  type AiModelInfo,
  type Answer,
  type Assessment,
  type AssessmentDetail,
  type Attempt,
  type CheckStatus,
  type EvidenceFile,
  type IntegrityEvent,
  type IdentityMonitorState,
  type IdentityVerification,
  type PendingOperation,
  type Question,
  type ReadinessCheck,
  type ReadinessKey,
  type RiskTimelineItem,
  type Route,
  type Session,
  type YoloObjectResponse,
} from "./types";

const configuredApiBase = import.meta.env.VITE_API_BASE_URL;
if (import.meta.env.PROD && !configuredApiBase?.startsWith("https://")) {
  throw new Error("Production builds require VITE_API_BASE_URL to use HTTPS.");
}
const API_BASE = configuredApiBase ?? "http://127.0.0.1:8010";
const AI_ENGINE_BASE =
  import.meta.env.VITE_AI_ENGINE_URL ?? "http://127.0.0.1:8765";
const PRE_ROLL_MS = 5000;
const POST_ROLL_MS = 5000;

const RISK_WINDOW_MS = 30_000;
const RISK_WEIGHTS: Record<string, number> = {
  APP_FOCUS_LOST: 5,
  FULLSCREEN_EXIT: 8,
  HEARTBEAT_GAP: 9,
  CAMERA_DISABLED: 9,
  MICROPHONE_DISABLED: 8,
  BACKGROUND_SPEECH: 7,
  PHONE_DETECTED: 12,
  FACE_ABSENT: 8,
  MULTIPLE_PERSONS: 11,
  AI_ENGINE_INTERRUPTED: 8,
  CLIPBOARD_COPY: 5,
  CLIPBOARD_CUT: 6,
  CLIPBOARD_PASTE: 7,
  PRINT_SCREEN_ATTEMPT: 7,
  DEVTOOLS_SHORTCUT: 6,
  SCREEN_SHARE_ATTEMPT: 8,
  IDENTITY_MISMATCH: 12,
};
const BROWSER_ACTIVITY_EVENTS = [
  "APP_FOCUS_LOST",
  "FULLSCREEN_EXIT",
  "CLIPBOARD_COPY",
  "CLIPBOARD_CUT",
  "CLIPBOARD_PASTE",
  "PRINT_SCREEN_ATTEMPT",
  "DEVTOOLS_SHORTCUT",
  "SCREEN_SHARE_ATTEMPT",
];

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
  {
    key: "backend",
    label: "Assessment connection",
    status: "pending",
    detail: "Not checked",
  },
  { key: "camera", label: "Camera", status: "pending", detail: "Not checked" },
  {
    key: "identity",
    label: "Student identity",
    status: "pending",
    detail: "University reference not checked",
  },
  {
    key: "microphone",
    label: "Microphone",
    status: "pending",
    detail: "Not checked",
  },
  {
    key: "sidecar",
    label: "Local monitoring",
    status: "pending",
    detail: "Not checked",
  },
  {
    key: "screen",
    label: "Screen recording",
    status: "pending",
    detail: "Not checked",
  },
  {
    key: "devices",
    label: "Connected devices",
    status: "pending",
    detail: "Not checked",
  },
  {
    key: "fullscreen",
    label: "Fullscreen",
    status: "pending",
    detail: "Not entered",
  },
];

const initialIdentityMonitor: IdentityMonitorState = {
  status: "waiting",
  faceCount: null,
  similarity: null,
  checkedAt: null,
  detail: "Identity check will run during the assessment",
};

async function api<T>(
  path: string,
  options: RequestInit = {},
  simulateOffline = false,
): Promise<T> {
  if (simulateOffline)
    throw new ApiError("Simulated network offline", undefined, true);

  const response = await fetch(`${API_BASE}${path}`, {
    signal: AbortSignal.timeout(8000),
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });
  if (!response.ok) {
    const message = await response.text();
    let detail = message;
    try {
      detail = (JSON.parse(message) as { detail?: string }).detail ?? message;
    } catch {}
    throw new ApiError(
      detail || `Request failed with status ${response.status}`,
      response.status,
      response.status >= 500,
    );
  }
  return response.json() as Promise<T>;
}

function errorMessage(error: unknown, fallback: string) {
  return error instanceof Error ? error.message : fallback;
}

function shouldQueueOperation(error: unknown) {
  return !(error instanceof ApiError) || error.retriable;
}

async function login(email: string, password: string): Promise<Session> {
  const auth = await api<{ access_token: string; user: Session["user"] }>(
    "/auth/login",
    {
      method: "POST",
      body: JSON.stringify({
        email,
        password,
      }),
    },
  );
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

async function sha256Hex(input: string) {
  const bytes = new TextEncoder().encode(input);
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return Array.from(new Uint8Array(digest), (byte) =>
    byte.toString(16).padStart(2, "0"),
  ).join("");
}

async function sha256Blob(blob: Blob) {
  const digest = await crypto.subtle.digest(
    "SHA-256",
    await blob.arrayBuffer(),
  );
  return Array.from(new Uint8Array(digest), (byte) =>
    byte.toString(16).padStart(2, "0"),
  ).join("");
}

function riskWeight(eventType: string, priorityScore: number) {
  return RISK_WEIGHTS[eventType] ?? Math.max(2, priorityScore);
}

function riskLabel(score: number) {
  if (score >= 70) return "Critical";
  if (score >= 45) return "High";
  if (score >= 20) return "Moderate";
  return "Low";
}

function pruneRiskTimeline(items: RiskTimelineItem[], now = Date.now()) {
  return items.filter(
    (item) => now - new Date(item.occurredAt).getTime() <= RISK_WINDOW_MS,
  );
}

function targetSummary(target: EventTarget | null) {
  const element = target instanceof HTMLElement ? target : null;
  return {
    tag: element?.tagName ?? "UNKNOWN",
    input_type: element instanceof HTMLInputElement ? element.type : null,
    editable: Boolean(element?.isContentEditable),
  };
}

function isBrowserActivityEvent(eventType: string) {
  return BROWSER_ACTIVITY_EVENTS.includes(eventType);
}

function App() {
  const [session, setSession] = useState<Session | null>(null);
  const [assessments, setAssessments] = useState<Assessment[]>([]);
  const [selected, setSelected] = useState<AssessmentDetail | null>(null);
  const [attempt, setAttempt] = useState<Attempt | null>(null);
  const [draftAnswers, setDraftAnswers] = useState<Record<string, string>>({});
  const [lastEvent, setLastEvent] = useState<IntegrityEvent | null>(null);
  const [readinessChecks, setReadinessChecks] =
    useState<ReadinessCheck[]>(initialChecks);
  const [consentAccepted, setConsentAccepted] = useState(false);
  const [consentAcceptedAt, setConsentAcceptedAt] = useState<string | null>(
    null,
  );
  const [fullscreenActive, setFullscreenActive] = useState(
    Boolean(document.fullscreenElement),
  );
  const [lastHeartbeatAckAt, setLastHeartbeatAckAt] = useState<string | null>(
    null,
  );
  const [heartbeatGapNotified, setHeartbeatGapNotified] = useState(false);
  const [aiModel, setAiModel] = useState<AiModelInfo | null>(null);
  const [faceMonitor, setFaceMonitor] = useState({
    status: "idle",
    faceCount: null as number | null,
    samplesAnalyzed: 0,
    detail: "Waiting for sidecar",
  });
  const [identityMonitor, setIdentityMonitor] = useState(initialIdentityMonitor);
  const [objectMonitor, setObjectMonitor] = useState({
    status: "idle",
    label: "No object sample",
    confidence: null as number | null,
    detail: "Phone detector pending",
  });
  const [screenMonitor, setScreenMonitor] = useState({
    status: "pending",
    detail: "Screen recording permission pending",
  });
  const [riskTimeline, setRiskTimeline] = useState<RiskTimelineItem[]>([]);
  const [retryQueue, setRetryQueue] = useState<PendingOperation[]>([]);
  const [simulateOffline, setSimulateOffline] = useState(false);
  const [status, setStatus] = useState("ready");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loginEmail, setLoginEmail] = useState("");
  const [loginPassword, setLoginPassword] = useState("");
  const [identityEnrolled, setIdentityEnrolled] = useState(false);
  const [route, setRoute] = useState<Route>(() =>
    parseRoute(window.location.hash),
  );
  const [attemptedAssessmentIds, setAttemptedAssessmentIds] = useState<
    string[]
  >([]);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const identityReferenceRef = useRef<string | null>(null);
  const identityMismatchRef = useRef({ consecutive: 0, lastEventAt: 0, checking: false });
  const streamRef = useRef<MediaStream | null>(null);
  const microphoneStreamRef = useRef<MediaStream | null>(null);
  const screenStreamRef = useRef<MediaStream | null>(null);
  const mediaRecorderRef = useRef<RollingEvidenceRecorder | null>(null);
  const screenMediaRecorderRef = useRef<RollingEvidenceRecorder | null>(null);
  const flushingRef = useRef(false);
  const submissionPendingRef = useRef(false);
  const pendingIntegrityRef = useRef(new Set<Promise<unknown>>());
  const retryQueueRef = useRef(retryQueue);
  retryQueueRef.current = retryQueue;
  const autoEventRef = useRef<Record<string, number>>({});
  const screenCaptureRequestRef = useRef(false);
  const audioSignalRef = useRef({ consecutiveLoudSamples: 0, lastSentAt: 0 });
  const objectSignalRef = useRef({
    consecutivePhoneSamples: 0,
    consecutiveClearSamples: 0,
    activePhoneEventId: null as string | null,
    analyzing: false,
  });
  const readinessRef = useRef({ consentAccepted, readinessChecks });
  readinessRef.current = { consentAccepted, readinessChecks };

  const authHeaders: Record<string, string> = session
    ? { Authorization: `Bearer ${session.token}` }
    : {};
  const readinessByKey = useMemo(
    () =>
      Object.fromEntries(readinessChecks.map((check) => [check.key, check])),
    [readinessChecks],
  ) as Record<ReadinessKey, ReadinessCheck>;
  const required = requirements(selected?.rules);
  const allChecksReady = readinessChecks
    .filter((check) => requiredCheck(check.key, selected?.rules))
    .every((check) => check.status === "pass");
  const canStartAttempt = Boolean(
    session &&
    selected &&
    consentAccepted &&
    allChecksReady &&
    status !== "saving",
  );
  const isSubmitted = attempt?.status === "SUBMITTED";
  const monitoringActive = Boolean(attempt && !isSubmitted);
  const sidecarReady = readinessByKey.sidecar?.status === "pass";
  const liveRiskScore = useMemo(
    () =>
      Math.min(
        100,
        pruneRiskTimeline(riskTimeline).reduce(
          (total, item) => total + item.weight,
          0,
        ),
      ),
    [riskTimeline],
  );
  const liveRiskLabel = riskLabel(liveRiskScore);

  function updateCheck(
    key: ReadinessKey,
    nextStatus: CheckStatus,
    detail: string,
  ) {
    setReadinessChecks((current) =>
      current.map((check) =>
        check.key === key ? { ...check, status: nextStatus, detail } : check,
      ),
    );
  }

  function enqueueOperation(operation: PendingOperation) {
    setRetryQueue((current) => {
      if (
        operation.kind === "HEARTBEAT" &&
        current.some((queued) => queued.kind === "HEARTBEAT")
      ) {
        return current;
      }
      return [...current, operation];
    });
    setStatus("offline");
  }

  async function executeOperation(
    operation: PendingOperation,
    token: string,
    honorOffline = false,
  ) {
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
        const existing = current.answers.filter(
          (item) => item.id !== answer.id,
        );
        return { ...current, answers: [...existing, answer] };
      });
    }
    if (operation.kind === "HEARTBEAT") {
      setLastHeartbeatAckAt(new Date().toISOString());
      setHeartbeatGapNotified(false);
    }
  }

  function stopRecorder(recorderRef: {
    current: RollingEvidenceRecorder | null;
  }) {
    recorderRef.current?.stop();
    recorderRef.current = null;
  }

  function startRecorder(
    stream: MediaStream,
    recorderRef: { current: RollingEvidenceRecorder | null },
  ) {
    stopRecorder(recorderRef);
    if (!window.MediaRecorder) return;
    try {
      recorderRef.current = new RollingEvidenceRecorder(
        stream,
        PRE_ROLL_MS,
        POST_ROLL_MS,
      );
    } catch {
      recorderRef.current = null;
    }
  }

  function stopRollingRecorder() {
    stopRecorder(mediaRecorderRef);
  }
  function startRollingRecorder(stream: MediaStream) {
    startRecorder(stream, mediaRecorderRef);
  }
  function stopScreenRecorder() {
    stopRecorder(screenMediaRecorderRef);
  }
  function startScreenRecorder(stream: MediaStream) {
    startRecorder(stream, screenMediaRecorderRef);
  }

  function stopScreenCapture() {
    screenStreamRef.current?.getVideoTracks().forEach((track) => {
      track.onended = null;
    });
    screenStreamRef.current?.getTracks().forEach((track) => track.stop());
    screenStreamRef.current = null;
    stopScreenRecorder();
    screenCaptureRequestRef.current = false;
    setScreenMonitor({
      status: "pending",
      detail: "Screen recording permission pending",
    });
  }

  async function uploadEvidenceClip(event: IntegrityEvent, capturedAt: string) {
    if (!attempt || !session || simulateOffline) return;
    const useScreenRecording = isBrowserActivityEvent(event.event_type);
    const recorder = useScreenRecording
      ? screenMediaRecorderRef.current
      : mediaRecorderRef.current;
    try {
      if (!recorder) throw new Error("The evidence recorder is not available.");
      const captured = await recorder.capture(new Date(capturedAt).getTime());
      const clip = captured.blob;
      const mimeType = clip.type || "video/webm";
      const sha256_hash = await sha256Blob(clip);
      const formData = new FormData();
      formData.set(
        "file",
        new File(
          [clip],
          event.event_type.toLowerCase() + "-" + event.id + ".webm",
          { type: mimeType },
        ),
      );
      formData.set("kind", useScreenRecording ? "SCREEN_RECORDING" : "VIDEO");
      formData.set("sha256_hash", sha256_hash);
      formData.set(
        "duration_ms",
        String(captured.endedAt - captured.startedAt),
      );
      formData.set(
        "captured_start_at",
        new Date(captured.startedAt).toISOString(),
      );
      formData.set("captured_end_at", new Date(captured.endedAt).toISOString());
      const response = await fetch(
        API_BASE +
          "/attempts/" +
          attempt.id +
          "/events/" +
          event.id +
          "/evidence",
        {
          method: "POST",
          headers: {
            Authorization: "Bearer " + session.token,
          },
          body: formData,
        },
      );
      if (!response.ok) throw new Error(await response.text());
      const evidenceFile = (await response.json()) as EvidenceFile;
      setLastEvent((current) =>
        current?.id === event.id
          ? {
              ...current,
              evidence_status: "READY",
              evidence_files: [...current.evidence_files, evidenceFile],
            }
          : current,
      );
    } catch (nextError) {
      try {
        const response = await api<IntegrityEvent>(
          "/attempts/" +
            attempt.id +
            "/events/" +
            event.id +
            "/evidence/failure",
          {
            method: "POST",
            headers: authHeaders,
            body: JSON.stringify({
              reason: "clip_upload_failed",
              detail: errorMessage(nextError, "Evidence clip upload failed."),
            }),
          },
          false,
        );
        setLastEvent(response);
      } catch {
        setLastEvent((current) =>
          current?.id === event.id
            ? { ...current, evidence_status: "FAILED" }
            : current,
        );
      }
    }
  }

  function shouldCaptureClip(eventType: string, snapshot: string | null) {
    if (isBrowserActivityEvent(eventType)) {
      return Boolean(
        screenMediaRecorderRef.current &&
        [
          "APP_FOCUS_LOST",
          "FULLSCREEN_EXIT",
          "CLIPBOARD_COPY",
          "CLIPBOARD_CUT",
          "CLIPBOARD_PASTE",
          "PRINT_SCREEN_ATTEMPT",
          "DEVTOOLS_SHORTCUT",
          "SCREEN_SHARE_ATTEMPT",
        ].includes(eventType),
      );
    }

    return Boolean(
      snapshot &&
      mediaRecorderRef.current &&
      [
        "FACE_ABSENT",
        "MULTIPLE_PERSONS",
        "PHONE_DETECTED",
        "IDENTITY_MISMATCH",
        "CAMERA_DISABLED",
        "BACKGROUND_SPEECH",
        "AI_ENGINE_INTERRUPTED",
      ].includes(eventType),
    );
  }

  async function flushQueue() {
    if (
      !session ||
      simulateOffline ||
      flushingRef.current ||
      retryQueue.length === 0
    )
      return;
    flushingRef.current = true;
    setStatus("syncing");
    setError(null);
    let failedOperation: PendingOperation | null = null;

    for (const operation of retryQueue) {
      setRetryQueue((current) =>
        current.map((queued) =>
          queued.id === operation.id
            ? { ...queued, status: "retrying" }
            : queued,
        ),
      );
      try {
        await executeOperation(operation, session.token);
        setRetryQueue((current) =>
          current.filter((queued) => queued.id !== operation.id),
        );
      } catch (nextError) {
        failedOperation = operation;
        setRetryQueue((current) =>
          current.map((queued) =>
            queued.id === operation.id
              ? { ...queued, status: "failed" }
              : queued,
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
  }

  async function loadAssessment(assessmentId: string, token = session?.token) {
    if (!token) return;
    setStatus("loading");
    setError(null);
    try {
      const detail = await api<AssessmentDetail>(
        `/assessments/${assessmentId}`,
        {
          headers: { Authorization: `Bearer ${token}` },
        },
      );
      setSelected(detail);
      setAttempt(null);
      setConsentAccepted(false);
      setConsentAcceptedAt(null);
      setReadinessChecks(initialChecks);
      setDraftAnswers({});
      setLastEvent(null);
      setRiskTimeline([]);
      stopScreenCapture();
      setStatus("ready");
    } catch (nextError) {
      setStatus("error");
      setError(
        errorMessage(
          nextError,
          "Assessment could not be loaded. Please retry.",
        ),
      );
    }
  }

  async function refreshAssessments() {
    if (!session) return;
    setStatus("connecting");
    setError(null);
    try {
      await loadAssessments(session.token);
      setStatus("ready");
    } catch (nextError) {
      setStatus("error");
      setError(errorMessage(nextError, "Unable to load your assessments."));
    }
  }

  async function completeSignIn(nextSession: Session) {
    const identityReference = await fetchIdentityReference(nextSession.token);
    identityReferenceRef.current = identityReference;
    identityMismatchRef.current = { consecutive: 0, lastEventAt: 0, checking: false };
    setIdentityEnrolled(Boolean(identityReference));
    setSession(nextSession);
    if (identityReference) await loadAssessments(nextSession.token);
    setLoginPassword("");
    setStatus("ready");
  }

  async function signIn(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setStatus("connecting");
    setError(null);
    try {
      const nextSession = await login(loginEmail.trim(), loginPassword);
      await completeSignIn(nextSession);
    } catch (nextError) {
      setSession(null);
      setStatus("error");
      setError(errorMessage(nextError, "Sign-in failed. Check your email and password."));
    }
  }

  async function requestCandidateActivation(email: string) {
    return api<{ email: string; message: string; dev_verification_code?: string | null }>(
      "/auth/activation/request",
      { method: "POST", body: JSON.stringify({ email }) },
    );
  }

  async function activateCandidateAccount(email: string, code: string, password: string) {
    setStatus("connecting");
    setError(null);
    try {
      const auth = await api<{ access_token: string; user: Session["user"] }>("/auth/activation/complete", {
        method: "POST",
        body: JSON.stringify({ email, code, password }),
      });
      await completeSignIn({ token: auth.access_token, user: auth.user });
    } catch (nextError) {
      setStatus("error");
      setError(errorMessage(nextError, "Account activation failed."));
      throw nextError;
    }
  }

  const activeAttempt =
    attempt && attempt.status !== "SUBMITTED" ? attempt : null;

  useEffect(() => {
    document.getElementById("main-content")?.focus();
    window.scrollTo(0, 0);
  }, [route.name]);

  useEffect(() => {
    const sync = () => setRoute(parseRoute(window.location.hash));
    window.addEventListener("hashchange", sync);
    return () => window.removeEventListener("hashchange", sync);
  }, []);

  useEffect(() => {
    if (!session) return;
    if (activeAttempt) {
      if (
        route.name !== "test" ||
        route.assessmentId !== activeAttempt.assessment_id
      ) {
        window.history.replaceState(
          null,
          "",
          routeHash({
            name: "test",
            assessmentId: activeAttempt.assessment_id,
          }),
        );
        setRoute({ name: "test", assessmentId: activeAttempt.assessment_id });
      }
      return;
    }
    if (route.name === "test" && !attempt) {
      window.history.replaceState(
        null,
        "",
        routeHash({ name: "setup", assessmentId: route.assessmentId }),
      );
      setRoute({ name: "setup", assessmentId: route.assessmentId });
    }
  }, [activeAttempt, route, session]);

  useEffect(() => {
    if (!session || activeAttempt) return;
    const setupId =
      route.name === "setup" || route.name === "test"
        ? route.assessmentId
        : null;
    if (!setupId || selected?.id === setupId) return;
    void loadAssessment(setupId);
  }, [session, activeAttempt, route, selected?.id]);

  useEffect(() => {
    if (attempt) {
      document.getElementById("main-content")?.focus();
      window.scrollTo(0, 0);
    }
  }, [attempt?.id]);

  useEffect(() => {
    if (attempt) {
      document.title = `${attempt.status === "SUBMITTED" ? "Submitted" : (selected?.title ?? "Assessment")} | ProctorAI Candidate`;
    } else if (route.name === "assessments") {
      document.title = `Your assessments | ProctorAI Candidate`;
    } else if (route.name === "home" || route.name === "help") {
      document.title = `${route.name === "home" ? "Dashboard" : "Help & guidance"} | ProctorAI Candidate`;
    } else {
      document.title = `Assessment setup | ProctorAI Candidate`;
    }
  }, [attempt?.id, attempt?.status, route.name, selected?.title]);

  useEffect(() => {
    if (isSubmitted) {
      stopScreenCapture();
    }
  }, [isSubmitted]);

  function trackIntegrityTask<T>(task: Promise<T>): Promise<T> {
    pendingIntegrityRef.current.add(task);
    void task.then(
      () => pendingIntegrityRef.current.delete(task),
      () => pendingIntegrityRef.current.delete(task),
    );
    return task;
  }

  function sendIntegrityEvent(
    ...args: Parameters<typeof performIntegrityEvent>
  ) {
    if (
      submissionPendingRef.current ||
      !enabled(selected?.rules, args[0] ?? "APP_FOCUS_LOST")
    )
      return Promise.resolve(null);
    return trackIntegrityTask(performIntegrityEvent(...args));
  }

  async function performIntegrityEvent(
    eventType = "APP_FOCUS_LOST",
    metadata: Record<string, unknown> = {
      source: "candidate-week5-runner",
      reason: "manual_dummy_event",
    },
    severity = "MEDIUM",
    priorityScore = 5,
    automatic = false,
    snapshotDataUrl?: string | null,
  ): Promise<IntegrityEvent | null> {
    if (!attempt || isSubmitted || !session) {
      if (!automatic)
        setError(
          "Start the assessment attempt before sending a monitoring event.",
        );
      return null;
    }

    const now = Date.now();
    if (automatic && now - (autoEventRef.current[eventType] ?? 0) < 5000)
      return null;
    autoEventRef.current[eventType] = now;
    const capturedAt = new Date().toISOString();
    const weight = riskWeight(eventType, priorityScore);
    const recentRiskItems = pruneRiskTimeline(riskTimeline, now);
    const nextRiskScore = Math.min(
      100,
      recentRiskItems.reduce((total, item) => total + item.weight, 0) + weight,
    );
    const riskItem: RiskTimelineItem = {
      id: crypto.randomUUID(),
      eventType,
      weight,
      occurredAt: capturedAt,
      source: String(metadata.source ?? "candidate-monitor"),
    };
    setRiskTimeline([...recentRiskItems, riskItem].slice(-30));
    const snapshot = isBrowserActivityEvent(eventType)
      ? null
      : (snapshotDataUrl ?? captureFrameDataUrl());
    const captureClip = shouldCaptureClip(eventType, snapshot);
    const proofKind = captureClip
      ? isBrowserActivityEvent(eventType)
        ? "SCREEN_RECORDING_CLIP"
        : "ROLLING_CLIP"
      : snapshot
        ? "CAMERA_SNAPSHOT"
        : "SESSION_LOG";
    const proof = {
      kind: proofKind,
      captured_at: capturedAt,
      source: metadata.source ?? "candidate-monitor",
      evidence_source: isBrowserActivityEvent(eventType) ? "screen" : "camera",
      screen_recording_active: Boolean(screenMediaRecorderRef.current),
      page_hidden: document.hidden,
      fullscreen_active: Boolean(document.fullscreenElement),
      viewport: { width: window.innerWidth, height: window.innerHeight },
      camera_snapshot: snapshot
        ? {
            data_url: snapshot,
            mime_type: snapshot.slice(5, snapshot.indexOf(";")) || "image/jpeg",
            size_bytes: snapshot.length,
            sha256_hash: await sha256Hex(snapshot),
          }
        : null,
      review_note: snapshot
        ? captureClip
          ? isBrowserActivityEvent(eventType)
            ? "Screen-recording clip captured locally with pre/post context around the browser activity signal."
            : "Rolling evidence clip captured locally with pre/post context around the signal."
          : "Camera snapshot captured locally at the time of the signal."
        : "Browser/session state captured at the time of the signal.",
    };

    const operation = buildOperation(
      "EVENT",
      `/attempts/${attempt.id}/events`,
      {
        event_type: eventType,
        severity,
        confidence:
          eventType === "IDENTITY_MISMATCH" ? 0.5 : automatic ? 1 : 0.88,
        priority_score: priorityScore,
        occurred_at: capturedAt,
        evidence_status: captureClip ? "PENDING" : "READY",
        metadata: {
          ...metadata,
          automatic,
          queued_from: "candidate-production-runner",
          risk: {
            score: nextRiskScore,
            label: riskLabel(nextRiskScore),
            weight,
            window_ms: RISK_WINDOW_MS,
            timeline_size: recentRiskItems.length + 1,
          },
          proof,
        },
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
      if (captureClip)
        void trackIntegrityTask(uploadEvidenceClip(event, capturedAt));
      if (!simulateOffline) setStatus("ready");
      return event;
    } catch (nextError) {
      if (shouldQueueOperation(nextError)) {
        enqueueOperation(operation);
      } else {
        setStatus("error");
        setError(errorMessage(nextError, "Monitoring event failed."));
      }
      return null;
    }
  }

  async function checkSidecarHealth() {
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 20000);
    try {
      const response = await fetch(`${AI_ENGINE_BASE}/health`, {
        signal: controller.signal,
      });
      if (!response.ok) throw new Error(`Sidecar returned ${response.status}`);
      const health = (await response.json()) as {
        status: string;
        model: AiModelInfo;
      };
      setAiModel(health.model);
      setFaceMonitor((current) => ({
        ...current,
        detail: `${health.model.detector} ready`,
      }));
      updateCheck(
        "sidecar",
        health.status === "ok" ? "pass" : "fail",
        health.status === "ok"
          ? "Local monitoring is available"
          : "Local monitoring is not ready. Restart the service and retry.",
      );
      return health.status === "ok";
    } catch (nextError) {
      setAiModel(null);
      setFaceMonitor((current) => ({
        ...current,
        status: "idle",
        detail: "Sidecar pending",
      }));
      updateCheck(
        "sidecar",
        "fail",
        `Local monitoring is unavailable: ${errorMessage(nextError, "health check failed")}`,
      );
      return false;
    } finally {
      window.clearTimeout(timeout);
    }
  }

  async function requestScreenCapture() {
    if (!navigator.mediaDevices?.getDisplayMedia) {
      setScreenMonitor({
        status: "unavailable",
        detail: "Screen recording is not supported in this browser",
      });
      return {
        passed: false,
        detail: "Screen recording is not supported in this browser.",
      };
    }

    screenCaptureRequestRef.current = true;
    try {
      setScreenMonitor({
        status: "requesting",
        detail: "Waiting for screen capture permission",
      });
      screenStreamRef.current?.getTracks().forEach((track) => track.stop());
      stopScreenRecorder();
      const stream = await navigator.mediaDevices.getDisplayMedia({
        video: {
          displaySurface: "monitor",
        },
        audio: false,
        monitorTypeSurfaces: "include",
        selfBrowserSurface: "exclude",
        surfaceSwitching: "exclude",
      } as DisplayMediaStreamOptions);
      const track = stream.getVideoTracks()[0];
      if (!track || track.readyState !== "live" || track.muted) {
        stream.getTracks().forEach((item) => item.stop());
        throw new Error("No live screen capture is available.");
      }
      const settings = track.getSettings() as MediaTrackSettings & {
        displaySurface?: string;
      };
      if (settings.displaySurface && settings.displaySurface !== "monitor") {
        stream.getTracks().forEach((item) => item.stop());
        throw new Error(
          "Select Entire screen/full display, not a browser tab or window.",
        );
      }

      screenStreamRef.current = stream;
      startScreenRecorder(stream);
      track.onended = () => {
        setScreenMonitor({
          status: "stopped",
          detail:
            "Screen recording stopped; browser-activity clips cannot be attached",
        });
        updateCheck(
          "screen",
          "fail",
          "Screen recording stopped. Share your screen again before continuing.",
        );
        stopScreenRecorder();
        if (attempt && !isSubmitted) {
          void sendIntegrityEvent(
            "SCREEN_RECORDING_STOPPED",
            {
              source: "screen_recording_monitor",
              review_note:
                "Screen recording was stopped during the active assessment.",
            },
            "HIGH",
            8,
            true,
          );
        }
      };
      setScreenMonitor({
        status: "active",
        detail: "Screen recording buffer active for browser-activity evidence",
      });
      return {
        passed: true,
        detail: track.label
          ? `Full display recording active: ${track.label}`
          : "Full display recording active",
      };
    } catch (nextError) {
      const detail = errorMessage(
        nextError,
        "Screen recording permission was not granted",
      );
      setScreenMonitor({ status: "denied", detail });
      return { passed: false, detail };
    } finally {
      screenCaptureRequestRef.current = false;
    }
  }

  async function auditConnectedDevices() {
    if (!navigator.mediaDevices?.enumerateDevices) {
      return {
        passed: false,
        detail: "Device enumeration is not supported in this browser.",
      };
    }

    await navigator.mediaDevices.enumerateDevices();
    const screenInfo = window.screen as Screen & { isExtended?: boolean };
    const getScreenDetails = (
      window as unknown as {
        getScreenDetails?: () => Promise<{
          screens: unknown[];
          currentScreen?: unknown;
        }>;
      }
    ).getScreenDetails;

    let displayDetail = "Single-display check unavailable in this browser";
    let extraDisplays = false;
    if (typeof screenInfo.isExtended === "boolean") {
      extraDisplays = screenInfo.isExtended;
      displayDetail = screenInfo.isExtended
        ? "extended display detected"
        : "single display";
    } else if (getScreenDetails) {
      try {
        const details = await getScreenDetails();
        extraDisplays = details.screens.length > 1;
        displayDetail = `${details.screens.length} display${details.screens.length === 1 ? "" : "s"} detected`;
      } catch {
        displayDetail =
          "display permission not granted for multi-monitor check";
      }
    }

    const issues: string[] = [];
    if (extraDisplays) issues.push("extra monitor/display detected");

    const summary = `${displayDetail}. Built-in cameras, microphones, speakers, and Bluetooth devices are allowed.`;
    return {
      passed: issues.length === 0,
      detail: issues.length
        ? `${issues.join("; ")}. Disconnect extra displays and check again. ${summary}`
        : `${summary} No extra display detected.`,
    };
  }

  function captureFrameDataUrl() {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (
      !video ||
      !canvas ||
      video.readyState < HTMLMediaElement.HAVE_CURRENT_DATA
    )
      return null;

    if (!video.videoWidth || !video.videoHeight) return null;
    const scale = Math.min(1, 640 / Math.max(video.videoWidth, video.videoHeight));
    canvas.width = Math.max(1, Math.round(video.videoWidth * scale));
    canvas.height = Math.max(1, Math.round(video.videoHeight * scale));
    const context = canvas.getContext("2d");
    if (!context) return null;
    context.drawImage(video, 0, 0, canvas.width, canvas.height);
    return canvas.toDataURL("image/jpeg", 0.76);
  }

  async function identityReferenceDataUrl() {
    if (identityReferenceRef.current) return identityReferenceRef.current;
    if (!session) throw new Error("Sign in with your university account to verify identity.");
    const reference = await fetchIdentityReference(session.token);
    if (!reference) throw new Error("No identity photo is registered for this account.");
    identityReferenceRef.current = reference;
    return reference;
  }

  async function fetchIdentityReference(token: string) {
    const response = await fetch(`${API_BASE}/identity/reference`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
      signal: AbortSignal.timeout(15000),
    });
    if (!response.ok) {
      if (response.status === 404) return null;
      const detail = await response.text();
      throw new Error(detail || "Could not load the university identity photo.");
    }
    const blob = await response.blob();
    const reference = await new Promise<string>((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => typeof reader.result === "string" ? resolve(reader.result) : reject(new Error("Could not read the university identity photo."));
      reader.onerror = () => reject(new Error("Could not read the university identity photo."));
      reader.readAsDataURL(blob);
    });
    return reference;
  }

  async function compareIdentityFrames(frameDataUrl: string, referenceDataUrl: string) {
    const response = await fetch(`${AI_ENGINE_BASE}/verify-identity`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ frame_data_url: frameDataUrl, reference_data_url: referenceDataUrl }),
      signal: AbortSignal.timeout(30000),
    });
    if (!response.ok) throw new Error((await response.text()) || "Identity verification service is unavailable.");
    return await response.json() as IdentityVerification;
  }

  async function verifyIdentityFrame(frameDataUrl: string) {
    return compareIdentityFrames(frameDataUrl, await identityReferenceDataUrl());
  }

  async function enrollIdentity(photoDataUrl: string) {
    if (!session) throw new Error("Sign in before enrolling your identity photo.");
    let verification: IdentityVerification;
    try {
      verification = await compareIdentityFrames(photoDataUrl, photoDataUrl);
    } catch {
      throw new Error("Identity verification is unavailable. Check the local AI service and retry.");
    }
    if (!verification.matched) {
      const detail = verification.reason === "no_face"
        ? "No face was found. Center your face in the frame and try again."
        : verification.reason === "multiple_faces"
          ? "More than one face was found. Make sure only you are visible and try again."
          : "The camera image could not be verified. Adjust your position and lighting, then retry.";
      throw new Error(detail);
    }

    const imageBlob = await (await fetch(photoDataUrl)).blob();
    if (imageBlob.size > 1024 * 1024) throw new Error("Captured photo is too large. Please retry.");
    const form = new FormData();
    form.append("image", imageBlob, "identity.jpg");
    const response = await fetch(`${API_BASE}/identity/reference`, {
      method: "POST",
      headers: { Authorization: `Bearer ${session.token}` },
      body: form,
      signal: AbortSignal.timeout(15000),
    });
    if (!response.ok) {
      let message = "Could not save your identity photo.";
      try {
        const body = await response.json() as { detail?: string };
        if (body.detail) message = body.detail;
      } catch {}
      throw new Error(message);
    }
    identityReferenceRef.current = photoDataUrl;
    setIdentityEnrolled(true);
    await loadAssessments(session.token);
  }

  async function checkIdentityForSetup(frameDataUrl: string) {
    const result = await verifyIdentityFrame(frameDataUrl);
    const detail = result.matched
      ? "Identity matches the university photo linked to this account."
      : result.reason === "no_face"
        ? "No face was found. Center your face in the camera and try again."
        : result.reason === "multiple_faces"
          ? "More than one face was found. Make sure only you are visible and try again."
          : result.reason.startsWith("reference_")
            ? "The university photo could not be verified. Contact your university to update it."
            : "Your face did not match the university photo. Adjust lighting and try again.";
    return { passed: result.matched, detail, similarity: result.similarity };
  }

  async function analyzeIdentitySample() {
    if (!monitoringActive || !required.identity || !attempt || !session || identityMismatchRef.current.checking) return;
    const frameDataUrl = captureFrameDataUrl();
    if (!frameDataUrl) return;
    identityMismatchRef.current.checking = true;
    setIdentityMonitor((current) => ({
      ...current,
      status: "checking",
      detail: "Checking the live face against the enrolled identity photo",
    }));
    try {
      const result = await verifyIdentityFrame(frameDataUrl);
      const checkedAt = new Date().toISOString();
      if (result.matched) {
        identityMismatchRef.current.consecutive = 0;
        setIdentityMonitor({
          status: "matched",
          faceCount: result.face_count,
          similarity: result.similarity,
          checkedAt,
          detail: "Live face matches the enrolled identity photo",
        });
        return;
      }
      identityMismatchRef.current.consecutive += 1;
      const detail = result.reason === "multiple_faces"
        ? `${result.face_count} faces detected; only the candidate should be visible`
        : result.reason === "no_face"
          ? "No face detected; center your face in the camera"
          : result.reason.startsWith("reference_")
            ? "Enrolled identity photo could not be verified; contact support"
            : "Live face does not match the enrolled identity photo";
      setIdentityMonitor({
        status: "review",
        faceCount: result.face_count,
        similarity: result.similarity,
        checkedAt,
        detail: `${detail} (${identityMismatchRef.current.consecutive}/2 checks)`,
      });
      const now = Date.now();
      if (identityMismatchRef.current.consecutive < 2 || now - identityMismatchRef.current.lastEventAt < 5 * 60_000) return;
      identityMismatchRef.current.lastEventAt = now;
      const event = await sendIntegrityEvent("IDENTITY_MISMATCH", {
        source: "periodic_face_identity_check",
        candidate_email: session.user.email,
        similarity: result.similarity,
        threshold: result.threshold,
        verification_result: result.reason,
        face_count: result.face_count,
        consecutive_mismatches: identityMismatchRef.current.consecutive,
        detector: result.detector,
        recognizer: result.recognizer,
        review_note: "Identity could not be confirmed. Send to a proctor for human review; do not make an automatic misconduct decision.",
      }, "HIGH", 12, true, frameDataUrl);
      setIdentityMonitor((current) => ({
        ...current,
        detail: event
          ? `${detail}; sent to the proctor for review`
          : `${detail}; proctor event could not be synced yet`,
      }));
    } catch (error) {
      setIdentityMonitor((current) => ({
        ...current,
        status: "error",
        checkedAt: new Date().toISOString(),
        detail: errorMessage(error, "Identity check failed; check the AI service and enrolled photo"),
      }));
    } finally {
      identityMismatchRef.current.checking = false;
    }
  }

  async function analyzeFaceSample(
    observedFaceCount?: number,
    source = "camera_sampler",
  ) {
    if (!attempt || isSubmitted || !sidecarReady || !required.face) return;
    const frameDataUrl =
      observedFaceCount === undefined ? captureFrameDataUrl() : null;
    if (observedFaceCount === undefined && frameDataUrl === null) {
      setFaceMonitor((current) => ({
        ...current,
        status: "waiting",
        detail: "Waiting for camera frame",
      }));
      return;
    }

    try {
      const response = await fetch(`${AI_ENGINE_BASE}/analyze-frame`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          session_id: attempt.id,
          frame_data_url: frameDataUrl,
          ...(observedFaceCount === undefined
            ? {}
            : { observed_face_count: observedFaceCount }),
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
            face_count: analysis.face_count,
            model: analysis.model,
          },
          event.severity,
          event.priority_score,
          true,
          frameDataUrl,
        );
      }

      if (
        analysis.events.length === 0 &&
        analysis.face_count === 0 &&
        analysis.state.consecutive_absent_frames >= 2
      ) {
        await sendIntegrityEvent(
          "FACE_ABSENT",
          {
            source,
            detector: "candidate_face_fallback",
            ai_engine_url: AI_ENGINE_BASE,
            samples_analyzed: analysis.state.samples_analyzed,
            face_count: analysis.face_count,
            consecutive_absent_frames: analysis.state.consecutive_absent_frames,
            model: analysis.model,
            review_note:
              "Candidate-side fallback sent this event because the face count stayed at zero.",
          },
          "HIGH",
          8,
          true,
          frameDataUrl,
        );
      }

      if (
        analysis.events.length === 0 &&
        analysis.face_count > 1 &&
        analysis.state.consecutive_multiple_frames >= 2
      ) {
        await sendIntegrityEvent(
          "MULTIPLE_PERSONS",
          {
            source,
            detector: "candidate_face_fallback",
            ai_engine_url: AI_ENGINE_BASE,
            samples_analyzed: analysis.state.samples_analyzed,
            face_count: analysis.face_count,
            consecutive_multiple_frames:
              analysis.state.consecutive_multiple_frames,
            model: analysis.model,
            review_note:
              "Candidate-side fallback sent this event because multiple faces persisted.",
          },
          "HIGH",
          9,
          true,
          frameDataUrl,
        );
      }
    } catch (nextError) {
      setFaceMonitor((current) => ({
        ...current,
        status: "error",
        detail:
          nextError instanceof Error
            ? nextError.message
            : "Face analysis failed",
      }));
      void sendIntegrityEvent(
        "AI_ENGINE_INTERRUPTED",
        {
          source: "ai_sidecar",
          reason: "frame_analysis_failed",
          ai_engine_url: AI_ENGINE_BASE,
          error:
            nextError instanceof Error
              ? nextError.message
              : "Face analysis failed",
        },
        "HIGH",
        8,
        true,
        frameDataUrl,
      );
    }
  }

  async function runFaceDemo(observedFaceCount: number) {
    const samples = observedFaceCount > 1 ? 2 : 3;
    for (let index = 0; index < samples; index += 1) {
      await analyzeFaceSample(observedFaceCount, "manual_face_demo");
    }
  }

  async function analyzeObjectSample() {
    if (!attempt || isSubmitted || !required.phone) return;
    if (objectSignalRef.current.analyzing) return;
    const frameDataUrl = captureFrameDataUrl();
    if (!frameDataUrl) {
      setObjectMonitor((current) => ({
        ...current,
        status: "waiting",
        detail: "Waiting for camera frame",
      }));
      return;
    }

    objectSignalRef.current.analyzing = true;

    try {
      const response = await fetch(`${AI_ENGINE_BASE}/detect-objects`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          session_id: attempt.id,
          frame_data_url: frameDataUrl,
          config: {
            min_confidence: 0.12,
            max_detections: 20,
            phone_like_classes: ["cell phone", "remote"],
          },
        }),
      });
      if (!response.ok) throw new Error(await response.text());

      const analysis = (await response.json()) as YoloObjectResponse;
      const phone = analysis.phone_like_objects.sort(
        (left, right) => right.confidence - left.confidence,
      )[0];
      const topDetection = [...analysis.objects].sort(
        (left, right) => right.confidence - left.confidence,
      )[0];
      const topLabels = analysis.objects
        .slice(0, 3)
        .map(
          (item) => `${item.class_name} ${(item.confidence * 100).toFixed(0)}%`,
        )
        .join(", ");
      objectSignalRef.current.consecutivePhoneSamples = phone
        ? objectSignalRef.current.consecutivePhoneSamples + 1
        : 0;
      objectSignalRef.current.consecutiveClearSamples = phone
        ? 0
        : objectSignalRef.current.consecutiveClearSamples + 1;
      if (!phone && objectSignalRef.current.consecutiveClearSamples >= 3) {
        objectSignalRef.current.activePhoneEventId = null;
      }

      setObjectMonitor({
        status: phone ? "candidate" : "scanning",
        label: phone
          ? `${phone.class_name} candidate`
          : topDetection
            ? topDetection.class_name
            : "No phone",
        confidence: phone
          ? phone.confidence
          : (topDetection?.confidence ?? null),
        detail: phone
          ? `${objectSignalRef.current.consecutivePhoneSamples}/2 phone-like samples`
          : topLabels
            ? `YOLO scanning | ${topLabels}`
            : `YOLO scanning with ${analysis.model.model_path ?? analysis.model.detector}`,
      });

      const confidentPhoneSample = Boolean(phone && phone.confidence >= 0.25);
      const persistentPhoneSample =
        objectSignalRef.current.consecutivePhoneSamples >= 2;
      if (
        phone &&
        (confidentPhoneSample || persistentPhoneSample) &&
        !objectSignalRef.current.activePhoneEventId
      ) {
        const event = await sendIntegrityEvent(
          "PHONE_DETECTED",
          {
            ...analysis.events[0]?.metadata,
            source: "object_detector",
            detector: analysis.model.detector,
            model: analysis.model,
            object_type: phone.class_name,
            confidence: Number(phone.confidence.toFixed(4)),
            bbox: phone.bbox,
            min_score: 0.12,
            consecutive_phone_samples:
              objectSignalRef.current.consecutivePhoneSamples,
            trigger_reason: confidentPhoneSample
              ? "single_high_confidence_sample"
              : "consecutive_samples",
            detections: analysis.objects.map((item) => ({
              class: item.class_name,
              score: Number(item.confidence.toFixed(4)),
              bbox: item.bbox,
              scratch_classifier: item.scratch_classifier ?? null,
            })),
            review_note:
              "YOLO object detector found a phone-like object in consecutive camera frames.",
          },
          "HIGH",
          9,
          true,
          frameDataUrl,
        );
        if (event) objectSignalRef.current.activePhoneEventId = event.id;
        setObjectMonitor((current) => ({
          ...current,
          status: "event",
          detail: "Phone event sent to proctor",
        }));
      }
    } catch (nextError) {
      setObjectMonitor({
        status: "error",
        label: "Detector error",
        confidence: null,
        detail:
          nextError instanceof Error
            ? nextError.message
            : "Phone detection failed",
      });
      void sendIntegrityEvent(
        "AI_ENGINE_INTERRUPTED",
        {
          source: "object_detector",
          detector: "ultralytics-yolo",
          reason: "object_detection_failed",
          error:
            nextError instanceof Error
              ? nextError.message
              : "Phone detection failed",
        },
        "HIGH",
        8,
        true,
      );
    } finally {
      objectSignalRef.current.analyzing = false;
    }
  }

  function sendPhoneObjectEvent() {
    void sendIntegrityEvent(
      "PHONE_DETECTED",
      {
        source: "manual_object_demo",
        detector: "candidate_review_control",
        object_type: "phone",
        review_note:
          "Phone/object integrity event captured with the current camera proof frame.",
      },
      "HIGH",
      9,
      false,
    );
  }

  function sendBackgroundVoiceEvent() {
    void sendIntegrityEvent(
      "BACKGROUND_SPEECH",
      {
        source: "manual_audio_demo",
        detector: "candidate_review_control",
        signal: "background_voice_or_noise",
        review_note:
          "Background voice/noise integrity event captured with the current session proof.",
      },
      "MEDIUM",
      7,
      false,
    );
  }

  function readinessMetrics() {
    return {
      consent_accepted: consentAccepted,
      consent_accepted_at: consentAcceptedAt,
      consent_version: "candidate-preflight-v1",
      checks: Object.fromEntries(
        readinessChecks.map((check) => [
          check.key,
          { status: check.status, detail: check.detail },
        ]),
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
        void sendIntegrityEvent(
          "FULLSCREEN_EXIT",
          { source: "fullscreen_monitor" },
          "HIGH",
          8,
          true,
        );
      }
    };

    document.addEventListener("fullscreenchange", handleFullscreenChange);
    return () =>
      document.removeEventListener("fullscreenchange", handleFullscreenChange);
  }, [monitoringActive, session?.token, simulateOffline, selected?.rules]);

  useEffect(() => {
    if (!monitoringActive || !enabled(selected?.rules, "APP_FOCUS_LOST"))
      return;

    const handleFocusLost = () => {
      void sendIntegrityEvent(
        "APP_FOCUS_LOST",
        { source: "focus_monitor" },
        "MEDIUM",
        5,
        true,
      );
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
  }, [monitoringActive, sidecarReady, session?.token, simulateOffline]);

  useEffect(() => {
    if (!monitoringActive) return;
    void sendHeartbeat("periodic");
    const interval = window.setInterval(
      () => void sendHeartbeat("periodic"),
      10000,
    );
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
    if (!monitoringActive) return;
    const interval = window.setInterval(() => {
      setRiskTimeline((current) => pruneRiskTimeline(current));
    }, 2000);
    return () => window.clearInterval(interval);
  }, [monitoringActive]);

  useEffect(() => {
    if (!monitoringActive) return;

    const sendClipboardSignal = (
      event: ClipboardEvent,
      action: "copy" | "cut" | "paste",
    ) => {
      const eventType =
        action === "paste"
          ? "CLIPBOARD_PASTE"
          : action === "cut"
            ? "CLIPBOARD_CUT"
            : "CLIPBOARD_COPY";
      if (!enabled(selected?.rules, eventType)) return;
      event.preventDefault();
      void sendIntegrityEvent(
        eventType,
        {
          source: "clipboard_monitor",
          action,
          target: targetSummary(event.target),
          selected_text_length: window.getSelection()?.toString().length ?? 0,
          review_note:
            "Clipboard activity was blocked during the active assessment and sent for proctor review.",
        },
        action === "paste" ? "HIGH" : "MEDIUM",
        action === "paste" ? 7 : 6,
        true,
      );
    };

    const handleKeyDown = (event: KeyboardEvent) => {
      const key = event.key.toLowerCase();
      const shortcut = [
        event.ctrlKey ? "ctrl" : null,
        event.metaKey ? "meta" : null,
        event.altKey ? "alt" : null,
        event.shiftKey ? "shift" : null,
        key,
      ]
        .filter(Boolean)
        .join("+");

      if (event.key === "PrintScreen") {
        void sendIntegrityEvent(
          "PRINT_SCREEN_ATTEMPT",
          {
            source: "keyboard_monitor",
            shortcut,
            review_note: "Print screen key was pressed during the assessment.",
          },
          "HIGH",
          7,
          true,
        );
      }

      const devtoolsShortcut =
        event.key === "F12" ||
        ((event.ctrlKey || event.metaKey) &&
          event.shiftKey &&
          ["i", "j", "c"].includes(key));
      if (devtoolsShortcut && enabled(selected?.rules, "DEVTOOLS_SHORTCUT")) {
        event.preventDefault();
        void sendIntegrityEvent(
          "DEVTOOLS_SHORTCUT",
          {
            source: "keyboard_monitor",
            shortcut,
            review_note:
              "Developer-tools shortcut was blocked during the assessment.",
          },
          "MEDIUM",
          6,
          true,
        );
      }
    };

    const handleCopy = (event: ClipboardEvent) =>
      sendClipboardSignal(event, "copy");
    const handleCut = (event: ClipboardEvent) =>
      sendClipboardSignal(event, "cut");
    const handlePaste = (event: ClipboardEvent) =>
      sendClipboardSignal(event, "paste");

    document.addEventListener("copy", handleCopy);
    document.addEventListener("cut", handleCut);
    document.addEventListener("paste", handlePaste);
    window.addEventListener("keydown", handleKeyDown);

    return () => {
      document.removeEventListener("copy", handleCopy);
      document.removeEventListener("cut", handleCut);
      document.removeEventListener("paste", handlePaste);
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [monitoringActive, session?.token, simulateOffline, riskTimeline]);

  useEffect(() => {
    if (
      !monitoringActive ||
      !enabled(selected?.rules, "SCREEN_SHARE_ATTEMPT") ||
      !navigator.mediaDevices?.getDisplayMedia
    )
      return;
    const mediaDevices = navigator.mediaDevices;
    const originalGetDisplayMedia =
      mediaDevices.getDisplayMedia.bind(mediaDevices);
    mediaDevices.getDisplayMedia = async (
      constraints?: DisplayMediaStreamOptions,
    ) => {
      if (screenCaptureRequestRef.current) {
        return originalGetDisplayMedia(constraints);
      }
      await sendIntegrityEvent(
        "SCREEN_SHARE_ATTEMPT",
        {
          source: "screen_capture_monitor",
          constraints_requested: Boolean(constraints),
          review_note:
            "A screen-capture request was initiated during the active assessment.",
        },
        "HIGH",
        8,
        true,
      );
      return originalGetDisplayMedia(constraints);
    };
    return () => {
      mediaDevices.getDisplayMedia = originalGetDisplayMedia;
    };
  }, [monitoringActive, session?.token, simulateOffline, riskTimeline]);

  useEffect(() => {
    if (
      !monitoringActive ||
      !enabled(selected?.rules, "HEARTBEAT_GAP") ||
      heartbeatGapNotified
    )
      return;
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
  }, [
    monitoringActive,
    heartbeatGapNotified,
    lastHeartbeatAckAt,
    session?.token,
    simulateOffline,
  ]);

  useEffect(() => {
    if (
      !monitoringActive ||
      !required.camera ||
      !navigator.mediaDevices?.getUserMedia
    ) {
      return;
    }

    let cancelled = false;
    const notifyCameraDisabled = (reason: string) => {
      void sendIntegrityEvent(
        "CAMERA_DISABLED",
        { source: "camera_sampler", reason },
        "HIGH",
        8,
        true,
      );
    };

    navigator.mediaDevices
      .getUserMedia({ video: { width: { ideal: 640 }, height: { ideal: 480 } }, audio: false })
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
        startRollingRecorder(stream);
        stream.getVideoTracks().forEach((track) => {
          track.onended = () => notifyCameraDisabled("camera_track_ended");
          track.onmute = () => notifyCameraDisabled("camera_track_muted");
        });
        setFaceMonitor((current) => ({
          ...current,
          status: sidecarReady ? "camera" : "camera-only",
          detail: sidecarReady
            ? "Camera sampler active"
            : "Camera active; face sidecar pending",
        }));
      })
      .catch(() => {
        setFaceMonitor((current) => ({
          ...current,
          status: "warning",
          detail: "Camera stream unavailable",
        }));
        notifyCameraDisabled("camera_stream_unavailable");
      });

    return () => {
      cancelled = true;
      streamRef.current?.getVideoTracks().forEach((track) => {
        track.onended = null;
        track.onmute = null;
      });
      streamRef.current?.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
      stopRollingRecorder();
    };
  }, [monitoringActive, session?.token, simulateOffline]);

  useEffect(() => {
    if (
      !monitoringActive ||
      !required.microphone ||
      !navigator.mediaDevices?.getUserMedia
    ) {
      return;
    }

    let cancelled = false;
    let audioContext: AudioContext | null = null;
    let intervalId = 0;
    const notifyMicrophoneDisabled = (
      reason: string,
      severity = "HIGH",
      priorityScore = 8,
    ) => {
      void sendIntegrityEvent(
        "MICROPHONE_DISABLED",
        { source: "microphone_monitor", reason },
        severity,
        priorityScore,
        true,
      );
    };

    navigator.mediaDevices
      .getUserMedia({ video: false, audio: true })
      .then((stream) => {
        if (cancelled) {
          stream.getTracks().forEach((track) => track.stop());
          return;
        }

        microphoneStreamRef.current = stream;
        stream.getAudioTracks().forEach((track) => {
          track.onended = () =>
            notifyMicrophoneDisabled("microphone_track_ended");
          track.onmute = () =>
            notifyMicrophoneDisabled("microphone_track_muted", "MEDIUM", 7);
        });

        audioContext = new AudioContext();
        const analyser = audioContext.createAnalyser();
        analyser.fftSize = 512;
        audioContext.createMediaStreamSource(stream).connect(analyser);
        const timeDomainData = new Uint8Array(analyser.fftSize);
        const threshold = 0.08;
        const minimumSamples = 6;
        const cooldownMs = 15000;

        intervalId = window.setInterval(() => {
          analyser.getByteTimeDomainData(timeDomainData);
          let sumSquares = 0;
          for (const value of timeDomainData) {
            const centered = (value - 128) / 128;
            sumSquares += centered * centered;
          }
          const rms = Math.sqrt(sumSquares / timeDomainData.length);
          audioSignalRef.current.consecutiveLoudSamples =
            rms > threshold
              ? audioSignalRef.current.consecutiveLoudSamples + 1
              : 0;

          if (
            audioSignalRef.current.consecutiveLoudSamples >= minimumSamples &&
            Date.now() - audioSignalRef.current.lastSentAt > cooldownMs
          ) {
            audioSignalRef.current.lastSentAt = Date.now();
            void sendIntegrityEvent(
              "BACKGROUND_SPEECH",
              {
                source: "microphone_monitor",
                detector: "browser_audio_rms",
                signal: "sustained_audio_level",
                rms: Number(rms.toFixed(4)),
                threshold,
                samples_above_threshold:
                  audioSignalRef.current.consecutiveLoudSamples,
                review_note:
                  "Sustained microphone activity detected; review for background voice or noise.",
              },
              "MEDIUM",
              7,
              true,
            );
          }
        }, 500);
      })
      .catch(() => notifyMicrophoneDisabled("microphone_stream_unavailable"));

    return () => {
      cancelled = true;
      if (intervalId) window.clearInterval(intervalId);
      microphoneStreamRef.current?.getAudioTracks().forEach((track) => {
        track.onended = null;
        track.onmute = null;
      });
      microphoneStreamRef.current?.getTracks().forEach((track) => track.stop());
      microphoneStreamRef.current = null;
      audioSignalRef.current.consecutiveLoudSamples = 0;
      objectSignalRef.current.consecutivePhoneSamples = 0;
      objectSignalRef.current.consecutiveClearSamples = 0;
      objectSignalRef.current.activePhoneEventId = null;
      void audioContext?.close();
    };
  }, [monitoringActive, session?.token, simulateOffline]);

  useEffect(() => {
    if (!monitoringActive || !sidecarReady || !required.face) return;
    const interval = window.setInterval(() => void analyzeFaceSample(), 3000);
    return () => window.clearInterval(interval);
  }, [monitoringActive, sidecarReady, attempt?.id, required.face]);

  useEffect(() => {
    identityMismatchRef.current = { consecutive: 0, lastEventAt: 0, checking: false };
    setIdentityMonitor(initialIdentityMonitor);
    if (!monitoringActive || !required.identity) return;
    void analyzeIdentitySample();
    const firstRetry = window.setTimeout(() => void analyzeIdentitySample(), 3000);
    const interval = window.setInterval(() => void analyzeIdentitySample(), 60_000);
    return () => {
      window.clearTimeout(firstRetry);
      window.clearInterval(interval);
    };
  }, [monitoringActive, attempt?.id, required.identity, session?.token]);

  useEffect(() => {
    if (!monitoringActive || !required.phone) return;
    void analyzeObjectSample();
    const interval = window.setInterval(() => void analyzeObjectSample(), 2000);
    return () => window.clearInterval(interval);
  }, [monitoringActive, attempt?.id, required.phone]);

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
      const health = await api<{ status: string }>(
        "/health",
        {},
        simulateOffline,
      );
      updateCheck(
        "backend",
        health.status === "ok" ? "pass" : "fail",
        health.status === "ok"
          ? "Assessment service is available"
          : "Assessment service is not ready. Retry in a moment.",
      );
    } catch {
      updateCheck(
        "backend",
        "fail",
        "Assessment service is unavailable. Check your connection and retry.",
      );
    }

    if (required.sidecar) await checkSidecarHealth();

    updateCheck(
      "fullscreen",
      document.fullscreenElement ? "pass" : "warning",
      document.fullscreenElement ? "Fullscreen active" : "Fullscreen inactive",
    );
    setStatus("ready");
  }

  function handleConsent(accepted: boolean) {
    setConsentAccepted(accepted);
    setConsentAcceptedAt(accepted ? new Date().toISOString() : null);
    if (!accepted) {
      stopScreenCapture();
    }
  }

  async function startAttempt() {
    if (!selected) return;
    if (
      !canStartAttempt ||
      (required.fullscreen && !document.fullscreenElement)
    ) {
      setError(
        "Complete consent and the enabled requirement checks before starting.",
      );
      return;
    }

    setStatus("saving");
    setError(null);
    try {
      const health = await api<{ status: string }>(
        "/health",
        {},
        simulateOffline,
      ).catch(() => null);
      if (health?.status !== "ok") {
        updateCheck(
          "backend",
          "fail",
          "Assessment service is unavailable. Check your connection and retry.",
        );
        throw new Error(
          "The assessment connection changed. Repeat the system check before starting.",
        );
      }
      if (required.sidecar && !(await checkSidecarHealth())) {
        throw new Error(
          "Local monitoring is unavailable. Repeat the system check before starting.",
        );
      }
      if (
        required.screen &&
        (!screenMediaRecorderRef.current ||
          !screenStreamRef.current
            ?.getVideoTracks()
            .some((track) => track.readyState === "live"))
      ) {
        updateCheck(
          "screen",
          "fail",
          "Screen recording is not active. Share your screen before starting.",
        );
        throw new Error(
          "Screen recording is required before starting the assessment.",
        );
      }
      if (required.fullscreen && !document.fullscreenElement)
        throw new Error("Restore fullscreen before starting the assessment.");
      if (
        !readinessRef.current.consentAccepted ||
        readinessRef.current.readinessChecks
          .filter((check) => requiredCheck(check.key, selected.rules))
          .some((check) => check.status !== "pass")
      ) {
        throw new Error(
          "A requirement changed. Complete the remaining checks before starting.",
        );
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
      setAttemptedAssessmentIds((current) =>
        current.includes(detail.assessment_id)
          ? current
          : [...current, detail.assessment_id],
      );
      setDraftAnswers(
        Object.fromEntries(
          detail.answers.map((answer) => [
            answer.question_id,
            answer.selected_option ?? answer.answer_text ?? "",
          ]),
        ),
      );
      setStatus("ready");
      if (detail.status !== "SUBMITTED")
        void sendHeartbeat("attempt_started", started.attempt_id);
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
    if (!attempt || submissionPendingRef.current) return;
    if (retryQueue.length > 0) {
      setError(
        "Queued answers or monitoring events must sync before submission.",
      );
      return;
    }

    submissionPendingRef.current = true;
    setSubmitting(true);
    setStatus("saving");
    setError(null);
    try {
      // Keep the attempt writable until every already-captured clip is persisted.
      // Event POSTs may add upload tasks while the first batch is draining.
      while (pendingIntegrityRef.current.size) {
        await Promise.allSettled([...pendingIntegrityRef.current]);
      }
      if (retryQueueRef.current.length)
        throw new Error(
          "Queued monitoring events must sync before submission.",
        );
      const result = await api<{
        status: string;
        score: number;
        answers: Answer[];
      }>(
        `/attempts/${attempt.id}/submit`,
        { method: "POST", headers: authHeaders },
        simulateOffline,
      );
      setAttempt((current) =>
        current
          ? {
              ...current,
              status: result.status,
              score: result.score,
              answers: result.answers,
            }
          : current,
      );
      setAssessments((current) =>
        current.map((assessment) =>
          assessment.id === attempt.assessment_id
            ? { ...assessment, attempt_status: "SUBMITTED" }
            : assessment,
        ),
      );
      setStatus("ready");
    } catch (nextError) {
      setStatus("error");
      setError(errorMessage(nextError, "Submit failed."));
    } finally {
      submissionPendingRef.current = false;
      setSubmitting(false);
    }
  }

  async function requestFullscreen() {
    setError(null);
    try {
      await document.documentElement.requestFullscreen();
    } catch (nextError) {
      updateCheck(
        "fullscreen",
        "fail",
        "Fullscreen could not be enabled. Use a supported desktop browser and retry.",
      );
      setError(
        nextError instanceof Error
          ? nextError.message
          : "Fullscreen request failed.",
      );
    }
  }

  function openAssessment(assessmentId: string) {
    window.location.hash = `/assessments/${assessmentId}/setup`;
  }

  function returnToAssessments() {
    setAttempt(null);
    setConsentAccepted(false);
    setConsentAcceptedAt(null);
    setReadinessChecks(initialChecks);
    setDraftAnswers({});
    setLastHeartbeatAckAt(null);
    setRiskTimeline([]);
    stopScreenCapture();
    window.location.hash = "/assessments";
  }

  const busyStatus = ["connecting", "loading", "checking", "saving"].includes(
    status,
  );
  const setupAssessment =
    !attempt &&
    selected &&
    (route.name === "setup" || route.name === "test") &&
    route.assessmentId === selected.id
      ? selected
      : null;
  const testAssessment =
    attempt && selected && attempt.assessment_id === selected.id
      ? selected
      : null;

  if (!session) {
    return (
      <LoginPage
        email={loginEmail}
        password={loginPassword}
        busy={status === "connecting"}
        error={error}
        onEmailChange={setLoginEmail}
        onPasswordChange={setLoginPassword}
        onSubmit={signIn}
        onRequestActivation={requestCandidateActivation}
        onActivate={activateCandidateAccount}
      />
    );
  }

  if (!identityEnrolled) {
    return (
      <IdentityEnrollmentPage
        name={session.user.full_name}
        email={session.user.email}
        busy={status === "connecting" || status === "loading"}
        error={error}
        onEnroll={enrollIdentity}
      />
    );
  }

  return (
    <div className={`candidate-shell${attempt ? " exam-shell" : ""}`}>
      <a
        className="skip-link"
        href="#main-content"
        onClick={(event) => {
          event.preventDefault();
          document.getElementById("main-content")?.focus();
        }}
      >
        Skip to main content
      </a>
      <header className="app-header">
        <a
          className="brand"
          href={attempt ? undefined : "#/dashboard"}
          aria-label="ProctorAI candidate dashboard"
        >
          <ShieldCheck size={26} aria-hidden="true" />
          <span>
            Proctor<span className="brand-ai">AI</span>
          </span>
          <span className="portal-label">Candidate workspace</span>
        </a>
        {!attempt ? (
          <nav className="candidate-nav" aria-label="Candidate navigation">
            <a
              href="#/dashboard"
              className={route.name === "home" ? "active" : ""}
              aria-current={route.name === "home" ? "page" : undefined}
            >
              <LayoutDashboard size={16} />
              Dashboard
            </a>
            <a
              href="#/assessments"
              className={
                ["assessments", "setup"].includes(route.name) ? "active" : ""
              }
              aria-current={route.name === "assessments" ? "page" : undefined}
            >
              <BookOpen size={16} />
              My assessments
            </a>
            <a
              href="#/help"
              className={route.name === "help" ? "active" : ""}
              aria-current={route.name === "help" ? "page" : undefined}
            >
              <CircleHelp size={16} />
              Help & guidance
            </a>
          </nav>
        ) : (
          <span className="exam-header-label">
            <ShieldCheck size={14} />
            Assessment in progress
          </span>
        )}
        <div className="candidate-header-tools">
          <div
            className={`network ${simulateOffline ? "offline" : status}`}
            aria-live="polite"
          >
            {simulateOffline ? (
              <WifiOff size={16} aria-hidden="true" />
            ) : (
              <Wifi size={16} aria-hidden="true" />
            )}
            {simulateOffline
              ? "Offline"
              : status === "ready"
                ? "Connected"
                : status === "saving"
                  ? "Saving…"
                  : status === "error"
                    ? "Connection issue"
                    : "Connecting…"}
          </div>
          <span className="candidate-avatar" title={session?.user.full_name}>
            {session?.user.full_name
              .split(" ")
              .map((part) => part[0])
              .slice(0, 2)
              .join("") || "C"}
          </span>
        </div>
      </header>

      {error ? (
        <div className="error-panel" role="alert">
          {error}
        </div>
      ) : null}

      {attempt ? (
        <TestPage
          key={attempt.id}
          assessment={testAssessment}
          attempt={attempt}
          draftAnswers={draftAnswers}
          fullscreenActive={fullscreenActive}
          saving={submitting || status === "saving"}
          simulateOffline={simulateOffline}
          monitoringActive={monitoringActive}
          sidecarReady={sidecarReady}
          faceMonitor={faceMonitor}
          identityMonitor={identityMonitor}
          objectMonitor={objectMonitor}
          screenMonitor={screenMonitor}
          aiModel={aiModel}
          liveRiskScore={liveRiskScore}
          liveRiskLabel={liveRiskLabel}
          lastHeartbeatAckAt={lastHeartbeatAckAt}
          retryQueue={retryQueue}
          lastEvent={lastEvent}
          videoRef={videoRef}
          canvasRef={canvasRef}
          onAnswer={saveAnswer}
          onDraftChange={(questionId, value) =>
            setDraftAnswers((current) => ({ ...current, [questionId]: value }))
          }
          onSubmit={submitAttempt}
          onFlushQueue={flushQueue}
          onSimulateOfflineChange={setSimulateOffline}
          onRequestFullscreen={requestFullscreen}
          onExit={returnToAssessments}
          sendIntegrityEvent={sendIntegrityEvent}
          onFaceDemo={runFaceDemo}
          onPhoneDemo={sendPhoneObjectEvent}
          onVoiceDemo={sendBackgroundVoiceEvent}
        />
      ) : route.name === "home" ? (
        <CandidateHome
          assessments={assessments}
          name={session?.user.full_name ?? ""}
          connected={Boolean(session)}
          onOpen={openAssessment}
        />
      ) : route.name === "help" ? (
        <CandidateHelp />
      ) : route.name === "assessments" ? (
        <AssessmentsPage
          assessments={assessments}
          connected={Boolean(session)}
          busy={busyStatus}
          attemptedAssessmentIds={attemptedAssessmentIds}
          onRefresh={refreshAssessments}
          onOpen={openAssessment}
        />
      ) : (
        <SetupPage
          key={route.assessmentId}
          step={route.name === "setup" ? (route.step ?? "consent") : "consent"}
          assessment={setupAssessment}
          checks={readinessChecks}
          consent={consentAccepted}
          busy={busyStatus}
          error={error}
          canStart={canStartAttempt}
          starting={status === "saving"}
          onBack={() => {
            window.location.hash = "/assessments";
          }}
          onReload={() => {
            void loadAssessment(route.assessmentId);
          }}
          onConsent={handleConsent}
          onCheck={updateCheck}
          onSystemCheck={runReadinessChecks}
          onScreenCapture={requestScreenCapture}
          onDeviceAudit={auditConnectedDevices}
          onIdentityVerify={checkIdentityForSetup}
          onFullscreen={requestFullscreen}
          onStart={startAttempt}
        />
      )}
      {!attempt ? (
        <footer className="candidate-footer">
          <span>
            <ShieldCheck size={14} />
            ProctorAI · A focused assessment experience
          </span>
          <a href="#/help">
            Help & guidance <CircleHelp size={13} />
          </a>
        </footer>
      ) : null}
    </div>
  );
}

const root =
  import.meta.hot?.data.root ?? createRoot(document.getElementById("root")!);
root.render(<App />);
if (import.meta.hot) import.meta.hot.data.root = root;
