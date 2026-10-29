import { useState } from "react";

export type RuleMap = Record<string, Record<string, unknown>>;
type Person = {
  id: string;
  full_name: string;
  email: string;
  role: string;
  roll_number?: string | null;
  program?: string | null;
  admission_year?: number | null;
  section?: string | null;
};

export const features = [
  {
    name: "Face monitoring",
    detail: "Detect missing faces and multiple people using your camera.",
    keys: ["FACE_ABSENT", "MULTIPLE_PERSONS"],
  },
  {
    name: "Phone detection",
    detail: "Detect phone-like objects. Requires camera access.",
    keys: ["PHONE_DETECTED"],
  },
  {
    name: "Microphone monitoring",
    detail: "Microphone availability and sustained background audio.",
    keys: ["MICROPHONE_DISABLED", "BACKGROUND_SPEECH"],
  },
  {
    name: "Screen recording",
    detail: "Record event-based screen clips for proctor review.",
    keys: ["SCREEN_RECORDING"],
  },
  {
    name: "Fullscreen requirement",
    detail: "Require fullscreen at setup and report exits during the test.",
    keys: ["FULLSCREEN_EXIT"],
  },
  {
    name: "Tab and app switching",
    detail: "Report when the assessment loses focus.",
    keys: ["APP_FOCUS_LOST"],
  },
  {
    name: "Clipboard restrictions",
    detail: "Block and report copy, cut, and paste actions.",
    keys: ["CLIPBOARD_COPY", "CLIPBOARD_CUT", "CLIPBOARD_PASTE"],
  },
  {
    name: "Restricted shortcuts",
    detail: "Report print-screen and developer-tool shortcuts.",
    keys: ["PRINT_SCREEN_ATTEMPT", "DEVTOOLS_SHORTCUT"],
  },
  {
    name: "Screen-sharing detection",
    detail: "Report additional screen-capture requests during the test.",
    keys: ["SCREEN_SHARE_ATTEMPT"],
  },
  {
    name: "Extra display check",
    detail: "Check for connected extra displays before starting.",
    keys: ["DISPLAY_CHECK"],
  },
  {
    name: "Connection monitoring",
    detail: "Report heartbeat gaps during the assessment.",
    keys: ["HEARTBEAT_GAP"],
  },
] as const;

export function defaultRules(): RuleMap {
  const rules: RuleMap = {};
  for (const feature of features)
    for (const key of feature.keys)
      rules[key] = { enabled: true, severity: "HIGH" };
  rules.AI_ENGINE_INTERRUPTED = { enabled: true, severity: "HIGH" };
  rules.CAMERA_DISABLED = { enabled: true, severity: "HIGH" };
  for (const key of [
    "APP_FOCUS_LOST",
    "CLIPBOARD_COPY",
    "CLIPBOARD_CUT",
    "DEVTOOLS_SHORTCUT",
    "BACKGROUND_SPEECH",
  ])
    rules[key].severity = "MEDIUM";
  rules.FACE_ABSENT.absent_frame_threshold = 3;
  rules.MULTIPLE_PERSONS.multiple_frame_threshold = 2;
  rules.PHONE_DETECTED.phone_frame_threshold = 2;
  rules.HEARTBEAT_GAP.gap_threshold_ms = 15000;
  return rules;
}

export function FeatureChoices({
  rules,
  onChange,
  disabled = false,
}: {
  rules: RuleMap;
  onChange: (rules: RuleMap) => void;
  disabled?: boolean;
}) {
  return (
    <fieldset className="feature-choices" disabled={disabled}>
      <legend className="sr-only">Proctoring features</legend>
      <div className="policy-grid">
        {features.map((feature) => {
          const enabled = feature.keys.some(
            (key) => rules[key]?.enabled !== false,
          );
          return (
            <label className="policy-row" key={feature.name}>
              <span>
                <strong>{feature.name}</strong>
                <small>{feature.detail}</small>
              </span>
              <input
                className="toggle"
                type="checkbox"
                aria-label={feature.name}
                checked={enabled}
                onChange={(event) => {
                  const next = { ...rules };
                  for (const key of feature.keys)
                    next[key] = {
                      ...rules[key],
                      enabled: event.target.checked,
                    };
                  const cameraNeeded = [
                    "FACE_ABSENT",
                    "MULTIPLE_PERSONS",
                    "PHONE_DETECTED",
                  ].some((key) => next[key]?.enabled !== false);
                  next.CAMERA_DISABLED = {
                    ...next.CAMERA_DISABLED,
                    enabled: cameraNeeded,
                  };
                  next.AI_ENGINE_INTERRUPTED = {
                    ...next.AI_ENGINE_INTERRUPTED,
                    enabled: cameraNeeded,
                  };
                  onChange(next);
                }}
              />
            </label>
          );
        })}
      </div>
    </fieldset>
  );
}

export function PeopleChoices({
  title,
  role,
  people,
  selected,
  onChange,
  disabled = false,
}: {
  title: string;
  role: string;
  people: Person[];
  selected: string[];
  onChange: (ids: string[]) => void;
  disabled?: boolean;
}) {
  const [query, setQuery] = useState("");
  const available = people.filter((person) => person.role === role);
  const visible = available.filter((person) =>
    `${person.full_name} ${person.email} ${person.roll_number ?? ""} ${person.program ?? ""} ${person.admission_year ?? ""} ${person.section ?? ""}`
      .toLowerCase()
      .includes(query.toLowerCase()),
  );
  return (
    <fieldset className="assignment-choice" disabled={disabled}>
      <legend>
        {title} <span className="count-badge">{selected.length} selected</span>
      </legend>
      <input
        type="search"
        aria-label={`Search ${title.toLowerCase()}`}
        placeholder="Search by name or email"
        value={query}
        onChange={(event) => setQuery(event.target.value)}
      />
      {available.length ? (
        <div className="assignment-select-all">
          <button
            type="button"
            className="text-button"
            onClick={() => onChange(available.map((person) => person.id))}
          >
            Select all
          </button>
          <button
            type="button"
            className="text-button"
            onClick={() => onChange([])}
          >
            Clear
          </button>
        </div>
      ) : null}
      <div className="assignment-options">
        {visible.map((person) => (
          <label className="assignment-option" key={person.id}>
            <input
              type="checkbox"
              checked={selected.includes(person.id)}
              onChange={(event) =>
                onChange(
                  event.target.checked
                    ? [...selected, person.id]
                    : selected.filter((id) => id !== person.id),
                )
              }
            />
            <span>
              <strong>{person.full_name}</strong>
            <small>
              {person.roll_number ? `${person.roll_number} · ` : ""}
              {person.email}
              {person.program && person.admission_year && person.section
                ? ` · ${person.program} ${person.admission_year} · Section ${person.section}`
                : ""}
            </small>
            </span>
          </label>
        ))}
        {!visible.length ? (
          <p className="assignment-empty">
            {available.length
              ? "No matching accounts."
              : `No ${title.toLowerCase()} accounts are available yet.`}
          </p>
        ) : null}
      </div>
    </fieldset>
  );
}
