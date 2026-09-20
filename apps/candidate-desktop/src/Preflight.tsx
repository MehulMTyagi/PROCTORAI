import { useEffect, useRef, useState } from "react";
import { ArrowLeft, ArrowRight, Camera, Check, CheckCircle2, Circle, ClipboardList, Clock3, Expand, LockKeyhole, Mic, RotateCw, ScanFace, ShieldCheck, Wifi, XCircle } from "lucide-react";

export type ReadinessKey = "backend" | "camera" | "microphone" | "sidecar" | "fullscreen" | "liveness";
export type CheckStatus = "pending" | "pass" | "warning" | "fail";
export type ReadinessCheck = { key: ReadinessKey; label: string; status: CheckStatus; detail: string };
type Assessment = { id: string; title: string; description: string | null; duration_minutes: number | null; status: string };
type Props = {
  assessments: Assessment[];
  selected: Assessment | null;
  questionCount: number;
  checks: ReadinessCheck[];
  consent: boolean;
  busy: boolean;
  connected: boolean;
  onSelect: (id: string) => Promise<void>;
  onReconnect: () => Promise<void>;
  onConsent: (value: boolean) => void;
  onCheck: (key: ReadinessKey, status: CheckStatus, detail: string) => void;
  onSystemCheck: () => Promise<void>;
  onFullscreen: () => Promise<void>;
  onStart: () => Promise<void>;
};

const steps = [
  { path: "assessments", label: "Assessment", title: "Your assessment", icon: ClipboardList },
  { path: "consent", label: "Consent", title: "Privacy & consent", icon: ShieldCheck },
  { path: "system", label: "System", title: "System requirements", icon: Wifi },
  { path: "camera", label: "Camera", title: "Camera check", icon: Camera },
  { path: "microphone", label: "Microphone", title: "Microphone check", icon: Mic },
  { path: "liveness", label: "Liveness", title: "Liveness challenge", icon: ScanFace },
  { path: "review", label: "Review", title: "Ready for your assessment?", icon: CheckCircle2 },
];

const livenessChallenges = ["Blink once", "Turn your head left", "Turn your head right"];

function shuffledChallenges() {
  const items = [...livenessChallenges];
  const random = crypto.getRandomValues(new Uint32Array(items.length));
  for (let index = items.length - 1; index > 0; index -= 1) {
    const swapIndex = random[index] % (index + 1);
    [items[index], items[swapIndex]] = [items[swapIndex], items[index]];
  }
  return items;
}

async function sha256Hex(input: string) {
  const bytes = new TextEncoder().encode(input);
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("");
}

export function CheckResult({ check }: { check: ReadinessCheck }) {
  const Icon = check.status === "pass" ? CheckCircle2 : check.status === "pending" ? Circle : XCircle;
  return <div className={`requirement-result ${check.status}`} role="status">
    <Icon size={21} aria-hidden="true" />
    <div><strong>{check.label}</strong><p>{check.detail}</p></div>
    <span>{check.status === "pass" ? "Passed" : check.status === "pending" ? "Not checked" : "Needs attention"}</span>
  </div>;
}

