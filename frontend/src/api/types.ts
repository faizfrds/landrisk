// Mirrors backend/app/api/schemas.py manually -- no codegen, kept in sync
// by hand (prototype scope).

export type Hazard = "flood" | "subsidence" | "wildfire" | "heat" | "landuse";
export type Level = "low" | "moderate" | "high" | "severe" | "uncertain";

export interface HazardResult {
  level: Level;
  score: number;
  confidence: number;
  material_to_buyer: number;
  evidence: string[];
}

export interface EvidenceItem {
  source: string;
  dates: string;
  value: string;
}

export interface CellScore {
  h3_cell: string;
  hazard: Hazard;
  score_0_100: number;
}

export interface Coordinates {
  lat: number;
  lon: number;
}

export interface ReportResponse {
  report_id: string;
  parcel_id: string;
  data_version: string;
  hazards: Record<Hazard, HazardResult>;
  needs_expert_review: boolean;
  data_gaps: string[];
  evidence: Record<string, EvidenceItem>;
  report_md: string;
  cells: CellScore[];
  center: Coordinates;
}

export interface ProgressEvent {
  stage: string;
  message: string;
}
