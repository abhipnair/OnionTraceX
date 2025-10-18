import React, { useState, useEffect } from "react";
import { Play, RefreshCw, Square } from "lucide-react";

const CrawlerControlPanel: React.FC = () => {
  const [crawlerKeywords, setCrawlerKeywords] = useState("");
  const [crawlerFile, setCrawlerFile] = useState<File | null>(null);
  const [crawlerStatus, setCrawlerStatus] = useState("idle");
  const [crawlerProgress, setCrawlerProgress] = useState(0);
  const [crawlerMessage, setCrawlerMessage] = useState("");
  const [crawlerLoading, setCrawlerLoading] = useState(false);

  // adjustable crawler parameters
  const [seedDepth, setSeedDepth] = useState(2);
  const [pages, setPages] = useState(5);
  const [crawlDepth, setCrawlDepth] = useState(3);
  const [politeDelay, setPoliteDelay] = useState(2.0);

  const API_BASE = "http://localhost:5000/api/crawler";

  // --- API Functions ---
  const handleStartCrawler = async () => {
    setCrawlerLoading(true);
    setCrawlerMessage("Starting crawler...");

    try {
      // build body or form data based on file
      let body: BodyInit;
      let headers: Record<string, string> = {};

      if (crawlerFile) {
        const formData = new FormData();
        formData.append("keywords", crawlerKeywords);
        formData.append("seed_depth", String(seedDepth));
        formData.append("pages", String(pages));
        formData.append("crawl_depth", String(crawlDepth));
        formData.append("polite_delay", String(politeDelay));
        formData.append("seed_file", crawlerFile);
        body = formData;
      } else {
        headers["Content-Type"] = "application/json";
        body = JSON.stringify({
          keywords: crawlerKeywords.split(",").map(k => k.trim()).filter(Boolean),
          seed_depth: seedDepth,
          pages,
          crawl_depth: crawlDepth,
          polite_delay: politeDelay,
        });
      }

      const res = await fetch(`${API_BASE}/start`, {
        method: "POST",
        headers,
        body,
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.message || "Failed to start crawler");

      setCrawlerStatus(data.status || "starting");
      setCrawlerMessage(data.message || "Crawler started successfully!");
    } catch (err: any) {
      console.error(err);
      setCrawlerStatus("error");
      setCrawlerMessage(err.message || "Failed to start crawler");
    } finally {
      setCrawlerLoading(false);
    }
  };

  const checkCrawlerStatus = async () => {
    try {
      const res = await fetch(`${API_BASE}/status`);
      const data = await res.json();
      setCrawlerStatus(data.status);
      setCrawlerProgress(data.progress);
      setCrawlerMessage(data.message);
    } catch (err) {
      console.error("Status check error:", err);
    }
  };

  const handleStopCrawler = async () => {
    try {
      const res = await fetch(`${API_BASE}/stop`, { method: "POST" });
      const data = await res.json();
      setCrawlerStatus(data.status);
      setCrawlerMessage(data.message || "Crawler stopped manually.");
    } catch (err) {
      console.error("Stop crawler error:", err);
    }
  };

  useEffect(() => {
    const interval = setInterval(checkCrawlerStatus, 5000);
    return () => clearInterval(interval);
  }, []);

  // --- Render UI ---
  return (
    <div className="space-y-6 h-full">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-white">Crawler Control Panel</h2>
          <p className="text-gray-400">Launch, monitor, and manage crawler jobs</p>
        </div>
        <button
          onClick={checkCrawlerStatus}
          disabled={crawlerLoading}
          className="px-4 py-2 bg-cyan-600 hover:bg-cyan-700 rounded-lg flex items-center gap-2 disabled:opacity-50 transition-colors"
        >
          <RefreshCw size={18} className={crawlerLoading ? "animate-spin" : ""} />
          Refresh
        </button>
      </div>

      {/* Input Section */}
      <div className="bg-gray-800/50 backdrop-blur-sm p-6 rounded-xl border border-gray-700/50 space-y-6">
        {/* Keyword and file inputs */}
        <div>
          <label className="block text-gray-400 mb-2 font-medium">Search Keywords</label>
          <input
            type="text"
            value={crawlerKeywords}
            onChange={(e) => setCrawlerKeywords(e.target.value)}
            placeholder="Enter comma-separated keywords (e.g., drugs, hacking, forum)"
            className="w-full px-4 py-3 bg-gray-900/50 border border-gray-600 rounded-lg text-white focus:border-cyan-500 focus:ring-2 focus:ring-cyan-500/20 transition-all"
          />
        </div>

        <div>
          <label className="block text-gray-400 mb-2 font-medium">Seed File (optional)</label>
          <input
            type="file"
            onChange={(e) => setCrawlerFile(e.target.files ? e.target.files[0] : null)}
            className="w-full text-gray-300 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-cyan-600/20 file:text-cyan-300 hover:file:bg-cyan-600/30 transition-all"
          />
          {crawlerFile && (
            <p className="text-sm text-gray-400 mt-2">
              Selected: <span className="text-cyan-400">{crawlerFile.name}</span>
            </p>
          )}
        </div>

        {/* Parameter sliders */}
        <div className="grid grid-cols-2 gap-6">
          <div>
            <label className="block text-gray-400 mb-2 font-medium">
              Seed Depth ({seedDepth})
            </label>
            <input
              type="range"
              min="1"
              max="15"
              step="1"
              value={seedDepth}
              onChange={(e) => setSeedDepth(Number(e.target.value))}
              className="w-full accent-cyan-500"
            />
          </div>

          <div>
            <label className="block text-gray-400 mb-2 font-medium">
              Crawl Depth ({crawlDepth})
            </label>
            <input
              type="range"
              min="1"
              max="10"
              step="1"
              value={crawlDepth}
              onChange={(e) => setCrawlDepth(Number(e.target.value))}
              className="w-full accent-cyan-500"
            />
          </div>

          <div>
            <label className="block text-gray-400 mb-2 font-medium">
              Pages ({pages})
            </label>
            <input
              type="range"
              min="1"
              max="25"
              step="1"
              value={pages}
              onChange={(e) => setPages(Number(e.target.value))}
              className="w-full accent-cyan-500"
            />
          </div>

          <div>
            <label className="block text-gray-400 mb-2 font-medium">
              Polite Delay ({politeDelay}s)
            </label>
            <input
              type="range"
              min="0.5"
              max="10"
              step="0.5"
              value={politeDelay}
              onChange={(e) => setPoliteDelay(Number(e.target.value))}
              className="w-full accent-cyan-500"
            />
          </div>
        </div>

        {/* Action Buttons */}
        <div className="grid grid-cols-2 gap-4">
          <button
            onClick={handleStartCrawler}
            disabled={crawlerLoading || (!crawlerKeywords && !crawlerFile)}
            className="py-3 bg-cyan-600 hover:bg-cyan-700 rounded-lg font-semibold text-white flex justify-center items-center gap-2 disabled:opacity-50 transition-all"
          >
            {crawlerLoading ? <RefreshCw className="animate-spin" size={18} /> : <Play size={18} />}
            {crawlerLoading ? "Starting..." : "Start Crawler"}
          </button>

          <button
            onClick={handleStopCrawler}
            disabled={crawlerStatus !== "running"}
            className="py-3 bg-red-600 hover:bg-red-700 rounded-lg font-semibold text-white flex justify-center items-center gap-2 disabled:opacity-50 transition-all"
          >
            <Square size={18} />
            Stop Crawler
          </button>
        </div>
      </div>

      {/* Progress Section */}
      <div className="bg-gray-800/50 backdrop-blur-sm p-6 rounded-xl border border-gray-700/50">
        <div className="flex justify-between items-center mb-2">
          <span className="text-gray-400 text-sm font-medium">Crawler Status</span>
          <span
            className={`text-sm font-semibold ${
              crawlerStatus === "completed"
                ? "text-green-400"
                : crawlerStatus === "running"
                ? "text-cyan-400"
                : crawlerStatus === "starting"
                ? "text-yellow-400"
                : crawlerStatus === "error"
                ? "text-red-400"
                : "text-gray-400"
            }`}
          >
            {crawlerStatus.charAt(0).toUpperCase() + crawlerStatus.slice(1)}
          </span>
        </div>
        <div className="w-full bg-gray-900/50 rounded-full h-3 overflow-hidden border border-gray-700/50">
          <div
            className={`h-3 transition-all duration-500 ${
              crawlerStatus === "error" ? "bg-red-500" : "bg-cyan-500"
            }`}
            style={{ width: `${crawlerProgress}%` }}
          />
        </div>
        <p className="text-gray-400 text-sm mt-2">Progress: {crawlerProgress}%</p>
      </div>

      {/* Message / Logs */}
      {crawlerMessage && (
        <div
          className={`p-4 rounded-lg font-mono text-sm border ${
            crawlerStatus === "error"
              ? "bg-red-900/50 border-red-500 text-red-200"
              : "bg-gray-900/50 border-gray-700/50 text-gray-300"
          }`}
        >
          {crawlerMessage}
        </div>
      )}
    </div>
  );
};

export default CrawlerControlPanel;
