-- Idempotent schema for the Parcel Risk Report feature store.
-- {project} and {dataset} are substituted by create_tables.py.

CREATE SCHEMA IF NOT EXISTS `{project}.{dataset}`;

CREATE TABLE IF NOT EXISTS `{project}.{dataset}.hazard_features` (
  h3_cell       STRING NOT NULL,
  hazard        STRING NOT NULL,   -- flood | subsidence | wildfire | heat | landuse
  data_version  STRING NOT NULL,   -- per-hazard stamp, e.g. "flood-20260315"
  metrics       JSON,
  no_data       BOOL NOT NULL,     -- explicit; a cell with no usable observation is
                                    -- never silently scored as zero/low risk
  evidence_ids  ARRAY<STRING>,
  computed_at   TIMESTAMP NOT NULL
)
PARTITION BY DATE(computed_at)
CLUSTER BY hazard, h3_cell;

CREATE TABLE IF NOT EXISTS `{project}.{dataset}.evidence` (
  evidence_id     STRING NOT NULL,
  hazard          STRING,
  source_product  STRING,
  granule_ids     ARRAY<STRING>,
  date_start      DATE,
  date_end        DATE,
  method_version  STRING,
  values_json     JSON,            -- `values` is a BigQuery reserved word
  license         STRING,          -- e.g. "CC-BY-4.0" for AlphaEarth-derived evidence
  created_at      TIMESTAMP NOT NULL
)
CLUSTER BY evidence_id;

CREATE TABLE IF NOT EXISTS `{project}.{dataset}.parcels` (
  parcel_id     STRING NOT NULL,
  county_fips   STRING,
  address       STRING,
  geometry      GEOGRAPHY NOT NULL,
  h3_cells      ARRAY<STRING>,
  buffer_cells  ARRAY<STRING>,
  source        STRING,            -- "travis_county_parcel" | "point_buffer_fallback"
  created_at    TIMESTAMP NOT NULL
)
CLUSTER BY parcel_id;

CREATE TABLE IF NOT EXISTS `{project}.{dataset}.reports` (
  report_id            STRING NOT NULL,
  parcel_id             STRING NOT NULL,
  data_version          STRING NOT NULL,  -- composite hash across all 5 hazards
  jev_version           STRING,
  llm_model              STRING,
  scores                JSON,
  report_md             STRING,
  needs_expert_review   BOOL,
  data_gaps             JSON,
  center_lat            FLOAT64,          -- geocoded point, for GET /v1/reports/{id} map rendering
  center_lon            FLOAT64,
  created_at            TIMESTAMP NOT NULL
)
PARTITION BY DATE(created_at)
CLUSTER BY parcel_id;
