import { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Activity,
  AlertTriangle,
  BookOpen,
  CheckCircle2,
  ClipboardList,
  Plus,
  Radio,
  RefreshCw,
  Save,
  ShieldCheck,
  UserPlus,
  Users,
} from "lucide-react";
import "./styles.css";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";
const TUNNEL_BYPASS_HEADERS = { "bypass-tunnel-reminder": "1" };

type User = { id: string; email: string; full_name: string; role: string };
type Bootstrap = { assessment_id: string; assessment_title: string; attempt_id: string | null; role: string };
type Assessment = {
  id: string;
  title: string;
  description: string | null;
  status: string;
  duration_minutes: number | null;
  created_by_id: string;
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
type IntegrityEvent = {
  id: string;
  attempt_id: string;
  assessment_id: string;
  event_type: string;
  status: string;
  severity: string;
  confidence: number | null;
  priority_score: number;
  occurred_at: string;
  received_at: string;
  evidence_status: string;
  metadata: Record<string, unknown>;
  evidence_files: EvidenceFile[];
};
type EvidenceFile = {
  id: string;
  kind: string;
  mime_type: string;
  sha256_hash: string;
  size_bytes: number;
  duration_ms: number | null;
  download_url: string;
};
type EventProof = {
  kind?: string;
  captured_at?: string;
  review_note?: string;
  page_hidden?: boolean;
  fullscreen_active?: boolean;
  camera_snapshot?: {
    data_url?: string;
    mime_type?: string;
    sha256_hash?: string;
    size_bytes?: number;
  } | null;
};
type Session = { token: string; user: User; bootstrap: Bootstrap };
type AccountMode = "EXAMINER" | "PROCTOR";

class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

const accountEmail: Record<AccountMode, string> = {
  EXAMINER: "examiner@example.com",
  PROCTOR: "proctor@example.com",
};

async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...TUNNEL_BYPASS_HEADERS, ...options.headers },
  });
  if (!response.ok) {
    const message = await response.text();
    throw new ApiError(message || `Request failed with status ${response.status}`, response.status);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

function errorMessage(error: unknown, fallback: string) {
  return error instanceof Error ? error.message : fallback;
}

function eventProof(event: IntegrityEvent): EventProof | null {
  const proof = event.metadata?.proof;
  return proof && typeof proof === "object" ? proof as EventProof : null;
}

function EvidenceClip({ evidence, token }: { evidence: EvidenceFile; token: string }) {
  const [objectUrl, setObjectUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    let nextUrl: string | null = null;

    async function loadClip() {
      setError(null);
      try {
        const response = await fetch(`${API_BASE}${evidence.download_url}`, {
          headers: { Authorization: `Bearer ${token}`, ...TUNNEL_BYPASS_HEADERS },
        });
        if (!response.ok) throw new Error(await response.text());
        nextUrl = URL.createObjectURL(await response.blob());
        if (!cancelled) setObjectUrl(nextUrl);
      } catch (nextError) {
        if (!cancelled) setError(errorMessage(nextError, "Evidence clip could not be loaded."));
      }
    }

    void loadClip();
    return () => {
      cancelled = true;
      if (nextUrl) URL.revokeObjectURL(nextUrl);
    };
  }, [evidence.download_url, token]);

  return (
    <div className="evidence-clip">
      {objectUrl ? (
        <video controls src={objectUrl} />
      ) : (
        <div className="clip-placeholder">{error ?? "Loading evidence clip"}</div>
      )}
      <small>
        {evidence.kind} | {(evidence.size_bytes / 1024).toFixed(1)} KB
        {evidence.duration_ms ? ` | ${(evidence.duration_ms / 1000).toFixed(1)}s` : ""}
      </small>
      <code>SHA-256 {evidence.sha256_hash.slice(0, 16)}...</code>
    </div>
  );
}

async function login(mode: AccountMode): Promise<Session> {
  const auth = await api<{ access_token: string; user: User }>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email: accountEmail[mode], password: "password123" }),
  });
  const bootstrap = await api<Bootstrap>("/dev/bootstrap", {
    headers: { Authorization: `Bearer ${auth.access_token}` },
  });
  return { token: auth.access_token, user: auth.user, bootstrap };
}

