import type { AircraftState, Conflict } from "../types";
import "../App.css";

interface AirspaceMapProps {
  aircraft: AircraftState[];
  conflicts: Conflict[];
}

function clampPosition(value: number, min: number, max: number) {
  if (Number.isNaN(value)) return 0;
  return Math.min(Math.max(value, min), max);
}

function formatFlightLevel(value?: number) {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return "—";
  }
  return `FL${Math.round(Math.max(0, value)).toString().padStart(3, "0")}`;
}

export default function AirspaceMap({ aircraft, conflicts }: AirspaceMapProps) {
  const highlighted = new Set<string>();
  for (const conflict of conflicts) {
    highlighted.add(conflict.aircraft[0]);
    highlighted.add(conflict.aircraft[1]);
  }

  return (
    <section className="panel airspace-panel">
      <header className="panel__header">
        <h2>Airspace overview</h2>
        <span className="airspace-panel__meta">{aircraft.length} tracks</span>
      </header>
      <p className="panel__subtitle">
        Live 2D sector display showing simulated aircraft positions, headings, and conflict highlights.
      </p>

      <div className="airspace-map" role="presentation">
        <svg viewBox="-90 -60 180 120" aria-label="Airspace map" focusable="false">
          <defs>
            <radialGradient id="radar-gradient" cx="50%" cy="50%" r="65%">
              <stop offset="0%" stopColor="rgba(148, 163, 184, 0.2)" />
              <stop offset="100%" stopColor="rgba(30, 41, 59, 0.05)" />
            </radialGradient>
          </defs>

          <rect x="-90" y="-60" width="180" height="120" fill="url(#radar-gradient)" />

          {[20, 40, 60, 80].map((radius) => (
            <circle key={radius} cx={0} cy={0} r={radius} className="airspace-map__ring" />
          ))}

          {[...Array(6)].map((_, index) => {
            const angle = (index * 60 * Math.PI) / 180;
            const x = 90 * Math.cos(angle);
            const y = 60 * Math.sin(angle);
            return <line key={index} x1={0} y1={0} x2={x} y2={y} className="airspace-map__spoke" />;
          })}

          {aircraft.map((item) => {
            if (!item.position) return null;

            const x = clampPosition(item.position.x, -90, 90);
            const y = clampPosition(item.position.y, -60, 60);
            const heading = typeof item.heading === "number" ? item.heading : 0;
            const radians = (heading * Math.PI) / 180;
            const vectorLength = 8;
            const vx = Math.sin(radians) * vectorLength;
            const vy = -Math.cos(radians) * vectorLength;
            const isHighlighted = highlighted.has(item.callsign);

            return (
              <g
                key={item.callsign}
                className={`airspace-map__track${isHighlighted ? " airspace-map__track--conflict" : ""}`}
                transform={`translate(${x} ${y})`}
              >
                <circle r={2.4} />
                <line x1={0} y1={0} x2={vx} y2={vy} />
                <text x={6} y={-4} className="airspace-map__label">
                  {item.callsign}
                </text>
                <text x={6} y={6} className="airspace-map__label airspace-map__label--secondary">
                  {formatFlightLevel(item.flightLevel)}
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      <footer className="airspace-panel__legend">
        <span className="legend-dot" aria-hidden="true" />
        <span>Heading vector scaled to ~8 NM. Highlighted targets indicate an active conflict.</span>
      </footer>
    </section>
  );
}
