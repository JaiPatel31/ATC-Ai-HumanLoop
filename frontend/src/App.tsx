import { useEffect, useMemo, useRef, useState } from "react";
import type { KeyboardEvent as ReactKeyboardEvent, PointerEvent as ReactPointerEvent } from "react";
import { interpretTranscript, sendAudio } from "./api";
import ConflictResolutionPanel from "./components/ConflictResolutionPanel";
import type {
  ParsedTransmission,
  TransmissionEntry,
  AircraftState,
  Conflict,
  SttResult,
} from "./types";
import "./App.css";

const HISTORY_LIMIT = 10;

function formatFlightLevel(value?: number | null) {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return "—";
  }
  const level = Math.max(0, Math.round(value));
  return `FL${level.toString().padStart(3, "0")}`;
}

function formatClock(timestamp: string) {
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) {
    return "—";
  }
  return date.toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function buildAircraftStates(entries: TransmissionEntry[]): AircraftState[] {
  const states = new Map<string, AircraftState>();

  for (const entry of entries) {
    const parsed = entry.parsed;
    if (!parsed || typeof parsed.callsign !== "string" || !parsed.callsign) {
      continue;
    }

    const flightLevel =
      typeof parsed.flight_level === "number" && !Number.isNaN(parsed.flight_level)
        ? parsed.flight_level
        : undefined;
    const heading =
      typeof parsed.heading === "number" && !Number.isNaN(parsed.heading)
        ? parsed.heading
        : undefined;
    const command = typeof parsed.command === "string" ? parsed.command : undefined;
    const speaker = typeof parsed.speaker === "string" ? parsed.speaker : undefined;

    states.set(parsed.callsign, {
      callsign: parsed.callsign,
      flightLevel,
      heading,
      command,
      speaker,
      lastHeard: entry.timestamp,
    });
  }

  return Array.from(states.values()).sort(
    (a, b) => new Date(b.lastHeard).getTime() - new Date(a.lastHeard).getTime(),
  );
}

function normalizeHeading(value: number) {
  const normalized = ((value % 360) + 360) % 360;
  return Math.round(normalized);
}

function detectConflicts(states: AircraftState[]): Conflict[] {
  const conflicts: Conflict[] = [];
  const seen = new Set<string>();

  for (let i = 0; i < states.length; i += 1) {
    for (let j = i + 1; j < states.length; j += 1) {
      const a = states[i];
      const b = states[j];
      const keyBase = [a.callsign, b.callsign].sort().join("-");

      if (typeof a.flightLevel === "number" && typeof b.flightLevel === "number") {
        const diff = Math.abs(a.flightLevel - b.flightLevel);
        if (diff <= 10) {
          const separationFeet = diff * 100;
          const higher = a.flightLevel >= b.flightLevel ? a : b;
          const lower = higher === a ? b : a;
          const severity = diff === 0 ? "high" : "moderate";
          const altKey = `alt-${keyBase}`;

          if (!seen.has(altKey)) {
            conflicts.push({
              id: altKey,
              aircraft: [a.callsign, b.callsign],
              description:
                diff === 0
                  ? `${a.callsign} and ${b.callsign} are both assigned ${formatFlightLevel(
                      a.flightLevel,
                    )}.`
                  : `${a.callsign} at ${formatFlightLevel(a.flightLevel)} and ${b.callsign} at ${formatFlightLevel(
                      b.flightLevel,
                    )} have only ${separationFeet.toLocaleString()} ft of vertical separation.`,
              resolution:
                diff === 0
                  ? `Issue immediate vertical separation: clear ${higher.callsign} to ${formatFlightLevel(
                      (higher.flightLevel ?? 0) + 20,
                    )} or provide a descent for ${lower.callsign}.`
                  : `Confirm ${lower.callsign} maintains ${formatFlightLevel(
                      lower.flightLevel,
                    )} until ${higher.callsign} is clear, or expand separation to at least 2,000 ft.`,
              severity,
              metric: `Vertical separation ${separationFeet.toLocaleString()} ft`,
            });
            seen.add(altKey);
          }
        }
      }

      if (typeof a.heading === "number" && typeof b.heading === "number") {
        const rawDiff = Math.abs(a.heading - b.heading);
        const headingDiff = Math.min(rawDiff, 360 - rawDiff);
        if (headingDiff <= 20) {
          const headingKey = `hdg-${keyBase}`;
          if (!seen.has(headingKey)) {
            const severity = headingDiff <= 5 ? "high" : headingDiff <= 15 ? "moderate" : "low";
            const turnHeading = normalizeHeading((b.heading ?? 0) + 30);
            conflicts.push({
              id: headingKey,
              aircraft: [a.callsign, b.callsign],
              description: `${a.callsign} and ${b.callsign} are converging with only ${headingDiff.toFixed(
                0,
              )}° of heading separation.`,
              resolution:
                severity === "high"
                  ? `Vector ${b.callsign} immediately: suggest heading ${turnHeading.toString().padStart(3, "0")}° or greater divergence.`
                  : `Plan lateral separation: issue ${b.callsign} a 30° diverging turn to increase spacing.`,
              severity,
              metric: `Heading separation ${headingDiff.toFixed(0)}°`,
            });
            seen.add(headingKey);
          }
        }
      }
    }
  }

  return conflicts;
}

