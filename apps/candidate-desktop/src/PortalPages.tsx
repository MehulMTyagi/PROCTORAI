import {
  ArrowRight,
  BookOpen,
  Camera,
  CheckCircle2,
  ChevronRight,
  ClipboardList,
  Clock3,
  Headphones,
  Laptop,
  MonitorUp,
  ShieldCheck,
} from "lucide-react";
import type { Assessment } from "./types";

export function CandidateHome({
  assessments,
  name,
  connected,
  onOpen,
}: {
  assessments: Assessment[];
  name: string;
  connected: boolean;
  onOpen: (id: string) => void;
}) {
  const available = assessments.filter((item) =>
    ["ACTIVE", "PUBLISHED"].includes(item.status),
  );
  const next = available[0];
  return (
    <main id="main-content" tabIndex={-1} className="page candidate-home">
      <div className="candidate-page-heading">
        <div>
          <p className="eyebrow">YOUR ASSESSMENT WORKSPACE</p>
          <h1>
            Welcome
            {name ? ", " + name.replace(/^Dev\s+/, "").split(" ")[0] : ""}.
          </h1>
          <p>Everything you need for a focused assessment, in one place.</p>
        </div>
        <span className="date-label">
          {new Intl.DateTimeFormat("en-IN", {
            day: "numeric",
            month: "long",
            year: "numeric",
          }).format(new Date())}
        </span>
      </div>
      <div className="candidate-overview-grid">
        <section className="candidate-welcome">
          <span className="welcome-shield">
            <ShieldCheck size={36} />
          </span>
          <p className="eyebrow">TAKE THE NEXT STEP</p>
          <h2>
            Your preparation.
            <br />
            Your best performance.
          </h2>
          <p>
            Find your assessment, check your setup, and begin with confidence.
            We'll guide you through each step.
          </p>
          <a className="primary-link" href="#/assessments">
            View my assessments <ArrowRight size={17} />
          </a>
          <div className="candidate-ornament" aria-hidden="true">
            <span />
            <span />
            <span />
          </div>
        </section>
        <section className="next-assessment">
          <div className="next-card-heading">
            <span className="card-icon">
              <ClipboardList size={22} />
            </span>
            <span className="eyebrow">READY TO BEGIN</span>
          </div>
          {next ? (
            <>
              <span className="badge tone-success">Available</span>
              <h2>{next.title}</h2>
              <p>
                {next.description ||
                  "Complete your setup before starting this assessment."}
              </p>
              <div className="next-meta">
                <span>
                  <Clock3 size={15} />
                  {next.duration_minutes == null
                    ? "Untimed"
                    : next.duration_minutes + " minutes"}
                </span>
                <span>
                  <ShieldCheck size={15} />
                  Online assessment
                </span>
              </div>
              <button onClick={() => onOpen(next.id)}>
                Prepare for assessment <ArrowRight size={16} />
              </button>
            </>
          ) : (
            <>
              <h2>
                {connected
                  ? "You're all caught up"
                  : "Connecting to your workspace"}
              </h2>
              <p>
                {connected
                  ? "Your available assessments will appear here when an examiner assigns them to you."
                  : "Your assigned assessments will appear when the connection is ready."}
              </p>
              <a className="secondary-button" href="#/assessments">
                View assessment list <ArrowRight size={16} />
              </a>
            </>
          )}
        </section>
      </div>
      <div className="candidate-summary-strip">
        <div>
          <span className="summary-icon blue">
            <BookOpen size={21} />
          </span>
          <div>
            <strong>{assessments.length}</strong>
            <span>
              Assigned assessment{assessments.length === 1 ? "" : "s"}
            </span>
          </div>
        </div>
        <div>
          <span className="summary-icon green">
            <CheckCircle2 size={21} />
          </span>
          <div>
            <strong>{available.length}</strong>
            <span>Available to prepare</span>
          </div>
        </div>
        <div>
          <span className="summary-icon violet">
            <ShieldCheck size={21} />
          </span>
          <div>
            <strong>Guided setup</strong>
            <span>Check your equipment before you begin</span>
          </div>
        </div>
      </div>
      <section className="preparation-panel">
        <div className="preparation-heading">
          <div>
            <h2>A little preparation goes a long way</h2>
            <p>Get your space and equipment ready before your assessment.</p>
          </div>
          <a href="#/help">
            Preparation guide <ArrowRight size={15} />
          </a>
        </div>
        <div className="preparation-cards">
          {[
            {
              icon: <Laptop size={24} />,
              title: "Use a desktop or laptop",
              description:
                "Choose a supported browser and a stable internet connection.",
            },
            {
              icon: <Camera size={24} />,
              title: "Check your equipment",
              description:
                "Have your camera and microphone ready. Use one display.",
            },
            {
              icon: <Headphones size={24} />,
              title: "Find a quiet space",
              description:
                "Choose good lighting and a workspace where you won't be interrupted.",
            },
          ].map((item, index) => (
            <article key={item.title}>
              <span className="prep-number">0{index + 1}</span>
              <span className="prep-icon">{item.icon}</span>
              <h3>{item.title}</h3>
              <p>{item.description}</p>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}

export function CandidateHelp() {
  return (
    <main id="main-content" tabIndex={-1} className="page candidate-help">
      <div className="candidate-page-heading">
        <div>
          <p className="eyebrow">CANDIDATE GUIDANCE</p>
          <h1>A smoother assessment starts here.</h1>
          <p>Know what to expect before you begin.</p>
        </div>
        <span className="guide-mark">
          <BookOpen size={29} />
        </span>
      </div>
      <div className="help-intro">
        <ShieldCheck size={27} />
        <div>
          <h2>Your assessment, step by step</h2>
          <p>
            Select an assessment → complete setup → answer the questions →
            review and submit.
          </p>
        </div>
      </div>
      <div className="candidate-help-grid">
        <section className="help-faq">
          <h2>Common questions</h2>
          {[
            {
              q: "What equipment do I need?",
              a: "Use a desktop or laptop with a stable internet connection. Your examiner chooses which camera, microphone, display, fullscreen and liveness checks are required. Setup only asks for the features enabled for your assessment.",
            },
            {
              q: "Why do I need to share my screen?",
              a: "When enabled by your examiner, screen recording provides context for browser events. During setup, choose your entire display in the browser's sharing dialog. Tab or window capture will not pass the full-display check. Assessments with screen recording disabled skip this step.",
            },
            {
              q: "What if I deny a permission?",
              a: "The related setup check will show what needs attention. Enable the permission in your browser's site settings, then retry the check. You cannot begin until the required checks pass.",
            },
            {
              q: "What happens during the liveness check?",
              a: "You'll follow prompts to blink or turn your head. Keep your face visible in good lighting, click Capture, and perform the requested action while the camera samples your movement.",
            },
            {
              q: "Does an integrity signal mean I failed?",
              a: "No. Signals identify activity for a human proctor to review. The proctor considers the evidence and context before recording a decision.",
            },
            {
              q: "What happens if my connection drops?",
              a: "The application queues supported answers and monitoring signals for retry. Keep the assessment open, reconnect, and wait for queued items to sync before submitting.",
            },
          ].map((item) => (
            <details key={item.q}>
              <summary>
                {item.q}
                <ChevronRight size={16} />
              </summary>
              <p>{item.a}</p>
            </details>
          ))}
        </section>
        <aside className="candidate-help-aside">
          <span className="card-icon">
            <MonitorUp size={24} />
          </span>
          <h2>Before test day</h2>
          <ul>
            <li>Check your camera and microphone.</li>
            <li>Disconnect any extra displays.</li>
            <li>Close unrelated apps and browser tabs.</li>
            <li>Plug in your laptop or charge it fully.</li>
            <li>Make time for the setup checks.</li>
          </ul>
          <div className="help-contact">
            <strong>Need an accommodation?</strong>
            <p>
              Contact your examiner before starting. Your institution can advise
              on assessment arrangements.
            </p>
          </div>
          <a className="primary-link" href="#/assessments">
            Back to assessments <ArrowRight size={16} />
          </a>
        </aside>
      </div>
    </main>
  );
}
