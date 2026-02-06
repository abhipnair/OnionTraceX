import React, { useState, useEffect } from "react";
import {
  Play,
  RefreshCw,
  Square,
  Link2,
  Search,
  UploadCloud
} from "lucide-react";

const CrawlerControlPanel: React.FC = () => {
  /* ---------------- STATE ---------------- */
  const [keywords, setKeywords] = useState("");
  const [manualUrls, setManualUrls] = useState("");
  const [seedFile, setSeedFile] = useState<File | null>(null);

  const [crawlDepth, setCrawlDepth] = useState(3);
  const [politeDelay, setPoliteDelay] = useState(2.0);

  const [status, setStatus] = useState("idle");
  const [progress, setProgress] = useState(0);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  const API = "http://localhost:5000/api/crawler";

  /* ---------------- START CRAWLER ---------------- */
  const startCrawler = async () => {
    setLoading(true);
    setMessage("Initializing crawler...");

    try {
      let body: BodyInit;
      let headers: Record<string, string> = {};

      const keywordList = keywords
        .split(",")
        .map(k => k.trim())
        .filter(Boolean);

      const urlList = manualUrls
        .split(/\n|,/)
        .map(u => u.trim())
        .filter(Boolean);

      if (seedFile) {
        // -------- multipart/form-data --------
        const form = new FormData();
        form.append("keywords", keywordList.join(","));
        form.append("manual_urls", urlList.join("\n"));
        form.append("crawl_depth", String(crawlDepth));
        form.append("polite_delay", String(politeDelay));
        form.append("seed_file", seedFile);
        body = form;
      } else {
        // -------- JSON --------
        headers["Content-Type"] = "application/json";
        body = JSON.stringify({
          keywords: keywordList,
          manual_urls: urlList,
          crawl_depth: crawlDepth,
          polite_delay: politeDelay
        });
      }

      const res = await fetch(`${API}/start`, {
        method: "POST",
        headers,
        body
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.message || "Failed to start crawler");

      setStatus("starting");
      setMessage(data.message || "Crawler started");

    } catch (e: any) {
      setStatus("error");
      setMessage(e.message || "Crawler failed");
    } finally {
      setLoading(false);
    }
  };

  /* ---------------- STOP ---------------- */
  const stopCrawler = async () => {
    await fetch(`${API}/stop`, { method: "POST" });
    setStatus("stopped");
    setMessage("Crawler stopped manually");
  };

  /* ---------------- STATUS POLL ---------------- */
  const pollStatus = async () => {
    try {
      const res = await fetch(`${API}/status`);
      const data = await res.json();
      setStatus(data.status);
      setProgress(data.progress);
      setMessage(data.message);
    } catch {}
  };

  useEffect(() => {
    const i = setInterval(pollStatus, 4000);
    return () => clearInterval(i);
  }, []);

  /* ---------------- UI ---------------- */
  return (
    <div className="space-y-8">

      {/* HEADER */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-white">
            Crawler Control Panel
          </h2>
          <p className="text-gray-400">
            Keyword-based discovery and direct onion analysis
          </p>
        </div>
        <button
          onClick={pollStatus}
          className="px-4 py-2 bg-cyan-600 rounded-lg flex items-center gap-2"
        >
          <RefreshCw size={16} /> Refresh
        </button>
      </div>

      {/* INPUT SECTIONS */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

        {/* KEYWORDS */}
        <div className="bg-gray-800/60 p-6 rounded-xl border border-gray-700 space-y-3">
          <div className="flex items-center gap-2 text-cyan-400">
            <Search size={18} />
            <h3 className="font-semibold">Keyword Discovery</h3>
          </div>

          <textarea
            value={keywords}
            onChange={e => setKeywords(e.target.value)}
            placeholder="drugs, marketplace, forum, escrow"
            className="w-full h-28 p-4 bg-gray-900 border border-gray-600 rounded-lg text-white"
          />

          <p className="text-xs text-gray-400">
            Used for search-engine-based seed discovery
          </p>
        </div>

        {/* MANUAL URLS */}
        <div className="bg-gray-800/60 p-6 rounded-xl border border-gray-700 space-y-3">
          <div className="flex items-center gap-2 text-purple-400">
            <Link2 size={18} />
            <h3 className="font-semibold">Manual Onion URLs</h3>
          </div>

          <textarea
            value={manualUrls}
            onChange={e => setManualUrls(e.target.value)}
            placeholder={`http://example1.onion\nhttp://example2.onion`}
            className="w-full h-28 p-4 bg-gray-900 border border-gray-600 rounded-lg text-white"
          />

          <p className="text-xs text-gray-400">
            Direct targets injected into crawler queue
          </p>
        </div>
      </div>

      {/* SEED FILE */}
      <div className="bg-gray-800/60 p-6 rounded-xl border border-dashed border-gray-600">
        <div className="flex items-center gap-3 text-yellow-400 mb-3">
          <UploadCloud size={20} />
          <h3 className="font-semibold">Seed File Import</h3>
        </div>

        <label className="block cursor-pointer">
          <input
            type="file"
            className="hidden"
            onChange={e => setSeedFile(e.target.files?.[0] || null)}
          />
          <div className="p-4 bg-gray-900 rounded-lg border border-gray-700 text-center hover:border-yellow-500">
            {seedFile ? (
              <span className="text-yellow-400 font-mono">
                {seedFile.name}
              </span>
            ) : (
              <span className="text-gray-400">
                Upload .txt file with onion URLs or keywords
              </span>
            )}
          </div>
        </label>
      </div>

      {/* PARAMETERS */}
      <div className="grid grid-cols-2 gap-6 bg-gray-800/50 p-6 rounded-xl border border-gray-700">
        <div>
          <label className="text-gray-400 text-sm">
            Crawl Depth ({crawlDepth})
          </label>
          <input
            type="range"
            min="1"
            max="10"
            value={crawlDepth}
            onChange={e => setCrawlDepth(+e.target.value)}
            className="w-full accent-cyan-500"
          />
        </div>

        <div>
          <label className="text-gray-400 text-sm">
            Polite Delay ({politeDelay}s)
          </label>
          <input
            type="range"
            min="0.5"
            max="10"
            step="0.5"
            value={politeDelay}
            onChange={e => setPoliteDelay(+e.target.value)}
            className="w-full accent-cyan-500"
          />
        </div>
      </div>

      {/* ACTIONS */}
      <div className="grid grid-cols-2 gap-4">
        <button
          onClick={startCrawler}
          disabled={loading || (!keywords && !manualUrls && !seedFile)}
          className="py-3 bg-cyan-600 rounded-lg font-semibold flex justify-center gap-2"
        >
          {loading ? <RefreshCw className="animate-spin" /> : <Play />}
          Start Crawl
        </button>

        <button
          onClick={stopCrawler}
          disabled={status !== "running"}
          className="py-3 bg-red-600 rounded-lg font-semibold flex justify-center gap-2"
        >
          <Square />
          Stop
        </button>
      </div>

      {/* STATUS */}
      <div className="bg-gray-800/50 p-5 rounded-xl border border-gray-700">
        <div className="flex justify-between mb-2">
          <span className="text-gray-400 text-sm">Status</span>
          <span className="text-cyan-400 font-semibold">
            {status.toUpperCase()}
          </span>
        </div>
        <div className="h-3 bg-gray-900 rounded-full">
          <div
            className="h-3 bg-cyan-500"
            style={{ width: `${progress}%` }}
          />
        </div>
        <p className="text-gray-400 text-sm mt-2">{message}</p>
      </div>

    </div>
  );
};

export default CrawlerControlPanel;
