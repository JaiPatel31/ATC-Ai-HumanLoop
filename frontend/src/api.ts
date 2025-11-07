import type { SttResult } from "./types";

export async function sendAudio(source: Blob | File): Promise<SttResult> {
  const file =
    source instanceof File
      ? source
      : new File([source], `push-to-talk-${Date.now()}.webm`, {
          type: source.type || "audio/webm",
        });

  const form = new FormData();
  form.append("file", file);

  const res = await fetch("http://127.0.0.1:8000/stt", {
    method: "POST",
    body: form,
  });

  if (!res.ok) {
    throw new Error(`STT request failed with status ${res.status}`);
  }

  const data = (await res.json()) as SttResult;
  return data;
}

export async function interpretTranscript(transcript: string): Promise<SttResult> {
  const res = await fetch("http://127.0.0.1:8000/interpret", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ transcript }),
  });

  if (!res.ok) {
    throw new Error(`Interpretation request failed with status ${res.status}`);
  }

  const data = (await res.json()) as SttResult;
  return data;
}
