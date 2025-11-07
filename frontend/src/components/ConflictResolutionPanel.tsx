import type { AircraftState, Conflict, NextActionSuggestion } from "../types";
import "../App.css";

interface ConflictResolutionPanelProps {
  aircraftStates: AircraftState[];
  conflicts: Conflict[];
  nextAction?: NextActionSuggestion | null;
}

function formatFlightLevel(value?: number) {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return "—";
  }
  const level = Math.max(0, Math.round(value));
  return `FL${level.toString().padStart(3, "0")}`;
}

function formatRelativeTime(timestamp: string) {
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) return "—";

  const diff = Date.now() - date.getTime();
  if (diff < 45_000) {
    const seconds = Math.max(1, Math.round(diff / 1000));
    return `${seconds}s ago`;
  }
  if (diff < 90_000) {
    return "1m ago";
  }
  if (diff < 3_600_000) {
    const minutes = Math.round(diff / 60_000);
    return `${minutes}m ago`;
  }
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function formatPosition(position?: { x: number; y: number }) {
  if (!position) {
    return "—";
  }
  const east = position.x >= 0 ? "E" : "W";
  const north = position.y >= 0 ? "N" : "S";
  return `${Math.abs(position.x).toFixed(1)}${east} / ${Math.abs(position.y).toFixed(1)}${north}`;
}

function formatSpeed(speed?: number) {
  if (typeof speed !== "number" || Number.isNaN(speed)) {
    return "—";
  }
  return `${Math.round(speed)} kts`;
}

const severityLabels: Record<Conflict["severity"], string> = {
  high: "High risk",
  moderate: "Monitor",
  low: "Advisory",
};

export default function ConflictResolutionPanel({
  aircraftStates,
  conflicts,
  nextAction,
}: ConflictResolutionPanelProps) {
  return (
    <aside className="panel conflict-panel">
      <header className="panel__header">
        <h2>Conflict resolution</h2>
        <span className="conflict-panel__count">{aircraftStates.length} tracked</span>
      </header>
      <p className="panel__subtitle">
        Track aircraft assignments, highlight emerging conflicts, and capture a ready-made playbook for your
        next instruction.
      </p>

      {nextAction && (
        <section className="next-action">
          <div className="section-header">
            <h3>Next best action</h3>
            <span className="section-header__meta">Live recommendation</span>
          </div>
          <p className="next-action__title">{nextAction.title}</p>
          <p className="next-action__summary">{nextAction.summary}</p>
          <p className="next-action__rationale">{nextAction.rationale}</p>
        </section>
      )}

      <section className="conflict-panel__section">
        <div className="section-header">
          <h3>Active aircraft</h3>
          <span className="section-header__meta">Updated in real time</span>
        </div>
        {aircraftStates.length === 0 ? (
          <p className="empty-state">No transmissions yet. Upload audio to populate the loop.</p>
        ) : (
          <ul className="aircraft-list">
            {aircraftStates.map((state) => (
              <li key={state.callsign} className="aircraft-card">
                <div className="aircraft-card__header">
                  <div>
                    <p className="aircraft-card__callsign">{state.callsign}</p>
                    <p className="aircraft-card__timestamp">{formatRelativeTime(state.lastHeard)}</p>
                  </div>
                  <div className="aircraft-card__tags">
                    {state.origin && (
                      <span className={`badge badge--origin-${state.origin}`}>
                        {state.origin === "simulated" ? "Simulated" : "Live"}
                      </span>
                    )}
                    <span className={`badge${state.command ? "" : " badge--muted"}`}>
                      {state.command ? state.command : "Unknown"}
                    </span>
                  </div>
                </div>
                <dl className="aircraft-card__grid">
                  <div>
                    <dt>Flight level</dt>
                    <dd>{formatFlightLevel(state.flightLevel)}</dd>
                  </div>
                  <div>
                    <dt>Heading</dt>
                    <dd>
                      {typeof state.heading === "number" && !Number.isNaN(state.heading)
                        ? `${Math.round(state.heading)}°`
                        : "—"}
                    </dd>
                  </div>
                  <div>
                    <dt>Speaker</dt>
                    <dd>{state.speaker || "—"}</dd>
                  </div>
                  <div>
                    <dt>Position</dt>
                    <dd>{formatPosition(state.position)}</dd>
                  </div>
                  <div>
                    <dt>Ground speed</dt>
                    <dd>{formatSpeed(state.speed)}</dd>
                  </div>
                </dl>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="conflict-panel__section">
        <div className="section-header">
          <h3>Potential conflicts</h3>
          <span className="section-header__meta">
            {conflicts.length > 0 ? `${conflicts.length} flagged` : "All clear"}
          </span>
        </div>

        {conflicts.length === 0 ? (
          <div className="empty-state empty-state--success">
            <p>No vertical or lateral conflicts detected.</p>
            <p>Keep monitoring for new transmissions.</p>
          </div>
        ) : (
          <ul className="conflict-list">
            {conflicts.map((conflict) => (
              <li key={conflict.id} className={`conflict-card conflict-card--${conflict.severity}`}>
                <div className="conflict-card__header">
                  <span className="conflict-card__severity">{severityLabels[conflict.severity]}</span>
                  <span className="conflict-card__metric">{conflict.metric}</span>
                </div>
                <p className="conflict-card__description">{conflict.description}</p>
                <p className="conflict-card__resolution">{conflict.resolution}</p>
              </li>
            ))}
          </ul>
        )}
      </section>
    </aside>
  );
}
