import { useState } from "react";
import type { AnalyzeResponse } from "../types";
import ConfidenceScore from "./ConfidenceScore";
import WaveformViewer from "./WaveformViewer";
import ExplanationPanel from "./ExplanationPanel";
import VisualizationSuite from "./VisualizationSuite";
import { downloadReport } from "../api/client";

interface Props {
  result: AnalyzeResponse;
  audioUrl: string;
}

export default function ResultsPanel({ result, audioUrl }: Props) {
  const [downloading, setDownloading] = useState(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);

  async function handleDownloadPdf() {
    setDownloading(true);
    setDownloadError(null);
    try {
      await downloadReport(result.id);
    } catch {
      setDownloadError("Failed to generate report. Please try again.");
    } finally {
      setDownloading(false);
    }
  }

  return (
    <div className="results-panel">
      {/* ---- Header row: filename + download button ---------------------- */}
      <div className="results-panel-header">
        <h2 className="results-panel-title">{result.filename}</h2>
        <button
          className="pdf-download-btn"
          onClick={handleDownloadPdf}
          disabled={downloading}
          aria-label={`Download PDF report for ${result.filename}`}
          title="Download analysis report as PDF"
        >
          {downloading ? (
            <>
              <span className="pdf-btn-spinner" aria-hidden="true" />
              Generating…
            </>
          ) : (
            <>
              <span className="pdf-btn-icon" aria-hidden="true">📄</span>
              Download PDF
            </>
          )}
        </button>
      </div>

      {downloadError && (
        <p className="error-message pdf-error" role="alert">
          {downloadError}
        </p>
      )}

      <ConfidenceScore prediction={result.prediction} confidence={result.confidence} />

      <WaveformViewer audioUrl={audioUrl} suspiciousSegments={result.suspicious_segments} />

      <div className="results-grid">
        <div className="result-stat">
          <span>Room Acoustics Match</span>
          <strong>{result.room_acoustics_match}</strong>
        </div>
        <div className="result-stat">
          <span>Breathing Consistency</span>
          <strong>{result.breathing_consistency}</strong>
        </div>
        <div className="result-stat">
          <span>Inference Time</span>
          <strong>{result.inference_time_sec}s</strong>
        </div>
        <div className="result-stat">
          <span>Analyzed At</span>
          <strong>{new Date(result.timestamp).toLocaleString()}</strong>
        </div>
      </div>

      {/* ---- Visualization Suite ----------------------------------------- */}
      {result.viz && <VisualizationSuite result={result} />}

      {/* ---- XAI Explanation --------------------------------------------- */}
      {result.explanation && (
        <ExplanationPanel explanation={result.explanation} />
      )}
    </div>
  );
}