function normalizeParsed(parsed: ParsedTransmission | null | undefined): ParsedTransmission | null {
  if (!parsed) {
    return null;
  }

  return {
    callsign: typeof parsed.callsign === "string" ? parsed.callsign : null,
    command: typeof parsed.command === "string" ? parsed.command : null,
    flight_level:
      typeof parsed.flight_level === "number" && !Number.isNaN(parsed.flight_level)
        ? parsed.flight_level
        : null,
    heading:
      typeof parsed.heading === "number" && !Number.isNaN(parsed.heading)
        ? parsed.heading
        : null,
    speaker: typeof parsed.speaker === "string" ? parsed.speaker : null,
  };
}

export default function App() {
  const [transcript, setTranscript] = useState("");
  const [parsed, setParsed] = useState<ParsedTransmission | null>(null);
  const [response, setResponse] = useState("");
  const [history, setHistory] = useState<TransmissionEntry[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [manualTranscript, setManualTranscript] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [isMicSupported, setIsMicSupported] = useState(false);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const recordedChunksRef = useRef<BlobPart[]>([]);
  const pendingStopRef = useRef(false);

  const stopActiveStream = () => {
    const stream = mediaStreamRef.current;
    if (stream) {
      stream.getTracks().forEach((track) => track.stop());
    }
    mediaStreamRef.current = null;
  };

  useEffect(() => {
    const supported =
      typeof window !== "undefined" &&
      typeof navigator !== "undefined" &&
      typeof (window as typeof window & { MediaRecorder?: typeof MediaRecorder }).MediaRecorder !==
        "undefined" &&
      !!navigator.mediaDevices &&
      typeof navigator.mediaDevices.getUserMedia === "function";
    setIsMicSupported(Boolean(supported));

    return () => {
      const recorder = mediaRecorderRef.current;
      if (recorder && recorder.state !== "inactive") {
        recorder.stop();
      }
      stopActiveStream();
      mediaRecorderRef.current = null;
      recordedChunksRef.current = [];
      pendingStopRef.current = false;
    };
  }, []);

  const aircraftStates = useMemo(() => buildAircraftStates(history), [history]);
  const conflicts = useMemo(() => detectConflicts(aircraftStates), [aircraftStates]);

  async function processResult(result: SttResult) {
    const normalizedParsed = normalizeParsed(result.parsed);
    const transcriptText = result.transcript ?? "";
    const responseText = result.response ?? "";

    setTranscript(transcriptText);
    setParsed(normalizedParsed);
    setResponse(responseText);

    setHistory((prev) => {
      const entry: TransmissionEntry = {
        id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
        timestamp: new Date().toISOString(),
        transcript: transcriptText,
        parsed: normalizedParsed,
        response: responseText,
      };
      const updated = [...prev, entry];
      if (updated.length > HISTORY_LIMIT) {
        return updated.slice(updated.length - HISTORY_LIMIT);
      }
      return updated;
    });

    if (responseText || result.response_tts) {
      try {
        const ttsRes = await fetch("http://127.0.0.1:8000/tts", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            text: result.response_tts || responseText,
            speaker: normalizedParsed?.speaker || "controller",
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
  }

  async function processAudioFile(file: File) {
    setIsLoading(true);
    setError(null);

    try {
      const result = await sendAudio(file);
      await processResult(result);
    } catch (err) {
      console.error("Transmission error", err);
      setError("Unable to process the transmission. Please try a different recording.");
    } finally {
      setIsLoading(false);
    }
  }

  async function handleFile(e: React.ChangeEvent<HTMLInputElement>) {
    if (!e.target.files?.length) return;
    const file = e.target.files[0];

    try {
      await processAudioFile(file);
    } finally {
      e.target.value = "";
    }
  }

  async function handleManualSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!manualTranscript.trim()) {
      setError("Please enter a transmission to interpret.");
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const result = await interpretTranscript(manualTranscript.trim());
      await processResult(result);
      setManualTranscript("");
    } catch (err) {
      console.error("Interpretation error", err);
      setError("Unable to interpret the typed transmission. Please adjust the text and try again.");
    } finally {
      setIsLoading(false);
    }
  }

  async function beginPushToTalk() {
    if (isLoading) return;
    const activeRecorder = mediaRecorderRef.current;
    if (activeRecorder && activeRecorder.state === "recording") {
      return;
    }
    if (!isMicSupported) {
      setError("Push-to-talk is not supported in this browser. Please upload an audio file instead.");
      return;
    }
    if (typeof navigator === "undefined" || !navigator.mediaDevices?.getUserMedia) {
      setError("Microphone capture is unavailable. Please upload an audio file instead.");
      return;
    }

    setError(null);

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      recordedChunksRef.current = [];
      mediaStreamRef.current = stream;

      const recorder = new MediaRecorder(stream);
      mediaRecorderRef.current = recorder;

      recorder.addEventListener("dataavailable", (event) => {
        if (event.data && event.data.size > 0) {
          recordedChunksRef.current.push(event.data);
        }
      });

      recorder.addEventListener("stop", () => {
        setIsRecording(false);
        const chunks = recordedChunksRef.current;
        recordedChunksRef.current = [];
        stopActiveStream();
        mediaRecorderRef.current = null;

        if (!chunks.length) {
          if (pendingStopRef.current) {
            pendingStopRef.current = false;
          }
          setError("Recording was too short. Please try again.");
          return;
        }

        const mimeType = recorder.mimeType || "audio/webm";
        const blob = new Blob(chunks, { type: mimeType });
        const file = new File([blob], `push-to-talk-${Date.now()}.webm`, { type: mimeType });
        pendingStopRef.current = false;
        void processAudioFile(file);
      });

      recorder.start();
      setIsRecording(true);

      if (pendingStopRef.current) {
        recorder.stop();
      }
    } catch (err) {
      console.error("Microphone access error", err);
      stopActiveStream();
      mediaRecorderRef.current = null;
      recordedChunksRef.current = [];
      pendingStopRef.current = false;
      setIsRecording(false);
      setError(
        "Unable to access the microphone. Please allow permission or upload an audio file instead.",
      );
    }
  }

  function endPushToTalk() {
    pendingStopRef.current = true;
    const recorder = mediaRecorderRef.current;
    if (recorder && recorder.state !== "inactive") {
      recorder.stop();
    } else {
      setIsRecording(false);
    }
  }

  const handlePushToTalkPointerDown = (event: ReactPointerEvent<HTMLButtonElement>) => {
    if (isLoading || !isMicSupported) {
      return;
    }
    if (event.pointerType === "mouse" && event.button !== 0) {
      return;
    }
    event.preventDefault();
    pendingStopRef.current = false;
    void beginPushToTalk();
  };

  const handlePushToTalkPointerUp = (event: ReactPointerEvent<HTMLButtonElement>) => {
    event.preventDefault();
    endPushToTalk();
  };

  const handlePushToTalkPointerLeave = (event: ReactPointerEvent<HTMLButtonElement>) => {
    if (!isRecording) {
      return;
    }
    event.preventDefault();
    endPushToTalk();
  };

  const handlePushToTalkKeyDown = (event: ReactKeyboardEvent<HTMLButtonElement>) => {
    if (event.key === " " || event.key === "Enter") {
      if (!isRecording && !isLoading && isMicSupported) {
        event.preventDefault();
        pendingStopRef.current = false;
        void beginPushToTalk();
      }
    }
  };

  const handlePushToTalkKeyUp = (event: ReactKeyboardEvent<HTMLButtonElement>) => {
    if (event.key === " " || event.key === "Enter") {
      event.preventDefault();
      endPushToTalk();
    }
  };

  return (
    <div className="app-shell">
      <div className="app-container">
        <header className="app-header">
          <h1>ATC Voice Loop</h1>
          <p>
            Monitor live transcripts, surface emerging conflicts, and craft rapid controller responses in
            one focused workspace.
          </p>
        </header>

        <div className="app-grid">
          <div className="loop-column">
            <section className="panel">
              <div className="panel__header">
                <h2>New transmission</h2>
                <span className={`status-indicator${isLoading ? " status-indicator--active" : ""}`} />
              </div>
              <p className="panel__subtitle">
                Upload a recorded exchange or hold push-to-talk to capture one live. We will transcribe it,
                interpret the intent, and flag any conflicts automatically.
              </p>

              <div className="capture-actions">
                <label className={`file-input${isLoading ? " file-input--disabled" : ""}`}>
                  <span>{isLoading ? "Processing…" : "Choose audio file"}</span>
                  <input
                    type="file"
                    accept="audio/*"
                    onChange={handleFile}
                    disabled={isLoading}
                    className="file-input__control"
                  />
                </label>
                <button
                  type="button"
                  className={`push-to-talk${isRecording ? " push-to-talk--active" : ""}`}
                  onPointerDown={handlePushToTalkPointerDown}
                  onPointerUp={handlePushToTalkPointerUp}
                  onPointerLeave={handlePushToTalkPointerLeave}
                  onPointerCancel={handlePushToTalkPointerLeave}
                  onKeyDown={handlePushToTalkKeyDown}
                  onKeyUp={handlePushToTalkKeyUp}
                  disabled={isLoading || !isMicSupported}
                  aria-pressed={isRecording}
                >
                  <span className="push-to-talk__indicator" aria-hidden="true" />
                  {isRecording ? "Release to send" : "Hold to record"}
                </button>
              </div>
              <p
                className={`push-to-talk__hint${!isMicSupported ? " push-to-talk__hint--disabled" : ""}`}
              >
                {isMicSupported
                  ? isRecording
                    ? "Recording… release to send the transmission."
                    : "Hold the push-to-talk button to capture audio from your microphone."
                  : "Push-to-talk is unavailable in this browser. Upload an audio file instead."}
              </p>

              <form className="manual-form" onSubmit={handleManualSubmit}>
                <label className="manual-form__label" htmlFor="manual-transcript">
                  Or paste a transcript
                </label>
                <textarea
                  id="manual-transcript"
                  className="manual-form__textarea"
                  placeholder="CSA zero two five, request descent to flight level three one zero."
                  value={manualTranscript}
                  onChange={(event) => setManualTranscript(event.target.value)}
                  disabled={isLoading}
                  rows={4}
                />
                <button className="manual-form__submit" type="submit" disabled={isLoading}>
                  {isLoading ? "Interpreting…" : "Interpret transmission"}
                </button>
              </form>

              {error && <p className="panel__status panel__status--error">{error}</p>}
            </section>

            {transcript && (
              <section className="panel">
                <h2 className="panel__title">Latest transmission</h2>
                <div className="transcript-block">
                  <h3>Transcript</h3>
                  <p>{transcript}</p>
                </div>

                {parsed && (
                  <div className="transcript-block">
                    <h3>Parsed intent</h3>
                    <dl className="parsed-grid">
                      <div>
                        <dt>Callsign</dt>
                        <dd>{parsed.callsign || "—"}</dd>
                      </div>
                      <div>
                        <dt>Command</dt>
                        <dd>{parsed.command || "—"}</dd>
                      </div>
                      <div>
                        <dt>Flight level</dt>
                        <dd>{formatFlightLevel(parsed.flight_level)}</dd>
                      </div>
                      <div>
                        <dt>Heading</dt>
                        <dd>
                          {typeof parsed.heading === "number" && !Number.isNaN(parsed.heading)
                            ? `${Math.round(parsed.heading)}°`
                            : "—"}
                        </dd>
                      </div>
                      <div>
                        <dt>Speaker</dt>
                        <dd>{parsed.speaker || "—"}</dd>
                      </div>
                    </dl>
                  </div>
                )}

                {response && (
                  <div className="transcript-block transcript-block--response">
                    <h3>Suggested controller readback</h3>
                    <p>{response}</p>
                  </div>
                )}
              </section>
            )}

            {history.length > 0 && (
              <section className="panel">
                <h2 className="panel__title">Loop history</h2>
                <ul className="history-list">
                  {[...history]
                    .reverse()
                    .map((entry) => (
                      <li key={entry.id} className="history-item">
                        <div className="history-item__meta">
                          <span>{formatClock(entry.timestamp)}</span>
                          {entry.parsed?.callsign && <span>{entry.parsed.callsign}</span>}
                        </div>
                        <p className="history-item__transcript">{entry.transcript || "—"}</p>
                        {entry.response && (
                          <p className="history-item__response">{entry.response}</p>
                        )}
                      </li>
                    ))}
                </ul>
              </section>
            )}
          </div>

          <ConflictResolutionPanel aircraftStates={aircraftStates} conflicts={conflicts} />
        </div>
      </div>
    </div>
  );
}
