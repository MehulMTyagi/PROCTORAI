import { useState } from "react";
import { ArrowLeft, BookOpen, Camera, MailCheck, ShieldCheck, Wifi } from "lucide-react";
import type { FormEvent } from "react";

type ActivationResult = { email: string; message: string; dev_verification_code?: string | null };
type Screen = "login" | "request" | "activate";

type Props = {
  email: string;
  password: string;
  busy: boolean;
  error: string | null;
  onEmailChange: (value: string) => void;
  onPasswordChange: (value: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onRequestActivation: (email: string) => Promise<ActivationResult>;
  onActivate: (email: string, code: string, password: string) => Promise<void>;
};

export default function LoginPage(props: Props) {
  const [screen, setScreen] = useState<Screen>("login");
  const [activationEmail, setActivationEmail] = useState("");
  const [activationCode, setActivationCode] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [devCode, setDevCode] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [localError, setLocalError] = useState<string | null>(null);
  const [localBusy, setLocalBusy] = useState(false);
  const busy = props.busy || localBusy;
  const error = screen === "login" ? props.error : localError;

  async function sendActivationCode(email: string) {
    const result = await props.onRequestActivation(email.trim());
    setActivationEmail(result.email);
    setDevCode(result.dev_verification_code ?? null);
    setNotice(result.message);
  }

  async function requestActivation(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLocalError(null);
    setNotice(null);
    setLocalBusy(true);
    try {
      await sendActivationCode(activationEmail);
      setScreen("activate");
    } catch (cause) {
      setLocalError(cause instanceof Error ? cause.message : "Could not request account activation.");
    } finally {
      setLocalBusy(false);
    }
  }

  async function activate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLocalError(null);
    if (newPassword !== confirmPassword) {
      setLocalError("The passwords do not match.");
      return;
    }
    setLocalBusy(true);
    try {
      await props.onActivate(activationEmail, activationCode, newPassword);
    } catch (cause) {
      setLocalError(cause instanceof Error ? cause.message : "Could not activate this account.");
    } finally {
      setLocalBusy(false);
    }
  }

  async function resendActivationCode() {
    setLocalError(null);
    setLocalBusy(true);
    try {
      await sendActivationCode(activationEmail);
    } catch (cause) {
      setLocalError(cause instanceof Error ? cause.message : "Could not send another activation code.");
    } finally {
      setLocalBusy(false);
    }
  }

  function goTo(next: Screen) {
    setScreen(next);
    setLocalError(null);
    setNotice(null);
    props.onPasswordChange("");
  }

  return (
    <main className="login-page" id="main-content" tabIndex={-1}>
      <section className="login-card" aria-labelledby="login-title">
        <div className="login-brand">
          <ShieldCheck size={27} aria-hidden="true" />
          <span>Proctor<span className="brand-ai">AI</span></span>
        </div>

        {screen === "login" ? (
          <>
            <p className="eyebrow">Candidate workspace</p>
            <h1 id="login-title">Sign in to your assessment</h1>
            <p className="login-intro">Sign in with the account provided by your university. On your first sign-in, you will register a camera photo linked to this account.</p>
            {error ? <p className="login-error" role="alert">{error}</p> : null}
            <form onSubmit={props.onSubmit}>
              <label htmlFor="candidate-email">University email</label>
              <input id="candidate-email" type="email" autoComplete="username" required value={props.email} onChange={(event) => props.onEmailChange(event.target.value)} />
              <label htmlFor="candidate-password">Password</label>
              <input id="candidate-password" type="password" autoComplete="current-password" required value={props.password} onChange={(event) => props.onPasswordChange(event.target.value)} />
              <button type="submit" disabled={busy}>
                {busy ? <Wifi size={16} aria-hidden="true" /> : <BookOpen size={16} aria-hidden="true" />}
                {busy ? "Signing in..." : "Sign in"}
              </button>
            </form>
            <button className="auth-switch" type="button" onClick={() => goTo("request")}>
              <MailCheck size={16} aria-hidden="true" /> Activate a university-provided account
            </button>
            <p className="login-note">Your account must first be added by your university administrator. Contact your course administrator if you cannot sign in.</p>
          </>
        ) : null}

        {screen === "request" ? (
          <>
            <button className="auth-back" type="button" onClick={() => goTo("login")}><ArrowLeft size={15} aria-hidden="true" /> Back to sign in</button>
            <p className="eyebrow">Account activation</p>
            <h1 id="login-title">Activate your account</h1>
            <p className="login-intro">Enter the university email assigned to you. This only works after the administrator has added you to the student roster.</p>
            {error ? <p className="login-error" role="alert">{error}</p> : null}
            <form onSubmit={(event) => void requestActivation(event)}>
              <label htmlFor="activation-email">University email</label>
              <input id="activation-email" type="email" autoComplete="username" required value={activationEmail} onChange={(event) => setActivationEmail(event.target.value)} />
              <button type="submit" disabled={busy}>{busy ? <Wifi size={16} aria-hidden="true" /> : <MailCheck size={16} aria-hidden="true" />}{busy ? "Sending code..." : "Send activation code"}</button>
            </form>
          </>
        ) : null}

        {screen === "activate" ? (
          <>
            <button className="auth-back" type="button" onClick={() => goTo("request")}><ArrowLeft size={15} aria-hidden="true" /> Change email</button>
            <p className="eyebrow">Set up your sign-in</p>
            <h1 id="login-title">Check your university email</h1>
            <p className="login-intro">If <strong>{activationEmail}</strong> is on the student roster, an activation code has been sent. Set a password to finish activating your existing account.</p>
            {notice ? <p className="auth-notice" role="status">{notice}</p> : null}
            {devCode ? <p className="auth-dev-code" role="status">Local development code: <strong>{devCode}</strong></p> : null}
            {error ? <p className="login-error" role="alert">{error}</p> : null}
            <form onSubmit={(event) => void activate(event)}>
              <label htmlFor="activation-code">Six-digit activation code</label>
              <input id="activation-code" inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{6}" maxLength={6} required value={activationCode} onChange={(event) => setActivationCode(event.target.value.replace(/\D/g, "").slice(0, 6))} />
              <label htmlFor="new-password">Create password</label>
              <input id="new-password" type="password" autoComplete="new-password" minLength={12} required value={newPassword} onChange={(event) => setNewPassword(event.target.value)} />
              <label htmlFor="confirm-password">Confirm password</label>
              <input id="confirm-password" type="password" autoComplete="new-password" minLength={12} required value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} />
              <button type="submit" disabled={busy || activationCode.length !== 6}>{busy ? <Wifi size={16} aria-hidden="true" /> : <Camera size={16} aria-hidden="true" />}{busy ? "Activating..." : "Activate account and continue"}</button>
            </form>
            <button className="auth-switch" type="button" onClick={() => void resendActivationCode()} disabled={busy}>
              <MailCheck size={16} aria-hidden="true" /> Send another code
            </button>
            <p className="login-note">Your one-time face photo is enrolled after activation. It is linked to this university account.</p>
          </>
        ) : null}
      </section>
    </main>
  );
}
