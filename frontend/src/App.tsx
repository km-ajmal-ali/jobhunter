import { Routes, Route } from "react-router-dom";
import Navbar from "./components/Navbar";
import Home from "./pages/Home";
import JobDetail from "./pages/JobDetail";
import AdsterraBannerSlot from "./components/AdsterraBannerSlot";
import useIsMobile from "./hooks/useIsMobile";

/**
 * Root application component.
 * Sets up routing and the shared layout (navbar + main content area).
 */
export default function App() {
  const isMobile = useIsMobile();

  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />
      <main className="flex-1">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/jobs/:id" element={<JobDetail />} />
        </Routes>
      </main>
      <div className="flex justify-center py-4">
        {isMobile ? (
          <AdsterraBannerSlot adKey="ac137bf3f4da05de83e37f2328f6a4e2" width={320} height={50} />
        ) : (
          <AdsterraBannerSlot adKey="5cee582654db64e6aeba2c26aa51caa3" width={728} height={90} />
        )}
      </div>
      <footer className="border-t border-gray-200 bg-white py-6 text-center text-sm text-gray-500">
        <p>&copy; {new Date().getFullYear()} JobHunter. All job listings are property of their respective sources.</p>
      </footer>
    </div>
  );
}
