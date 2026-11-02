import { useMemo, useState } from "react";
import { Document, Page, pdfjs } from "react-pdf";

import { entityLabel } from "../lib/entities.js";
import { useElementWidth } from "../lib/useElementWidth.js";
import "./PdfViewer.css";

pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  "pdfjs-dist/build/pdf.worker.min.mjs",
  import.meta.url,
).toString();

const PAGE_MAX_WIDTH = 720;
const MIN_DRAW_PX = 6;

export default function PdfViewer({
  url,
  findings,
  selectedId,
  onSelect,
  drawMode,
  onDraw,
}) {
  const [containerRef, containerWidth] = useElementWidth();
  const pageWidth = Math.min(PAGE_MAX_WIDTH, Math.floor(containerWidth));

  const [pageCount, setPageCount] = useState(0);
  const [sizes, setSizes] = useState({}); // page index -> size in PDF points
  const [error, setError] = useState("");
  const [draft, setDraft] = useState(null); // the box being drawn, in screen pixels

  // react-pdf wants a stable object, otherwise it reloads the file on every render.
  const file = useMemo(() => ({ url, withCredentials: true }), [url]);

  const boxesByPage = useMemo(() => {
    const byPage = {};
    for (const finding of findings) {
      finding.boxes.forEach((box, index) => {
        if (!byPage[box.page]) byPage[box.page] = [];
        byPage[box.page].push({ finding, box, index });
      });
    }
    return byPage;
  }, [findings]);

  function handlePageLoaded(pageIndex, page) {
    const viewport = page.getViewport({ scale: 1 });
    setSizes((previous) => ({
      ...previous,
      [pageIndex]: { width: viewport.width, height: viewport.height },
    }));
  }

  // Pointer position inside the drawing layer, clamped to the page.
  function pointFrom(event) {
    const rect = event.currentTarget.getBoundingClientRect();
    return {
      x: Math.min(Math.max(event.clientX - rect.left, 0), rect.width),
      y: Math.min(Math.max(event.clientY - rect.top, 0), rect.height),
      width: rect.width,
      height: rect.height,
    };
  }

  function startDraw(pageIndex, event) {
    event.currentTarget.setPointerCapture(event.pointerId);
    const point = pointFrom(event);
    setDraft({ pageIndex, x0: point.x, y0: point.y, x1: point.x, y1: point.y });
  }

  function moveDraw(event) {
    if (!draft) return;
    const point = pointFrom(event);
    setDraft({ ...draft, x1: point.x, y1: point.y });
  }

  function endDraw(pageIndex, event) {
    if (!draft || draft.pageIndex !== pageIndex) return;
    const point = pointFrom(event);
    const size = sizes[pageIndex];
    const left = Math.min(draft.x0, point.x);
    const right = Math.max(draft.x0, point.x);
    const top = Math.min(draft.y0, point.y);
    const bottom = Math.max(draft.y0, point.y);
    setDraft(null);
    if (right - left < MIN_DRAW_PX || bottom - top < MIN_DRAW_PX) return; // just a click
    // Screen pixels -> PDF points, the unit the server stores.
    const scaleX = size.width / point.width;
    const scaleY = size.height / point.height;
    onDraw({
      page: pageIndex,
      x0: left * scaleX,
      y0: top * scaleY,
      x1: right * scaleX,
      y1: bottom * scaleY,
    });
  }

  return (
    <div
      className={`viewer${drawMode ? " viewer--drawing" : ""}`}
      ref={containerRef}
    >
      {error && (
        <p className="alert alert--error" role="alert">
          {error}
        </p>
      )}
      <Document
        file={file}
        onLoadSuccess={({ numPages }) => setPageCount(numPages)}
        onLoadError={() => setError("The document could not be displayed.")}
        loading={<p>Loading document…</p>}
      >
        {pageWidth > 0 &&
          Array.from({ length: pageCount }, (_, pageIndex) => {
            const size = sizes[pageIndex];
            const boxes = boxesByPage[pageIndex] || [];
            return (
              <div
                key={pageIndex}
                className="viewer__page"
                style={{ width: pageWidth }}
              >
                <Page
                  pageNumber={pageIndex + 1}
                  width={pageWidth}
                  renderTextLayer={false}
                  renderAnnotationLayer={false}
                  onLoadSuccess={(page) => handlePageLoaded(pageIndex, page)}
                />
                {size &&
                  boxes.map(({ finding, box, index }) => {
                    const classes = ["box", `box--${finding.tier}`];
                    if (finding.decision === "keep") classes.push("box--keep");
                    if (finding.id === selectedId)
                      classes.push("box--selected");
                    return (
                      <button
                        type="button"
                        key={`${finding.id}-${index}`}
                        id={`box-${finding.id}-${index}`}
                        className={classes.join(" ")}
                        style={{
                          left: `${(box.x0 / size.width) * 100}%`,
                          top: `${(box.y0 / size.height) * 100}%`,
                          width: `${((box.x1 - box.x0) / size.width) * 100}%`,
                          height: `${((box.y1 - box.y0) / size.height) * 100}%`,
                        }}
                        onClick={() => onSelect(finding.id, false)}
                        aria-label={`${entityLabel(finding.entity_type)}, page ${pageIndex + 1}`}
                      />
                    );
                  })}
                {drawMode && size && (
                  <div
                    className="viewer__draw"
                    onPointerDown={(event) => startDraw(pageIndex, event)}
                    onPointerMove={moveDraw}
                    onPointerUp={(event) => endDraw(pageIndex, event)}
                    onPointerCancel={() => setDraft(null)}
                  >
                    {draft && draft.pageIndex === pageIndex && (
                      <div
                        className="viewer__draft"
                        style={{
                          left: Math.min(draft.x0, draft.x1),
                          top: Math.min(draft.y0, draft.y1),
                          width: Math.abs(draft.x1 - draft.x0),
                          height: Math.abs(draft.y1 - draft.y0),
                        }}
                      />
                    )}
                  </div>
                )}
                <span className="viewer__pagenum">
                  Page {pageIndex + 1} of {pageCount}
                </span>
              </div>
            );
          })}
      </Document>
    </div>
  );
}
