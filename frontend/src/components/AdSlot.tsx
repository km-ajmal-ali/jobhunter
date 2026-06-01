/**
 * AdSense ad slot component.
 *
 * Renders a container div that Google AdSense auto-fills based on the
 * data-ad-slot and data-ad-format attributes.
 *
 * Usage:
 *   <AdSlot slot="1234567890" format="auto" className="my-4" />
 *
 * IMPORTANT:
 *   1. Replace "ca-pub-REPLACE_WITH_YOUR_ID" in index.html with your AdSense publisher ID.
 *   2. Replace the data-ad-slot values below with actual ad unit IDs from your AdSense account.
 *   3. AdSense may take 24-48 hours to show live ads after verification.
 */
import { useEffect, useRef } from "react";

interface AdSlotProps {
  /** Your AdSense ad unit slot ID (numeric). */
  slot: string;
  /** Ad format: "auto", "rectangle", "horizontal", "vertical", etc. */
  format?: string;
  /** Whether this is a full-width responsive ad. */
  fullWidth?: boolean;
  /** Additional CSS classes for the container. */
  className?: string;
}

/**
 * Renders an AdSense ad unit.
 * Pushes a new ad request when the component mounts.
 */
export default function AdSlot({
  slot,
  format = "auto",
  fullWidth = true,
  className = "",
}: AdSlotProps) {
  const adRef = useRef<HTMLModElement>(null);

  useEffect(() => {
    // Push the ad to AdSense's queue
    try {
      // @ts-expect-error — AdSense injects `adsbygoogle` on the window
      (window.adsbygoogle = window.adsbygoogle || []).push({});
    } catch (e) {
      console.warn("AdSense push failed:", e);
    }
  }, []);

  return (
    <div className={`ad-container ${className}`}>
      <ins
        ref={adRef}
        className="adsbygoogle"
        style={{ display: "block" }}
        data-ad-client="ca-pub-6872881712264544"
        data-ad-slot={slot}
        data-ad-format={format}
        data-full-width-responsive={fullWidth ? "true" : "false"}
      />
    </div>
  );
}
