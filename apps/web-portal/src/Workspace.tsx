import { useEffect, useRef, useState, type ReactNode } from "react";
import {
  ArrowUpRight,
  ChartNoAxesCombined,
  ChevronRight,
  CircleHelp,
  ClipboardList,
  FileCheck2,
  LayoutDashboard,
  LogOut,
  Menu,
  Radio,
  RefreshCw,
  Settings2,
  ShieldCheck,
  Users,
} from "lucide-react";

export type PortalRoute = {
  mode: "EXAMINER" | "PROCTOR";
  page: string;
  assessmentId?: string;
  tab: string;
};

export function readPortalRoute(): PortalRoute {
  const parts = window.location.hash
    .replace(/^#\/?/, "")
    .split("/")
    .filter(Boolean);
  const mode = parts[0] === "proctor" ? "PROCTOR" : "EXAMINER";
  const page = parts[1] ?? "overview";
  if (page === "assessments" && parts[2] && parts[2] !== "new") {
    return {
      mode,
      page: "builder",
      assessmentId: parts[2],
      tab: parts[3] ?? "overview",
    };
  }
  return {
    mode,
    page: page === "assessments" && parts[2] === "new" ? "new" : page,
    tab: "overview",
  };
}

export function StatusBadge({ status }: { status: string }) {
  const tone = [
    "ACTIVE",
    "PUBLISHED",
    "READY",
    "LIVE",
    "FALSE_POSITIVE",
  ].includes(status.toUpperCase())
    ? "green"
    : ["DRAFT", "PENDING", "UNREVIEWED", "MEDIUM", "INCONCLUSIVE"].includes(
          status.toUpperCase(),
        )
      ? "amber"
      : ["HIGH", "CRITICAL", "CONFIRMED_SUSPICIOUS", "FAILED"].includes(
            status.toUpperCase(),
          )
        ? "red"
        : "neutral";
  return (
    <span className={`badge badge-${tone}`}>
      <span className="badge-dot" />
      {status.toLowerCase().replaceAll("_", " ")}
    </span>
  );
}

export function StatCard({
  label,
  value,
  note,
  icon,
  tone = "blue",
}: {
  label: string;
  value: ReactNode;
  note: string;
  icon: ReactNode;
  tone?: string;
}) {
  return (
    <article className="stat-card">
      <div className="stat-top">
        <span>{label}</span>
        <span className={`stat-icon ${tone}`}>{icon}</span>
      </div>
      <strong>{value}</strong>
      <p>{note}</p>
    </article>
  );
}

export function EmptyState({
  title,
  description,
  action,
  icon,
}: {
  title: string;
  description: string;
  action?: ReactNode;
  icon?: ReactNode;
}) {
  return (
    <div className="empty-state">
      <span className="empty-icon">{icon ?? <ClipboardList size={25} />}</span>
      <h3>{title}</h3>
      <p>{description}</p>
      {action}
    </div>
  );
}

const examinerNav = [
  { page: "overview", label: "Overview", icon: LayoutDashboard },
  { page: "assessments", label: "Assessments", icon: ClipboardList },
  { page: "people", label: "People & assignments", icon: Users },
  { page: "settings", label: "Monitoring policy", icon: Settings2 },
];
const proctorNav = [
  { page: "overview", label: "Overview", icon: LayoutDashboard },
  { page: "monitoring", label: "Live monitoring", icon: Radio },
  { page: "reviews", label: "Evidence review", icon: FileCheck2 },
  { page: "reports", label: "Reports", icon: ChartNoAxesCombined },
];

export function Workspace({
  route,
  title,
  description,
  name,
  status,
  onRefresh,
  onLogout,
  children,
  actions,
}: {
  route: PortalRoute;
  title: string;
  description: string;
  name: string;
  status: string;
  onRefresh: () => void;
  onLogout: () => void;
  children: ReactNode;
  actions?: ReactNode;
}) {
  const [menuOpen, setMenuOpen] = useState(false);
  const [mobile, setMobile] = useState(
    () => window.matchMedia("(max-width: 780px)").matches,
  );
  const menuButton = useRef<HTMLButtonElement>(null);
  const sidebar = useRef<HTMLElement>(null);
  useEffect(() => {
    const query = window.matchMedia("(max-width: 780px)");
    const update = () => {
      setMobile(query.matches);
      setMenuOpen(false);
    };
    query.addEventListener("change", update);
    return () => query.removeEventListener("change", update);
  }, []);
  useEffect(() => {
    if (!menuOpen || !mobile) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    sidebar.current
      ?.querySelector<HTMLElement>("a[aria-current=page],a")
      ?.focus();
    function handleKey(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setMenuOpen(false);
        requestAnimationFrame(() => menuButton.current?.focus());
      }
      if (event.key === "Tab") {
        const links = sidebar.current?.querySelectorAll<HTMLElement>(
          "a[href],button:not(:disabled)",
        );
        if (!links?.length) return;
        const first = links[0],
          last = links[links.length - 1];
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first.focus();
        }
      }
    }
    document.addEventListener("keydown", handleKey);
    return () => {
      document.body.style.overflow = previousOverflow;
      document.removeEventListener("keydown", handleKey);
    };
  }, [menuOpen, mobile]);
  useEffect(() => {
    document.title = title + " | ProctorAI";
  }, [title]);
  const role = route.mode === "EXAMINER" ? "examiner" : "proctor";
  const healthy = ["ready", "live", "polling"].includes(status);
  return (
    <div className="app-shell">
      <a
        className="skip-link"
        href="#workspace-content"
        onClick={(event) => {
          event.preventDefault();
          document.getElementById("workspace-content")?.focus();
        }}
      >
        Skip to content
      </a>
      {menuOpen ? (
        <button
          className="sidebar-scrim"
          aria-label="Close navigation"
          onClick={() => setMenuOpen(false)}
        />
      ) : null}
      <aside
        id="workspace-navigation"
        ref={sidebar}
        inert={mobile && !menuOpen}
        className={`sidebar${menuOpen ? " is-open" : ""}`}
      >
        <a
          href={`#/${role}/overview`}
          className="brand"
          onClick={() => setMenuOpen(false)}
        >
          <span className="brand-mark">
            <ShieldCheck size={23} />
          </span>
          <span>
            Proctor<span className="brand-ai">AI</span>
            <small>ASSESSMENT WORKSPACE</small>
          </span>
        </a>
        <div className="workspace-selector">
          <span className="institution-icon">B</span>
          <div>
            <strong>Bennett University</strong>
            <span>
              {role === "examiner"
                ? "Assessment administration"
                : "Proctor workspace"}
            </span>
          </div>
        </div>
        <p className="nav-caption">WORKSPACE</p>
        <nav aria-label="Main navigation">
          {(route.mode === "EXAMINER" ? examinerNav : proctorNav).map(
            (item) => (
              <a
                key={item.page}
                href={`#/${role}/${item.page}`}
                onClick={() => setMenuOpen(false)}
                className={`nav-item${route.page === item.page || (item.page === "assessments" && ["builder", "new"].includes(route.page)) ? " active" : ""}`}
                aria-current={
                  route.page === item.page ||
                  (item.page === "assessments" &&
                    ["builder", "new"].includes(route.page))
                    ? "page"
                    : undefined
                }
              >
                <item.icon size={18} />
                <span>{item.label}</span>
              </a>
            ),
          )}
        </nav>
        <div className="sidebar-bottom">
          <a
            className={`nav-item${route.page === "help" ? " active" : ""}`}
            href={`#/${role}/help`}
            onClick={() => setMenuOpen(false)}
          >
            <CircleHelp size={18} />
            Help & guidance
          </a>
          <div className="role-switch" aria-label="Workspace role">
            <a
              href="#/examiner/overview"
              className={route.mode === "EXAMINER" ? "active" : ""}
            >
              Examiner
            </a>
            <a
              href="#/proctor/monitoring"
              className={route.mode === "PROCTOR" ? "active" : ""}
            >
              Proctor
            </a>
          </div>
          <div className="account">
            <span className="avatar">
              {name
                .split(" ")
                .map((part) => part[0])
                .slice(0, 2)
                .join("") || "PA"}
            </span>
            <div>
              <strong>{name || "Connecting…"}</strong>
              <span>
                {role === "examiner" ? "Examiner account" : "Proctor account"}
              </span>
            </div>
            <ShieldCheck size={15} />
          </div>
        </div>
      </aside>
      <div className="workspace" inert={mobile && menuOpen}>
        <header className="topbar">
          <div className="topbar-breadcrumb">
            <button
              ref={menuButton}
              className="icon-button mobile-menu"
              onClick={() => setMenuOpen(true)}
              aria-label="Open navigation"
              aria-controls="workspace-navigation"
              aria-expanded={menuOpen}
            >
              <Menu size={20} />
            </button>
            <span>Workspace</span>
            <ChevronRight size={14} />
            <strong>{title}</strong>
          </div>
          <div className="topbar-tools">
            <span className={`connection ${healthy ? "healthy" : ""}`}>
              <span />
              {healthy
                ? status === "polling"
                  ? "Connected · polling"
                  : "Connected"
                : status === "error" || status === "offline"
                  ? "Connection interrupted"
                  : "Connecting…"}
            </span>
            <button
              className="icon-button"
              onClick={onRefresh}
              aria-label="Refresh workspace"
              disabled={status === "loading"}
            >
              <RefreshCw size={17} />
            </button>
            <button className="icon-button" onClick={onLogout} aria-label="Sign out" title="Sign out">
              <LogOut size={17} />
            </button>
            <span className="top-avatar">
              {name
                .split(" ")
                .map((part) => part[0])
                .slice(0, 2)
                .join("") || "PA"}
            </span>
          </div>
        </header>
        <main
          id="workspace-content"
          tabIndex={-1}
          className="workspace-content"
        >
          <div className="page-heading">
            <div>
              <p className="eyebrow">
                {route.mode === "EXAMINER"
                  ? "ASSESSMENT MANAGEMENT"
                  : "EXAM INTEGRITY"}
              </p>
              <h1>{title}</h1>
              <p className="page-description">{description}</p>
            </div>
            <div className="page-actions">{actions}</div>
          </div>
          {children}
          <footer className="workspace-footer">
            <span>
              <ShieldCheck size={14} />
              ProctorAI · Assessment integrity, with human oversight
            </span>
            <a href={`#/${role}/help`}>
              Help center <ArrowUpRight size={13} />
            </a>
          </footer>
        </main>
      </div>
    </div>
  );
}
