import { useEffect, useMemo, useRef, useState } from "react";
import type { KeyboardEvent as ReactKeyboardEvent, PointerEvent as ReactPointerEvent } from "react";
import { interpretTranscript, sendAudio } from "./api";
import AirspaceMap from "./components/AirspaceMap";
import ConflictResolutionPanel from "./components/ConflictResolutionPanel";
import type {
  ParsedTransmission,
  TransmissionEntry,
  AircraftState,
  Conflict,
  NextActionSuggestion,
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

const SECTOR_HALF_WIDTH = 90;
const SECTOR_HALF_HEIGHT = 60;

function randomHeading() {
  return Math.round(Math.random() * 360);
}

function randomFlightLevel() {
  return 250 + Math.round(Math.random() * 80);
}

function randomSpeed() {
  return 320 + Math.round(Math.random() * 140);
}

function createRandomPosition() {
  return {
    x: Math.random() * SECTOR_HALF_WIDTH * 1.6 - SECTOR_HALF_WIDTH * 0.8,
    y: Math.random() * SECTOR_HALF_HEIGHT * 1.6 - SECTOR_HALF_HEIGHT * 0.8,
  };
}

function wrapCoordinate(value: number, limit: number) {
  if (value > limit) {
    return -limit + (value - limit);
  }
  if (value < -limit) {
    return limit + (value + limit);
  }
  return value;
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
          const severity: Conflict["severity"] = diff === 0 ? "high" : "moderate";
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
            const severity: Conflict["severity"] = headingDiff <= 5 ? "high" : headingDiff <= 15 ? "moderate" : "low";
            const turnHeading = normalizeHeading((b.heading ?? 0) + 30);
            conflicts.push({
              id: headingKey,
              aircraft: [a.callsign, b.callsign],
              description: `${a.callsign} and ${b.callsign} are converging with only ${headingDiff.toFixed(
                0,
              )}° of heading separation.`,
              resolution:
                severity === "high"
                  ? `Vector ${b.callsign} immediately: suggest heading ${turnHeading
                      .toString()
                      .padStart(3, "0")}° or greater divergence.`
                  : `Plan lateral separation: issue ${b.callsign} a 30° diverging turn to increase spacing.`,
              severity,
              metric: `Heading separation ${headingDiff.toFixed(0)}°`,
            });
            seen.add(headingKey);
          }
        }
      }

      if (a.position && b.position) {
        const dx = a.position.x - b.position.x;
        const dy = a.position.y - b.position.y;
        const distance = Math.sqrt(dx * dx + dy * dy);
        if (distance <= 12) {
          const proximityKey = `prox-${keyBase}`;
          if (!seen.has(proximityKey)) {
            const severity: Conflict["severity"] = distance <= 4 ? "high" : distance <= 8 ? "moderate" : "low";
            const suggestedTurn = normalizeHeading((a.heading ?? randomHeading()) + 45);
            conflicts.push({
              id: proximityKey,
              aircraft: [a.callsign, b.callsign],
              description: `${a.callsign} and ${b.callsign} are within ${distance.toFixed(
                1,
              )} NM of each other.`,
              resolution:
                severity === "high"
                  ? `Recommend immediate divergence: instruct ${a.callsign} to turn ${suggestedTurn
                      .toString()
                      .padStart(3, "0")}° and adjust one aircraft by ±2,000 ft.`
                  : `Plan a proactive vector: nudge ${b.callsign} 20° off course or alter speed to build spacing.`,
              severity,
              metric: `Proximity ${distance.toFixed(1)} NM`,
            });
            seen.add(proximityKey);
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
  const [aircraftStates, setAircraftStates] = useState<AircraftState[]>([]);
  const aircraftMapRef = useRef<Map<string, AircraftState>>(new Map());

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const recordedChunksRef = useRef<BlobPart[]>([]);
  const pendingStopRef = useRef(false);

  const commitAircraftMap = (map: Map<string, AircraftState>) => {
    aircraftMapRef.current = map;
    const sorted = Array.from(map.values()).sort(
      (a, b) => new Date(b.lastHeard).getTime() - new Date(a.lastHeard).getTime(),
    );
    setAircraftStates(sorted);
  };

  const updateAircraft = (
    callsign: string,
    builder: (previous: AircraftState | undefined) => AircraftState,
  ) => {
    const map = new Map(aircraftMapRef.current);
    const next = builder(map.get(callsign));
    map.set(callsign, next);
    commitAircraftMap(map);
  };

  const ingestTransmission = (parsedTransmission: ParsedTransmission | null, timestamp: string) => {
    if (!parsedTransmission?.callsign) {
      return;
    }

    const callsign = parsedTransmission.callsign as string;

    updateAircraft(callsign, (previous) => {
      const position = previous?.position ?? createRandomPosition();
      const speed = previous?.speed ?? randomSpeed();
      const heading =
        typeof parsedTransmission.heading === "number" && !Number.isNaN(parsedTransmission.heading)
          ? parsedTransmission.heading
          : typeof previous?.heading === "number" && !Number.isNaN(previous.heading)
          ? previous.heading
          : randomHeading();
      const flightLevel =
        typeof parsedTransmission.flight_level === "number" &&
        !Number.isNaN(parsedTransmission.flight_level)
          ? parsedTransmission.flight_level
          : typeof previous?.flightLevel === "number" && !Number.isNaN(previous.flightLevel)
          ? previous.flightLevel
          : randomFlightLevel();

      return {
        callsign,
        flightLevel,
        heading,
        command: parsedTransmission.command ?? previous?.command,
        speaker: parsedTransmission.speaker ?? previous?.speaker,
        lastHeard: timestamp,
        position: { ...position },
        speed,
        origin: previous?.origin ?? "live",
      };
    });
  };

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

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }

    const now = new Date().toISOString();
    const seeds = [
      { callsign: "SIM210", heading: 45, flightLevel: 320 },
      { callsign: "SIM432", heading: 135, flightLevel: 280 },
      { callsign: "SIM905", heading: 300, flightLevel: 360 },
    ];

    const map = new Map(aircraftMapRef.current);
    let changed = false;
    for (const seed of seeds) {
      if (map.has(seed.callsign)) {
        continue;
      }
      map.set(seed.callsign, {
        callsign: seed.callsign,
        flightLevel: seed.flightLevel,
        heading: seed.heading,
        command: "maintain",
        speaker: "simulated",
        lastHeard: now,
        position: createRandomPosition(),
        speed: randomSpeed(),
        origin: "simulated",
      });
      changed = true;
    }

    if (changed) {
      commitAircraftMap(map);
    }
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }

    let animationFrame: number;
    let last = typeof performance !== "undefined" ? performance.now() : Date.now();
    let accumulator = 0;

    const tick = (time: number) => {
      const now = time ?? (typeof performance !== "undefined" ? performance.now() : Date.now());
      const deltaSeconds = Math.max(0, (now - last) / 1000);
      last = now;
      accumulator += deltaSeconds;

      if (accumulator >= 0.5) {
        const stepSeconds = accumulator;
        accumulator = 0;
        const map = new Map<string, AircraftState>();
        let changed = false;

        aircraftMapRef.current.forEach((state, key) => {
          const heading =
            typeof state.heading === "number" && !Number.isNaN(state.heading)
              ? state.heading
              : randomHeading();
          const speed =
            typeof state.speed === "number" && !Number.isNaN(state.speed)
              ? state.speed
              : randomSpeed();
          const basePosition = state.position ?? createRandomPosition();
          const radians = (heading * Math.PI) / 180;
          const distanceNm = speed * (stepSeconds / 3600);
          let nextX = basePosition.x + Math.sin(radians) * distanceNm;
          let nextY = basePosition.y - Math.cos(radians) * distanceNm;
          nextX = wrapCoordinate(nextX, SECTOR_HALF_WIDTH - 2);
          nextY = wrapCoordinate(nextY, SECTOR_HALF_HEIGHT - 2);

          if (
            !state.position ||
            Math.abs(nextX - state.position.x) > 0.001 ||
            Math.abs(nextY - state.position.y) > 0.001 ||
            speed !== state.speed ||
            heading !== state.heading
          ) {
            const updated: AircraftState = {
              ...state,
              heading,
              speed,
              position: { x: nextX, y: nextY },
              lastHeard: state.origin === "simulated" ? new Date().toISOString() : state.lastHeard,
            };
            map.set(key, updated);
            changed = true;
          } else {
            map.set(key, state);
          }
        });

        if (changed) {
          commitAircraftMap(map);
        } else if (map.size > 0) {
          aircraftMapRef.current = map;
        }
      }

      animationFrame = window.requestAnimationFrame(tick);
    };

    animationFrame = window.requestAnimationFrame(tick);
    return () => window.cancelAnimationFrame(animationFrame);
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }

    const interval = window.setInterval(() => {
      const map = new Map(aircraftMapRef.current);
      let changed = false;

      map.forEach((state, key) => {
        if (state.origin !== "simulated") {
          return;
        }

        let flightLevel = state.flightLevel ?? randomFlightLevel();
        if (Math.random() < 0.25) {
          const delta = Math.random() < 0.5 ? -10 : 10;
          flightLevel = Math.max(180, Math.min(410, flightLevel + delta));
        }
        const headingDelta = (Math.random() - 0.5) * 30;
        const heading = normalizeHeading((state.heading ?? randomHeading()) + headingDelta);

        map.set(key, {
          ...state,
          flightLevel,
          heading,
          command: Math.random() < 0.4 ? "maintain" : state.command ?? "monitor",
          lastHeard: new Date().toISOString(),
        });
        changed = true;
      });

      if (changed) {
        commitAircraftMap(map);
      }
    }, 12000);

    return () => window.clearInterval(interval);
  }, []);

  const conflicts = useMemo(() => detectConflicts(aircraftStates), [aircraftStates]);
  const nextAction = useMemo<NextActionSuggestion | null>(() => {
    if (conflicts.length > 0) {
      const priority = { high: 0, moderate: 1, low: 2 } as const;
      const [top] = [...conflicts].sort(
        (a, b) => priority[a.severity] - priority[b.severity],
      );
      if (top) {
        return {
          title: "Resolve highlighted conflict",
          summary: top.resolution,
          rationale: top.description,
        };
      }
    }

    if (parsed?.command && parsed.speaker === "pilot") {
      const callsign = parsed.callsign ?? "the aircraft";
      const acknowledgement =
        response ||
        `Clear ${callsign} to ${parsed.command} and provide the corresponding heading or level.`;
      return {
        title: "Acknowledge pilot request",
        summary: acknowledgement,
        rationale: `${callsign} reported as ${parsed.command}. Issue a clear readback to keep the loop tight.`,
      };
    }

    if (aircraftStates.length > 0) {
      const recent = aircraftStates[0];
      const levelText = formatFlightLevel(recent.flightLevel);
      return {
        title: "Maintain situational scan",
        summary: `Confirm ${recent.callsign} holds ${levelText} and current vector.`,
        rationale: `${recent.callsign} was last heard ${formatClock(recent.lastHeard)} and remains the most recent contact.`,
      };
    }

    return null;
  }, [conflicts, parsed, response, aircraftStates]);

  async function processResult(
    result: SttResult,
    options: { recordHistory?: boolean; timestamp?: string; playAudio?: boolean } = {},
  ) {
    const normalizedParsed = normalizeParsed(result.parsed);
    const transcriptText = result.transcript ?? "";
    const responseText = result.response ?? "";
    const entryTimestamp = options.timestamp ?? new Date().toISOString();

    setTranscript(transcriptText);
    setParsed(normalizedParsed);
    setResponse(responseText);

    if (options.recordHistory !== false) {
      setHistory((prev) => {
        const entry: TransmissionEntry = {
          id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
          timestamp: entryTimestamp,
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
    }

    ingestTransmission(normalizedParsed, entryTimestamp);

    if ((responseText || result.response_tts) && options.playAudio !== false) {
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

  const handleDownloadLog = () => {
    if (history.length === 0 || typeof window === "undefined") {
      return;
    }

    const payload = {
      generatedAt: new Date().toISOString(),
      transmissions: history,
      aircraft: aircraftStates,
    };

    const blob = new Blob([JSON.stringify(payload, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `atc-session-${new Date().toISOString().replace(/[:.]/g, "-")}.json`;
    document.body.appendChild(anchor);
    anchor.click();
    document.body.removeChild(anchor);
    URL.revokeObjectURL(url);
  };

  const handleReplay = (entry: TransmissionEntry) => {
    void processResult(
      {
        transcript: entry.transcript,
        parsed: entry.parsed,
        response: entry.response,
        response_tts: entry.response,
      },
      { recordHistory: false, playAudio: false, timestamp: new Date().toISOString() },
    );
  };

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
                <div className="panel__header">
                  <h2>Loop history</h2>
                  <button
                    type="button"
                    className="log-export"
                    onClick={handleDownloadLog}
                    title="Download the current session log as JSON"
                  >
                    Download log
                  </button>
                </div>
                <ul className="history-list">
                  {[...history]
                    .reverse()
                    .map((entry) => (
                      <li key={entry.id} className="history-item">
                        <div className="history-item__meta">
                          <div className="history-item__meta-group">
                            <span>{formatClock(entry.timestamp)}</span>
                            {entry.parsed?.callsign && <span>{entry.parsed.callsign}</span>}
                          </div>
                          <button
                            type="button"
                            className="history-item__replay"
                            onClick={() => handleReplay(entry)}
                          >
                            Replay
                          </button>
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

          <div className="analysis-column">
            <AirspaceMap aircraft={aircraftStates} conflicts={conflicts} />
            <ConflictResolutionPanel
              aircraftStates={aircraftStates}
              conflicts={conflicts}
              nextAction={nextAction}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
