import { useMemo, useState } from "react";
import { Document, Page, pdfjs } from "react-pdf";

import { entityLabel } from "../lib/entities.js";
import "./PdfViewer.css";
import { useElementWidth } from "../lib/useElementWidth.js";

pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  "pdfjs-dist/build/pdf.worker.min.mjs",
  import.meta.url,
).toString();

const PAGE_MAX_WIDTH = 720;

export default function PdfViewer({ url, findings, selectedId, onSelect }) {
  const [containerRef, containerWidth] = useElementWidth();
  const pageWidth = Math.min(PAGE_MAX_WIDTH, Math.floor(containerWidth));
  const [pageCount, setPageCount] = useState(0);
  const [sizes, setSizes] = useState({}); // page index -> size in PDF points
  const [error, setError] = useState("");

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

  return (
    <div className="viewer" ref={containerRef}>
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
