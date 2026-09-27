import type { Hazard, HazardResult } from "../api/types";

const TITLES: Record<Hazard, string> = {
  flood: "Flood",
  subsidence: "Ground subsidence",
  wildfire: "Wildfire",
  heat: "Extreme heat",
  landuse: "Land-use change",
};

const LEVEL_COLORS: Record<string, string> = {
  low: "#2e7d32",
  moderate: "#f9a825",
  high: "#e65100",
  severe: "#c62828",
  uncertain: "#616161",
};

interface Props {
  hazard: Hazard;
  result: HazardResult;
}

export default function HazardCard({ hazard, result }: Props) {
  return (
    <div className="hazard-card">
      <div className="hazard-card-header">
        <h3>{TITLES[hazard]}</h3>
        <span className="level-badge" style={{ backgroundColor: LEVEL_COLORS[result.level] }}>
          {result.level}
        </span>
      </div>
      <div className="hazard-card-meta">
        Score {result.score}/100 &middot; Confidence {(result.confidence * 100).toFixed(0)}%
      </div>
      {result.evidence.length > 0 && (
        <div className="hazard-card-evidence">Evidence: {result.evidence.join(", ")}</div>
      )}
    </div>
  );
}
