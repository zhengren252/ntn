import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import Home from "@/pages/Home";
import Dashboard from "@/pages/Dashboard";
import FundManagement from "@/pages/FundManagement";
import CircuitBreaker from "@/pages/CircuitBreaker";
import MemoryNetwork from "@/pages/MemoryNetwork";
import SystemConfig from "@/pages/SystemConfig";

export default function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/fund-management" element={<FundManagement />} />
        <Route path="/circuit-breaker" element={<CircuitBreaker />} />
        <Route path="/memory-network" element={<MemoryNetwork />} />
        <Route path="/system-config" element={<SystemConfig />} />
        <Route path="/other" element={<div className="text-center text-xl">Other Page - Coming Soon</div>} />
      </Routes>
    </Router>
  );
}
