// Run against the running candidate portal with @playwright/cli run-code --filename=scripts/browser/check-evidence-recorder.js
async (page) => {
  return await page.evaluate(async () => {
    const { RollingEvidenceRecorder } =
      await import("/src/evidenceRecorder.ts");
    const canvas = document.createElement("canvas");
    canvas.width = 320;
    canvas.height = 240;
    const context = canvas.getContext("2d");
    let frame = 0;
    const draw = setInterval(() => {
      context.fillStyle = frame++ % 2 ? "#2563eb" : "#e2e8f0";
      context.fillRect(0, 0, 320, 240);
    }, 100);
    const stream = canvas.captureStream(10);
    const recorder = new RollingEvidenceRecorder(stream);
    let url;
    try {
      await new Promise((resolve) => setTimeout(resolve, 6500));
      const eventTime = Date.now();
      const clip = await recorder.capture(eventTime);
      const video = document.createElement("video");
      video.muted = true;
      url = URL.createObjectURL(clip.blob);
      await new Promise((resolve, reject) => {
        const timer = setTimeout(
          () => reject(new Error("Clip did not become playable")),
          10000,
        );
        video.oncanplay = () => {
          clearTimeout(timer);
          resolve();
        };
        video.onerror = () => {
          clearTimeout(timer);
          reject(new Error(video.error?.message));
        };
        video.src = url;
      });
      const result = {
        bytes: clip.blob.size,
        duration: video.duration,
        readyState: video.readyState,
        preRollMs: eventTime - clip.startedAt,
        postRollMs: clip.endedAt - eventTime,
      };
      if (
        !Number.isFinite(result.duration) ||
        result.readyState < 2 ||
        result.preRollMs < 5000 ||
        result.postRollMs < 4900
      )
        throw new Error(JSON.stringify(result));
      return result;
    } finally {
      recorder.stop();
      clearInterval(draw);
      stream.getTracks().forEach((track) => track.stop());
      if (url) URL.revokeObjectURL(url);
    }
  });
};
