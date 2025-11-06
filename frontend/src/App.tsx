import { useState } from "react";
import { sendAudio } from "./api";

export default function App() {
  const [transcript, setTranscript] = useState("");
  const [parsed, setParsed] = useState<any>(null);
  const [response, setResponse] = useState("");

async function handleFile(e: React.ChangeEvent<HTMLInputElement>) {
  if (!e.target.files?.length) return;
  const file = e.target.files[0];

  // 🧠 Step 1: Send audio to STT backend
  const result = await sendAudio(file);

  // 🧱 Step 2: Update UI state
  setTranscript(result.transcript);
  setParsed(result.parsed);
  setResponse(result.response);

  // 🔊 Step 3: Fetch and play the TTS audio response
  try {
    const ttsRes = await fetch("http://127.0.0.1:8000/tts", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    text: result.response_tts || result.response,
    speaker: result.parsed?.speaker || "controller",
  }),
});

    if (!ttsRes.ok) throw new Error("TTS request failed");
    const blob = await ttsRes.blob();
    const audioUrl = URL.createObjectURL(blob);
    new Audio(audioUrl).play();
  } catch (err) {
    console.error("TTS playback error:", err);
  }
}

  return (
    <div className="p-6 font-mono text-gray-100 bg-slate-900 min-h-screen">
      <h1 className="text-3xl font-bold mb-4">ATC Voice Loop</h1>

      <input
        type="file"
        accept="audio/*"
        onChange={handleFile}
        className="mb-6 p-2 bg-slate-800 rounded"
      />

      {transcript && (
        <div className="bg-slate-800 p-4 rounded shadow-lg">
          <h2 className="text-xl font-semibold mb-2">🗣️ Transcript</h2>
          <p className="text-lg mb-4">{transcript}</p>

          {parsed && (
            <>
              <h2 className="text-xl font-semibold mb-2">🧩 Parsed Intent</h2>
              <pre className="bg-slate-700 p-2 rounded mb-4 text-sm">
                {JSON.stringify(parsed, null, 2)}
              </pre>
            </>
          )}

          {response && (
            <>
              <h2 className="text-xl font-semibold mb-2">🎧 Controller Response</h2>
              <p className="text-lg text-green-400">{response}</p>
            </>
          )}
        </div>
      )}
    </div>
  );
}

