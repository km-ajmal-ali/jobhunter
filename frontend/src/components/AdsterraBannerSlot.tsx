/**
 * Adsterra "banner" ad slot (the `atOptions` + script-tag format).
 *
 * This format relies on a global `atOptions` variable and a script that
 * calls `document.write` to inject its iframe. Running that directly on
 * the page is unsafe in a React SPA — document.write() after initial load
 * can wipe the page. Instead, this renders the ad inside its own isolated
 * iframe, so the ad script's document.write only touches that iframe's
 * document, never the host page.
 *
 * Usage:
 *   <AdsterraBannerSlot adKey="5cee582654db64e6aeba2c26aa51caa3" width={728} height={90} />
 */
import { useEffect, useRef } from "react";

interface AdsterraBannerSlotProps {
  /** The 'key' value from Adsterra's atOptions snippet. */
  adKey: string;
  width: number;
  height: number;
  /** The 'format' value from Adsterra's atOptions snippet. */
  format?: string;
  className?: string;
}

export default function AdsterraBannerSlot({
  adKey,
  width,
  height,
  format = "iframe",
  className = "",
}: AdsterraBannerSlotProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const iframe = document.createElement("iframe");
    iframe.style.border = "none";
    iframe.style.overflow = "hidden";
    iframe.width = String(width);
    iframe.height = String(height);
    container.appendChild(iframe);

    const doc = iframe.contentWindow?.document;
    if (doc) {
      doc.open();
      doc.write(`<!DOCTYPE html>
<html>
  <head><style>body{margin:0;padding:0;}</style></head>
  <body>
    <script>
      atOptions = {
        'key': '${adKey}',
        'format': '${format}',
        'height': ${height},
        'width': ${width},
        'params': {}
      };
    </script>
    <script src="https://bauval.org/22/${adKey}"></script>
  </body>
</html>`);
      doc.close();
    }

    return () => {
      container.innerHTML = "";
    };
  }, [adKey, width, height, format]);

  return (
    <div
      ref={containerRef}
      className={`flex justify-center ${className}`}
      style={{ minHeight: height }}
    />
  );
}