export default function Preflight(props: Props) {
  const { checks, selected, consent, onCheck } = props;
  const [route, setRoute] = useState(() => window.location.hash.slice(2));
  const [testing, setTesting] = useState(false);
  const [level, setLevel] = useState(0);
  const [challengeOrder, setChallengeOrder] = useState(() => shuffledChallenges());
  const [challengeIndex, setChallengeIndex] = useState(0);
  const [challengeHashes, setChallengeHashes] = useState<string[]>([]);
  const camera = useRef<MediaStream | null>(null);
  const microphone = useRef<MediaStream | null>(null);
  const livenessVideo = useRef<HTMLVideoElement | null>(null);
  const livenessCanvas = useRef<HTMLCanvasElement | null>(null);
  const generation = useRef(0);
  const heading = useRef<HTMLHeadingElement>(null);
  const pass = (key: ReadinessKey) => checks.some((check) => check.key === key && check.status === "pass");
  const completed = [
    Boolean(selected),
    consent,
    pass("backend") && pass("sidecar"),
    pass("camera"),
    pass("microphone"),
    pass("liveness"),
    checks.every((check) => check.status === "pass"),
  ];
  const firstIncomplete = completed.findIndex((done) => !done);
  const availableThrough = firstIncomplete < 0 ? 6 : Math.min(firstIncomplete, 6);
  const requestedStep = steps.findIndex((step) => step.path === route);
  const index = Math.min(Math.max(requestedStep, 0), availableThrough);
  const step = steps[index];
  const busy = props.busy || testing;

  function navigate(next: number) {
    window.location.hash = `/${steps[next].path}`;
  }

  useEffect(() => {
    const sync = () => setRoute(window.location.hash.slice(2));
    window.addEventListener("hashchange", sync);
    return () => window.removeEventListener("hashchange", sync);
  }, []);

  useEffect(() => {
    if (route !== step.path) {
      window.history.replaceState(null, "", `#/${step.path}`);
      setRoute(step.path);
    }
    document.title = `${step.label} | ProctorAI Candidate`;
    heading.current?.focus();
    window.scrollTo(0, 0);
  }, [step.path, route]);

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
    onCheck("liveness", "pending", "Not checked");
    setChallengeOrder(shuffledChallenges());
    setChallengeIndex(0);
    setChallengeHashes([]);
  }, [consent]);

  useEffect(() => {
    if (step.path !== "liveness" || !livenessVideo.current || !camera.current) return;
    livenessVideo.current.srcObject = camera.current;
    void livenessVideo.current.play().catch(() => {});
  }, [step.path, checks.find((check) => check.key === "camera")?.status]);

  useEffect(() => {
    if (step.path !== "microphone" || !microphone.current || !pass("microphone")) return;
    const context = new AudioContext();
    const analyser = context.createAnalyser();
    analyser.fftSize = 256;
    const source = context.createMediaStreamSource(microphone.current);
    source.connect(analyser);
    void context.resume().catch(() => {});
    const data = new Uint8Array(analyser.fftSize);
    const interval = window.setInterval(() => {
      analyser.getByteTimeDomainData(data);
      const rms = Math.sqrt(data.reduce((sum, sample) => sum + ((sample - 128) / 128) ** 2, 0) / data.length);
      setLevel(Math.min(100, Math.round(rms * 500)));
    }, 100);
    return () => {
      window.clearInterval(interval);
      source.disconnect();
      void context.close();
      setLevel(0);
    };
  }, [step.path, checks.find((check) => check.key === "microphone")?.status]);

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
      if (!navigator.mediaDevices?.getUserMedia) throw new Error("Device access is unavailable. Open this page on localhost or HTTPS in a supported browser.");
      const acquisition = navigator.mediaDevices.getUserMedia(kind === "camera" ? { video: { width: 640, height: 480 } } : { audio: true });
      void acquisition.then((stream) => {
        if (expired || request !== generation.current) stream.getTracks().forEach((track) => track.stop());
      }).catch(() => {});
      const stream = await Promise.race([
        acquisition,
        new Promise<never>((_, reject) => {
          timer = window.setTimeout(() => { expired = true; reject(new Error("Permission request timed out. Allow device access in your browser, then retry.")); }, 15000);
        }),
      ]);
      if (request !== generation.current) return;
      const track = stream.getTracks()[0];
      if (!track || track.readyState !== "live" || track.muted) {
        stream.getTracks().forEach((item) => item.stop());
        throw new Error("No live input is available. Check the device connection and retry.");
      }
      streamRef.current = stream;
      track.onended = () => onCheck(kind, "fail", "Device disconnected. Reconnect it and run the check again.");
      track.onmute = () => onCheck(kind, "fail", "Device input paused. Restore access and run the check again.");
      onCheck(kind, "pass", track.label || `${kind === "camera" ? "Camera" : "Microphone"} input available`);
      if (kind === "camera") {
        onCheck("liveness", "pending", "Run the liveness challenge after the camera check.");
        setChallengeOrder(shuffledChallenges());
        setChallengeIndex(0);
        setChallengeHashes([]);
      }
    } catch (error) {
      if (request !== generation.current) return;
      const message = error instanceof DOMException && error.name === "NotAllowedError"
        ? "Access denied. Allow this device in your browser's site permissions, then retry."
        : error instanceof DOMException && error.name === "NotFoundError"
          ? "No device found. Connect a device, then retry."
          : error instanceof Error ? error.message : "Device unavailable. Check the connection and retry.";
      onCheck(kind, "fail", message);
    } finally {
      window.clearTimeout(timer);
      if (request === generation.current) setTesting(false);
    }
  }

  async function captureLivenessFrame() {
    if (!camera.current || !pass("camera")) {
      onCheck("liveness", "fail", "Run the camera check before liveness.");
      return;
    }

    const video = livenessVideo.current;
    const canvas = livenessCanvas.current;
    if (!video || !canvas || video.readyState < HTMLMediaElement.HAVE_CURRENT_DATA) {
      onCheck("liveness", "fail", "Live camera preview is not ready. Reopen the liveness step and retry.");
      return;
    }

    canvas.width = 224;
    canvas.height = 168;
    const context = canvas.getContext("2d");
    if (!context) return;
    context.drawImage(video, 0, 0, canvas.width, canvas.height);
    const dataUrl = canvas.toDataURL("image/jpeg", 0.58);
    const hash = await sha256Hex(dataUrl);
    const nextHashes = [...challengeHashes, hash];
    const uniqueCount = new Set(nextHashes).size;

    if (nextHashes.length >= challengeOrder.length) {
      if (uniqueCount < challengeOrder.length) {
        onCheck("liveness", "fail", "Liveness failed because the captured challenge frames did not change. Retry with clear movement.");
        setChallengeIndex(0);
        setChallengeHashes([]);
        return;
      }
      onCheck("liveness", "pass", "Blink and head-turn challenge completed with changing live frames.");
      setChallengeIndex(challengeOrder.length - 1);
      setChallengeHashes(nextHashes);
      return;
    }

    setChallengeHashes(nextHashes);
    setChallengeIndex(nextHashes.length);
    onCheck("liveness", "pending", `${nextHashes.length} of ${challengeOrder.length} liveness prompts captured.`);
  }

  function resetLiveness() {
    setChallengeOrder(shuffledChallenges());
    setChallengeIndex(0);
    setChallengeHashes([]);
    onCheck("liveness", "pending", "Run the blink and head-turn prompts.");
  }

  return <div className="preflight-layout">
    <aside className="journey-sidebar">
      <p className="eyebrow">Before you begin</p>
      <h2>Session setup</h2>
      <nav aria-label="Assessment setup"><ol className="step-list">
        {steps.map((item, i) => <li key={item.path}>
          <button className={`step-link ${i === index ? "current" : ""}`} aria-current={i === index ? "step" : undefined}
            disabled={i > availableThrough || busy} onClick={() => navigate(i)}>
            <span className={`step-number ${completed[i] ? "complete" : ""}`}>{completed[i] ? <Check size={16} aria-label="Complete" /> : i + 1}</span>
            <span>{item.label}</span>
            {i > availableThrough && <LockKeyhole size={14} aria-label="Locked" />}
          </button>
        </li>)}
      </ol></nav>
      <div className="privacy-note"><ShieldCheck size={21} aria-hidden="true" /><p>Camera analysis stays on your device. Monitoring signals are available to your proctor for review.</p></div>
    </aside>

    <main id="main-content" className="setup-page" tabIndex={-1}>
      <div className="page-heading"><span className="eyebrow">Step {index + 1} of {steps.length}</span>
        <h1 ref={heading} tabIndex={-1}>{step.title}</h1>
      </div>

      {index === 0 && <section aria-label="Assigned assessments">
        <div className="section-heading"><h2>Assigned to you</h2><button className="icon-button" title="Refresh assessments" aria-label="Refresh assessments" onClick={props.onReconnect} disabled={busy}><RotateCw size={18} /></button></div>
        {!props.connected && props.busy ? <div className="empty-state" role="status"><Wifi size={28} /><h2>Connecting to your assessment</h2><p>Loading your assigned assessments...</p></div>
          : !props.connected ? <div className="empty-state"><Wifi size={28} /><h2>Connection unavailable</h2><p>Your assessments could not be loaded.</p><button onClick={props.onReconnect} disabled={busy}>Reconnect</button></div>
          : !props.assessments.length ? <div className="empty-state"><ClipboardList size={28} /><h2>No assigned assessments</h2><p>Check with your examiner, then refresh this page.</p></div>
          : <div className="assessment-choices" role="radiogroup" aria-label="Choose an assessment">{props.assessments.map((assessment) => <label className={`assessment-choice ${selected?.id === assessment.id ? "chosen" : ""}`} key={assessment.id}>
            <input type="radio" name="assessment" checked={selected?.id === assessment.id} disabled={busy} onChange={() => void props.onSelect(assessment.id)} />
            <span><strong>{assessment.title}</strong><span className="assessment-description">{assessment.description || "Assigned assessment"}</span>
              <span className="assessment-meta"><Clock3 size={15} /> {assessment.duration_minutes == null ? "No time limit specified" : `${assessment.duration_minutes} minutes`} <span>{assessment.status}</span></span></span>
          </label>)}</div>}
      </section>}

      {index === 1 && <section aria-label="Consent requirements">
        <div className="policy-row"><Camera size={23} /><div><h2>Camera & microphone access</h2><p>Your camera supports local face checks during the assessment. Microphone access is checked before you begin; audio is not recorded in this version.</p></div></div>
        <div className="policy-row"><ShieldCheck size={23} /><div><h2>Privacy & human review</h2><p>Camera frames are analyzed locally. Focus changes, fullscreen exits, connection health, liveness, and face-check signals may be sent for proctor review. A signal is not a misconduct decision. Short evidence clips are uploaded only when an integrity event needs review.</p></div></div>
        <div className="policy-row"><ClipboardList size={23} /><div><h2>Assessment conditions</h2><p>Camera access, microphone access, a working connection, local monitoring, and fullscreen are required. Contact your examiner before starting if you need an accommodation.</p></div></div>
        <label className="consent-control"><input type="checkbox" checked={consent} onChange={(event) => props.onConsent(event.target.checked)} /><span>I have read this information and consent to monitoring for this assessment.</span></label>
      </section>}

      {index === 2 && <section aria-label="System checks">
        <p className="page-description">Verify your assessment connection and local monitoring service.</p>
        <div className="requirement-list">{checks.filter((check) => check.key === "backend" || check.key === "sidecar").map((check) => <CheckResult check={check} key={check.key} />)}</div>
        <button onClick={props.onSystemCheck} disabled={busy}><RotateCw size={18} />{props.busy ? "Checking system..." : "Check system"}</button>
      </section>}

      {index === 3 && <section aria-label="Camera requirement">
        <p className="page-description">A working camera is required for local face monitoring.</p>
        <div className="camera-preview">
          {pass("camera") ? <video autoPlay muted playsInline aria-label="Camera preview" ref={(node) => { if (node && camera.current) node.srcObject = camera.current; }} />
            : <div className="preview-placeholder"><Camera size={36} /><span>{testing ? "Waiting for camera permission" : "Camera is not connected"}</span></div>}
          <span className="preview-label"><span className={pass("camera") ? "live-dot" : ""} />Local preview</span>
        </div>
        <CheckResult check={checks.find((check) => check.key === "camera")!} />
        <button onClick={() => void testDevice("camera")} disabled={busy}><Camera size={18} />{testing ? "Checking camera..." : pass("camera") ? "Test camera again" : "Enable camera"}</button>
      </section>}

      {index === 4 && <section aria-label="Microphone requirement">
        <p className="page-description">A working microphone is required for this assessment.</p>
        <div className="microphone-preview"><Mic size={40} aria-hidden="true" /><strong>{pass("microphone") ? "Microphone connected" : "Microphone is not connected"}</strong>
          <meter min={0} max={100} value={level} aria-label="Microphone input level" />
          <span>Input level: {level}%</span>
        </div>
        <CheckResult check={checks.find((check) => check.key === "microphone")!} />
        <button onClick={() => void testDevice("microphone")} disabled={busy}><Mic size={18} />{testing ? "Checking microphone..." : pass("microphone") ? "Test microphone again" : "Enable microphone"}</button>
      </section>}

      {index === 5 && <section aria-label="Liveness challenge">
        <p className="page-description">Complete the randomized live-camera prompts. Move clearly before capturing each prompt.</p>
        <div className="camera-preview">
          {pass("camera") ? <video autoPlay muted playsInline aria-label="Liveness camera preview" ref={livenessVideo} />
            : <div className="preview-placeholder"><ScanFace size={36} /><span>Camera check required before liveness</span></div>}
          <span className="preview-label"><span className={pass("camera") ? "live-dot" : ""} />Local liveness preview</span>
          <canvas ref={livenessCanvas} aria-hidden="true" hidden />
        </div>
        <div className="liveness-panel">
          <span className="eyebrow">Prompt {Math.min(challengeIndex + 1, challengeOrder.length)} of {challengeOrder.length}</span>
          <h2>{challengeOrder[Math.min(challengeIndex, challengeOrder.length - 1)]}</h2>
          <p>{pass("liveness") ? "Challenge complete." : "Perform the prompt, then capture the frame."}</p>
        </div>
        <CheckResult check={checks.find((check) => check.key === "liveness")!} />
        <div className="liveness-actions">
          <button onClick={() => void captureLivenessFrame()} disabled={busy || !pass("camera") || pass("liveness")}><ScanFace size={18} />Capture prompt</button>
          <button className="secondary-button" onClick={resetLiveness} disabled={busy}><RotateCw size={18} />Reset challenge</button>
        </div>
      </section>}

      {index === 6 && <section aria-label="Final readiness review">
        <div className="review-assessment"><ClipboardList size={25} /><div><h2>{selected?.title}</h2><p>{selected?.duration_minutes == null ? "No time limit specified" : `${selected.duration_minutes} minutes`} / {props.questionCount} questions</p></div></div>
        <div className="requirement-list"><div className="requirement-result pass"><ShieldCheck size={21} /><div><strong>Monitoring consent</strong><p>Accepted for this assessment</p></div><span>Accepted</span></div>
          {checks.map((check) => <CheckResult check={check} key={check.key} />)}</div>
        {!pass("fullscreen") && <button onClick={props.onFullscreen} disabled={busy}><Expand size={18} />Enter fullscreen</button>}
      </section>}

      <footer className="setup-footer">
        <button className="secondary-button" disabled={index === 0 || busy} onClick={() => navigate(index - 1)}><ArrowLeft size={18} />Back</button>
        <span>{completed.filter(Boolean).length} of {steps.length} complete</span>
        {index < 6 ? <button disabled={!completed[index] || busy} onClick={() => navigate(index + 1)}>Continue<ArrowRight size={18} /></button>
          : <button disabled={!completed.every(Boolean) || busy} onClick={props.onStart}>{props.busy ? "Starting..." : "Start assessment"}<ArrowRight size={18} /></button>}
      </footer>
    </main>
  </div>;
}
