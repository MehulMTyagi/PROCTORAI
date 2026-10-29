import { useEffect, useMemo, useRef, useState } from "react";
import { serverDate } from "./time";
import { requirements } from "./proctoring";
import type { RefObject } from "react";
import {
  Activity,
  AlertTriangle,
  ArrowLeft,
  Check,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  ClipboardList,
  Expand,
  Keyboard,
  MonitorUp,
  Radio,
  RotateCw,
  Save,
  ScanFace,
  ScreenShare,
  Send,
  ShieldCheck,
  Smartphone,
  Timer,
  UserRoundX,
  UsersRound,
  Volume2,
} from "lucide-react";
import type {
  AiModelInfo,
  AssessmentDetail,
  Attempt,
  FaceMonitorState,
  IdentityMonitorState,
  IntegrityEvent,
  ObjectMonitorState,
  PendingOperation,
  Question,
  ScreenMonitorState,
  SendIntegrityEvent,
} from "./types";

type Props = {
  assessment: AssessmentDetail | null;
  attempt: Attempt;
  draftAnswers: Record<string, string>;
  fullscreenActive: boolean;
  saving: boolean;
  simulateOffline: boolean;
  monitoringActive: boolean;
  sidecarReady: boolean;
  faceMonitor: FaceMonitorState;
  identityMonitor: IdentityMonitorState;
  objectMonitor: ObjectMonitorState;
  screenMonitor: ScreenMonitorState;
  aiModel: AiModelInfo | null;
  liveRiskScore: number;
  liveRiskLabel: string;
  lastHeartbeatAckAt: string | null;
  retryQueue: PendingOperation[];
  lastEvent: IntegrityEvent | null;
  videoRef: RefObject<HTMLVideoElement | null>;
  canvasRef: RefObject<HTMLCanvasElement | null>;
  onAnswer: (question: Question, value: string) => void;
  onDraftChange: (questionId: string, value: string) => void;
  onSubmit: () => Promise<void>;
  onFlushQueue: () => Promise<void>;
  onSimulateOfflineChange: (value: boolean) => void;
  onRequestFullscreen: () => Promise<void>;
  onExit: () => void;
  sendIntegrityEvent: SendIntegrityEvent;
  onFaceDemo: (faceCount: number) => Promise<void>;
  onPhoneDemo: () => void;
  onVoiceDemo: () => void;
};

function formatCountdown(ms: number) {
  const total = Math.floor(ms / 1000);
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  const seconds = total % 60;
  return hours > 0
    ? `${hours}:${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`
    : `${minutes}:${String(seconds).padStart(2, "0")}`;
}

function useCountdown(
  startedAt: string | null,
  durationMinutes: number | null,
  active: boolean,
) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (!active || !startedAt || !durationMinutes) return;
    setNow(Date.now());
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, [active, startedAt, durationMinutes]);
  if (!startedAt || !durationMinutes) return null;
  const remainingMs =
    serverDate(startedAt).getTime() + durationMinutes * 60_000 - now;
  return { expired: remainingMs <= 0, remainingMs: Math.max(0, remainingMs) };
}

