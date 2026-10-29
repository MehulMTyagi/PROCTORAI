import { fixWebmDuration } from "@fix-webm-duration/fix";

export type EvidenceClip = { blob: Blob; startedAt: number; endedAt: number };
type Waiter = {
  resolve: (clip: EvidenceClip) => void;
  reject: (error: Error) => void;
};
type Segment = {
  recorder: MediaRecorder;
  chunks: Blob[];
  startedAt: number;
  deadline: number;
  timer: number;
  waiters: Waiter[];
};

/**
 * Staggered, complete recordings preserve each WebM's initialization header.
 * Retaining arbitrary timeslice blobs from a long recording is not playable.
 * Only event-selected segments are returned for upload; all others are discarded.
 */
export class RollingEvidenceRecorder {
  private segments = new Set<Segment>();
  private interval: number;
  private stopped = false;
  private mimeType: string;

  constructor(
    private stream: MediaStream,
    private preRollMs = 5000,
    private postRollMs = 5000,
  ) {
    this.mimeType = MediaRecorder.isTypeSupported("video/webm;codecs=vp8")
      ? "video/webm;codecs=vp8"
      : "video/webm";
    this.beginSegment();
    this.interval = window.setInterval(() => {
      try {
        this.beginSegment();
      } catch {
        this.stop();
      }
    }, preRollMs);
  }

  get state() {
    return this.stopped ? "inactive" : "recording";
  }

  private scheduleStop(segment: Segment) {
    window.clearTimeout(segment.timer);
    segment.timer = window.setTimeout(
      () => {
        if (segment.recorder.state !== "inactive") segment.recorder.stop();
      },
      Math.max(0, segment.deadline - Date.now()),
    );
  }

  private beginSegment() {
    if (this.stopped) return;
    const recorder = new MediaRecorder(this.stream, {
      mimeType: this.mimeType,
    });
    const segment: Segment = {
      recorder,
      chunks: [],
      startedAt: Date.now(),
      deadline: Date.now() + this.preRollMs * 2,
      timer: 0,
      waiters: [],
    };
    recorder.ondataavailable = (event) => {
      if (event.data.size) segment.chunks.push(event.data);
    };
    recorder.onstop = () => {
      void this.finishSegment(segment);
    };
    recorder.onerror = () => {
      window.clearTimeout(segment.timer);
      this.segments.delete(segment);
      segment.waiters
        .splice(0)
        .forEach((waiter) =>
          waiter.reject(new Error("Evidence recording failed.")),
        );
      segment.chunks = [];
    };
    // Keep the browser's complete recording container intact. Timeslice chunks
    // are fragments and can be uploaded without the EBML initialization header.
    recorder.start();
    this.segments.add(segment);
    this.scheduleStop(segment);
  }

  private async finishSegment(segment: Segment) {
    window.clearTimeout(segment.timer);
    this.segments.delete(segment);
    if (!segment.waiters.length) {
      segment.chunks = [];
      return;
    }
    const endedAt = Date.now();
    try {
      if (!segment.chunks.length)
        throw new Error("No media was captured for this event.");
      const original = new Blob(segment.chunks, {
        type: segment.recorder.mimeType || this.mimeType,
      });
      segment.chunks = [];
      const blob = await fixWebmDuration(
        original,
        endedAt - segment.startedAt,
        { logger: false },
      );
      const clip = { blob, startedAt: segment.startedAt, endedAt };
      segment.waiters.splice(0).forEach((waiter) => waiter.resolve(clip));
    } catch (error) {
      segment.waiters
        .splice(0)
        .forEach((waiter) =>
          waiter.reject(
            error instanceof Error
              ? error
              : new Error("Clip finalization failed."),
          ),
        );
    }
  }

  capture(eventTime: number): Promise<EvidenceClip> {
    const active = [...this.segments]
      .filter((segment) => segment.recorder.state === "recording")
      .sort((a, b) => b.startedAt - a.startedAt);
    const segment =
      active.find((item) => item.startedAt <= eventTime - this.preRollMs) ??
      active.at(-1);
    if (!segment || this.stopped)
      return Promise.reject(new Error("The evidence recorder is not active."));
    segment.deadline = Math.max(segment.deadline, eventTime + this.postRollMs);
    this.scheduleStop(segment);
    return new Promise((resolve, reject) => {
      segment.waiters.push({ resolve, reject });
    });
  }

  stop() {
    this.stopped = true;
    window.clearInterval(this.interval);
    for (const segment of this.segments) {
      window.clearTimeout(segment.timer);
      if (segment.recorder.state !== "inactive") segment.recorder.stop();
    }
  }
}
