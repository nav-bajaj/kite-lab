import { ScriptPanel } from "./components/ScriptPanel";
import { QuickActions } from "./components/QuickActions";

export default function App() {
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-6 py-6">
          <h1 className="text-gray-900">Stock Analysis Control Panel</h1>
          <p className="text-gray-500 mt-1">Execute Python scripts and manage your analysis workflow</p>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-8 space-y-6">
        {/* Script Panels */}
        <ScriptPanel
          title="Market Data Fetcher"
          description="Download historical market data for specified stocks"
          scriptName="fetch_market_data.py"
          arguments={[
            { name: "ticker", placeholder: "AAPL", type: "text" },
            { name: "start_date", placeholder: "2024-01-01", type: "date" },
            { name: "end_date", placeholder: "2024-12-31", type: "date" },
          ]}
          accentColor="blue"
        />

        <ScriptPanel
          title="Technical Indicators"
          description="Calculate RSI, MACD, and moving averages for stock analysis"
          scriptName="calculate_indicators.py"
          arguments={[
            { name: "ticker", placeholder: "GOOGL", type: "text" },
            { name: "period", placeholder: "14", type: "number" },
            { name: "indicators", placeholder: "RSI,MACD,SMA", type: "text" },
          ]}
          accentColor="purple"
        />

        <ScriptPanel
          title="Portfolio Backtester"
          description="Run backtesting simulations on your trading strategies"
          scriptName="backtest_strategy.py"
          arguments={[
            { name: "strategy", placeholder: "momentum", type: "text" },
            { name: "capital", placeholder: "100000", type: "number" },
            { name: "benchmark", placeholder: "SPY", type: "text" },
          ]}
          accentColor="blue"
        />

        <ScriptPanel
          title="Risk Analysis"
          description="Generate risk metrics and portfolio volatility reports"
          scriptName="analyze_risk.py"
          arguments={[
            { name: "portfolio", placeholder: "portfolio.csv", type: "text" },
            { name: "confidence_level", placeholder: "0.95", type: "number" },
          ]}
          accentColor="purple"
        />
      </main>

      {/* Bottom Quick Actions */}
      <QuickActions />
    </div>
  );
}
