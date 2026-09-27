import type { ProgressEvent, ReportResponse } from "./types";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export async function getReport(reportId: string): Promise<ReportResponse> {
  const resp = await fetch(`${BASE_URL}/v1/reports/${reportId}`);
  if (!resp.ok) throw new Error(`Failed to fetch report ${reportId}: ${resp.status}`);
  return resp.json();
}

export function getReportPdfUrl(reportId: string): string {
  return `${BASE_URL}/v1/reports/${reportId}/pdf`;
}

/**
 * POSTs an address and streams SSE progress events, resolving with the
 * final report. Native EventSource can't POST a body, so this parses SSE
 * frames manually from a streamed fetch response.
 */
export async function postReportStream(
  address: string,
  onProgress: (event: ProgressEvent) => void
): Promise<ReportResponse> {
  const resp = await fetch(`${BASE_URL}/v1/reports?stream=true`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
    body: JSON.stringify({ address }),
  });
  if (!resp.ok || !resp.body) {
    throw new Error(`Failed to start report generation: ${resp.status}`);
  }

  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    // SSE allows CRLF, LF, or CR line endings (sse-starlette emits CRLF);
    // normalize so frames split on a blank line regardless. A trailing "\r"
    // is held back in case its "\n" arrives in the next chunk.
    let text = buffer + decoder.decode(value, { stream: true });
    const heldCr = text.endsWith("\r") ? "\r" : "";
    if (heldCr) text = text.slice(0, -1);
    text = text.replace(/\r\n?/g, "\n");

    const frames = text.split("\n\n");
    buffer = (frames.pop() ?? "") + heldCr;

    for (const frame of frames) {
      const eventLine = frame.split("\n").find((l) => l.startsWith("event:"));
      const dataLine = frame.split("\n").find((l) => l.startsWith("data:"));
      if (!eventLine || !dataLine) continue;

      const eventType = eventLine.slice("event:".length).trim();
      const data = JSON.parse(dataLine.slice("data:".length).trim());

      if (eventType === "progress") {
        onProgress(data as ProgressEvent);
      } else if (eventType === "done") {
        return data as ReportResponse;
      }
    }
  }

  throw new Error("Stream ended without a final report");
}