export default function TestPage(props: Props) {
  const required = requirements(props.assessment?.rules);
  const attempt = props.attempt;
  const submitted = attempt.status === "SUBMITTED";
  const questions = useMemo(
    () => props.assessment?.questions ?? [],
    [props.assessment],
  );
  const [index, setIndex] = useState(0);
  const [confirming, setConfirming] = useState(false);
  const promptRef = useRef<HTMLHeadingElement | null>(null);
  const safeIndex = Math.min(index, Math.max(0, questions.length - 1));
  const question = questions[safeIndex];
  const countdown = useCountdown(
    attempt.started_at,
    props.assessment?.duration_minutes ?? null,
    !submitted,
  );
  const answeredCount = questions.filter(
    (item) => (props.draftAnswers[item.id] ?? "").trim().length > 0,
  ).length;
  const submitBlocked = props.saving || props.retryQueue.length > 0;

  useEffect(() => {
    promptRef.current?.focus();
  }, [safeIndex]);

  function goTo(next: number) {
    setIndex(Math.min(Math.max(next, 0), questions.length - 1));
  }

  function answerLabel(answerQuestion: Question) {
    const answer = attempt.answers.find(
      (item) => item.question_id === answerQuestion.id,
    );
    if (answerQuestion.question_type === "MCQ") {
      return (
        answerQuestion.options?.find(
          (option) => option.id === answer?.selected_option,
        )?.label ??
        answer?.selected_option ??
        null
      );
    }
    return answer?.answer_text ?? null;
  }

  if (submitted) {
    return (
      <main id="main-content" tabIndex={-1} className="page test-page">
        <section className="receipt" aria-label="Submission receipt">
          <div className="receipt-banner">
            <CheckCircle2 size={36} aria-hidden="true" />
            <div>
              <h1>Assessment submitted</h1>
              <p>
                {props.assessment?.title ?? "Your assessment"} has been
                submitted successfully.
              </p>
            </div>
            <span className="score-chip">Score {attempt.score ?? 0}</span>
          </div>
          {questions.length > 0 ? (
            <ol className="receipt-list">
              {questions.map((item, itemIndex) => (
                <li key={item.id} className="receipt-item">
                  <div className="receipt-item-head">
                    <span>
                      Question {itemIndex + 1} ·{" "}
                      {item.question_type === "MCQ"
                        ? "Multiple choice"
                        : "Short answer"}{" "}
                      · {item.points} point{item.points === 1 ? "" : "s"}
                    </span>
                    <span className="badge tone-neutral">
                      {attempt.answers.find(
                        (answer) => answer.question_id === item.id,
                      )?.score_awarded ?? 0}{" "}
                      / {item.points}
                    </span>
                  </div>
                  <h2>{item.prompt}</h2>
                  <p className="receipt-answer">
                    <strong>Your answer:</strong>{" "}
                    {answerLabel(item) ?? "Not answered"}
                  </p>
                </li>
              ))}
            </ol>
          ) : (
            <p className="receipt-empty">
              This assessment did not contain any questions.
            </p>
          )}
          <div className="receipt-actions">
            <button className="secondary-button" onClick={props.onExit}>
              <ArrowLeft size={16} aria-hidden="true" />
              Back to assessments
            </button>
          </div>
        </section>
      </main>
    );
  }

  return (
    <main id="main-content" tabIndex={-1} className="page test-page">
      <div className="exam-bar">
        <div className="exam-bar-title">
          <h1>{props.assessment?.title ?? "Assessment"}</h1>
          <span>
            {questions.length > 0
              ? `Question ${safeIndex + 1} of ${questions.length}`
              : "No questions yet"}
          </span>
        </div>
        <div className="exam-bar-status">
          {!props.fullscreenActive && (
            <button
              className="chip-button"
              onClick={() => void props.onRequestFullscreen()}
            >
              <Expand size={14} aria-hidden="true" />
              Fullscreen
            </button>
          )}
          <span
            className={`timer-chip${countdown ? (countdown.expired ? " expired" : countdown.remainingMs < 5 * 60_000 ? " warn" : "") : ""}`}
          >
            <Timer size={14} aria-hidden="true" />
            {countdown
              ? countdown.expired
                ? "Time expired"
                : `${formatCountdown(countdown.remainingMs)} left`
              : "No time limit"}
          </span>
          <span className="chip exam-recording-status">
            <ShieldCheck size={14} aria-hidden="true" />
            {props.monitoringActive
              ? "Monitoring active"
              : "Monitoring standby"}
          </span>
          <button
            className="danger-button"
            onClick={() => setConfirming(true)}
            disabled={submitBlocked}
            title={
              props.retryQueue.length > 0
                ? "Queued answers must sync before submission"
                : "Submit your assessment for scoring"
            }
          >
            Submit
          </button>
        </div>
      </div>

      {confirming && (
        <div
          className="submit-confirm"
          role="alertdialog"
          aria-label="Confirm submission"
        >
          <AlertTriangle size={20} aria-hidden="true" />
          <div className="submit-confirm-text">
            <strong>Submit your assessment?</strong>
            <span>
              {answeredCount} of {questions.length} answered
              {questions.length - answeredCount > 0
                ? ` — ${questions.length - answeredCount} unanswered`
                : ""}
              . You cannot return after submitting.
            </span>
          </div>
          <div className="submit-confirm-actions">
            <button
              className="secondary-button"
              onClick={() => setConfirming(false)}
            >
              Keep working
            </button>
            <button
              className="danger-button"
              onClick={() => {
                setConfirming(false);
                void props.onSubmit();
              }}
              disabled={props.saving}
            >
              {props.saving ? "Submitting..." : "Submit now"}
            </button>
          </div>
        </div>
      )}

      {question ? (
        <div className="exam-layout">
          <div className="exam-main">
            <article className="question-card" key={question.id}>
              <div className="question-head">
                <span className="eyebrow">
                  Question {safeIndex + 1} ·{" "}
                  {question.question_type === "MCQ"
                    ? "Multiple choice"
                    : "Short answer"}{" "}
                  · {question.points} point{question.points === 1 ? "" : "s"}
                </span>
              </div>
              <h2 ref={promptRef} tabIndex={-1}>
                {question.prompt}
              </h2>
              {question.question_type === "MCQ" && question.options ? (
                <div
                  className="option-list"
                  role="group"
                  aria-label={`Options for question ${safeIndex + 1}`}
                >
                  {question.options.map((option, optionIndex) => {
                    const selected =
                      props.draftAnswers[question.id] === option.id;
                    return (
                      <button
                        key={option.id}
                        className={`option${selected ? " selected" : ""}`}
                        aria-pressed={selected}
                        disabled={submitted || props.saving}
                        onClick={() => props.onAnswer(question, option.id)}
                      >
                        <span className="option-marker">
                          {selected ? (
                            <Check size={14} aria-hidden="true" />
                          ) : (
                            String.fromCharCode(65 + optionIndex)
                          )}
                        </span>
                        {option.label}
                      </button>
                    );
                  })}
                </div>
              ) : (
                <textarea
                  aria-label={`Answer for question ${safeIndex + 1}`}
                  disabled={submitted || props.saving}
                  placeholder="Type your answer here..."
                  value={props.draftAnswers[question.id] ?? ""}
                  onChange={(event) =>
                    props.onDraftChange(question.id, event.target.value)
                  }
                  onBlur={(event) =>
                    props.onAnswer(question, event.target.value)
                  }
                />
              )}
              <div className="question-actions">
                <button
                  className="secondary-button"
                  onClick={() =>
                    props.onAnswer(
                      question,
                      props.draftAnswers[question.id] ?? "",
                    )
                  }
                  disabled={submitted}
                >
                  <Save size={15} aria-hidden="true" />
                  Save answer
                </button>
              </div>
            </article>

            <div className="question-pager">
              <button
                className="secondary-button"
                onClick={() => goTo(safeIndex - 1)}
                disabled={safeIndex === 0}
              >
                <ChevronLeft size={16} aria-hidden="true" />
                Previous
              </button>
              <span>
                {safeIndex + 1} of {questions.length}
              </span>
              <button
                className="secondary-button"
                onClick={() => goTo(safeIndex + 1)}
                disabled={safeIndex >= questions.length - 1}
              >
                Next
                <ChevronRight size={16} aria-hidden="true" />
              </button>
            </div>
          </div>

          <aside className="exam-rail">
            <section className="rail-card" aria-label="Question navigation">
              <div className="rail-card-head">
                <h2>Progress</h2>
                <span>
                  {answeredCount} of {questions.length} answered
                </span>
              </div>
              <div className="nav-grid">
                {questions.map((item, itemIndex) => {
                  const answered =
                    (props.draftAnswers[item.id] ?? "").trim().length > 0;
                  return (
                    <button
                      key={item.id}
                      className={`nav-dot${itemIndex === safeIndex ? " current" : ""}${answered ? " answered" : ""}`}
                      aria-label={`Question ${itemIndex + 1}${answered ? ", answered" : ", not answered"}`}
                      aria-current={
                        itemIndex === safeIndex ? "true" : undefined
                      }
                      onClick={() => goTo(itemIndex)}
                    >
                      {itemIndex + 1}
                    </button>
                  );
                })}
              </div>
            </section>

            <section className="rail-card" aria-label="Proctoring status">
              <div className="rail-card-head">
                <h2>Proctoring</h2>
                <span className="proctor-live">
                  <span className="live-dot" />
                  {props.monitoringActive ? "Active" : "Standby"}
                </span>
              </div>
              <ul className="proctor-list">
                <li>
                  <ShieldCheck size={15} aria-hidden="true" />
                  <span>Monitoring</span>
                  <strong>
                    {props.monitoringActive ? "Active" : "Standby"}
                  </strong>
                </li>
                <li>
                  <ScanFace size={15} aria-hidden="true" />
                  <span>Camera</span>
                  <strong>
                    {!required.camera
                      ? "Disabled"
                      : !required.face
                        ? "Enabled"
                        : props.faceMonitor.faceCount === null
                          ? "No sample"
                          : `${props.faceMonitor.faceCount} face${props.faceMonitor.faceCount === 1 ? "" : "s"}`}
                  </strong>
                </li>
                <li>
                  <ScanFace size={15} aria-hidden="true" />
                  <span>Identity</span>
                  <strong>
                    {props.identityMonitor.status === "matched"
                      ? "Verified"
                      : props.identityMonitor.status === "checking"
                        ? "Checking"
                        : props.identityMonitor.status === "review"
                          ? "Review"
                          : props.identityMonitor.status === "error"
                            ? "Error"
                            : "Waiting"}
                  </strong>
                </li>
                <li>
                  <MonitorUp size={15} aria-hidden="true" />
                  <span>Screen</span>
                  <strong>
                    {!required.screen
                      ? "Disabled"
                      : props.screenMonitor.status === "active"
                        ? "Recording"
                        : "Off"}
                  </strong>
                </li>
                <li>
                  <Activity size={15} aria-hidden="true" />
                  <span>Risk</span>
                  <strong
                    className={`risk-${props.liveRiskLabel.toLowerCase()}`}
                  >
                    {props.liveRiskScore}/100 {props.liveRiskLabel}
                  </strong>
                </li>
                <li>
                  <Radio size={15} aria-hidden="true" />
                  <span>Heartbeat</span>
                  <strong>
                    {props.lastHeartbeatAckAt ? "Synced" : "Waiting"}
                  </strong>
                </li>
                <li>
                  <RotateCw size={15} aria-hidden="true" />
                  <span>Sync</span>
                  <strong>
                    {props.retryQueue.length > 0
                      ? `${props.retryQueue.length} queued`
                      : "Clear"}
                  </strong>
                </li>
              </ul>
              <video
                ref={props.videoRef}
                hidden={!required.camera}
                aria-label="Local face monitor preview"
                muted
                playsInline
              />
            </section>

            {import.meta.env.DEV ? (
              <details className="diag-panel">
                <summary>Proctoring diagnostics &amp; demo tools</summary>
                <div className="diag-body">
                  <div className="diag-group">
                    <span className="diag-title">Network</span>
                    <label className="switch-control">
                      <input
                        type="checkbox"
                        checked={props.simulateOffline}
                        onChange={(event) =>
                          props.onSimulateOfflineChange(event.target.checked)
                        }
                      />
                      <span>Simulate network outage</span>
                    </label>
                    <p className="diag-line">
                      {props.retryQueue.length} queued operation
                      {props.retryQueue.length === 1 ? "" : "s"}
                      {props.retryQueue[0]
                        ? ` — next: ${props.retryQueue[0].label} (${props.retryQueue[0].status})`
                        : ""}
                    </p>
                    <button
                      className="secondary-button small"
                      onClick={() => void props.onFlushQueue()}
                      disabled={
                        props.simulateOffline || props.retryQueue.length === 0
                      }
                    >
                      <RotateCw size={14} aria-hidden="true" />
                      Retry sync
                    </button>
                  </div>

                  <div className="diag-group">
                    <span className="diag-title">
                      Face &amp; object monitors
                    </span>
                    <p className="diag-line">
                      Face:{" "}
                      {props.aiModel
                        ? `${props.aiModel.name} · ${props.faceMonitor.samplesAnalyzed} samples`
                        : props.faceMonitor.detail}
                    </p>
                    <p className="diag-line" aria-live="polite">
                      Identity: {props.identityMonitor.detail}
                      {props.identityMonitor.similarity !== null
                        ? ` · similarity ${props.identityMonitor.similarity.toFixed(2)}`
                        : ""}
                      {props.identityMonitor.checkedAt
                        ? ` · checked ${new Date(props.identityMonitor.checkedAt).toLocaleTimeString()}`
                        : ""}
                    </p>
                    <p className="diag-line">
                      Object:{" "}
                      {props.objectMonitor.confidence === null
                        ? props.objectMonitor.detail
                        : `${props.objectMonitor.detail} · ${Math.round(props.objectMonitor.confidence * 100)}%`}
                    </p>
                    <div className="button-grid">
                      <button
                        className="secondary-button small"
                        onClick={() => void props.onFaceDemo(0)}
                        disabled={
                          !props.monitoringActive || !props.sidecarReady
                        }
                      >
                        <UserRoundX size={14} aria-hidden="true" />
                        Face absent
                      </button>
                      <button
                        className="secondary-button small"
                        onClick={() => void props.onFaceDemo(2)}
                        disabled={
                          !props.monitoringActive || !props.sidecarReady
                        }
                      >
                        <UsersRound size={14} aria-hidden="true" />
                        Multiple people
                      </button>
                      <button
                        className="secondary-button small"
                        onClick={props.onPhoneDemo}
                        disabled={!props.monitoringActive}
                      >
                        <Smartphone size={14} aria-hidden="true" />
                        Phone/object
                      </button>
                      <button
                        className="secondary-button small"
                        onClick={props.onVoiceDemo}
                        disabled={!props.monitoringActive}
                      >
                        <Volume2 size={14} aria-hidden="true" />
                        Background voice
                      </button>
                    </div>
                  </div>

                  <div className="diag-group">
                    <span className="diag-title">Browser integrity</span>
                    <p className="diag-line">
                      Clipboard, shortcut, focus, fullscreen, and screen-share
                      signals are sent live. Screen evidence:{" "}
                      {props.screenMonitor.status} |{" "}
                      {props.screenMonitor.detail}
                    </p>
                    <div className="button-grid">
                      <button
                        className="secondary-button small"
                        onClick={() =>
                          void props.sendIntegrityEvent(
                            "CLIPBOARD_PASTE",
                            {
                              source: "manual_browser_demo",
                              action: "paste",
                              review_note:
                                "Manual browser-integrity demo event.",
                            },
                            "HIGH",
                            7,
                            false,
                          )
                        }
                        disabled={!props.monitoringActive}
                      >
                        <ClipboardList size={14} aria-hidden="true" />
                        Clipboard
                      </button>
                      <button
                        className="secondary-button small"
                        onClick={() =>
                          void props.sendIntegrityEvent(
                            "DEVTOOLS_SHORTCUT",
                            {
                              source: "manual_browser_demo",
                              shortcut: "F12",
                              review_note:
                                "Manual shortcut-integrity demo event.",
                            },
                            "MEDIUM",
                            6,
                            false,
                          )
                        }
                        disabled={!props.monitoringActive}
                      >
                        <Keyboard size={14} aria-hidden="true" />
                        Shortcut
                      </button>
                      <button
                        className="secondary-button small"
                        onClick={() =>
                          void props.sendIntegrityEvent(
                            "SCREEN_SHARE_ATTEMPT",
                            {
                              source: "manual_browser_demo",
                              review_note:
                                "Manual screen-share-integrity demo event.",
                            },
                            "HIGH",
                            8,
                            false,
                          )
                        }
                        disabled={!props.monitoringActive}
                      >
                        <ScreenShare size={14} aria-hidden="true" />
                        Screen share
                      </button>
                    </div>
                  </div>

                  <div className="diag-group">
                    <span className="diag-title">Last event</span>
                    <p className="diag-line">
                      <strong>
                        {props.lastEvent
                          ? props.lastEvent.event_type.replaceAll("_", " ")
                          : "None"}
                      </strong>
                      <br />
                      {props.lastEvent
                        ? `${props.lastEvent.status} | Priority ${props.lastEvent.priority_score} | Evidence ${props.lastEvent.evidence_status}`
                        : "Ready"}
                    </p>
                    <button
                      className="secondary-button small"
                      onClick={() => void props.sendIntegrityEvent()}
                      disabled={!props.monitoringActive}
                    >
                      <Send size={14} aria-hidden="true" />
                      Send test event
                    </button>
                  </div>
                </div>
              </details>
            ) : null}
          </aside>
        </div>
      ) : (
        <div className="state-card" role="status">
          <ClipboardList size={30} aria-hidden="true" />
          <h2>No questions available</h2>
          <p>
            This assessment does not have questions yet. Contact your examiner.
          </p>
        </div>
      )}

      <canvas ref={props.canvasRef} aria-hidden="true" hidden />
    </main>
  );
}
