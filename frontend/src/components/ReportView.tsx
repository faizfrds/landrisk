import type { Hazard, ReportResponse } from "../api/types";
import { getReportPdfUrl } from "../api/client";
import HazardCard from "./HazardCard";
import MapView from "./MapView";

const HAZARD_ORDER: Hazard[] = ["flood", "subsidence", "wildfire", "heat", "landuse"];

interface Props {
  report: ReportResponse;
}

export default function ReportView({ report }: Props) {
  return (
    <div className="report-view">
      <div className="report-header">
        <h2>Report {report.report_id}</h2>
        <a href={getReportPdfUrl(report.report_id)} target="_blank" rel="noreferrer">
          Download PDF
        </a>
      </div>

      {report.needs_expert_review && (
        <div className="banner banner-warning">This report has been flagged for expert review.</div>
      )}

      <div className="hazard-grid">
        {HAZARD_ORDER.map((hazard) => (
          <HazardCard key={hazard} hazard={hazard} result={report.hazards[hazard]} />
        ))}
      </div>

      {report.cells.length > 0 && (
        <MapView cells={report.cells} center={{ lat: report.center.lat, lng: report.center.lon }} />
      )}

      {report.data_gaps.length > 0 && (
        <div className="data-gaps">
          <h3>Data gaps</h3>
          <ul>
            {report.data_gaps.map((gap, i) => (
              <li key={i}>{gap}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="report-markdown" dangerouslySetInnerHTML={{ __html: renderMarkdownStub(report.report_md) }} />
    </div>
  );
}

// Minimal markdown-to-HTML for headings/paragraphs/lists -- a prototype
// display only; the PDF (rendered server-side with the `markdown` package)
// is the fidelity-complete version. Escapes HTML first: report_md is
// LLM-generated text and must never be trusted as raw markup.
function escapeHtml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function renderMarkdownStub(md: string): string {
  return escapeHtml(md)
    .split("\n")
    .map((line) => {
      if (line.startsWith("### ")) return `<h4>${line.slice(4)}</h4>`;
      if (line.startsWith("## ")) return `<h3>${line.slice(3)}</h3>`;
      if (line.startsWith("# ")) return `<h2>${line.slice(2)}</h2>`;
      if (line.startsWith("- ")) return `<li>${line.slice(2)}</li>`;
      if (line.trim() === "") return "<br/>";
      return `<p>${line}</p>`;
    })
    .join("\n");
}
