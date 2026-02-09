import React, { useEffect, useState } from "react";
import {
  RefreshCw,
  AlertCircle,
  Activity,
  Settings,
  Database
} from "lucide-react";

/* ============================
   API
============================ */

const API_BASE_URL = "http://localhost:5000/api";

/* ============================
   Types
============================ */

interface SystemHealth {
  database: string;
  dbConnections: number;
  crawler: string;
  activeCrawlers: number;
  tor: string;
  torCircuits: number;
}

interface CrawlerConfig {
  crawlRate: number;
  circuitRotation: number;
  timeout: number;
}

/* ============================
   Component
============================ */

const SystemSettings: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [systemHealth, setSystemHealth] = useState<SystemHealth | null>(null);
  const [crawlerConfig, setCrawlerConfig] = useState<CrawlerConfig>({
    crawlRate: 30,
    circuitRotation: 10,
    timeout: 30
  });

  /* ============================
     API Calls
  ============================ */

  const fetchSystemHealth = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE_URL}/system/health`);
      const json = await res.json();
      if (!json.success) throw new Error(json.error);
      setSystemHealth(json.data);
    } catch {
      setError("Failed to load system health");
    } finally {
      setLoading(false);
    }
  };

  const updateCrawlerConfig = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/system/config`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(crawlerConfig)
      });
      const json = await res.json();
      if (!json.success) throw new Error(json.error);
      alert("Configuration updated successfully");
    } catch {
      alert("Failed to update configuration");
    }
  };

  useEffect(() => {
    fetchSystemHealth();
  }, []);

  /* ============================
     Render
  ============================ */

  return (
    <div className="space-y-6 h-full">

      {/* ================= Header ================= */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-white">System Settings</h2>
          <p className="text-gray-400">System configuration and monitoring</p>
        </div>
        <button
          onClick={fetchSystemHealth}
          disabled={loading}
          className="px-4 py-2 bg-cyan-600 hover:bg-cyan-700 rounded-lg flex items-center gap-2"
        >
          <RefreshCw size={18} className={loading ? "animate-spin" : ""} />
          Refresh
        </button>
      </div>

      {error && (
        <div className="bg-red-900/40 border border-red-600 text-red-200 p-4 rounded-lg flex gap-2">
          <AlertCircle size={18} />
          {error}
        </div>
      )}

      {/* ================= System Health ================= */}
      {systemHealth && (
        <div className="bg-gray-800/60 p-6 rounded-xl border border-gray-700">
          <div className="flex items-center gap-2 mb-6">
            <Activity className="text-cyan-400" />
            <h3 className="text-lg font-semibold text-cyan-400">
              System Health
            </h3>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {[
              ["Database", systemHealth.database, systemHealth.dbConnections],
              ["Crawler", systemHealth.crawler, systemHealth.activeCrawlers],
              ["Tor Network", systemHealth.tor, systemHealth.torCircuits]
            ].map(([label, status, value]) => (
              <div
                key={label}
                className="bg-gray-900/40 p-4 rounded-lg border border-gray-700"
              >
                <div className="flex justify-between mb-2">
                  <span className="text-gray-400">{label}</span>
                  <span
                    className={`text-xs px-2 py-1 rounded ${
                      status === "healthy" || status === "connected" || status === "active"
                        ? "bg-green-900/40 text-green-400"
                        : "bg-red-900/40 text-red-400"
                    }`}
                  >
                    {status}
                  </span>
                </div>
                <p className="text-sm text-gray-400">
                  Value: <span className="text-gray-300">{value}</span>
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ================= Crawler Config ================= */}
      <div className="bg-gray-800/60 p-6 rounded-xl border border-gray-700">
        <div className="flex items-center gap-2 mb-6">
          <Settings className="text-cyan-400" />
          <h3 className="text-lg font-semibold text-cyan-400">
            Crawler Configuration
          </h3>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {[
            ["Crawl Rate", "crawlRate"],
            ["Circuit Rotation", "circuitRotation"],
            ["Timeout", "timeout"]
          ].map(([label, key]) => (
            <input
              key={key}
              type="number"
              value={(crawlerConfig as any)[key]}
              onChange={(e) =>
                setCrawlerConfig({
                  ...crawlerConfig,
                  [key]: Number(e.target.value)
                })
              }
              placeholder={label}
              className="input"
            />
          ))}
        </div>

        <button
          onClick={updateCrawlerConfig}
          className="mt-6 px-6 py-2 bg-cyan-600 hover:bg-cyan-700 rounded-lg"
        >
          Update Configuration
        </button>
      </div>

      {/* ================= System Info ================= */}
      <div className="bg-gray-800/60 p-6 rounded-xl border border-gray-700">
        <div className="flex items-center gap-2 mb-4">
          <Database className="text-cyan-400" />
          <h3 className="text-lg font-semibold text-cyan-400">
            System Information
          </h3>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div>Version: <span className="text-gray-300">v1.0.0</span></div>
          <div>Uptime: <span className="text-gray-300">24 days</span></div>
          <div>Data: <span className="text-gray-300">~2.4 GB</span></div>
          <div>Status: <span className="text-green-400">Operational</span></div>
        </div>
      </div>

    </div>
  );
};

export default SystemSettings;