function App() {
  const [mode, setMode] = useState<AccountMode>("EXAMINER");
  const [session, setSession] = useState<Session | null>(null);
  const [assessments, setAssessments] = useState<Assessment[]>([]);
  const [selected, setSelected] = useState<AssessmentDetail | null>(null);
  const [events, setEvents] = useState<IntegrityEvent[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [socketState, setSocketState] = useState("offline");
  const [status, setStatus] = useState("loading");
  const [error, setError] = useState<string | null>(null);
  const [lastAction, setLastAction] = useState<string | null>(null);
  const [assessmentForm, setAssessmentForm] = useState({
    title: "Programming Placement Test",
    description: "Week 3 examiner-created assessment",
    duration_minutes: 60,
    status: "ACTIVE",
  });
  const [questionForm, setQuestionForm] = useState({
    prompt: "Which data structure uses FIFO ordering?",
    correct_answer: "queue",
    points: 5,
  });
  const [rulesText, setRulesText] = useState(
    JSON.stringify(
      {
        APP_FOCUS_LOST: { enabled: true, severity: "MEDIUM", min_persistence_ms: 500 },
        FULLSCREEN_EXIT: { enabled: true, severity: "HIGH", min_persistence_ms: 0 },
        HEARTBEAT_GAP: { enabled: true, severity: "HIGH", gap_threshold_ms: 15000 },
        CAMERA_DISABLED: { enabled: true, severity: "HIGH" },
        MICROPHONE_DISABLED: { enabled: true, severity: "HIGH" },
        BACKGROUND_SPEECH: { enabled: true, severity: "MEDIUM", sustained_audio_samples: 6 },
        PHONE_DETECTED: { enabled: true, severity: "HIGH" },
        LIVENESS_FAILED: { enabled: true, severity: "HIGH", challenge_set: ["blink", "turn_left", "turn_right"] },
        AI_ENGINE_INTERRUPTED: { enabled: true, severity: "HIGH" },
        FACE_ABSENT: { enabled: true, severity: "HIGH", absent_frame_threshold: 3 },
        MULTIPLE_PERSONS: { enabled: true, severity: "HIGH", multiple_frame_threshold: 2 },
      },
      null,
      2,
    ),
  );

  const authHeaders: Record<string, string> = session
    ? { Authorization: `Bearer ${session.token}` }
    : {};
  const candidates = users.filter((user) => user.role === "CANDIDATE");
  const proctors = users.filter((user) => user.role === "PROCTOR");
  const sortedEvents = useMemo(
    () => [...events].sort((a, b) => b.priority_score - a.priority_score),
    [events],
  );

  async function loadAssessment(assessmentId: string, token = session?.token) {
    if (!token) return;
    const detail = await api<AssessmentDetail>(`/assessments/${assessmentId}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    setSelected(detail);
  }

  async function loadEvents(assessmentId: string, token = session?.token) {
    if (!token) return;
    setEvents(
      await api<IntegrityEvent[]>(`/proctor/assessments/${assessmentId}/events`, {
        headers: { Authorization: `Bearer ${token}` },
      }),
    );
  }

  async function selectAssessment(assessmentId: string) {
    await loadAssessment(assessmentId);
    if (mode === "PROCTOR") await loadEvents(assessmentId);
  }

  async function assignDefaultReviewTeam(assessmentId: string) {
    const defaultCandidate = users.find((user) => user.role === "CANDIDATE");
    const defaultProctor = users.find((user) => user.role === "PROCTOR");
    await Promise.all([
      defaultCandidate
        ? api<void>(`/assessments/${assessmentId}/candidates`, {
            method: "POST",
            headers: authHeaders,
            body: JSON.stringify({ user_id: defaultCandidate.id }),
          })
        : Promise.resolve(),
      defaultProctor
        ? api<void>(`/assessments/${assessmentId}/proctors`, {
            method: "POST",
            headers: authHeaders,
            body: JSON.stringify({ user_id: defaultProctor.id }),
          })
        : Promise.resolve(),
    ]);
  }

  async function loadMode(nextMode: AccountMode = mode) {
    setStatus("loading");
    setError(null);
    setLastAction(null);
    setSocketState("offline");
    try {
      const nextSession = await login(nextMode);
      setSession(nextSession);
      const headers = { Authorization: `Bearer ${nextSession.token}` };
      const nextAssessments = await api<Assessment[]>("/assessments", { headers });
      setAssessments(nextAssessments);

      if (nextMode === "EXAMINER") {
        setUsers(await api<User[]>("/users", { headers }));
      }

      if (nextAssessments[0]) await loadAssessment(nextAssessments[0].id, nextSession.token);
      else setSelected(null);

      if (nextMode === "PROCTOR") {
        if (nextAssessments[0]) await loadEvents(nextAssessments[0].id, nextSession.token);
        else setEvents([]);
      } else {
        setEvents([]);
      }
      setStatus("ready");
    } catch (nextError) {
      setStatus("error");
      setError(errorMessage(nextError, "Unable to load portal."));
    }
  }

  useEffect(() => {
    loadMode(mode);
  }, [mode]);

  useEffect(() => {
    if (!session || mode !== "PROCTOR" || !selected) return;
    const wsBase = API_BASE.replace(/^http/, "ws");
    const socket = new WebSocket(
      `${wsBase}/ws/proctor/assessments/${selected.id}?token=${session.token}`,
    );
    socket.onopen = () => setSocketState("live");
    socket.onclose = () => setSocketState("offline");
    socket.onerror = () => setSocketState("error");
    socket.onmessage = (message) => {
      const nextEvent = JSON.parse(message.data) as IntegrityEvent;
      setEvents((current) => [nextEvent, ...current.filter((event) => event.id !== nextEvent.id)]);
    };
    return () => socket.close();
  }, [mode, session, selected?.id]);

  useEffect(() => {
    if (!session || mode !== "PROCTOR" || !selected) return;
    const interval = window.setInterval(() => {
      void loadEvents(selected.id)
        .then(() => setSocketState((current) => current === "live" ? current : "polling"))
        .catch(() => setSocketState((current) => current === "live" ? current : "offline"));
    }, 5000);
    return () => window.clearInterval(interval);
  }, [mode, session, selected?.id]);

  async function createAssessment() {
    setStatus("saving");
    setError(null);
    setLastAction(null);
    try {
      const created = await api<Assessment>("/assessments", {
        method: "POST",
        headers: authHeaders,
        body: JSON.stringify(assessmentForm),
      });
      await assignDefaultReviewTeam(created.id);
      setAssessments((current) => [created, ...current]);
      await loadAssessment(created.id);
      setLastAction(`Created assessment "${created.title}" and connected it to the default candidate and proctor.`);
      setStatus("ready");
    } catch (nextError) {
      setStatus("error");
      setError(errorMessage(nextError, "Assessment save failed."));
    }
  }

  async function addQuestion() {
    if (!selected) return;
    setStatus("saving");
    setError(null);
    setLastAction(null);
    try {
      await api<Question>(`/assessments/${selected.id}/questions`, {
        method: "POST",
        headers: authHeaders,
        body: JSON.stringify({
          prompt: questionForm.prompt,
          question_type: "MCQ",
          options: [
            { id: "stack", label: "Stack" },
            { id: "queue", label: "Queue" },
            { id: "tree", label: "Tree" },
            { id: "graph", label: "Graph" },
          ],
          correct_answer: questionForm.correct_answer,
          points: questionForm.points,
          display_order: selected.questions.length + 1,
        }),
      });
      await loadAssessment(selected.id);
      setLastAction("Question added.");
      setStatus("ready");
    } catch (nextError) {
      setStatus("error");
      setError(errorMessage(nextError, "Question save failed."));
    }
  }

  async function assignUser(kind: "candidates" | "proctors", userId: string, fullName: string) {
    if (!selected) return;
    setStatus("saving");
    setError(null);
    setLastAction(null);
    try {
      await api<void>(`/assessments/${selected.id}/${kind}`, {
        method: "POST",
        headers: authHeaders,
        body: JSON.stringify({ user_id: userId }),
      });
      setLastAction(`${fullName} assigned as ${kind === "candidates" ? "candidate" : "proctor"}.`);
      await loadAssessment(selected.id);
      setStatus("ready");
    } catch (nextError) {
      setStatus("error");
      setError(errorMessage(nextError, "Assignment failed."));
    }
  }

  async function saveRules() {
    if (!selected) return;
    setStatus("saving");
    setError(null);
    setLastAction(null);
    try {
      await api(`/assessments/${selected.id}/rules`, {
        method: "PUT",
        headers: authHeaders,
        body: JSON.stringify({ rules: JSON.parse(rulesText), config_version: "week3-ui" }),
      });
      setLastAction("Proctoring rules saved.");
      setStatus("ready");
    } catch (nextError) {
      setStatus("error");
      setError(errorMessage(nextError, "Rule save failed."));
    }
  }

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <ShieldCheck size={28} />
          <span>ProctorAI</span>
        </div>
        <div className="role-switch" aria-label="Portal role switch">
          <button className={mode === "EXAMINER" ? "active" : ""} onClick={() => setMode("EXAMINER")}>
            Examiner
          </button>
          <button className={mode === "PROCTOR" ? "active" : ""} onClick={() => setMode("PROCTOR")}>
            Proctor
          </button>
        </div>
        <nav>
          <a className={`nav-item ${mode === "EXAMINER" ? "active" : ""}`} href="#assessments">
            <ClipboardList size={18} />
            Assessments
          </a>
          <a className={`nav-item ${mode === "PROCTOR" ? "active" : ""}`} href="#queue">
            <Activity size={18} />
            Event Queue
          </a>
        </nav>
      </aside>

      <section className="workspace">
        <header className="topbar">
          <div>
            <p className="eyebrow">{mode === "EXAMINER" ? "Examiner Workspace" : "Proctor Dashboard"}</p>
            <h1>{mode === "EXAMINER" ? "Assessment Setup" : selected?.title ?? session?.bootstrap.assessment_title ?? "Connecting"}</h1>
            {mode === "PROCTOR" && assessments.length > 0 ? (
              <label className="assessment-picker">
                Assessment queue
                <select
                  value={selected?.id ?? ""}
                  onChange={(event) => void selectAssessment(event.target.value)}
                >
                  {assessments.map((assessment) => (
                    <option value={assessment.id} key={assessment.id}>
                      {assessment.title}
                    </option>
                  ))}
                </select>
              </label>
            ) : null}
          </div>
          <div className={`status-pill ${mode === "PROCTOR" ? socketState : status}`}>
            {mode === "PROCTOR" ? <Radio size={16} /> : <CheckCircle2 size={16} />}
            {mode === "PROCTOR" ? socketState : status}
          </div>
        </header>

        {error ? <div className="error-panel" role="alert">{error}</div> : null}
        {lastAction ? <div className="success-panel" role="status">{lastAction}</div> : null}

        {mode === "EXAMINER" ? (
          <section className="examiner-grid" id="assessments">
            <div className="panel">
              <div className="panel-header">
                <h2>Create Assessment</h2>
                <button onClick={createAssessment} disabled={status === "saving"} aria-label="Create assessment">
                  <Plus size={18} />
                </button>
              </div>
              <div className="form-stack">
                <label>
                  Title
                  <input
                    value={assessmentForm.title}
                    required
                    onChange={(event) => setAssessmentForm((current) => ({ ...current, title: event.target.value }))}
                  />
                </label>
                <label>
                  Description
                  <textarea
                    rows={3}
                    value={assessmentForm.description}
                    onChange={(event) =>
                      setAssessmentForm((current) => ({ ...current, description: event.target.value }))
                    }
                  />
                </label>
                <div className="form-row">
                  <label>
                    Duration
                    <input
                      type="number"
                      min={1}
                      max={480}
                      value={assessmentForm.duration_minutes}
                      onChange={(event) =>
                        setAssessmentForm((current) => ({
                          ...current,
                          duration_minutes: Number(event.target.value),
                        }))
                      }
                    />
                  </label>
                  <label>
                    Status
                    <select
                      value={assessmentForm.status}
                      onChange={(event) => setAssessmentForm((current) => ({ ...current, status: event.target.value }))}
                    >
                      <option>DRAFT</option>
                      <option>PUBLISHED</option>
                      <option>ACTIVE</option>
                      <option>CLOSED</option>
                    </select>
                  </label>
                </div>
              </div>
            </div>

            <div className="panel">
              <div className="panel-header">
                <h2>Assessments</h2>
                <button onClick={() => loadMode("EXAMINER")} aria-label="Refresh assessments">
                  <RefreshCw size={18} />
                </button>
              </div>
              <div className="assessment-list">
                {assessments.map((assessment) => (
                  <button
                    className={selected?.id === assessment.id ? "assessment-row active" : "assessment-row"}
                    key={assessment.id}
                    onClick={() => selectAssessment(assessment.id)}
                  >
                    <span>{assessment.title}</span>
                    <strong>{assessment.status}</strong>
                  </button>
                ))}
              </div>
            </div>

            <div className="panel wide">
              <div className="panel-header">
                <h2>{selected ? selected.title : "Assessment Detail"}</h2>
                <BookOpen size={19} />
              </div>
              {selected ? (
                <div className="detail-grid">
                  <section>
                    <h3>Questions</h3>
                    <div className="question-table">
                      {selected.questions.length === 0 ? (
                        <div className="empty-state">No questions yet</div>
                      ) : (
                        selected.questions.map((question) => (
                          <article key={question.id}>
                            <strong>{question.prompt}</strong>
                            <span>
                              {question.question_type} | {question.points} points
                            </span>
                          </article>
                        ))
                      )}
                    </div>
                    <div className="form-stack compact">
                      <label>
                        MCQ Prompt
                        <input
                          value={questionForm.prompt}
                          onChange={(event) => setQuestionForm((current) => ({ ...current, prompt: event.target.value }))}
                        />
                      </label>
                      <div className="form-row">
                        <label>
                          Correct Option ID
                          <input
                            value={questionForm.correct_answer}
                            onChange={(event) =>
                              setQuestionForm((current) => ({ ...current, correct_answer: event.target.value }))
                            }
                          />
                        </label>
                        <label>
                          Points
                          <input
                            type="number"
                            min={1}
                            value={questionForm.points}
                            onChange={(event) =>
                              setQuestionForm((current) => ({ ...current, points: Number(event.target.value) }))
                            }
                          />
                        </label>
                      </div>
                      <button className="primary-action" onClick={addQuestion} disabled={status === "saving"}>
                        <Plus size={18} />
                        Add MCQ
                      </button>
                    </div>
                  </section>
                  <section>
                    <h3>Assignments</h3>
                    <div className="assignment-grid">
                      <div>
                        <span className="mini-label">Candidates</span>
                        {candidates.map((candidate) => (
                          <button
                            disabled={status === "saving"}
                            key={candidate.id}
                            onClick={() => assignUser("candidates", candidate.id, candidate.full_name)}
                          >
                            <UserPlus size={16} />
                            {candidate.full_name}
                          </button>
                        ))}
                      </div>
                      <div>
                        <span className="mini-label">Proctors</span>
                        {proctors.map((proctor) => (
                          <button
                            disabled={status === "saving"}
                            key={proctor.id}
                            onClick={() => assignUser("proctors", proctor.id, proctor.full_name)}
                          >
                            <Users size={16} />
                            {proctor.full_name}
                          </button>
                        ))}
                      </div>
                    </div>
                    <h3>Rules</h3>
                    <label className="rules-editor">
                      JSON configuration
                      <textarea rows={8} value={rulesText} onChange={(event) => setRulesText(event.target.value)} />
                    </label>
                    <button className="primary-action" onClick={saveRules} disabled={status === "saving"}>
                      <Save size={18} />
                      Save Rules
                    </button>
                  </section>
                </div>
              ) : (
                <div className="empty-state">Select or create an assessment</div>
              )}
            </div>
          </section>
        ) : (
          <section className="proctor-stack" id="queue">
            <div className="summary-grid">
              <div className="metric">
                <span>Unreviewed</span>
                <strong>{events.filter((event) => event.status === "UNREVIEWED").length}</strong>
              </div>
              <div className="metric">
                <span>High Priority</span>
                <strong>
                  {
                    events.filter(
                      (event) =>
                        event.priority_score >= 8 ||
                        event.severity === "HIGH" ||
                        event.severity === "CRITICAL",
                    ).length
                  }
                </strong>
              </div>
              <div className="metric">
                <span>Evidence Pending</span>
                <strong>{events.filter((event) => event.evidence_status === "PENDING").length}</strong>
              </div>
            </div>

            <section className="panel">
              <div className="panel-header">
                <h2>Potential Integrity Events</h2>
                <button onClick={() => loadMode("PROCTOR")} aria-label="Refresh events">
                  <RefreshCw size={18} />
                </button>
              </div>
              {sortedEvents.length === 0 ? (
                <div className="empty-state">
                  <CheckCircle2 size={32} />
                  <span>No events yet</span>
                </div>
              ) : (
                <div className="event-list">
                  {sortedEvents.map((event) => (
                    <article className="event-row" key={event.id}>
                      <div className="event-icon">
                        <AlertTriangle size={20} />
                      </div>
                      <div className="event-main">
                        <div className="event-title">
                          <strong>{event.event_type.replaceAll("_", " ")}</strong>
                          <span>{event.status}</span>
                        </div>
                        <div className="event-meta">
                          <span>{new Date(event.occurred_at).toLocaleTimeString()}</span>
                          <span>{event.severity}</span>
                          <span>Priority {event.priority_score}</span>
                          <span>Evidence {event.evidence_status}</span>
                        </div>
                        {eventProof(event) ? (
                          <div className="event-proof">
                            {eventProof(event)?.camera_snapshot?.data_url ? (
                              <img alt={`${event.event_type.replaceAll("_", " ")} proof`} src={eventProof(event)?.camera_snapshot?.data_url} />
                            ) : null}
                            <div>
                              <strong>{eventProof(event)?.kind?.replaceAll("_", " ") ?? "Session proof"}</strong>
                              <span>{eventProof(event)?.review_note ?? "Review the event context before making a decision."}</span>
                              <small>
                                Captured {eventProof(event)?.captured_at ? new Date(eventProof(event)!.captured_at!).toLocaleString() : "during attempt"}
                                {" | "}Fullscreen {eventProof(event)?.fullscreen_active ? "active" : "inactive"}
                                {" | "}Page {eventProof(event)?.page_hidden ? "hidden" : "visible"}
                              </small>
                              {eventProof(event)?.camera_snapshot?.sha256_hash ? (
                                <code>SHA-256 {eventProof(event)?.camera_snapshot?.sha256_hash?.slice(0, 16)}...</code>
                              ) : null}
                            </div>
                          </div>
                        ) : (
                          <div className="event-proof">
                            <div>
                              <strong>Metadata only</strong>
                              <span>No proof bundle was attached to this older event.</span>
                            </div>
                          </div>
                        )}
                        {event.evidence_files.length > 0 && session ? (
                          <div className="evidence-clips">
                            {event.evidence_files.map((evidence) => (
                              <EvidenceClip evidence={evidence} key={evidence.id} token={session.token} />
                            ))}
                          </div>
                        ) : null}
                      </div>
                    </article>
                  ))}
                </div>
              )}
            </section>
          </section>
        )}
      </section>
    </main>
  );
}

createRoot(document.getElementById("root")!).render(<App />);
