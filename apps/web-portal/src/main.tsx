import { useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Activity,
  AlertTriangle,
  BookOpen,
  CheckCircle2,
  ClipboardList,
  Download,
  EyeOff,
  Plus,
  Radio,
  RefreshCw,
  Save,
  ShieldCheck,
  Users,
  ArrowLeft,
  ArrowRight,
  ArrowUpRight,
  Clock3,
  FileCheck2,
  Search,
  Settings2,
  Video,
  ChevronRight,
  LockKeyhole,
} from "lucide-react";
import "./styles.css";
import "./legibility.css";
import {
  EmptyState,
  StatCard,
  StatusBadge,
  Workspace,
  readPortalRoute,
} from "./Workspace";
import { serverDate } from "./time";
import {
  defaultRules,
  FeatureChoices,
  PeopleChoices,
  type RuleMap,
} from "./AssessmentSetup";
import "./assessment-setup.css";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8010";
const TUNNEL_BYPASS_HEADERS = { "bypass-tunnel-reminder": "1" };

type User = { id: string; email: string; full_name: string; role: string };
type Bootstrap = {
  assessment_id: string;
  assessment_title: string;
  attempt_id: string | null;
  role: string;
};
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
type AssessmentDetail = Assessment & {
  questions: Question[];
  rules: RuleMap;
  candidate_ids: string[];
  proctor_ids: string[];
};
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
  reviews: EventReview[];
};
type EventReview = {
  id: string;
  event_id: string;
  reviewer_id: string;
  decision: string;
  note: string | null;
  reviewed_at: string;
};
type EvidenceFile = {
  id: string;
  kind: string;
  original_filename: string | null;
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
type EventFilter = "ALL" | "HIGH" | "BROWSER" | "AI" | "EVIDENCE";

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
    headers: {
      "Content-Type": "application/json",
      ...TUNNEL_BYPASS_HEADERS,
      ...options.headers,
    },
  });
  if (!response.ok) {
    const message = await response.text();
    throw new ApiError(
      message || `Request failed with status ${response.status}`,
      response.status,
    );
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

function errorMessage(error: unknown, fallback: string) {
  return error instanceof Error ? error.message : fallback;
}

function eventProof(event: IntegrityEvent): EventProof | null {
  const proof = event.metadata?.proof;
  return proof && typeof proof === "object" ? (proof as EventProof) : null;
}

function metadataRiskScore(event: IntegrityEvent) {
  const risk = event.metadata?.risk;
  if (!risk || typeof risk !== "object") return null;
  const score = Number((risk as { score?: unknown }).score);
  return Number.isFinite(score) ? score : null;
}

function isBrowserEvent(event: IntegrityEvent) {
  return [
    "APP_FOCUS_LOST",
    "FULLSCREEN_EXIT",
    "CLIPBOARD_COPY",
    "CLIPBOARD_CUT",
    "CLIPBOARD_PASTE",
    "PRINT_SCREEN_ATTEMPT",
    "DEVTOOLS_SHORTCUT",
    "SCREEN_SHARE_ATTEMPT",
  ].includes(event.event_type);
}

function isAiEvent(event: IntegrityEvent) {
  return [
    "FACE_ABSENT",
    "MULTIPLE_PERSONS",
    "PHONE_DETECTED",
    "BACKGROUND_SPEECH",
    "LIVENESS_FAILED",
    "AI_ENGINE_INTERRUPTED",
  ].includes(event.event_type);
}

function EvidenceClip({
  evidence,
  token,
}: {
  evidence: EvidenceFile;
  token: string;
}) {
  const [objectUrl, setObjectUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    let nextUrl: string | null = null;

    async function loadClip() {
      setError(null);
      try {
        const response = await fetch(`${API_BASE}${evidence.download_url}`, {
          headers: {
            Authorization: `Bearer ${token}`,
            ...TUNNEL_BYPASS_HEADERS,
          },
        });
        if (!response.ok) throw new Error(await response.text());
        nextUrl = URL.createObjectURL(await response.blob());
        if (!cancelled) setObjectUrl(nextUrl);
      } catch (nextError) {
        if (!cancelled)
          setError(
            errorMessage(nextError, "Evidence clip could not be loaded."),
          );
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
        <video
          controls
          aria-label="Evidence clip"
          src={objectUrl}
          onError={() =>
            setError(
              "This clip cannot be played. Download it for inspection, or review another event.",
            )
          }
        />
      ) : (
        <div className="clip-placeholder">
          {error ?? "Loading evidence clip"}
        </div>
      )}
      {objectUrl ? (
        <a
          className="evidence-download"
          href={objectUrl}
          download={evidence.original_filename ?? "proctorai-evidence.webm"}
        >
          Download evidence file
        </a>
      ) : null}
      {objectUrl && error ? (
        <p role="alert" className="playback-error">
          {error}
        </p>
      ) : null}
      <small>
        {evidence.kind} | {(evidence.size_bytes / 1024).toFixed(1)} KB
        {evidence.duration_ms
          ? ` | ${(evidence.duration_ms / 1000).toFixed(1)}s`
          : ""}
      </small>
      <code>SHA-256 {evidence.sha256_hash.slice(0, 16)}...</code>
    </div>
  );
}

async function login(mode: AccountMode): Promise<Session> {
  const auth = await api<{ access_token: string; user: User }>("/auth/login", {
    method: "POST",
    body: JSON.stringify({
      email: accountEmail[mode],
      password: "password123",
    }),
  });
  const bootstrap = await api<Bootstrap>("/dev/bootstrap", {
    headers: { Authorization: `Bearer ${auth.access_token}` },
  });
  return { token: auth.access_token, user: auth.user, bootstrap };
}

function App() {
  const [route, setRoute] = useState(readPortalRoute);
  const [mode, setMode] = useState<AccountMode>(() => readPortalRoute().mode);
  const [search, setSearch] = useState("");
  const [assessmentFilter, setAssessmentFilter] = useState("ALL");
  const [reviewFilter, setReviewFilter] = useState("ALL");
  const [activeEventId, setActiveEventId] = useState<string | null>(null);
  const [reviewNote, setReviewNote] = useState("");
  const loadGeneration = useRef(0);
  const [session, setSession] = useState<Session | null>(null);
  const [assessments, setAssessments] = useState<Assessment[]>([]);
  const [selected, setSelected] = useState<AssessmentDetail | null>(null);
  const [events, setEvents] = useState<IntegrityEvent[]>([]);
  const [eventFilter, setEventFilter] = useState<EventFilter>("ALL");
  const [users, setUsers] = useState<User[]>([]);
  const [socketState, setSocketState] = useState("offline");
  const [status, setStatus] = useState("loading");
  const [error, setError] = useState<string | null>(null);
  const [lastAction, setLastAction] = useState<string | null>(null);
  const [reviewSavingId, setReviewSavingId] = useState<string | null>(null);
  const [assessmentForm, setAssessmentForm] = useState({
    title: "",
    description: "",
    duration_minutes: 60,
    status: "DRAFT",
  });
  const [questionForm, setQuestionForm] = useState({
    prompt: "",
    correct_answer: "a",
    points: 5,
    options: [
      { id: "a", label: "" },
      { id: "b", label: "" },
      { id: "c", label: "" },
      { id: "d", label: "" },
    ],
  });
  const [rulesText, setRulesText] = useState(() =>
    JSON.stringify(defaultRules(), null, 2),
  );
  const [creationCandidates, setCreationCandidates] = useState<string[]>([]);
  const [creationProctors, setCreationProctors] = useState<string[]>([]);
  const [creationRules, setCreationRules] = useState<RuleMap>(defaultRules);
  const [assignedCandidates, setAssignedCandidates] = useState<string[]>([]);
  const [assignedProctors, setAssignedProctors] = useState<string[]>([]);

  const authHeaders: Record<string, string> = session
    ? { Authorization: `Bearer ${session.token}` }
    : {};
  const candidates = users.filter((user) => user.role === "CANDIDATE");
  const sortedEvents = useMemo(
    () => [...events].sort((a, b) => b.priority_score - a.priority_score),
    [events],
  );
  const filteredEvents = useMemo(
    () =>
      sortedEvents.filter((event) => {
        if (reviewFilter === "UNREVIEWED" && event.status !== "UNREVIEWED")
          return false;
        if (reviewFilter === "REVIEWED" && event.status === "UNREVIEWED")
          return false;
        if (
          search &&
          !`${event.event_type} ${event.attempt_id} ${event.severity}`
            .toLowerCase()
            .includes(search.toLowerCase())
        )
          return false;
        if (eventFilter === "HIGH")
          return (
            event.priority_score >= 8 ||
            event.severity === "HIGH" ||
            event.severity === "CRITICAL"
          );
        if (eventFilter === "BROWSER") return isBrowserEvent(event);
        if (eventFilter === "AI") return isAiEvent(event);
        if (eventFilter === "EVIDENCE")
          return (
            event.evidence_status === "PENDING" ||
            event.evidence_files.length > 0
          );
        return true;
      }),
    [sortedEvents, eventFilter, reviewFilter, search],
  );

  useEffect(() => {
    if (
      filteredEvents.length &&
      !filteredEvents.some((event) => event.id === activeEventId)
    ) {
      setActiveEventId(filteredEvents[0].id);
      setReviewNote("");
    }
  }, [filteredEvents, activeEventId]);

  useEffect(() => {
    function onLocationChange() {
      const next = readPortalRoute();
      setRoute(next);
      setMode(next.mode);
      setSearch("");
      setLastAction(null);
      document.getElementById("workspace-content")?.focus();
      window.scrollTo(0, 0);
    }
    window.addEventListener("hashchange", onLocationChange);
    return () => window.removeEventListener("hashchange", onLocationChange);
  }, []);

  useEffect(() => {
    if (
      route.assessmentId &&
      session?.user.role === mode &&
      assessments.some((item) => item.id === route.assessmentId) &&
      selected?.id !== route.assessmentId
    ) {
      void loadAssessment(route.assessmentId).catch((nextError) =>
        setError(errorMessage(nextError, "Assessment could not be loaded.")),
      );
    }
  }, [route.assessmentId, session?.token, assessments, mode]);

  function navigate(path: string) {
    window.location.hash = path;
  }

  async function loadAssessment(assessmentId: string, token = session?.token) {
    if (!token) return;
    const detail = await api<AssessmentDetail>(`/assessments/${assessmentId}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    setSelected(detail);
    setRulesText(
      JSON.stringify({ ...defaultRules(), ...detail.rules }, null, 2),
    );
    setAssignedCandidates(detail.candidate_ids);
    setAssignedProctors(detail.proctor_ids);
  }

  async function loadEvents(assessmentId: string, token = session?.token) {
    if (!token) return;
    setEvents(
      await api<IntegrityEvent[]>(
        `/proctor/assessments/${assessmentId}/events`,
        {
          headers: { Authorization: `Bearer ${token}` },
        },
      ),
    );
  }

  async function selectAssessment(assessmentId: string) {
    await loadAssessment(assessmentId);
    if (mode === "PROCTOR") await loadEvents(assessmentId);
  }

  async function loadMode(nextMode: AccountMode = mode) {
    const generation = ++loadGeneration.current;
    setStatus("loading");
    setError(null);
    setLastAction(null);
    setSocketState("offline");
    try {
      const nextSession = await login(nextMode);
      if (generation !== loadGeneration.current) return;
      setSession(nextSession);
      const headers = { Authorization: `Bearer ${nextSession.token}` };
      const nextAssessments = await api<Assessment[]>("/assessments", {
        headers,
      });
      if (generation !== loadGeneration.current) return;
      setAssessments(nextAssessments);

      if (nextMode === "EXAMINER") {
        setUsers(await api<User[]>("/users", { headers }));
      }

      const firstAssessment =
        nextAssessments.find((item) => item.id === route.assessmentId) ??
        nextAssessments.find((item) => item.id === selected?.id) ??
        nextAssessments[0];
      if (firstAssessment)
        await loadAssessment(firstAssessment.id, nextSession.token);
      else setSelected(null);

      if (nextMode === "PROCTOR") {
        if (firstAssessment)
          await loadEvents(firstAssessment.id, nextSession.token);
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
    if (
      !session ||
      session.user.role !== mode ||
      mode !== "PROCTOR" ||
      !selected
    )
      return;
    const wsBase = API_BASE.replace(/^http/, "ws");
    const socket = new WebSocket(
      `${wsBase}/ws/proctor/assessments/${selected.id}?token=${session.token}`,
    );
    socket.onopen = () => setSocketState("live");
    socket.onclose = () => setSocketState("offline");
    socket.onerror = () => setSocketState("error");
    socket.onmessage = (message) => {
      const nextEvent = JSON.parse(message.data) as IntegrityEvent;
      setEvents((current) => [
        nextEvent,
        ...current.filter((event) => event.id !== nextEvent.id),
      ]);
    };
    return () => socket.close();
  }, [mode, session, selected?.id]);

  useEffect(() => {
    if (
      !session ||
      session.user.role !== mode ||
      mode !== "PROCTOR" ||
      !selected
    )
      return;
    const interval = window.setInterval(() => {
      void loadEvents(selected.id)
        .then(() =>
          setSocketState((current) =>
            current === "live" ? current : "polling",
          ),
        )
        .catch(() =>
          setSocketState((current) =>
            current === "live" ? current : "offline",
          ),
        );
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
        body: JSON.stringify({
          ...assessmentForm,
          candidate_ids: creationCandidates,
          proctor_ids: creationProctors,
          rules: creationRules,
        }),
      });
      setAssessments((current) => [created, ...current]);
      await loadAssessment(created.id);
      navigate(`/examiner/assessments/${created.id}/questions`);
      setLastAction(
        `Created "${created.title}" with ${creationCandidates.length} candidate(s), ${creationProctors.length} proctor(s), and your selected monitoring settings.`,
      );
      setCreationCandidates([]);
      setCreationProctors([]);
      setCreationRules(defaultRules());
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
          options: questionForm.options,
          correct_answer: questionForm.correct_answer,
          points: questionForm.points,
          display_order: selected.questions.length + 1,
        }),
      });
      await loadAssessment(selected.id);
      setLastAction("Question added.");
      setQuestionForm({
        prompt: "",
        correct_answer: "a",
        points: 5,
        options: [
          { id: "a", label: "" },
          { id: "b", label: "" },
          { id: "c", label: "" },
          { id: "d", label: "" },
        ],
      });
      setStatus("ready");
    } catch (nextError) {
      setStatus("error");
      setError(errorMessage(nextError, "Question save failed."));
    }
  }

  async function saveAssignments() {
    if (!selected) return;
    setStatus("saving");
    setError(null);
    setLastAction(null);
    try {
      const detail = await api<AssessmentDetail>(
        `/assessments/${selected.id}/assignments`,
        {
          method: "PUT",
          headers: authHeaders,
          body: JSON.stringify({
            candidate_ids: assignedCandidates,
            proctor_ids: assignedProctors,
          }),
        },
      );
      setSelected(detail);
      setLastAction("Candidate and proctor assignments saved.");
      setStatus("ready");
    } catch (nextError) {
      setStatus("error");
      setError(errorMessage(nextError, "Assignments could not be saved."));
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
        body: JSON.stringify({
          rules: JSON.parse(rulesText),
          config_version: "assessment-v1",
        }),
      });
      setLastAction("Proctoring rules saved.");
      setStatus("ready");
    } catch (nextError) {
      setStatus("error");
      setError(errorMessage(nextError, "Rule save failed."));
    }
  }

  async function reviewEvent(
    event: IntegrityEvent,
    decision: "CONFIRMED_SUSPICIOUS" | "FALSE_POSITIVE" | "INCONCLUSIVE",
  ) {
    if (!session) return;
    setReviewSavingId(event.id);
    setError(null);
    setLastAction(null);
    try {
      const updated = await api<IntegrityEvent>(
        `/proctor/events/${event.id}/reviews`,
        {
          method: "POST",
          headers: authHeaders,
          body: JSON.stringify({
            decision,
            note:
              reviewNote.trim() ||
              (decision === "CONFIRMED_SUSPICIOUS"
                ? "Marked suspicious after proctor review."
                : decision === "FALSE_POSITIVE"
                  ? "Dismissed as false positive after proctor review."
                  : "Marked inconclusive after proctor review."),
          }),
        },
      );
      setEvents((current) => [
        updated,
        ...current.filter((item) => item.id !== updated.id),
      ]);
      setLastAction(
        `${event.event_type.replaceAll("_", " ")} reviewed as ${decision.replaceAll("_", " ").toLowerCase()}.`,
      );
    } catch (nextError) {
      setError(errorMessage(nextError, "Review save failed."));
    } finally {
      setReviewSavingId(null);
    }
  }

  function exportEventsCsv(eventRows: IntegrityEvent[] = filteredEvents) {
    const escapeCsv = (value: unknown) =>
      `"${String(value ?? "").replaceAll('"', '""')}"`;
    const rows = [
      [
        "Occurred At",
        "Event",
        "Severity",
        "Priority",
        "Risk",
        "Status",
        "Evidence",
        "Attempt",
      ],
      ...eventRows.map((event) => [
        event.occurred_at,
        event.event_type,
        event.severity,
        event.priority_score,
        metadataRiskScore(event) ?? "",
        event.status,
        event.evidence_status,
        event.attempt_id,
      ]),
    ];
    const blob = new Blob(
      [rows.map((row) => row.map(escapeCsv).join(",")).join("\n")],
      { type: "text/csv" },
    );
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `proctorai-events-${new Date().toISOString().slice(0, 10)}.csv`;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  async function saveAssessmentDetails() {
    if (!selected) return;
    setStatus("saving");
    setError(null);
    try {
      await api(`/assessments/${selected.id}`, {
        method: "PUT",
        headers: authHeaders,
        body: JSON.stringify({
          title: selected.title,
          description: selected.description,
          duration_minutes: selected.duration_minutes,
          status: selected.status,
        }),
      });
      setAssessments((current) =>
        current.map((item) =>
          item.id === selected.id ? { ...item, ...selected } : item,
        ),
      );
      setLastAction("Assessment details saved.");
      setStatus("ready");
    } catch (nextError) {
      setError(errorMessage(nextError, "Assessment could not be saved."));
      setStatus("error");
    }
  }

  const saving = status === "saving";
  const visibleAssessments = assessments.filter(
    (item) =>
      (assessmentFilter === "ALL" || item.status === assessmentFilter) &&
      (item.title + " " + (item.description ?? ""))
        .toLowerCase()
        .includes(search.toLowerCase()),
  );
  const activeEvent =
    filteredEvents.find((item) => item.id === activeEventId) ??
    filteredEvents[0];
  const unreviewed = events.filter(
    (item) => item.status === "UNREVIEWED",
  ).length;
  const highPriority = events.filter((item) => item.priority_score >= 8).length;
  const evidenceReady = events.filter(
    (item) => item.evidence_files.length > 0,
  ).length;
  const reviewed = events.length - unreviewed;
  const pageMetadata: Record<string, [string, string]> = {
    overview: [
      "Your workspace, at a glance",
      mode === "EXAMINER"
        ? "Create thoughtful assessments. Keep every exam organized."
        : "Stay on top of integrity signals and the reviews that need your attention.",
    ],
    assessments: [
      "Assessments",
      "Manage your assessments, questions, and candidate assignments.",
    ],
    new: [
      "Create an assessment",
      "Choose who takes the test, who reviews it, and how it is monitored.",
    ],
    builder: [
      selected?.title ?? "Assessment details",
      "Everything you need to prepare and manage this assessment.",
    ],
    people: [
      "People & assignments",
      "Connect candidates and proctors to the right assessments.",
    ],
    monitoring: [
      "Live monitoring",
      "Follow incoming integrity signals as candidates take their assessments.",
    ],
    reviews: [
      "Evidence review",
      "Review the context, inspect the evidence, and record your decision.",
    ],
    reports: [
      "Integrity reports",
      "A clear record of signals and review outcomes for each assessment.",
    ],
    settings: [
      "Monitoring policy",
      "Configure the signals your proctors should receive.",
    ],
    help: [
      "Help & guidance",
      "Practical guidance for a smooth assessment experience.",
    ],
  };
  const [pageTitle, pageDescription] = pageMetadata[route.page] ?? [
    "Page not found",
    "This page is not available in your workspace.",
  ];
  const assessmentPicker = (
    <label className="assessment-picker">
      <span>Assessment</span>
      <select
        aria-label="Choose assessment"
        value={selected?.id ?? ""}
        disabled={!assessments.length || saving}
        onChange={(event) => {
          setActiveEventId(null);
          void selectAssessment(event.target.value).catch((nextError) =>
            setError(
              errorMessage(nextError, "Assessment could not be loaded."),
            ),
          );
        }}
      >
        {!assessments.length ? (
          <option value="">No assessments available</option>
        ) : null}
        {assessments.map((item) => (
          <option key={item.id} value={item.id}>
            {item.title}
          </option>
        ))}
      </select>
    </label>
  );
  const openBuilder = (id: string, tab = "overview") =>
    navigate("/examiner/assessments/" + id + "/" + tab);
  const assessmentTable = (items: Assessment[]) => (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Assessment</th>
            <th>Status</th>
            <th>Duration</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.id}>
              <td>
                <div className="table-title">
                  <span className="table-icon">
                    <ClipboardList size={19} />
                  </span>
                  <div>
                    <button
                      className="text-button"
                      onClick={() => openBuilder(item.id)}
                    >
                      {item.title}
                    </button>
                    <small>{item.description || "No description added"}</small>
                  </div>
                </div>
              </td>
              <td>
                <StatusBadge status={item.status} />
              </td>
              <td>
                <span className="with-icon">
                  <Clock3 size={14} />
                  {item.duration_minutes == null
                    ? "Untimed"
                    : item.duration_minutes + " min"}
                </span>
              </td>
              <td>
                <button
                  className="quiet-button"
                  onClick={() => openBuilder(item.id)}
                >
                  Manage <ArrowUpRight size={15} />
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
  const peoplePanel = (
    <section className="panel">
      <div className="panel-header">
        <div>
          <h2>People & assignments</h2>
          <p>
            Only selected candidates can access this test. Selected proctors can
            review its events.
          </p>
        </div>
      </div>
      <div className="form-body">
        <div className="creation-people">
          <PeopleChoices
            title="Candidates"
            role="CANDIDATE"
            people={users}
            selected={assignedCandidates}
            onChange={setAssignedCandidates}
            disabled={!selected || saving}
          />
          <PeopleChoices
            title="Proctors"
            role="PROCTOR"
            people={users}
            selected={assignedProctors}
            onChange={setAssignedProctors}
            disabled={!selected || saving}
          />
        </div>
        <div className="assignment-edit-actions">
          <button
            className="primary-button"
            disabled={!selected || saving}
            onClick={() => void saveAssignments()}
          >
            <Save size={16} />
            {saving ? "Saving…" : "Save assignments"}
          </button>
        </div>
      </div>
    </section>
  );
  let ruleEntries: [string, Record<string, unknown>][] = [];
  try {
    ruleEntries = Object.entries(
      JSON.parse(rulesText) as Record<string, Record<string, unknown>>,
    );
  } catch {
    /* The advanced editor reports invalid JSON when saved. */
  }
  const policyPanel = (
    <section className="panel">
      <div className="panel-header">
        <div>
          <h2>Integrity signals</h2>
          <p>Choose which features are enabled for this assessment.</p>
        </div>
        <button
          className="primary-button"
          disabled={!selected || saving || !ruleEntries.length}
          onClick={() => void saveRules()}
        >
          <Save size={16} />
          {saving ? "Saving…" : "Save policy"}
        </button>
      </div>
      <div className="notice neutral">
        <ShieldCheck size={19} />
        <p>
          Signals support a proctor's review. They do not determine whether a
          candidate has committed misconduct.
        </p>
      </div>
      <div className="form-body">
        <FeatureChoices
          rules={Object.fromEntries(ruleEntries)}
          disabled={saving}
          onChange={(rules) => setRulesText(JSON.stringify(rules, null, 2))}
        />
      </div>
      <details className="advanced-settings">
        <summary>Advanced policy configuration</summary>
        <label>
          Policy JSON
          <textarea
            className="code-input"
            rows={14}
            value={rulesText}
            onChange={(event) => setRulesText(event.target.value)}
          />
        </label>
      </details>
    </section>
  );
  const eventDetail = activeEvent ? (
    <article className="panel review-detail">
      <div className="panel-header">
        <div>
          <p className="eyebrow">INTEGRITY EVENT</p>
          <h2>{activeEvent.event_type.toLowerCase().replaceAll("_", " ")}</h2>
        </div>
        <StatusBadge status={activeEvent.severity} />
      </div>
      <div className="event-context">
        <div>
          <span>Occurred</span>
          <strong>
            {serverDate(activeEvent.occurred_at).toLocaleString()}
          </strong>
        </div>
        <div>
          <span>Attempt</span>
          <strong className="mono">{activeEvent.attempt_id.slice(0, 8)}</strong>
        </div>
        <div>
          <span>Confidence</span>
          <strong>
            {activeEvent.confidence == null
              ? "Not available"
              : Math.round(activeEvent.confidence * 100) + "%"}
          </strong>
        </div>
        <div>
          <span>Evidence</span>
          <StatusBadge status={activeEvent.evidence_status} />
        </div>
      </div>
      {activeEvent.evidence_files.length && session ? (
        <div className="evidence-clips">
          {activeEvent.evidence_files.map((file) => (
            <EvidenceClip key={file.id} evidence={file} token={session.token} />
          ))}
        </div>
      ) : eventProof(activeEvent)?.camera_snapshot?.data_url ? (
        <figure className="proof-image">
          <img
            src={eventProof(activeEvent)?.camera_snapshot?.data_url}
            alt={
              "Camera evidence for " +
              activeEvent.event_type.toLowerCase().replaceAll("_", " ")
            }
          />
          <figcaption>Captured at the time of the integrity signal.</figcaption>
        </figure>
      ) : (
        <div className="evidence-placeholder">
          <Video size={30} />
          <strong>
            {activeEvent.evidence_status === "PENDING"
              ? "Evidence is processing"
              : "No media attached"}
          </strong>
          <span>
            {activeEvent.evidence_status === "PENDING"
              ? "The clip will appear when capture and upload complete."
              : "Use the recorded session context when reviewing this event."}
          </span>
        </div>
      )}
      {eventProof(activeEvent) ? (
        <div className="evidence-note">
          <ShieldCheck size={17} />
          <p>
            {eventProof(activeEvent)?.review_note ??
              "Inspect the evidence and event context before making a decision."}
          </p>
        </div>
      ) : null}
      <div className="review-decision">
        <h3>Record your review</h3>
        <p>Consider the full context before confirming a signal.</p>
        <label>
          Review note <span className="optional">(optional)</span>
          <textarea
            rows={3}
            value={reviewNote}
            placeholder="Add context for your decision…"
            onChange={(event) => setReviewNote(event.target.value)}
          />
        </label>
        <div className="review-actions">
          <button
            className="danger-outline"
            disabled={reviewSavingId === activeEvent.id}
            onClick={() =>
              void reviewEvent(activeEvent, "CONFIRMED_SUSPICIOUS")
            }
          >
            <AlertTriangle size={16} />
            Confirm suspicious
          </button>
          <button
            className="secondary-button"
            disabled={reviewSavingId === activeEvent.id}
            onClick={() => void reviewEvent(activeEvent, "FALSE_POSITIVE")}
          >
            <CheckCircle2 size={16} />
            False positive
          </button>
          <button
            className="secondary-button"
            disabled={reviewSavingId === activeEvent.id}
            onClick={() => void reviewEvent(activeEvent, "INCONCLUSIVE")}
          >
            <EyeOff size={16} />
            Inconclusive
          </button>
        </div>
        {activeEvent.reviews.length ? (
          <div className="review-history">
            <h4>Review history</h4>
            {activeEvent.reviews.map((review) => (
              <div key={review.id}>
                <StatusBadge status={review.decision} />
                <span>{serverDate(review.reviewed_at).toLocaleString()}</span>
                {review.note ? <p>{review.note}</p> : null}
              </div>
            ))}
          </div>
        ) : null}
      </div>
    </article>
  ) : null;

  return (
    <Workspace
      route={route}
      title={pageTitle}
      description={pageDescription}
      name={session?.user.full_name ?? ""}
      status={mode === "PROCTOR" && status === "ready" ? socketState : status}
      onRefresh={() => void loadMode(mode)}
      actions={
        mode === "EXAMINER" &&
        ["overview", "assessments"].includes(route.page) ? (
          <button
            className="primary-button"
            onClick={() => navigate("/examiner/assessments/new")}
          >
            <Plus size={17} />
            Create assessment
          </button>
        ) : route.page === "reports" ? (
          <button
            className="primary-button"
            disabled={!events.length}
            onClick={() => exportEventsCsv(events)}
          >
            <Download size={16} />
            Export CSV
          </button>
        ) : null
      }
    >
      {error ? (
        <div className="error-panel" role="alert">
          <AlertTriangle size={18} />
          <div>
            <strong>Something needs your attention</strong>
            <p>{error}</p>
          </div>
          <button
            className="secondary-button small"
            onClick={() => void loadMode(mode)}
          >
            Retry connection
          </button>
        </div>
      ) : null}
      {lastAction ? (
        <div className="success-panel" role="status">
          <CheckCircle2 size={17} />
          {lastAction}
        </div>
      ) : null}
      {status === "loading" && !session ? (
        <div className="loading-workspace" role="status">
          <RefreshCw size={22} className="spin" />
          <h2>Preparing your workspace</h2>
          <p>Loading your assessments and account.</p>
        </div>
      ) : null}

      {route.page === "overview" ? (
        <>
          <div className="stats-grid">
            <StatCard
              label={
                mode === "EXAMINER" ? "Total assessments" : "Integrity events"
              }
              value={mode === "EXAMINER" ? assessments.length : events.length}
              note={
                mode === "EXAMINER"
                  ? "Across your workspace"
                  : "In the selected assessment"
              }
              icon={<ClipboardList size={20} />}
            />
            <StatCard
              label={
                mode === "EXAMINER" ? "Active assessments" : "Awaiting review"
              }
              value={
                mode === "EXAMINER"
                  ? assessments.filter((item) => item.status === "ACTIVE")
                      .length
                  : unreviewed
              }
              note={
                mode === "EXAMINER"
                  ? "Currently open for candidates"
                  : "Signals that need a decision"
              }
              icon={<Activity size={20} />}
              tone="green"
            />
            <StatCard
              label={
                mode === "EXAMINER" ? "Candidate accounts" : "High priority"
              }
              value={mode === "EXAMINER" ? candidates.length : highPriority}
              note={
                mode === "EXAMINER"
                  ? "Available for assignment"
                  : "Priority score of 8 or above"
              }
              icon={<Users size={20} />}
              tone="purple"
            />
            <StatCard
              label={
                mode === "EXAMINER" ? "Draft assessments" : "Evidence available"
              }
              value={
                mode === "EXAMINER"
                  ? assessments.filter((item) => item.status === "DRAFT").length
                  : evidenceReady
              }
              note={
                mode === "EXAMINER"
                  ? "Ready for your next edit"
                  : "Events with attached media"
              }
              icon={<FileCheck2 size={20} />}
              tone="amber"
            />
          </div>
          <div className="overview-grid">
            <section className="welcome-card">
              <span className="welcome-icon">
                <ShieldCheck size={29} />
              </span>
              <p className="eyebrow">A CLEARER WAY TO ASSESS</p>
              <h2>
                Good assessments.
                <br />
                Confident decisions.
              </h2>
              <p>
                {mode === "EXAMINER"
                  ? "Build your assessment, bring the right people together, and let your proctors focus on what matters."
                  : "Keep an eye on incoming signals and review each event with evidence and context."}
              </p>
              <button
                className="primary-button"
                onClick={() =>
                  navigate(
                    mode === "EXAMINER"
                      ? "/examiner/assessments"
                      : "/proctor/reviews",
                  )
                }
              >
                {mode === "EXAMINER"
                  ? "Manage assessments"
                  : "Open review queue"}
                <ArrowRight size={17} />
              </button>
              <div className="welcome-lines" aria-hidden="true">
                <span />
                <span />
                <span />
              </div>
            </section>
            <section className="panel quick-start">
              <div className="panel-header">
                <h2>
                  {mode === "EXAMINER"
                    ? "Your assessment workflow"
                    : "Review workflow"}
                </h2>
                <span className="subtle-icon">
                  <Settings2 size={18} />
                </span>
              </div>
              {(mode === "EXAMINER"
                ? [
                    {
                      title: "Prepare an assessment",
                      description: "Set a duration and add your questions.",
                      link: "/examiner/assessments",
                    },
                    {
                      title: "Assign your people",
                      description: "Connect candidates and proctors.",
                      link: "/examiner/people",
                    },
                    {
                      title: "Review with evidence",
                      description: "Open the proctor's review workspace.",
                      link: "/proctor/reviews",
                    },
                  ]
                : [
                    {
                      title: "Select an assessment",
                      description: "Choose the queue you want to follow.",
                      link: "/proctor/monitoring",
                    },
                    {
                      title: "Inspect each signal",
                      description: "Watch the clip and read its context.",
                      link: "/proctor/reviews",
                    },
                    {
                      title: "Keep a clear record",
                      description: "Export events and review outcomes.",
                      link: "/proctor/reports",
                    },
                  ]
              ).map((item, index) => (
                <a
                  className="workflow-item"
                  href={"#" + item.link}
                  key={item.title}
                >
                  <span className="step-number">0{index + 1}</span>
                  <div>
                    <strong>{item.title}</strong>
                    <p>{item.description}</p>
                  </div>
                  <ChevronRight size={17} />
                </a>
              ))}
            </section>
          </div>
          {mode === "EXAMINER" ? (
            <section className="panel">
              <div className="panel-header">
                <div>
                  <h2>Recent assessments</h2>
                  <p>Pick up where you left off.</p>
                </div>
                <a className="text-link" href="#/examiner/assessments">
                  View all <ArrowRight size={15} />
                </a>
              </div>
              {assessments.length ? (
                assessmentTable(assessments.slice(0, 5))
              ) : (
                <EmptyState
                  title="Your first assessment starts here"
                  description="Create an assessment, add questions, and assign candidates to get started."
                  action={
                    <button
                      className="primary-button"
                      onClick={() => navigate("/examiner/assessments/new")}
                    >
                      <Plus size={16} />
                      Create assessment
                    </button>
                  }
                />
              )}
            </section>
          ) : (
            <section className="panel">
              <div className="panel-header">
                <h2>Assessment queue</h2>
                {assessmentPicker}
              </div>
              <div className="notice neutral">
                <Radio size={20} />
                <p>
                  {selected
                    ? "Monitoring " +
                      selected.title +
                      ". Open live monitoring to follow incoming signals, or evidence review to record decisions."
                    : "You have no assigned assessments yet."}
                </p>
              </div>
            </section>
          )}
        </>
      ) : null}

      {route.page === "assessments" ? (
        <section className="panel">
          <div className="list-toolbar">
            <div className="segmented" aria-label="Assessment status filter">
              {["ALL", "ACTIVE", "DRAFT", "CLOSED"].map((filter) => (
                <button
                  key={filter}
                  className={assessmentFilter === filter ? "active" : ""}
                  aria-pressed={assessmentFilter === filter}
                  onClick={() => setAssessmentFilter(filter)}
                >
                  {filter === "ALL" ? "All assessments" : filter.toLowerCase()}
                  <span>
                    {filter === "ALL"
                      ? assessments.length
                      : assessments.filter((item) => item.status === filter)
                          .length}
                  </span>
                </button>
              ))}
            </div>
            <label className="search-field">
              <Search size={17} />
              <input
                aria-label="Search assessments"
                placeholder="Search assessments…"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
              />
            </label>
          </div>
          {visibleAssessments.length ? (
            assessmentTable(visibleAssessments)
          ) : (
            <EmptyState
              title={
                assessments.length
                  ? "No matching assessments"
                  : "No assessments yet"
              }
              description={
                assessments.length
                  ? "Try another search or status filter."
                  : "Create your first assessment to start building your question set."
              }
            />
          )}
          <div className="table-footer">
            {visibleAssessments.length} assessment
            {visibleAssessments.length === 1 ? "" : "s"} shown
          </div>
        </section>
      ) : null}

      {route.page === "new" ? (
        <>
          <a className="back-link" href="#/examiner/assessments">
            <ArrowLeft size={16} />
            Back to assessments
          </a>
          <div className="editor-layout">
            <form
              className="panel"
              onSubmit={(event) => {
                event.preventDefault();
                void createAssessment();
              }}
            >
              <div className="panel-header">
                <div>
                  <h2>Assessment details</h2>
                  <p>Give your assessment a clear name and purpose.</p>
                </div>
                <span className="form-step">Configure your test</span>
              </div>
              <div className="form-body form-stack">
                <label>
                  Assessment name
                  <input
                    autoFocus
                    required
                    maxLength={255}
                    placeholder="e.g. Introduction to Computer Science"
                    value={assessmentForm.title}
                    onChange={(event) =>
                      setAssessmentForm((current) => ({
                        ...current,
                        title: event.target.value,
                      }))
                    }
                  />
                </label>
                <label>
                  Description
                  <textarea
                    rows={4}
                    placeholder="What should candidates know before they begin?"
                    value={assessmentForm.description}
                    onChange={(event) =>
                      setAssessmentForm((current) => ({
                        ...current,
                        description: event.target.value,
                      }))
                    }
                  />
                </label>
                <div className="form-row">
                  <label>
                    Duration in minutes
                    <input
                      type="number"
                      min={1}
                      max={480}
                      required
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
                    Assessment status
                    <select
                      value={assessmentForm.status}
                      onChange={(event) =>
                        setAssessmentForm((current) => ({
                          ...current,
                          status: event.target.value,
                        }))
                      }
                    >
                      {["DRAFT", "PUBLISHED", "ACTIVE", "CLOSED"].map(
                        (value) => (
                          <option key={value} value={value}>
                            {value.toLowerCase()}
                          </option>
                        ),
                      )}
                    </select>
                  </label>
                </div>
                <section className="creation-section">
                  <h3>Choose your people</h3>
                  <p>
                    Select the candidates taking this test and the proctors
                    reviewing it. You can select more than one.
                  </p>
                  <div className="creation-people">
                    <PeopleChoices
                      title="Candidates"
                      role="CANDIDATE"
                      people={users}
                      selected={creationCandidates}
                      onChange={setCreationCandidates}
                      disabled={saving}
                    />
                    <PeopleChoices
                      title="Proctors"
                      role="PROCTOR"
                      people={users}
                      selected={creationProctors}
                      onChange={setCreationProctors}
                      disabled={saving}
                    />
                  </div>
                </section>
                <section className="creation-section">
                  <h3>Choose proctoring features</h3>
                  <p>
                    Candidate setup and monitoring follow these settings. Phone
                    detection and liveness require camera access even when face
                    monitoring is off.
                  </p>
                  <FeatureChoices
                    rules={creationRules}
                    onChange={setCreationRules}
                    disabled={saving}
                  />
                </section>
                <div className="form-actions">
                  <a className="secondary-button" href="#/examiner/assessments">
                    Cancel
                  </a>
                  <button
                    className="primary-button"
                    disabled={saving || !assessmentForm.title.trim()}
                    type="submit"
                  >
                    {saving ? "Creating…" : "Create & add questions"}
                    <ArrowRight size={16} />
                  </button>
                </div>
              </div>
            </form>
            <aside className="editor-aside">
              <span className="aside-symbol">
                <ClipboardList size={27} />
              </span>
              <h2>Make it your assessment</h2>
              <ol className="simple-steps">
                <li>
                  <span>1</span>
                  <div>
                    <strong>Add the details</strong>
                    <p>
                      Name your assessment, choose your people, and enable the
                      monitoring you need.
                    </p>
                  </div>
                </li>
                <li>
                  <span>2</span>
                  <div>
                    <strong>Build your question set</strong>
                    <p>Add questions and mark the correct answers.</p>
                  </div>
                </li>
                <li>
                  <span>3</span>
                  <div>
                    <strong>Review and publish</strong>
                    <p>
                      Check your selections before making the assessment
                      available.
                    </p>
                  </div>
                </li>
              </ol>
              <div className="aside-note">
                <LockKeyhole size={18} />
                <p>
                  A draft stays unavailable to candidates until you change its
                  status.
                </p>
              </div>
            </aside>
          </div>
        </>
      ) : null}

      {route.page === "builder" ? (
        <>
          <a className="back-link" href="#/examiner/assessments">
            <ArrowLeft size={16} />
            All assessments
          </a>
          {selected && selected.id === route.assessmentId ? (
            <>
              <div className="assessment-banner">
                <div className="with-icon">
                  <span className="large-icon">
                    <ClipboardList size={25} />
                  </span>
                  <div>
                    <strong>{selected.title}</strong>
                    <span>
                      {selected.questions.length} questions ·{" "}
                      {selected.duration_minutes == null
                        ? "Untimed"
                        : selected.duration_minutes + " minutes"}
                    </span>
                  </div>
                </div>
                <StatusBadge status={selected.status} />
              </div>
              <nav className="page-tabs" aria-label="Assessment pages">
                {[
                  ["overview", "Details"],
                  ["questions", "Questions"],
                  ["people", "People"],
                  ["rules", "Monitoring policy"],
                ].map(([tab, label]) => (
                  <a
                    key={tab}
                    href={"#/examiner/assessments/" + selected.id + "/" + tab}
                    className={route.tab === tab ? "active" : ""}
                    aria-current={route.tab === tab ? "page" : undefined}
                  >
                    {label}
                    {tab === "questions" ? (
                      <span>{selected.questions.length}</span>
                    ) : null}
                  </a>
                ))}
              </nav>
              {route.tab === "overview" ? (
                <form
                  className="panel narrow-panel"
                  onSubmit={(event) => {
                    event.preventDefault();
                    void saveAssessmentDetails();
                  }}
                >
                  <div className="panel-header">
                    <div>
                      <h2>Assessment details</h2>
                      <p>Update the information candidates will see.</p>
                    </div>
                  </div>
                  <div className="form-body form-stack">
                    <label>
                      Assessment name
                      <input
                        required
                        maxLength={255}
                        value={selected.title}
                        onChange={(event) =>
                          setSelected((current) =>
                            current
                              ? { ...current, title: event.target.value }
                              : current,
                          )
                        }
                      />
                    </label>
                    <label>
                      Description
                      <textarea
                        rows={4}
                        value={selected.description ?? ""}
                        onChange={(event) =>
                          setSelected((current) =>
                            current
                              ? { ...current, description: event.target.value }
                              : current,
                          )
                        }
                      />
                    </label>
                    <div className="form-row">
                      <label>
                        Duration in minutes
                        <input
                          type="number"
                          min={1}
                          max={480}
                          required
                          value={selected.duration_minutes ?? 60}
                          onChange={(event) =>
                            setSelected((current) =>
                              current
                                ? {
                                    ...current,
                                    duration_minutes: Number(
                                      event.target.value,
                                    ),
                                  }
                                : current,
                            )
                          }
                        />
                      </label>
                      <label>
                        Status
                        <select
                          value={selected.status}
                          onChange={(event) =>
                            setSelected((current) =>
                              current
                                ? { ...current, status: event.target.value }
                                : current,
                            )
                          }
                        >
                          {["DRAFT", "PUBLISHED", "ACTIVE", "CLOSED"].map(
                            (value) => (
                              <option key={value} value={value}>
                                {value.toLowerCase()}
                              </option>
                            ),
                          )}
                        </select>
                      </label>
                    </div>
                    <div className="form-actions">
                      <button
                        className="primary-button"
                        disabled={saving}
                        type="submit"
                      >
                        <Save size={16} />
                        {saving ? "Saving…" : "Save changes"}
                      </button>
                    </div>
                  </div>
                </form>
              ) : null}
              {route.tab === "questions" ? (
                <div className="question-editor-grid">
                  <section className="panel">
                    <div className="panel-header">
                      <div>
                        <h2>
                          Question set{" "}
                          <span className="count-badge">
                            {selected.questions.length}
                          </span>
                        </h2>
                        <p>
                          {selected.questions.reduce(
                            (total, item) => total + item.points,
                            0,
                          )}{" "}
                          total points
                        </p>
                      </div>
                    </div>
                    {selected.questions.length ? (
                      <ol className="question-list">
                        {selected.questions.map((question, index) => (
                          <li key={question.id}>
                            <span className="question-index">
                              {String(index + 1).padStart(2, "0")}
                            </span>
                            <div>
                              <h3>{question.prompt}</h3>
                              <div className="question-labels">
                                <span>Multiple choice</span>
                                <span>{question.points} points</span>
                              </div>
                              {question.options ? (
                                <div className="question-options">
                                  {question.options.map((option) => (
                                    <span
                                      className={
                                        option.id === question.correct_answer
                                          ? "correct"
                                          : ""
                                      }
                                      key={option.id}
                                    >
                                      {option.id.toUpperCase()}. {option.label}
                                      {option.id === question.correct_answer ? (
                                        <CheckCircle2 size={13} />
                                      ) : null}
                                    </span>
                                  ))}
                                </div>
                              ) : null}
                            </div>
                          </li>
                        ))}
                      </ol>
                    ) : (
                      <EmptyState
                        title="Build your question set"
                        description="Use the form to add your first multiple-choice question."
                        icon={<BookOpen size={26} />}
                      />
                    )}
                  </section>
                  <form
                    className="panel"
                    onSubmit={(event) => {
                      event.preventDefault();
                      void addQuestion();
                    }}
                  >
                    <div className="panel-header">
                      <h2>Add a question</h2>
                      <Plus size={18} />
                    </div>
                    <div className="form-body form-stack">
                      <label>
                        Question
                        <textarea
                          rows={3}
                          required
                          placeholder="Write your question…"
                          value={questionForm.prompt}
                          onChange={(event) =>
                            setQuestionForm((current) => ({
                              ...current,
                              prompt: event.target.value,
                            }))
                          }
                        />
                      </label>
                      <fieldset>
                        <legend>Answer options</legend>
                        {questionForm.options.map((option, index) => (
                          <label className="option-input" key={option.id}>
                            <span>{option.id.toUpperCase()}</span>
                            <input
                              required
                              aria-label={"Option " + option.id.toUpperCase()}
                              placeholder={"Answer option " + (index + 1)}
                              value={option.label}
                              onChange={(event) =>
                                setQuestionForm((current) => ({
                                  ...current,
                                  options: current.options.map((item) =>
                                    item.id === option.id
                                      ? { ...item, label: event.target.value }
                                      : item,
                                  ),
                                }))
                              }
                            />
                          </label>
                        ))}
                      </fieldset>
                      <div className="form-row">
                        <label>
                          Correct answer
                          <select
                            value={questionForm.correct_answer}
                            onChange={(event) =>
                              setQuestionForm((current) => ({
                                ...current,
                                correct_answer: event.target.value,
                              }))
                            }
                          >
                            {questionForm.options.map((option) => (
                              <option key={option.id} value={option.id}>
                                Option {option.id.toUpperCase()}
                              </option>
                            ))}
                          </select>
                        </label>
                        <label>
                          Points
                          <input
                            type="number"
                            min={1}
                            max={100}
                            required
                            value={questionForm.points}
                            onChange={(event) =>
                              setQuestionForm((current) => ({
                                ...current,
                                points: Number(event.target.value),
                              }))
                            }
                          />
                        </label>
                      </div>
                      <button
                        className="primary-button"
                        disabled={saving}
                        type="submit"
                      >
                        <Plus size={16} />
                        {saving ? "Adding…" : "Add question"}
                      </button>
                    </div>
                  </form>
                </div>
              ) : null}
              {route.tab === "people" ? peoplePanel : null}
              {route.tab === "rules" ? policyPanel : null}
            </>
          ) : (
            <EmptyState
              title={
                status === "loading"
                  ? "Loading assessment…"
                  : "Assessment unavailable"
              }
              description="Select an assessment from your list to manage its details."
              action={
                <a href="#/examiner/assessments" className="primary-button">
                  View assessments <ArrowRight size={16} />
                </a>
              }
            />
          )}
        </>
      ) : null}

      {route.page === "people" ? (
        <>
          <div className="context-bar">
            <div>
              <Users size={20} />
              <span>Assign people to an assessment</span>
            </div>
            {assessmentPicker}
          </div>
          {peoplePanel}
        </>
      ) : null}
      {route.page === "settings" ? (
        <>
          <div className="context-bar">
            <div>
              <Settings2 size={20} />
              <span>Choose where to apply your policy</span>
            </div>
            {assessmentPicker}
          </div>
          {policyPanel}
        </>
      ) : null}

      {["monitoring", "reviews", "reports"].includes(route.page) ? (
        <div className="context-bar">
          <div>
            <span
              className={
                "live-indicator " +
                (socketState === "live" || socketState === "polling"
                  ? "connected"
                  : "")
              }
            />
            <span>
              {socketState === "live"
                ? "Live event stream"
                : socketState === "polling"
                  ? "Connected with polling"
                  : "Connecting to event stream"}
            </span>
          </div>
          {assessmentPicker}
        </div>
      ) : null}

      {route.page === "monitoring" ? (
        <>
          <div className="stats-grid">
            <StatCard
              label="Signals received"
              value={events.length}
              note="Current assessment"
              icon={<Activity size={20} />}
            />
            <StatCard
              label="Awaiting review"
              value={unreviewed}
              note="Needs a proctor decision"
              icon={<FileCheck2 size={20} />}
              tone="amber"
            />
            <StatCard
              label="High priority"
              value={highPriority}
              note="Priority score of 8 or above"
              icon={<AlertTriangle size={20} />}
              tone="red"
            />
            <StatCard
              label="Sessions with signals"
              value={new Set(events.map((item) => item.attempt_id)).size}
              note="Distinct attempts in this queue"
              icon={<Users size={20} />}
              tone="purple"
            />
          </div>
          <section className="panel">
            <div className="panel-header">
              <div>
                <h2>Incoming integrity signals</h2>
                <p>Signals appear during an attempt, before submission.</p>
              </div>
              <a className="secondary-button" href="#/proctor/reviews">
                Open review queue <ArrowRight size={15} />
              </a>
            </div>
            {events.length ? (
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Event</th>
                      <th>Session</th>
                      <th>Priority</th>
                      <th>Received</th>
                      <th>Review</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sortedEvents.map((event) => (
                      <tr key={event.id}>
                        <td>
                          <div className="with-icon">
                            <span className="signal-icon">
                              <AlertTriangle size={17} />
                            </span>
                            <strong className="event-name">
                              {event.event_type
                                .toLowerCase()
                                .replaceAll("_", " ")}
                            </strong>
                          </div>
                        </td>
                        <td className="mono">{event.attempt_id.slice(0, 8)}</td>
                        <td>
                          <StatusBadge status={event.severity} />
                        </td>
                        <td>
                          {serverDate(event.occurred_at).toLocaleTimeString(
                            [],
                            { hour: "2-digit", minute: "2-digit" },
                          )}
                        </td>
                        <td>
                          <button
                            className="quiet-button"
                            onClick={() => {
                              setActiveEventId(event.id);
                              navigate("/proctor/reviews");
                            }}
                          >
                            Review <ArrowUpRight size={15} />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <EmptyState
                title="You're ready to monitor"
                description="Integrity signals will appear here when candidates begin their assessments. No signals have been received for this assessment yet."
                icon={<Radio size={29} />}
              />
            )}
          </section>
          <div className="notice neutral">
            <ShieldCheck size={19} />
            <p>
              AI and browser signals flag activity for review. Inspect the
              supporting evidence before recording a decision.
            </p>
          </div>
        </>
      ) : null}

      {route.page === "reviews" ? (
        <>
          <div className="list-toolbar review-toolbar">
            <label className="search-field">
              <Search size={17} />
              <input
                aria-label="Search integrity events"
                placeholder="Search events or attempt ID…"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
              />
            </label>
            <select
              aria-label="Review status"
              value={reviewFilter}
              onChange={(event) => setReviewFilter(event.target.value)}
            >
              <option value="ALL">All review statuses</option>
              <option value="UNREVIEWED">Awaiting review</option>
              <option value="REVIEWED">Reviewed</option>
            </select>
            <div className="segmented">
              {(
                ["ALL", "HIGH", "BROWSER", "AI", "EVIDENCE"] as EventFilter[]
              ).map((filter) => (
                <button
                  key={filter}
                  aria-pressed={eventFilter === filter}
                  className={eventFilter === filter ? "active" : ""}
                  onClick={() => setEventFilter(filter)}
                >
                  {filter === "ALL" ? "All signals" : filter.toLowerCase()}
                </button>
              ))}
            </div>
          </div>
          {filteredEvents.length ? (
            <div className="review-layout">
              <section
                className="panel review-queue"
                aria-label="Integrity event queue"
              >
                <div className="panel-header">
                  <h2>Event queue</h2>
                  <span className="count-badge">{filteredEvents.length}</span>
                </div>
                {filteredEvents.map((event) => (
                  <button
                    className={
                      "queue-item" +
                      (activeEvent?.id === event.id ? " selected" : "")
                    }
                    key={event.id}
                    aria-pressed={activeEvent?.id === event.id}
                    onClick={() => {
                      setActiveEventId(event.id);
                      setReviewNote("");
                    }}
                  >
                    <div className="queue-item-top">
                      <StatusBadge status={event.severity} />
                      <time>
                        {serverDate(event.occurred_at).toLocaleTimeString([], {
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </time>
                    </div>
                    <strong>
                      {event.event_type.toLowerCase().replaceAll("_", " ")}
                    </strong>
                    <span>Attempt {event.attempt_id.slice(0, 8)}</span>
                    <small>
                      <span
                        className={
                          "review-dot " +
                          (event.status === "UNREVIEWED" ? "pending" : "")
                        }
                      />
                      {event.status.toLowerCase().replaceAll("_", " ")}
                    </small>
                  </button>
                ))}
              </section>
              {eventDetail}
            </div>
          ) : (
            <section className="panel">
              <EmptyState
                title={
                  events.length
                    ? "No events match your filters"
                    : "Your review queue is clear"
                }
                description={
                  events.length
                    ? "Change the search or review filters to see more signals."
                    : "When a candidate triggers an integrity signal, its context and evidence will appear here."
                }
                icon={<FileCheck2 size={29} />}
              />
            </section>
          )}
        </>
      ) : null}

      {route.page === "reports" ? (
        <>
          <div className="stats-grid">
            <StatCard
              label="Total signals"
              value={events.length}
              note="For the selected assessment"
              icon={<Activity size={20} />}
            />
            <StatCard
              label="Reviewed"
              value={reviewed}
              note={
                events.length
                  ? Math.round((reviewed / events.length) * 100) +
                    "% of signals"
                  : "No signals received"
              }
              icon={<FileCheck2 size={20} />}
              tone="green"
            />
            <StatCard
              label="Confirmed suspicious"
              value={
                events.filter(
                  (item) =>
                    item.reviews[0]?.decision === "CONFIRMED_SUSPICIOUS",
                ).length
              }
              note="After a proctor's review"
              icon={<AlertTriangle size={20} />}
              tone="red"
            />
            <StatCard
              label="False positives"
              value={
                events.filter(
                  (item) => item.reviews[0]?.decision === "FALSE_POSITIVE",
                ).length
              }
              note="Dismissed by a proctor"
              icon={<CheckCircle2 size={20} />}
              tone="purple"
            />
          </div>
          <div className="report-grid">
            <section className="panel">
              <div className="panel-header">
                <h2>Signals by category</h2>
                <span className="count-badge">{events.length}</span>
              </div>
              {events.length ? (
                <div className="category-bars">
                  {Object.entries(
                    events.reduce<Record<string, number>>(
                      (counts, item) => ({
                        ...counts,
                        [item.event_type]: (counts[item.event_type] ?? 0) + 1,
                      }),
                      {},
                    ),
                  )
                    .sort((a, b) => b[1] - a[1])
                    .map(([name, count]) => (
                      <div className="category-row" key={name}>
                        <div>
                          <strong>
                            {name.toLowerCase().replaceAll("_", " ")}
                          </strong>
                          <span>{count}</span>
                        </div>
                        <div className="bar-track">
                          <span
                            style={{
                              width: (count / events.length) * 100 + "%",
                            }}
                          />
                        </div>
                      </div>
                    ))}
                </div>
              ) : (
                <EmptyState
                  title="No report data yet"
                  description="Reports use actual integrity events and recorded reviews from the selected assessment."
                />
              )}
            </section>
            <section className="panel export-card">
              <span className="large-icon">
                <Download size={27} />
              </span>
              <h2>A record you can work with</h2>
              <p>
                Download the selected assessment's event log with timestamps,
                priorities, evidence status, and review status.
              </p>
              <button
                className="primary-button"
                disabled={!events.length}
                onClick={() => exportEventsCsv(events)}
              >
                <Download size={16} />
                Download event CSV
              </button>
              <small>
                CSV · {events.length} event{events.length === 1 ? "" : "s"}
              </small>
            </section>
          </div>
        </>
      ) : null}

      {route.page === "help" ? (
        <div className="help-grid">
          {[
            {
              icon: <ClipboardList size={24} />,
              title: "Prepare an assessment",
              content:
                "Create an assessment as a draft, add questions, choose the correct answers, and assign candidates and proctors. Change the status to active when candidates may begin.",
            },
            {
              icon: <Video size={24} />,
              title: "A smooth candidate setup",
              content:
                "Candidates complete consent, connection, full-display screen recording, camera, microphone, display and liveness checks. The assessment opens when its requirements pass.",
            },
            {
              icon: <FileCheck2 size={24} />,
              title: "Review with context",
              content:
                "Select an assessment in the proctor workspace. Open an integrity event to view its clip or snapshot, add a note, and mark it suspicious, false positive or inconclusive.",
            },
            {
              icon: <ShieldCheck size={24} />,
              title: "Permissions & privacy",
              content:
                "Candidates approve browser camera, microphone and screen permissions. Browser activity uses screen evidence; camera signals use camera evidence. A proctor reviews the signals before making a decision.",
            },
          ].map((item) => (
            <article className="panel help-card" key={item.title}>
              <span className="large-icon">{item.icon}</span>
              <h2>{item.title}</h2>
              <p>{item.content}</p>
            </article>
          ))}
        </div>
      ) : null}
      {!pageMetadata[route.page] ? (
        <EmptyState
          title="Let's get you back on track"
          description="Use the workspace navigation to open an available page."
          action={
            <a
              className="primary-button"
              href={
                "#/" +
                (mode === "EXAMINER" ? "examiner" : "proctor") +
                "/overview"
              }
            >
              Go to overview <ArrowRight size={16} />
            </a>
          }
        />
      ) : null}
    </Workspace>
  );
}

const root =
  import.meta.hot?.data.root ?? createRoot(document.getElementById("root")!);
root.render(<App />);
if (import.meta.hot) import.meta.hot.data.root = root;
