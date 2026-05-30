import { Routes, Route } from "react-router-dom";
import Navbar from "./components/Navbar";
import Home from "./pages/Home";
import JobDetail from "./pages/JobDetail";

/**
 * Root application component.
 * Sets up routing and the shared layout (navbar + main content area).
 */
export default function App() {
  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />
      <main className="flex-1">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/jobs/:id" element={<JobDetail />} />
        </Routes>
      </main>
      <footer className="border-t border-gray-200 bg-white py-6 text-center text-sm text-gray-500">
        <p>&copy; {new Date().getFullYear()} JobHunter. All job listings are property of their respective sources.</p>
      </footer>
    </div>
  );
}
