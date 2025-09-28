import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Home from '@/pages/Home';
import Strategy from '@/pages/Strategy';
import Trading from '@/pages/Trading';
import Risk from '@/pages/Risk';
import Data from '@/pages/Data';
import Finance from '@/pages/Finance';
import Monitor from '@/pages/Monitor';
import AiLab from '@/pages/AiLab';
import Review from '@/pages/Review';
import RiskRehearsal from '@/pages/RiskRehearsal';
import TradingReplay from '@/pages/TradingReplay';

export default function App() {
  return (
    <Router>
      {/* 跳转到主内容的无障碍快捷链接（键盘Tab可见） */}
      <a href="#main-content" className="skip-link">跳转到主内容</a>
      {/* 路由定义 */}
      <Routes>
        <Route path="/" element={<Home />} />
        
        {/* Dashboard路由组 */}
        <Route path="/strategy" element={<Strategy />} />
        <Route path="/trading" element={<Trading />} />
        <Route path="/risk" element={<Risk />} />
        <Route path="/data" element={<Data />} />
        <Route path="/finance" element={<Finance />} />
        <Route path="/monitor" element={<Monitor />} />
        
        {/* E2E测试路由 */}
        <Route path="/ai-lab" element={<AiLab />} />
        <Route path="/review" element={<Review />} />
        <Route path="/risk-rehearsal" element={<RiskRehearsal />} />
        <Route path="/trading-replay" element={<TradingReplay />} />
        
        <Route
          path="/other"
          element={
            <div className="text-center text-xl">Other Page - Coming Soon</div>
          }
        />
      </Routes>
    </Router>
  );
}
