import { useEffect, useState } from "react";

/**
 * Tracks whether the viewport is below `breakpoint` px wide.
 * Used to pick a narrower ad unit on mobile instead of squishing a desktop-sized one.
 */
export default function useIsMobile(breakpoint = 640) {
  const [isMobile, setIsMobile] = useState(() => window.innerWidth < breakpoint);

  useEffect(() => {
    const mql = window.matchMedia(`(max-width: ${breakpoint - 1}px)`);
    const handler = (e: MediaQueryListEvent) => setIsMobile(e.matches);
    mql.addEventListener("change", handler);
    return () => mql.removeEventListener("change", handler);
  }, [breakpoint]);

  return isMobile;
}
