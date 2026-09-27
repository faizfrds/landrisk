import type { Hazard } from "../api/types";

const LABELS: Record<Hazard, string> = {
  flood: "Flood",
  subsidence: "Subsidence",
  wildfire: "Wildfire",
  heat: "Heat",
  landuse: "Land-use change",
};

interface Props {
  hazards: Hazard[];
  visible: Record<Hazard, boolean>;
  onToggle: (hazard: Hazard) => void;
}

export default function HazardLayerToggle({ hazards, visible, onToggle }: Props) {
  return (
    <div className="hazard-layer-toggle">
      {hazards.map((hazard) => (
        <label key={hazard}>
          <input type="checkbox" checked={visible[hazard]} onChange={() => onToggle(hazard)} />
          {LABELS[hazard]}
        </label>
      ))}
    </div>
  );
}
