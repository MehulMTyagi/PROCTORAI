import { useEffect, useRef, useState } from "react";
import { Camera, Check, ShieldCheck, UserRoundCheck } from "lucide-react";

type Props = {
  name: string;
  email: string;
  busy: boolean;
  error: string | null;
  onEnroll: (photoDataUrl: string) => Promise<void>;
};

export default function IdentityEnrollmentPage(props: Props) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [cameraReady, setCameraReady] = useState(false);
  const [cameraError, setCameraError] = useState<string | null>(null);
  const [working, setWorking] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const mediaDevices = navigator.mediaDevices;
    if (!mediaDevices?.getUserMedia) {
      setCameraError("Camera access is unavailable in this browser or page context.");
      return;
    }
    void mediaDevices
      .getUserMedia({ video: { width: 640, height: 480, facingMode: "user" }, audio: false })
      .then((stream) => {
        if (cancelled) {
          stream.getTracks().forEach((track) => track.stop());
          return;
        }
        streamRef.current = stream;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          void videoRef.current.play().then(() => setCameraReady(true)).catch(() => {
            setCameraError("Allow camera playback and retry.");
          });
        }
      })
      .catch(() => setCameraError("Allow camera access to enroll your identity photo."));
    return () => {
      cancelled = true;
      streamRef.current?.getTracks().forEach((track) => track.stop());
    };
  }, []);

  async function captureAndEnroll() {
    const video = videoRef.current;
    if (!video || !cameraReady || !video.videoWidth) {
      setCameraError("The camera is not ready yet. Please wait and try again.");
      return;
    }
    const scale = Math.min(1, 640 / video.videoWidth);
    const canvas = document.createElement("canvas");
    canvas.width = Math.round(video.videoWidth * scale);
    canvas.height = Math.round(video.videoHeight * scale);
    const context = canvas.getContext("2d");
    if (!context) {
      setCameraError("Could not capture the camera image. Please retry.");
      return;
    }
    context.drawImage(video, 0, 0, canvas.width, canvas.height);
    setWorking(true);
    setCameraError(null);
    try {
      await props.onEnroll(canvas.toDataURL("image/jpeg", 0.82));
    } catch (error) {
      setCameraError(error instanceof Error ? error.message : "Enrollment failed. Please try again.");
    } finally {
      setWorking(false);
    }
  }

  const disabled = props.busy || working || !cameraReady;

  return (
    <main className="login-page" id="main-content" tabIndex={-1}>
      <section className="login-card enrollment-card" aria-labelledby="enrollment-title">
        <div className="login-brand">
          <ShieldCheck size={27} aria-hidden="true" />
          <span>Proctor<span className="brand-ai">AI</span></span>
        </div>
        <p className="eyebrow">First-time identity setup</p>
        <h1 id="enrollment-title">Register your face once</h1>
        <p className="login-intro">
          Signed in as <strong>{props.name || props.email}</strong>. Take a clear, front-facing photo. It will be linked to this account and cannot be replaced from the candidate app.
        </p>
        <div className="enrollment-preview">
          <video ref={videoRef} autoPlay muted playsInline aria-label="Camera preview for identity enrollment" />
          <span><UserRoundCheck size={15} aria-hidden="true" /> Center your face in the frame</span>
        </div>
        {cameraError ? <p className="login-error" role="alert">{cameraError}</p> : null}
        {props.error ? <p className="login-error" role="alert">{props.error}</p> : null}
        <button className="enrollment-submit" onClick={() => void captureAndEnroll()} disabled={disabled}>
          {working || props.busy ? <Check size={16} aria-hidden="true" /> : <Camera size={16} aria-hidden="true" />}
          {working || props.busy ? "Checking and saving…" : cameraReady ? "Capture and register" : "Starting camera…"}
        </button>
        <p className="login-note">Make sure you are alone in the frame and the lighting is clear. Contact your university administrator if this is the wrong account.</p>
      </section>
    </main>
  );
}
