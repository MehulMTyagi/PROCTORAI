export type User = {
  id: string;
  email: string;
  full_name: string;
  role: string;
};
export type Assessment = {
  id: string;
  title: string;
  description: string | null;
  status: string;
  duration_minutes: number | null;
};
export type Question = {
  id: string;
  prompt: string;
  question_type: string;
  options: { id: string; label: string }[] | null;
  correct_answer: string | null;
  points: number;
  display_order: number;
};
export type AssessmentDetail = Assessment & {
  questions: Question[];
  rules?: import("./proctoring").ProctoringRules;
};
export type Attempt = {
  id: string;
  assessment_id: string;
  status: string;
  score: number | null;
  started_at: string | null;
  answers: Answer[];
};
export type Answer = {
  id: string;
  question_id: string;
  answer_text: string | null;
  selected_option: string | null;
  score_awarded: number | null;
};
export type IntegrityEvent = {
  id: string;
  event_type: string;
  status: string;
  priority_score: number;
  evidence_status: string;
  metadata: Record<string, unknown>;
  evidence_files: EvidenceFile[];
};
export type EvidenceFile = {
  id: string;
  kind: string;
  mime_type: string;
  sha256_hash: string;
  size_bytes: number;
  duration_ms: number | null;
  download_url: string;
};
export type AiModelInfo = {
  name: string;
  version: string;
  detector: string;
  cascade_path?: string | null;
  model_path?: string | null;
};
export type AiEventCandidate = {
  event_type: "FACE_ABSENT" | "MULTIPLE_PERSONS";
  severity: "HIGH";
  confidence: number;
  priority_score: number;
  metadata: Record<string, unknown>;
};
export type AiFrameResponse = {
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
export type YoloDetectedObject = {
  class_name: string;
  confidence: number;
  bbox: number[];
  phone_like: boolean;
};
export type YoloObjectEventCandidate = {
  event_type: "PHONE_DETECTED";
  severity: "HIGH";
  confidence: number;
  priority_score: number;
  metadata: Record<string, unknown>;
};
export type YoloObjectResponse = {
  objects: YoloDetectedObject[];
  phone_like_objects: YoloDetectedObject[];
  events: YoloObjectEventCandidate[];
  model: AiModelInfo;
};
export type LivenessResponse = {
  passed: boolean;
  confidence: number;
  results: {
    prompt: string;
    passed: boolean;
    reason: string;
    confidence: number;
  }[];
  model: AiModelInfo;
};
export type Session = { token: string; user: User };
export type PendingOperation = {
  id: string;
  kind: "ANSWER" | "EVENT" | "HEARTBEAT";
  path: string;
  method: "POST";
  body: Record<string, unknown>;
  label: string;
  queued_at: string;
  status: "queued" | "retrying" | "failed";
};
export type RollingChunk = {
  blob: Blob;
  startedAt: number;
  endedAt: number;
};
export type RiskTimelineItem = {
  id: string;
  eventType: string;
  weight: number;
  occurredAt: string;
  source: string;
};
export type FaceMonitorState = {
  status: string;
  faceCount: number | null;
  samplesAnalyzed: number;
  detail: string;
};
export type ObjectMonitorState = {
  status: string;
  label: string;
  confidence: number | null;
  detail: string;
};
export type ScreenMonitorState = {
  status: string;
  detail: string;
};

export type ReadinessKey =
  | "backend"
  | "camera"
  | "microphone"
  | "sidecar"
  | "screen"
  | "devices"
  | "fullscreen"
  | "liveness";
export type CheckStatus = "pending" | "pass" | "warning" | "fail";
export type ReadinessCheck = {
  key: ReadinessKey;
  label: string;
  status: CheckStatus;
  detail: string;
};
export type LivenessPrompt = "BLINK" | "TURN_LEFT" | "TURN_RIGHT";
export type LivenessSample = {
  prompt: LivenessPrompt;
  frame_data_urls: string[];
};

export type SendIntegrityEvent = (
  eventType?: string,
  metadata?: Record<string, unknown>,
  severity?: string,
  priorityScore?: number,
  automatic?: boolean,
  snapshotDataUrl?: string | null,
) => Promise<IntegrityEvent | null>;

export type Route =
  | { name: "home" }
  | { name: "help" }
  | { name: "assessments" }
  | { name: "setup"; assessmentId: string; step?: string }
  | { name: "test"; assessmentId: string };

export function parseRoute(hash: string): Route {
  const parts = hash.replace(/^#\/?/, "").split("/").filter(Boolean);
  if (parts[0] === "assessments" && parts[1] && parts[2] === "test") {
    return { name: "test", assessmentId: parts[1] };
  }
  if (parts[0] === "assessments" && parts[1] && parts[2] === "setup") {
    return {
      name: "setup",
      assessmentId: parts[1],
      step: parts[3] ?? "consent",
    };
  }
  if (parts[0] === "dashboard" || parts.length === 0) return { name: "home" };
  if (parts[0] === "help") return { name: "help" };
  return { name: "assessments" };
}

export function routeHash(route: Route): string {
  if (route.name === "setup")
    return `#/assessments/${route.assessmentId}/setup/${route.step ?? "consent"}`;
  if (route.name === "test") return `#/assessments/${route.assessmentId}/test`;
  if (route.name === "home") return "#/dashboard";
  if (route.name === "help") return "#/help";
  return "#/assessments";
}
