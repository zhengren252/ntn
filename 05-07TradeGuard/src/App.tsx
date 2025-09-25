import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import Home from "@/pages/Home";
import MasterControl from "@/pages/MasterControl";
import TraderWorkstation from "@/pages/TraderWorkstation";
import RiskManagement from "@/pages/RiskManagement";
import FinanceManagement from "@/pages/FinanceManagement";
import SystemConfiguration from "@/pages/SystemConfiguration";
import MonitoringDashboard from "@/pages/MonitoringDashboard";

export default function App() {
  return (
    <Router>
      <div className="min-h-screen bg-gray-100">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/master" element={<MasterControl />} />
          <Route path="/trader" element={<TraderWorkstation />} />
          <Route path="/risk" element={<RiskManagement />} />
          <Route path="/finance" element={<FinanceManagement />} />
          <Route path="/config" element={<SystemConfiguration />} />
          <Route path="/dashboard" element={<MonitoringDashboard />} />
        </Routes>
      </div>
    </Router>
  );
}
