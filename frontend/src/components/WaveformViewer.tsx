/**
 * AcousticSpace — Enhanced WaveformViewer
 * =========================================
 * Renders the audio waveform via WaveSurfer.js with:
 *   - Highlighted suspicious segments (red overlay rectangles)
 *   - Play/Pause + seek-to-segment controls
 *   - Duration display once audio is decoded
 */

import { useEffect, useRef, useState } from "react";
import WaveSurfer from "wavesurfer.js";
import type { SuspiciousSegment } from "../types";

interface Props {
  audioUrl: string;
  suspiciousSegments?: SuspiciousSegment[];
}

export default function WaveformViewer({
  audioUrl,
  suspiciousSegments = [],
}: Props) {
  const containerRef   = useRef<HTMLDivElement>(null);
  const overlayRef     = useRef<HTMLCanvasElement>(null);
  const wavesurferRef  = useRef<WaveSurfer | null>(null);
  const [playing, setPlaying]   = useState(false);
  const [duration, setDuration] = useState<number | null>(null);
  const [ready, setReady]       = useState(false);

  // ---- initialise WaveSurfer -----------------------------------------------
  useEffect(() => {
    if (!containerRef.current) return;
    const ws = WaveSurfer.create({
      container:     containerRef.current,
      waveColor:     "#7c9dfc",
      progressColor: "#3854c9",
      height:        80,
      cursorColor:   "#4fd6e0",
      normalize:     true,
      barWidth:      2,
      barGap:        1,
      barRadius:     2,
    });

    ws.load(audioUrl);
    ws.on("ready",  () => { setDuration(ws.getDuration()); setReady(true); });
    ws.on("play",   () => setPlaying(true));
    ws.on("pause",  () => setPlaying(false));
    ws.on("finish", () => setPlaying(false));
    wavesurferRef.current = ws;
    return () => { ws.destroy(); };
  }, [audioUrl]);

  // ---- draw suspicious segment overlays onto a canvas above the waveform --
  useEffect(() => {
    const canvas = overlayRef.current;
    if (!canvas || !ready || duration === null || duration === 0) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    suspiciousSegments.forEach(({ start_sec, end_sec }) => {
      const x = (start_sec / duration) * canvas.width;
      const w = Math.max(((end_sec - start_sec) / duration) * canvas.width, 2);
      ctx.fillStyle = "rgba(255, 107, 107, 0.28)";
      ctx.fillRect(x, 0, w, canvas.height);
      // left border
      ctx.fillStyle = "rgba(255, 107, 107, 0.85)";
      ctx.fillRect(x, 0, 2, canvas.height);
    });
  }, [ready, duration, suspiciousSegments]);

  function seekTo(sec: number) {
    const ws = wavesurferRef.current;
    if (!ws || duration === null || duration === 0) return;
    ws.seekTo(sec / duration);
  }

  return (
    <div className="waveform-viewer waveform-viewer--enhanced">
      {/* Waveform + overlay stack */}
      <div className="waveform-stack" aria-label="Audio waveform">
        <div ref={containerRef} className="waveform-inner" />
        <canvas
          ref={overlayRef}
          className="waveform-overlay"
          width={800}
          height={80}
          aria-hidden="true"
        />
      </div>

      {/* Controls */}
      <div className="waveform-controls waveform-controls--enhanced">
        <button
          className="waveform-btn"
          onClick={() => wavesurferRef.current?.playPause()}
          aria-label={playing ? "Pause" : "Play"}
          disabled={!ready}
        >
          {playing ? "⏸ Pause" : "▶ Play"}
        </button>

        {duration !== null && (
          <span className="waveform-duration">
            Duration: {duration.toFixed(2)}s
          </span>
        )}

        {suspiciousSegments.length > 0 && ready && (
          <div className="waveform-seg-btns">
            {suspiciousSegments.map((seg, i) => (
              <button
                key={i}
                className="waveform-seg-btn"
                onClick={() => seekTo(seg.start_sec)}
                title={`Jump to suspicious region at ${seg.start_sec.toFixed(2)}s`}
              >
                ⚠ {seg.start_sec.toFixed(2)}s
              </button>
            ))}
          </div>
        )}
      </div>

      {suspiciousSegments.length > 0 && (
        <div className="suspicious-segments">
          <strong>Suspicious regions:</strong>
          <ul>
            {suspiciousSegments.map((seg, i) => (
              <li key={i}>
                {seg.start_sec.toFixed(2)}s – {seg.end_sec.toFixed(2)}s
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
