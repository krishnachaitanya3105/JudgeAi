import {
  Highlight,
  PdfHighlighter,
  PdfLoader,
  Popup,
  Tip,
} from 'react-pdf-highlighter';
import 'react-pdf-highlighter/dist/style.css';

const WORKER = 'https://unpkg.com/pdfjs-dist@4.4.168/build/pdf.worker.min.mjs';

function HighlightPopup({ comment }) {
  if (!comment?.text) return null;
  return (
    <div style={{ fontSize: 12, padding: '4px 8px', maxWidth: 220 }}>
      <span aria-hidden>{comment.emoji}</span> {comment.text}
    </div>
  );
}

/**
 * Highlights from API (`pdf_highlights`) use Comment.text DIRECTIVE | DEADLINE | PARTY → tint via CSS hooks.
 */
export default function JudgmentPdfPanel({ url, highlights = [], height = 460 }) {
  const classFor = (cmt) =>
    ({
      DIRECTIVE: 'judgeai-hl-directive',
      DEADLINE: 'judgeai-hl-deadline',
      PARTY: 'judgeai-hl-party',
    })[String(cmt?.text || '').trim()] || 'judgeai-hl-generic';

  const legend = (
    <div className="text-caption" style={{ marginTop: 10, display: 'flex', flexWrap: 'wrap', gap: '8px 14px', alignItems: 'center', color: 'var(--text-muted)' }}>
      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
        <span aria-hidden>🟨</span> Directive
      </span>
      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
        <span aria-hidden>🟦</span> Deadline / date cues
      </span>
      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
        <span aria-hidden>🟩</span> Party names / labels
      </span>
      <span style={{ opacity: 0.85 }}>Drag-select tip dismisses quickly by design.</span>
    </div>
  );

  if (!highlights?.length) {
    return (
      <div>
        <iframe
          title="judgment-pdf"
          src={url}
          style={{
            width: '100%',
            height,
            borderRadius: 'var(--radius-md)',
            border: '1px solid var(--border-default)',
          }}
        />
        {legend}
        <p className="text-caption" style={{ marginTop: 6, color: 'var(--text-muted)' }}>
          No layout highlights available for this case yet. Open once after extraction/backfill to generate overlays.
        </p>
      </div>
    );
  }

  return (
    <div style={{ position: 'relative' }}>
      <style>{`
        .judgeai-hl-directive .Highlight__parts .Highlight__part { background: rgba(253,224,71,0.45) !important; }
        .judgeai-hl-deadline .Highlight__parts .Highlight__part { background: rgba(147,197,253,0.55) !important; }
        .judgeai-hl-party .Highlight__parts .Highlight__part { background: rgba(134,239,172,0.5) !important; }
        .judgeai-hl-generic .Highlight__parts .Highlight__part { background: rgba(250,232,255,0.45) !important; }
      `}</style>

      <div style={{ border: '1px solid var(--border-default)', borderRadius: 'var(--radius-md)', overflow: 'auto', height }}>
        <PdfLoader url={url} workerSrc={WORKER} beforeLoad={<div style={{ padding: 24, color: 'var(--text-muted)' }}>Loading judgment PDF…</div>}>
          {(pdfDocument) => (
            <PdfHighlighter
              pdfDocument={pdfDocument}
              pdfScaleValue="auto"
              scrollRef={() => {}}
              onScrollChange={() => {}}
              onSelectionFinished={(position, content, hideTip) => (
                <Tip onOpen={() => hideTip()} onConfirm={() => hideTip()} />
              )}
              highlightTransform={(highlight, index, setTip, hideTip, viewportToScaled, screenshot, isScrolledTo) => {
                const hlClass = classFor(highlight.comment);
                return (
                  <Popup
                    key={index}
                    onMouseOver={(popupContent) => setTip(highlight, () => popupContent)}
                    onMouseOut={hideTip}
                  >
                    <div className={hlClass}>
                      <Highlight
                        position={highlight.position}
                        comment={highlight.comment}
                        isScrolledTo={isScrolledTo}
                      />
                    </div>
                    <HighlightPopup comment={highlight.comment} />
                  </Popup>
                );
              }}
              highlights={highlights}
            />
          )}
        </PdfLoader>
      </div>
      {legend}
    </div>
  );
}
