import { useEffect, useState } from "react";
import { Route, Routes, useNavigate, useParams } from "react-router-dom";

import { getReport, postReportStream } from "./api/client";
import type { ProgressEvent, ReportResponse } from "./api/types";
import AddressForm from "./components/AddressForm";
import ProgressStream from "./components/ProgressStream";
import ReportView from "./components/ReportView";

function HomePage() {
  const [events, setEvents] = useState<ProgressEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  async function handleSubmit(address: string) {
    setLoading(true);
    setError(null);
    setEvents([]);
    try {
      const report = await postReportStream(address, (event) => {
        setEvents((prev) => [...prev, event]);
      });
      navigate(`/reports/${report.report_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="home-page">
      <h1>Parcel Risk Report</h1>
      <p className="subtitle">Enter a US address to get a cited, satellite-backed climate-risk report.</p>
      <AddressForm onSubmit={handleSubmit} disabled={loading} />
      <ProgressStream events={events} />
      {error && <div className="banner banner-error">{error}</div>}
    </div>
  );
}

function ReportPage() {
  const { reportId } = useParams<{ reportId: string }>();
  const [report, setReport] = useState<ReportResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!reportId) return;
    getReport(reportId)
      .then(setReport)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load report"));
  }, [reportId]);

  if (error) return <div className="banner banner-error">{error}</div>;
  if (!report) return <div className="loading">Loading report…</div>;
  return <ReportView report={report} />;
}

export default function App() {
  return (
    <div className="app">
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/reports/:reportId" element={<ReportPage />} />
      </Routes>
    </div>
  );
}
