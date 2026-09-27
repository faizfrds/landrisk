import { Loader } from "@googlemaps/js-api-loader";
import { useEffect, useRef, useState } from "react";

import type { CellScore, Hazard } from "../api/types";
import { cellBoundaryLatLng } from "../utils/h3ToGeoJSON";
import HazardLayerToggle from "./HazardLayerToggle";

const HAZARD_COLORS: Record<Hazard, string> = {
  flood: "#1565c0",
  subsidence: "#6a1b9a",
  wildfire: "#e65100",
  heat: "#c62828",
  landuse: "#2e7d32",
};

interface Props {
  cells: CellScore[];
  center: google.maps.LatLngLiteral;
}

export default function MapView({ cells, center }: Props) {
  const mapDivRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<google.maps.Map | null>(null);
  const polygonsRef = useRef<Record<Hazard, google.maps.Polygon[]>>({
    flood: [], subsidence: [], wildfire: [], heat: [], landuse: [],
  });

  const hazards = Array.from(new Set(cells.map((c) => c.hazard))) as Hazard[];
  const [visible, setVisible] = useState<Record<Hazard, boolean>>(
    Object.fromEntries(hazards.map((h) => [h, true])) as Record<Hazard, boolean>
  );

  useEffect(() => {
    const apiKey = import.meta.env.VITE_GOOGLE_MAPS_API_KEY;
    if (!apiKey) {
      console.warn("VITE_GOOGLE_MAPS_API_KEY is not set -- map will not render.");
      return;
    }

    const loader = new Loader({ apiKey, version: "weekly" });
    let cancelled = false;

    loader.load().then(() => {
      if (cancelled || !mapDivRef.current) return;

      const map = new google.maps.Map(mapDivRef.current, {
        center,
        zoom: 15,
      });
      mapRef.current = map;

      for (const cell of cells) {
        const opacityByScore = 0.15 + (cell.score_0_100 / 100) * 0.45;
        const polygon = new google.maps.Polygon({
          paths: cellBoundaryLatLng(cell.h3_cell),
          strokeColor: HAZARD_COLORS[cell.hazard],
          strokeOpacity: 0.6,
          strokeWeight: 1,
          fillColor: HAZARD_COLORS[cell.hazard],
          fillOpacity: opacityByScore,
          map,
        });
        polygonsRef.current[cell.hazard].push(polygon);
      }
    });

    return () => {
      cancelled = true;
      for (const hazard of Object.keys(polygonsRef.current) as Hazard[]) {
        polygonsRef.current[hazard].forEach((p) => p.setMap(null));
        polygonsRef.current[hazard] = [];
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cells]);

  function handleToggle(hazard: Hazard) {
    const nextVisible = !visible[hazard];
    setVisible((prev) => ({ ...prev, [hazard]: nextVisible }));
    polygonsRef.current[hazard].forEach((p) => p.setMap(nextVisible ? mapRef.current : null));
  }

  return (
    <div className="map-view">
      <HazardLayerToggle hazards={hazards} visible={visible} onToggle={handleToggle} />
      <div ref={mapDivRef} className="map-canvas" />
    </div>
  );
}
