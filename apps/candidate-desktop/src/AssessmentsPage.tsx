import { useState } from "react";
import {
  ArrowRight,
  BookOpen,
  ClipboardList,
  Clock3,
  RotateCw,
  Search,
  ShieldCheck,
  WifiOff,
} from "lucide-react";
import type { Assessment } from "./types";

type Props = {
  assessments: Assessment[];
  connected: boolean;
  busy: boolean;
  attemptedAssessmentIds: string[];
  onRefresh: () => void;
  onOpen: (assessmentId: string) => void;
};

export default function AssessmentsPage(props: Props) {
  const [filter, setFilter] = useState("ALL");
  const [search, setSearch] = useState("");
  const available = (assessment: Assessment) =>
    ["ACTIVE", "PUBLISHED"].includes(assessment.status);
  const completed = (assessment: Assessment) =>
    assessment.attempt_status === "SUBMITTED";
  const visible = props.assessments.filter(
    (item) =>
      (filter === "ALL" ||
        (filter === "AVAILABLE" ? available(item) : !available(item))) &&
      (item.title + " " + (item.description ?? ""))
        .toLowerCase()
        .includes(search.toLowerCase()),
  );
  const connecting = !props.connected && props.busy;
  return (
    <main id="main-content" tabIndex={-1} className="page assessments-page">
      <div className="candidate-page-heading">
        <div>
          <p className="eyebrow">MAKE YOUR NEXT MOVE</p>
          <h1>My assessments</h1>
          <p>
            Choose an assessment, prepare your setup, and give it your best.
          </p>
        </div>
        <button
          className="secondary-button"
          disabled={props.busy}
          onClick={props.onRefresh}
        >
          <RotateCw size={16} className={props.busy ? "spin" : ""} />
          Refresh assessments
        </button>
      </div>
      <div className="assessment-toolbar">
        <div className="assessment-tabs" aria-label="Filter assessments">
          {[
            ["ALL", "All assessments"],
            ["AVAILABLE", "Available"],
            ["OTHER", "Not open"],
          ].map(([value, label]) => (
            <button
              key={value}
              aria-pressed={filter === value}
              className={filter === value ? "active" : ""}
              onClick={() => setFilter(value)}
            >
              {label}
              <span>
                {
                  props.assessments.filter(
                    (item) =>
                      value === "ALL" ||
                      (value === "AVAILABLE"
                        ? available(item)
                        : !available(item)),
                  ).length
                }
              </span>
            </button>
          ))}
        </div>
        <label className="candidate-search">
          <Search size={17} />
          <input
            aria-label="Search assessments"
            placeholder="Search assessments…"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </label>
      </div>
      {connecting ? (
        <div
          className="assessment-card-grid"
          aria-busy="true"
          aria-label="Loading assessments"
        >
          {[0, 1].map((index) => (
            <div key={index} className="assessment-card skeleton-card">
              <div className="skeleton skeleton-title" />
              <div className="skeleton skeleton-line" />
              <div className="skeleton skeleton-line short" />
            </div>
          ))}
        </div>
      ) : !props.connected ? (
        <div className="state-card" role="status">
          <WifiOff size={32} />
          <h2>Let's get you reconnected</h2>
          <p>
            Your assessments could not be loaded. Check your connection and try
            again.
          </p>
          <button disabled={props.busy} onClick={props.onRefresh}>
            <RotateCw size={16} />
            Reconnect
          </button>
        </div>
      ) : !visible.length ? (
        <div className="state-card" role="status">
          <ClipboardList size={32} />
          <h2>
            {props.assessments.length
              ? "No matching assessments"
              : "Nothing assigned just yet"}
          </h2>
          <p>
            {props.assessments.length
              ? "Try a different search or filter to find your assessment."
              : "Your assigned assessments will appear here. Contact your examiner if you expected to see one."}
          </p>
          {props.assessments.length ? (
            <button
              className="secondary-button"
              onClick={() => {
                setSearch("");
                setFilter("ALL");
              }}
            >
              Clear filters
            </button>
          ) : (
            <button
              className="secondary-button"
              disabled={props.busy}
              onClick={props.onRefresh}
            >
              <RotateCw size={16} />
              Check again
            </button>
          )}
        </div>
      ) : (
        <ul className="assessment-card-grid">
          {visible.map((assessment, index) => (
            <li key={assessment.id}>
              <article className="assessment-card">
                <div className="assessment-card-top">
                  <span
                    className={"assessment-course-icon color-" + (index % 3)}
                  >
                    <BookOpen size={27} />
                  </span>
                  <span
                    className={
                      "badge " +
                      (completed(assessment)
                        ? "tone-neutral"
                        : available(assessment)
                          ? "tone-success"
                          : "tone-neutral")
                    }
                  >
                    {completed(assessment)
                      ? "completed"
                      : assessment.status.toLowerCase()}
                  </span>
                </div>
                <div className="assessment-info">
                  <p className="assessment-type">PROCTORED ASSESSMENT</p>
                  <h2>{assessment.title}</h2>
                  <p className="assessment-description">
                    {assessment.description ||
                      "Review the assessment requirements and complete your setup before you begin."}
                  </p>
                  <div className="assessment-meta">
                    <span>
                      <Clock3 size={15} />
                      {assessment.duration_minutes == null
                        ? "No time limit"
                        : assessment.duration_minutes + " minutes"}
                    </span>
                    <span>
                      <ShieldCheck size={15} />
                      Guided setup
                    </span>
                  </div>
                </div>
                <div className="assessment-card-footer">
                  <span>
                    {completed(assessment)
                      ? "You have submitted this assessment"
                      : available(assessment)
                      ? "Ready for preparation"
                      : "This assessment is not open"}
                  </span>
                  <button
                    disabled={props.busy || !available(assessment) || completed(assessment)}
                    onClick={() => props.onOpen(assessment.id)}
                  >
                    {completed(assessment)
                      ? "Completed"
                      : assessment.attempt_status === "IN_PROGRESS" ||
                          props.attemptedAssessmentIds.includes(assessment.id)
                      ? "Continue"
                      : "Prepare"}
                    {!completed(assessment) ? <ArrowRight size={16} /> : null}
                  </button>
                </div>
              </article>
            </li>
          ))}
        </ul>
      )}
      <aside className="assessment-guidance">
        <span className="card-icon">
          <ShieldCheck size={22} />
        </span>
        <div>
          <strong>A quick setup. A focused assessment.</strong>
          <p>
            You'll check your connection and any camera, microphone, screen
            recording and device requirements enabled for your assessment.
          </p>
        </div>
        <a href="#/help">
          What to expect <ArrowRight size={15} />
        </a>
      </aside>
    </main>
  );
}
