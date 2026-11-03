/**
 * Adsterra ad slot component.
 *
 * Adsterra ad units work differently from AdSense: each unit ships its own
 * <script> tag that looks for a container div with a specific ID and
 * renders the ad into it. Since React won't execute a raw <script> tag
 * placed in JSX, this component injects it into the DOM on mount instead.
 *
 * Usage:
 *   <AdsterraSlot
 *     containerId="eae505e7ed90a116a0ce10cedc3824ba"
 *     scriptSrc="https://bauval.org/21/eae505e7ed90a116a0ce10cedc3824ba"
 *   />
 */
import { useEffect, useRef } from "react";

interface AdsterraSlotProps {
  /** The ID suffix from Adsterra's <div id="container-..."> snippet. */
  containerId: string;
  /** The ad unit's <script src="..."> URL from Adsterra. */
  scriptSrc: string;
  /** Additional CSS classes for the container. */
  className?: string;
}

export default function AdsterraSlot({ containerId, scriptSrc, className = "" }: AdsterraSlotProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const script = document.createElement("script");
    script.async = true;
    script.dataset.cfasync = "false";
    script.src = scriptSrc;
    container.appendChild(script);

    return () => {
      container.innerHTML = "";
    };
  }, [scriptSrc]);

  return <div id={`container-${containerId}`} ref={containerRef} className={className} />;
}
