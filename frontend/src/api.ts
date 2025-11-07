import type { SttResult } from "./types";

export async function sendAudio(file: File): Promise<SttResult> {
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
