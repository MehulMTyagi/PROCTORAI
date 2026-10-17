import { useEffect, useRef, useState } from "react";
import {
  ArrowLeft,
  ArrowRight,
  Ban,
  Camera,
  Check,
  CheckCircle2,
  Circle,
  ClipboardList,
  Clock3,
  Expand,
  Mic,
  MonitorCheck,
  RotateCw,
  ScanFace,
  ShieldCheck,
  XCircle,
} from "lucide-react";
import type {
  AssessmentDetail,
  CheckStatus,
  LivenessPrompt,
  LivenessSample,
  ReadinessCheck,
  ReadinessKey,
} from "./types";
import { requiredCheck, requirements } from "./proctoring";

type Props = {
  step: string;
  assessment: AssessmentDetail | null;
  checks: ReadinessCheck[];
  consent: boolean;
  busy: boolean;
  error: string | null;
  canStart: boolean;
  starting: boolean;
  onBack: () => void;
  onReload: () => void;
  onConsent: (value: boolean) => void;
  onCheck: (key: ReadinessKey, status: CheckStatus, detail: string) => void;
  onSystemCheck: () => Promise<void>;
  onScreenCapture: () => Promise<{ passed: boolean; detail: string }>;
  onDeviceAudit: () => Promise<{ passed: boolean; detail: string }>;
  onLivenessVerify: (
    samples: LivenessSample[],
  ) => Promise<{ passed: boolean; detail: string }>;
  onFullscreen: () => Promise<void>;
  onStart: () => Promise<void>;
};

type SectionState = "pass" | "pending" | "warning" | "fail" | "denied";

const livenessChallenges: { label: string; prompt: LivenessPrompt }[] = [
  { label: "Blink once", prompt: "BLINK" },
  { label: "Turn your head left", prompt: "TURN_LEFT" },
  { label: "Turn your head right", prompt: "TURN_RIGHT" },
];

function shuffledChallenges() {
  const items = [...livenessChallenges];
  const random = crypto.getRandomValues(new Uint32Array(items.length));
  for (let index = items.length - 1; index > 0; index -= 1) {
    const swapIndex = random[index] % (index + 1);
    [items[index], items[swapIndex]] = [items[swapIndex], items[index]];
  }
  return items;
}

function isDenied(check: ReadinessCheck) {
  return (
    check.status === "fail" && /denied|not granted|dismiss/i.test(check.detail)
  );
}

function groupStatus(checks: ReadinessCheck[]): SectionState {
  if (checks.length > 0 && checks.every((check) => check.status === "pass"))
    return "pass";
  if (checks.some(isDenied)) return "denied";
  if (checks.some((check) => check.status === "fail")) return "fail";
  if (checks.some((check) => check.status === "warning")) return "warning";
  return "pending";
}

function stateLabel(state: SectionState) {
  switch (state) {
    case "pass":
      return "Complete";
    case "denied":
      return "Permission denied";
    case "fail":
      return "Failed";
    case "warning":
      return "Attention needed";
    default:
      return "Pending";
  }
}

export function CheckResult({ check }: { check: ReadinessCheck }) {
  const denied = isDenied(check);
  const Icon =
    check.status === "pass"
      ? CheckCircle2
      : check.status === "pending"
        ? Circle
        : denied
          ? Ban
          : XCircle;
  return (
    <div
      className={`check-row ${check.status}${denied ? " denied" : ""}`}
      role="status"
    >
      <span className="check-icon">
        <Icon size={19} aria-hidden="true" />
      </span>
      <div className="check-text">
        <strong>{check.label}</strong>
        <p>{check.detail}</p>
      </div>
      <span className={`check-badge ${check.status}${denied ? " denied" : ""}`}>
        {check.status === "pass"
          ? "Passed"
          : check.status === "pending"
            ? "Not checked"
            : denied
              ? "Permission denied"
              : check.status === "warning"
                ? "Attention needed"
                : "Failed"}
      </span>
    </div>
  );
}

