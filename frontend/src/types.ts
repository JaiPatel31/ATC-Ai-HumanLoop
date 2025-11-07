export type ConflictSeverity = "low" | "moderate" | "high";

export interface ParsedTransmission {
  callsign?: string | null;
  command?: string | null;
  flight_level?: number | null;
  heading?: number | null;
  speaker?: string | null;
  // Allow additional properties returned by the backend without typing them explicitly.
  [key: string]: unknown;
}

export interface SttResult {
  transcript?: string | null;
  parsed: ParsedTransmission | null;
  response?: string | null;
  response_tts?: string | null;
}

export interface TransmissionEntry {
  id: string;
  timestamp: string;
  transcript: string;
  parsed: ParsedTransmission | null;
  response: string;
}

export interface AircraftState {
  callsign: string;
  flightLevel?: number;
  heading?: number;
  command?: string;
  speaker?: string;
  lastHeard: string;
  position?: {
    x: number;
    y: number;
  };
  speed?: number;
  origin?: "live" | "simulated";
}

export interface Conflict {
  id: string;
  aircraft: [string, string];
  description: string;
  resolution: string;
  severity: ConflictSeverity;
  metric: string;
}

export interface NextActionSuggestion {
  title: string;
  summary: string;
  rationale: string;
}