export default function SetupPage(props: Props) {
  const { checks, consent, onCheck } = props;
  const [testing, setTesting] = useState(false);
  const [level, setLevel] = useState(0);
  const [challengeOrder, setChallengeOrder] = useState(() =>
    shuffledChallenges(),
  );
  const [challengeIndex, setChallengeIndex] = useState(0);
  const [challengeSamples, setChallengeSamples] = useState<LivenessSample[]>(
    [],
  );
  const camera = useRef<MediaStream | null>(null);
  const microphone = useRef<MediaStream | null>(null);
  const livenessVideo = useRef<HTMLVideoElement | null>(null);
  const livenessCanvas = useRef<HTMLCanvasElement | null>(null);
  const generation = useRef(0);
  const pass = (key: ReadinessKey) =>
    checks.some((check) => check.key === key && check.status === "pass");
  const busy = props.busy || testing;
  const required = requirements(props.assessment?.rules);
  const requiredChecks = checks.filter((check) =>
    requiredCheck(check.key, props.assessment?.rules),
  );

  const allSections: { id: string; label: string; state: SectionState }[] = [
    { id: "consent", label: "Consent", state: consent ? "pass" : "pending" },
    {
      id: "system",
      label: "System connection",
      state: groupStatus(
        requiredChecks.filter(
          (check) => check.key === "backend" || check.key === "sidecar",
        ),
      ),
    },
    {
      id: "screen",
      label: "Screen recording",
      state: groupStatus(checks.filter((check) => check.key === "screen")),
    },
    {
      id: "camera",
      label: "Camera",
      state: groupStatus(checks.filter((check) => check.key === "camera")),
    },
    {
      id: "microphone",
      label: "Microphone",
      state: groupStatus(checks.filter((check) => check.key === "microphone")),
    },
    {
      id: "devices",
      label: "Connected devices",
      state: groupStatus(checks.filter((check) => check.key === "devices")),
    },
    {
      id: "liveness",
      label: "Liveness",
      state: groupStatus(checks.filter((check) => check.key === "liveness")),
    },
    { id: "review", label: "Final review", state: groupStatus(requiredChecks) },
  ];
  const sections = allSections.filter(
    (section) =>
      !["screen", "camera", "microphone", "devices", "liveness"].includes(
        section.id,
      ) ||
      required[
        section.id as
          "screen" | "camera" | "microphone" | "devices" | "liveness"
      ],
  );
  const doneCount = sections.filter(
    (section) => section.state === "pass",
  ).length;
  const firstIncomplete = sections.find((section) => section.state !== "pass");
  const activeSection = sections.some((section) => section.id === props.step)
    ? props.step
    : "consent";
  const activeIndex = sections.findIndex(
    (section) => section.id === activeSection,
  );
  const currentSection = sections[activeIndex];
  const allowedIndex = firstIncomplete
    ? sections.findIndex((section) => section.id === firstIncomplete.id)
    : sections.length - 1;
  const startHint = !props.canStart
    ? firstIncomplete
      ? `Complete "${firstIncomplete.label}" to enable the start button.`
      : "Enter fullscreen to enable the start button."
    : "All requirements are complete. You can start your assessment.";

  useEffect(() => {
    return () => {
      generation.current += 1;
      camera.current?.getTracks().forEach((track) => track.stop());
      microphone.current?.getTracks().forEach((track) => track.stop());
    };
  }, []);

  useEffect(() => {
    if (consent) return;
    generation.current += 1;
    camera.current?.getTracks().forEach((track) => track.stop());
    microphone.current?.getTracks().forEach((track) => track.stop());
    camera.current = null;
    microphone.current = null;
    setTesting(false);
    onCheck("camera", "pending", "Not checked");
    onCheck("microphone", "pending", "Not checked");
    onCheck("screen", "pending", "Not checked");
    onCheck("devices", "pending", "Not checked");
    onCheck("liveness", "pending", "Not checked");
    setChallengeOrder(shuffledChallenges());
    setChallengeIndex(0);
    setChallengeSamples([]);
  }, [consent]);

  useEffect(() => {
    if (!livenessVideo.current || !camera.current) return;
    livenessVideo.current.srcObject = camera.current;
    void livenessVideo.current.play().catch(() => {});
  }, [checks.find((check) => check.key === "camera")?.status]);

  useEffect(() => {
    if (!microphone.current || !pass("microphone")) return;
    const context = new AudioContext();
    const analyser = context.createAnalyser();
    analyser.fftSize = 256;
    const source = context.createMediaStreamSource(microphone.current);
    source.connect(analyser);
    void context.resume().catch(() => {});
    const data = new Uint8Array(analyser.fftSize);
    const interval = window.setInterval(() => {
      analyser.getByteTimeDomainData(data);
      const rms = Math.sqrt(
        data.reduce((sum, sample) => sum + ((sample - 128) / 128) ** 2, 0) /
          data.length,
      );
      setLevel(Math.min(100, Math.round(rms * 500)));
    }, 100);
    return () => {
      window.clearInterval(interval);
      source.disconnect();
      void context.close();
      setLevel(0);
    };
  }, [checks.find((check) => check.key === "microphone")?.status]);

  useEffect(() => {
    if (!props.assessment) return;
    if (!sections.some((section) => section.id === props.step)) {
      window.location.hash = `/assessments/${props.assessment.id}/setup/${firstIncomplete?.id ?? "review"}`;
      return;
    }
    if (activeIndex > allowedIndex) {
      window.location.hash = `/assessments/${props.assessment.id}/setup/${sections[allowedIndex].id}`;
      return;
    }
  }, [activeSection, allowedIndex, props.assessment?.id]);

  useEffect(() => {
    window.scrollTo(0, 0);
    const heading = document
      .getElementById(`setup-${activeSection}`)
      ?.querySelector<HTMLElement>("h2");
    heading?.setAttribute("tabindex", "-1");
    heading?.focus();
  }, [activeSection, props.assessment?.id]);

  function scrollToSection(id: string) {
    if (props.assessment)
      window.location.hash = `/assessments/${props.assessment.id}/setup/${id}`;
  }

  async function testDevice(kind: "camera" | "microphone") {
    if (!consent || testing) return;
    const request = ++generation.current;
    const streamRef = kind === "camera" ? camera : microphone;
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    setTesting(true);
    onCheck(kind, "pending", "Waiting for device access...");
    let timer = 0;
    let expired = false;
    try {
      if (!navigator.mediaDevices?.getUserMedia)
        throw new Error(
          "Device access is unavailable. Open this page on localhost or HTTPS in a supported browser.",
        );
      const acquisition = navigator.mediaDevices.getUserMedia(
        kind === "camera"
          ? { video: { width: 640, height: 480 } }
          : { audio: true },
      );
      void acquisition
        .then((stream) => {
          if (expired || request !== generation.current)
            stream.getTracks().forEach((track) => track.stop());
        })
        .catch(() => {});
      const stream = await Promise.race([
        acquisition,
        new Promise<never>((_, reject) => {
          timer = window.setTimeout(() => {
            expired = true;
            reject(
              new Error(
                "Permission request timed out. Allow device access in your browser, then retry.",
              ),
            );
          }, 15000);
        }),
      ]);
      if (request !== generation.current) return;
      const track = stream.getTracks()[0];
      if (!track || track.readyState !== "live" || track.muted) {
        stream.getTracks().forEach((item) => item.stop());
        throw new Error(
          "No live input is available. Check the device connection and retry.",
        );
      }
      streamRef.current = stream;
      track.onended = () =>
        onCheck(
          kind,
          "fail",
          "Device disconnected. Reconnect it and run the check again.",
        );
      track.onmute = () =>
        onCheck(
          kind,
          "fail",
          "Device input paused. Restore access and run the check again.",
        );
      onCheck(
        kind,
        "pass",
        track.label ||
          `${kind === "camera" ? "Camera" : "Microphone"} input available`,
      );
      if (kind === "camera") {
        onCheck(
          "liveness",
          "pending",
          "Run the liveness challenge after the camera check.",
        );
        setChallengeOrder(shuffledChallenges());
        setChallengeIndex(0);
        setChallengeSamples([]);
      }
    } catch (error) {
      if (request !== generation.current) return;
      const message =
        error instanceof DOMException && error.name === "NotAllowedError"
          ? "Access denied. Allow this device in your browser's site permissions, then retry."
          : error instanceof DOMException && error.name === "NotFoundError"
            ? "No device found. Connect a device, then retry."
            : error instanceof Error
              ? error.message
              : "Device unavailable. Check the connection and retry.";
      onCheck(kind, "fail", message);
    } finally {
      window.clearTimeout(timer);
      if (request === generation.current) setTesting(false);
    }
  }

  async function testScreenCapture() {
    if (!consent || testing) return;
    setTesting(true);
    onCheck("screen", "pending", "Waiting for screen-recording permission...");
    try {
      const result = await props.onScreenCapture();
      onCheck("screen", result.passed ? "pass" : "fail", result.detail);
    } catch (error) {
      onCheck(
        "screen",
        "fail",
        error instanceof Error
          ? error.message
          : "Screen recording unavailable.",
      );
    } finally {
      setTesting(false);
    }
  }

  async function auditDevices() {
    if (!consent || testing) return;
    setTesting(true);
    onCheck("devices", "pending", "Checking connected displays and devices...");
    try {
      const result = await props.onDeviceAudit();
      onCheck("devices", result.passed ? "pass" : "fail", result.detail);
    } catch (error) {
      onCheck(
        "devices",
        "fail",
        error instanceof Error
          ? error.message
          : "Connected device audit failed.",
      );
    } finally {
      setTesting(false);
    }
  }

  async function captureFrameBurst() {
    const video = livenessVideo.current;
    const canvas = livenessCanvas.current;
    if (
      !video ||
      !canvas ||
      video.readyState < HTMLMediaElement.HAVE_CURRENT_DATA
    )
      return [];

    canvas.width = 224;
    canvas.height = 168;
    const context = canvas.getContext("2d");
    if (!context) return [];

    const frames: string[] = [];
    for (let index = 0; index < 10; index += 1) {
      context.drawImage(video, 0, 0, canvas.width, canvas.height);
      frames.push(canvas.toDataURL("image/jpeg", 0.58));
      await new Promise((resolve) => window.setTimeout(resolve, 300));
    }
    return frames;
  }

  async function captureLivenessFrame() {
    if (!camera.current || !pass("camera")) {
      onCheck("liveness", "fail", "Run the camera check before liveness.");
      return;
    }

    setTesting(true);
    if (
      !livenessVideo.current ||
      livenessVideo.current.readyState < HTMLMediaElement.HAVE_CURRENT_DATA
    ) {
      onCheck(
        "liveness",
        "fail",
        "Live camera preview is not ready. Reopen the liveness step and retry.",
      );
      setTesting(false);
      return;
    }

    try {
      const frames = await captureFrameBurst();
      if (frames.length < 6)
        throw new Error("Could not capture enough live frames.");
      const nextSamples = [
        ...challengeSamples,
        {
          prompt: challengeOrder[challengeIndex].prompt,
          frame_data_urls: frames,
        },
      ];

      if (nextSamples.length >= challengeOrder.length) {
        const result = await props.onLivenessVerify(nextSamples);
        if (!result.passed) {
          onCheck("liveness", "fail", result.detail);
          setChallengeIndex(0);
          setChallengeSamples([]);
          return;
        }
        onCheck("liveness", "pass", result.detail);
        setChallengeIndex(challengeOrder.length - 1);
        setChallengeSamples(nextSamples);
        return;
      }

      setChallengeSamples(nextSamples);
      setChallengeIndex(nextSamples.length);
      onCheck(
        "liveness",
        "pending",
        `${nextSamples.length} of ${challengeOrder.length} liveness prompts captured.`,
      );
    } catch (error) {
      onCheck(
        "liveness",
        "fail",
        error instanceof Error
          ? error.message
          : "Liveness verification failed.",
      );
    } finally {
      setTesting(false);
    }
  }

  function resetLiveness() {
    setChallengeOrder(shuffledChallenges());
    setChallengeIndex(0);
    setChallengeSamples([]);
    onCheck("liveness", "pending", "Run the blink and head-turn prompts.");
  }

  function attachLivenessPreview(node: HTMLVideoElement | null) {
    livenessVideo.current = node;
    if (!node || !camera.current) return;
    node.srcObject = camera.current;
    void node.play().catch(() => {});
  }

  const assessment = props.assessment;

  if (!assessment) {
    return (
      <main id="main-content" tabIndex={-1} className="page setup-page">
        <button
          className="back-link"
          onClick={props.onBack}
          disabled={props.busy}
        >
          <ArrowLeft size={16} aria-hidden="true" />
          All assessments
        </button>
        {props.busy ? (
          <div className="state-card" role="status" aria-busy="true">
            <RotateCw size={28} className="spin" aria-hidden="true" />
            <h2>Loading assessment</h2>
            <p>Preparing your setup checklist...</p>
          </div>
        ) : (
          <div className="state-card" role="alert">
            <Ban size={30} aria-hidden="true" />
            <h2>Assessment could not be loaded</h2>
            <p>
              {props.error ??
                "The assessment is unavailable. It may have been closed or removed."}
            </p>
            <div className="state-actions">
              <button onClick={props.onReload} disabled={props.busy}>
                <RotateCw size={16} aria-hidden="true" />
                Try again
              </button>
              <button className="secondary-button" onClick={props.onBack}>
                <ArrowLeft size={16} aria-hidden="true" />
                All assessments
              </button>
            </div>
          </div>
        )}
      </main>
    );
  }

  return (
    <main id="main-content" tabIndex={-1} className="page setup-page">
      <button className="back-link" onClick={props.onBack} disabled={busy}>
        <ArrowLeft size={16} aria-hidden="true" />
        All assessments
      </button>

      <div className="setup-summary">
        <p className="eyebrow">Assessment setup</p>
        <h1>Let's get you ready.</h1>
        <p className="setup-assessment-name">{assessment.title}</p>
        <div className="setup-summary-meta">
          <span>
            <Clock3 size={15} aria-hidden="true" />
            {assessment.duration_minutes == null
              ? "No time limit"
              : `${assessment.duration_minutes} minute${assessment.duration_minutes === 1 ? "" : "s"}`}
          </span>
          <span>
            <ClipboardList size={15} aria-hidden="true" />
            {assessment.questions.length} question
            {assessment.questions.length === 1 ? "" : "s"}
          </span>
          <span className="badge tone-neutral">{assessment.status}</span>
        </div>
      </div>

      <div className="setup-layout">
        <aside className="setup-rail">
          <p className="rail-title">Before you begin</p>
          <nav aria-label="Setup progress">
            <ol className="rail-list">
              {sections.map((section, index) => (
                <li key={section.id}>
                  <button
                    className={`rail-link state-${section.state}${activeSection === section.id ? " current" : ""}`}
                    aria-current={
                      activeSection === section.id ? "step" : undefined
                    }
                    disabled={busy || index > allowedIndex}
                    onClick={() => scrollToSection(section.id)}
                  >
                    <span className="rail-dot">
                      {section.state === "pass" ? (
                        <Check size={13} aria-label="Complete" />
                      ) : (
                        index + 1
                      )}
                    </span>
                    <span className="rail-label">{section.label}</span>
                  </button>
                </li>
              ))}
            </ol>
          </nav>
          <div className="rail-progress">
            <div
              className="rail-progress-bar"
              role="progressbar"
              aria-valuemin={0}
              aria-valuemax={sections.length}
              aria-valuenow={doneCount}
              aria-label="Setup progress"
            >
              <span
                style={{
                  width: `${Math.round((doneCount / sections.length) * 100)}%`,
                }}
              />
            </div>
            <span>
              {doneCount} of {sections.length} complete
            </span>
          </div>
          <div className="privacy-note">
            <ShieldCheck size={20} aria-hidden="true" />
            <p>
              Camera analysis stays on your device. Monitoring signals are
              available to your proctor for review.
            </p>
          </div>
        </aside>

        <div className="setup-sections">
          <section
            id="setup-consent"
            hidden={activeSection !== "consent"}
            className={`setup-section state-${consent ? "pass" : "pending"}`}
          >
            <header className="section-head">
              <span className="section-num">
                {consent ? <Check size={15} aria-hidden="true" /> : 1}
              </span>
              <div className="section-title">
                <h2>Consent</h2>
                <p>
                  Review how this assessment is monitored and confirm you
                  accept.
                </p>
              </div>
              <span className={`section-state ${consent ? "pass" : "pending"}`}>
                {consent ? "Complete" : "Pending"}
              </span>
            </header>
            <div className="section-body">
              <div className="policy-row">
                <Camera size={22} aria-hidden="true" />
                <div>
                  <h3>Monitoring selected for this assessment</h3>
                  <p>
                    {required.camera
                      ? "Camera access is required. "
                      : "Camera access is not required. "}
                    {required.microphone
                      ? "Microphone monitoring is enabled; audio is not recorded. "
                      : "Microphone access is not required. "}
                    {required.screen
                      ? "Event-based screen recording is enabled."
                      : "Screen recording is disabled."}
                  </p>
                </div>
              </div>
              <div className="policy-row">
                <ShieldCheck size={22} aria-hidden="true" />
                <div>
                  <h3>Privacy &amp; human review</h3>
                  <p>
                    Camera frames are analyzed locally. Focus changes,
                    fullscreen exits, connection health, liveness, and
                    face-check signals may be sent for proctor review. A signal
                    is not a misconduct decision. Short evidence clips are
                    uploaded only when an integrity event needs review.
                  </p>
                </div>
              </div>
              <div className="policy-row">
                <ClipboardList size={22} aria-hidden="true" />
                <div>
                  <h3>Assessment conditions</h3>
                  <p>
                    Camera access, microphone access, a working connection,
                    local monitoring, and fullscreen are required. Contact your
                    examiner before starting if you need an accommodation.
                  </p>
                </div>
              </div>
              <label className="consent-control">
                <input
                  type="checkbox"
                  checked={consent}
                  onChange={(event) => props.onConsent(event.target.checked)}
                />
                <span>
                  I have read this information and consent to monitoring for
                  this assessment.
                </span>
              </label>
            </div>
          </section>

          <section
            id="setup-system"
            hidden={activeSection !== "system"}
            className={`setup-section state-${groupStatus(requiredChecks.filter((check) => check.key === "backend" || check.key === "sidecar"))}`}
          >
            <header className="section-head">
              <span className="section-num">
                {sections.findIndex((section) => section.id === "system") + 1}
              </span>
              <div className="section-title">
                <h2>System connection</h2>
                <p>
                  {required.sidecar
                    ? "Verify the assessment service and local monitoring are reachable."
                    : "Verify the assessment service is reachable. Local AI monitoring is disabled for this assessment."}
                </p>
              </div>
              <span
                className={`section-state ${groupStatus(requiredChecks.filter((check) => check.key === "backend" || check.key === "sidecar"))}`}
              >
                {stateLabel(
                  groupStatus(
                    requiredChecks.filter(
                      (check) =>
                        check.key === "backend" || check.key === "sidecar",
                    ),
                  ),
                )}
              </span>
            </header>
            <div className="section-body">
              <div className="check-list">
                {requiredChecks
                  .filter(
                    (check) =>
                      check.key === "backend" || check.key === "sidecar",
                  )
                  .map((check) => (
                    <CheckResult check={check} key={check.key} />
                  ))}
              </div>
              <button onClick={props.onSystemCheck} disabled={busy}>
                <RotateCw size={16} aria-hidden="true" />
                {props.busy
                  ? "Checking system..."
                  : pass("backend") && pass("sidecar")
                    ? "Check system again"
                    : "Check system"}
              </button>
            </div>
          </section>

          <section
            id="setup-screen"
            hidden={activeSection !== "screen"}
            className={`setup-section state-${groupStatus(checks.filter((check) => check.key === "screen"))}`}
          >
            <header className="section-head">
              <span className="section-num">
                {sections.findIndex((section) => section.id === "screen") + 1}
              </span>
              <div className="section-title">
                <h2>Screen recording</h2>
                <p>
                  Share your full screen so browser activity can be reviewed
                  during the assessment.
                </p>
              </div>
              <span
                className={`section-state ${groupStatus(checks.filter((check) => check.key === "screen"))}`}
              >
                {stateLabel(
                  groupStatus(checks.filter((check) => check.key === "screen")),
                )}
              </span>
            </header>
            <div className="section-body">
              <div className="feature-note">
                <MonitorCheck size={36} aria-hidden="true" />
                <strong>
                  {pass("screen")
                    ? "Screen recording ready"
                    : "Screen recording is required"}
                </strong>
                <span>
                  Select Entire screen/full display when prompted. Browser
                  security requires you to approve this manually.
                </span>
              </div>
              <div className="check-list">
                <CheckResult
                  check={checks.find((check) => check.key === "screen")!}
                />
              </div>
              <button onClick={() => void testScreenCapture()} disabled={busy}>
                <MonitorCheck size={16} aria-hidden="true" />
                {testing
                  ? "Checking screen..."
                  : pass("screen")
                    ? "Share screen again"
                    : "Enable screen recording"}
              </button>
            </div>
          </section>

          <section
            id="setup-camera"
            hidden={activeSection !== "camera"}
            className={`setup-section state-${groupStatus(checks.filter((check) => check.key === "camera"))}`}
          >
            <header className="section-head">
              <span className="section-num">
                {sections.findIndex((section) => section.id === "camera") + 1}
              </span>
              <div className="section-title">
                <h2>Camera</h2>
                <p>Enable your camera for local face monitoring.</p>
              </div>
              <span
                className={`section-state ${groupStatus(checks.filter((check) => check.key === "camera"))}`}
              >
                {stateLabel(
                  groupStatus(checks.filter((check) => check.key === "camera")),
                )}
              </span>
            </header>
            <div className="section-body">
              <div className="camera-preview">
                {pass("camera") ? (
                  <video
                    autoPlay
                    muted
                    playsInline
                    aria-label="Camera preview"
                    ref={(node) => {
                      if (node && camera.current)
                        node.srcObject = camera.current;
                    }}
                  />
                ) : (
                  <div className="preview-placeholder">
                    <Camera size={34} aria-hidden="true" />
                    <span>
                      {testing
                        ? "Waiting for camera permission"
                        : "Camera is not connected"}
                    </span>
                  </div>
                )}
                <span className="preview-label">
                  <span className={pass("camera") ? "live-dot" : ""} />
                  Local preview
                </span>
              </div>
              <div className="check-list">
                <CheckResult
                  check={checks.find((check) => check.key === "camera")!}
                />
              </div>
              <button onClick={() => void testDevice("camera")} disabled={busy}>
                <Camera size={16} aria-hidden="true" />
                {testing
                  ? "Checking camera..."
                  : pass("camera")
                    ? "Test camera again"
                    : "Enable camera"}
              </button>
            </div>
          </section>

          <section
            id="setup-microphone"
            hidden={activeSection !== "microphone"}
            className={`setup-section state-${groupStatus(checks.filter((check) => check.key === "microphone"))}`}
          >
            <header className="section-head">
              <span className="section-num">
                {sections.findIndex((section) => section.id === "microphone") +
                  1}
              </span>
              <div className="section-title">
                <h2>Microphone</h2>
                <p>Enable your microphone so audio signals can be reviewed.</p>
              </div>
              <span
                className={`section-state ${groupStatus(checks.filter((check) => check.key === "microphone"))}`}
              >
                {stateLabel(
                  groupStatus(
                    checks.filter((check) => check.key === "microphone"),
                  ),
                )}
              </span>
            </header>
            <div className="section-body">
              <div className="feature-note">
                <Mic size={36} aria-hidden="true" />
                <strong>
                  {pass("microphone")
                    ? "Microphone connected"
                    : "Microphone is not connected"}
                </strong>
                <meter
                  min={0}
                  max={100}
                  value={level}
                  aria-label="Microphone input level"
                />
                <span>Input level: {level}%</span>
              </div>
              <div className="check-list">
                <CheckResult
                  check={checks.find((check) => check.key === "microphone")!}
                />
              </div>
              <button
                onClick={() => void testDevice("microphone")}
                disabled={busy}
              >
                <Mic size={16} aria-hidden="true" />
                {testing
                  ? "Checking microphone..."
                  : pass("microphone")
                    ? "Test microphone again"
                    : "Enable microphone"}
              </button>
            </div>
          </section>

          <section
            id="setup-devices"
            hidden={activeSection !== "devices"}
            className={`setup-section state-${groupStatus(checks.filter((check) => check.key === "devices"))}`}
          >
            <header className="section-head">
              <span className="section-num">
                {sections.findIndex((section) => section.id === "devices") + 1}
              </span>
              <div className="section-title">
                <h2>Connected devices</h2>
                <p>
                  Confirm no extra monitor or extended display is connected.
                </p>
              </div>
              <span
                className={`section-state ${groupStatus(checks.filter((check) => check.key === "devices"))}`}
              >
                {stateLabel(
                  groupStatus(
                    checks.filter((check) => check.key === "devices"),
                  ),
                )}
              </span>
            </header>
            <div className="section-body">
              <p className="section-note">
                Built-in cameras, microphones, speakers, and Bluetooth devices
                are allowed; only extra displays are checked.
              </p>
              <div className="check-list">
                <CheckResult
                  check={checks.find((check) => check.key === "devices")!}
                />
              </div>
              <button onClick={() => void auditDevices()} disabled={busy}>
                <MonitorCheck size={16} aria-hidden="true" />
                {testing
                  ? "Checking devices..."
                  : pass("devices")
                    ? "Check devices again"
                    : "Check connected devices"}
              </button>
            </div>
          </section>

          <section
            id="setup-liveness"
            hidden={activeSection !== "liveness"}
            className={`setup-section state-${groupStatus(checks.filter((check) => check.key === "liveness"))}`}
          >
            <header className="section-head">
              <span className="section-num">
                {sections.findIndex((section) => section.id === "liveness") + 1}
              </span>
              <div className="section-title">
                <h2>Liveness</h2>
                <p>
                  Complete the randomized live-camera prompts to confirm you are
                  present.
                </p>
              </div>
              <span
                className={`section-state ${groupStatus(checks.filter((check) => check.key === "liveness"))}`}
              >
                {stateLabel(
                  groupStatus(
                    checks.filter((check) => check.key === "liveness"),
                  ),
                )}
              </span>
            </header>
            <div className="section-body">
              <div className="camera-preview">
                {pass("camera") ? (
                  <video
                    autoPlay
                    muted
                    playsInline
                    aria-label="Liveness camera preview"
                    ref={attachLivenessPreview}
                  />
                ) : (
                  <div className="preview-placeholder">
                    <ScanFace size={34} aria-hidden="true" />
                    <span>Camera check required before liveness</span>
                  </div>
                )}
                <span className="preview-label">
                  <span className={pass("camera") ? "live-dot" : ""} />
                  Local liveness preview
                </span>
                <canvas ref={livenessCanvas} aria-hidden="true" hidden />
              </div>
              <div className="liveness-panel">
                <p className="eyebrow">
                  Prompt {Math.min(challengeIndex + 1, challengeOrder.length)}{" "}
                  of {challengeOrder.length}
                </p>
                <h3>
                  {
                    challengeOrder[
                      Math.min(challengeIndex, challengeOrder.length - 1)
                    ].label
                  }
                </h3>
                <p>
                  {pass("liveness")
                    ? "Challenge complete."
                    : testing
                      ? "Sampling now. Keep the movement visible until the button unlocks."
                      : "Click capture, then perform the prompt slowly for about three seconds."}
                </p>
              </div>
              <div className="check-list">
                <CheckResult
                  check={checks.find((check) => check.key === "liveness")!}
                />
              </div>
              <div className="button-row">
                <button
                  onClick={() => void captureLivenessFrame()}
                  disabled={busy || !pass("camera") || pass("liveness")}
                >
                  <ScanFace size={16} aria-hidden="true" />
                  {testing ? "Sampling..." : "Capture prompt"}
                </button>
                <button
                  className="secondary-button"
                  onClick={resetLiveness}
                  disabled={busy}
                >
                  <RotateCw size={16} aria-hidden="true" />
                  Reset challenge
                </button>
              </div>
            </div>
          </section>

          <section
            id="setup-review"
            hidden={activeSection !== "review"}
            className={`setup-section state-${groupStatus(requiredChecks)}`}
          >
            <header className="section-head">
              <span className="section-num">
                {sections.findIndex((section) => section.id === "review") + 1}
              </span>
              <div className="section-title">
                <h2>Final review</h2>
                <p>
                  {required.fullscreen
                    ? "Confirm the enabled requirements and enter fullscreen before starting."
                    : "Confirm the enabled requirements before starting."}
                </p>
              </div>
              <span className={`section-state ${groupStatus(requiredChecks)}`}>
                {stateLabel(groupStatus(requiredChecks))}
              </span>
            </header>
            <div className="section-body">
              <div className="review-assessment">
                <ClipboardList size={24} aria-hidden="true" />
                <div>
                  <h3>{assessment.title}</h3>
                  <p>
                    {assessment.duration_minutes == null
                      ? "No time limit specified"
                      : `${assessment.duration_minutes} minutes`}{" "}
                    / {assessment.questions.length} questions
                  </p>
                </div>
              </div>
              <div className="check-list">
                <div className="check-row pass" role="status">
                  <span className="check-icon">
                    <ShieldCheck size={19} aria-hidden="true" />
                  </span>
                  <div className="check-text">
                    <strong>Monitoring consent</strong>
                    <p>Accepted for this assessment</p>
                  </div>
                  <span
                    className={`check-badge ${consent ? "pass" : "pending"}`}
                  >
                    {consent ? "Accepted" : "Required"}
                  </span>
                </div>
                {requiredChecks.map((check) => (
                  <CheckResult check={check} key={check.key} />
                ))}
              </div>
              {required.fullscreen && !pass("fullscreen") && (
                <button onClick={props.onFullscreen} disabled={busy}>
                  <Expand size={16} aria-hidden="true" />
                  Enter fullscreen
                </button>
              )}
            </div>
          </section>
        </div>
      </div>

      <footer className="setup-actionbar">
        <div className="actionbar-progress">
          <strong>
            Step {activeIndex + 1} of {sections.length} · {currentSection.label}
          </strong>
          <span>
            {activeSection === "review"
              ? startHint
              : currentSection.state === "pass"
                ? "This check is complete. Continue when you're ready."
                : "Complete this check to continue."}
          </span>
        </div>
        <div className="setup-navigation">
          <button
            className="secondary-button"
            onClick={() => scrollToSection(sections[activeIndex - 1].id)}
            disabled={activeIndex === 0 || busy}
          >
            <ArrowLeft size={16} />
            Previous
          </button>
          {activeSection === "review" ? (
            <button
              onClick={() => void props.onStart()}
              disabled={!props.canStart || busy}
            >
              {props.starting ? "Starting…" : "Start assessment"}
              <ArrowRight size={16} aria-hidden="true" />
            </button>
          ) : (
            <button
              onClick={() => scrollToSection(sections[activeIndex + 1].id)}
              disabled={currentSection.state !== "pass" || busy}
            >
              Continue
              <ArrowRight size={16} aria-hidden="true" />
            </button>
          )}
        </div>
      </footer>
    </main>
  );
}
