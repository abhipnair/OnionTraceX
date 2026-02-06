import React, { useState, useEffect } from "react";
import { RefreshCw, Filter, Eye, Globe, Clock, X } from "lucide-react";

const API_BASE = "http://localhost:5000/api";

/* -------------------------------------------------
   SAFE JSON HANDLING
------------------------------------------------- */
const safeJsonArray = (value: any): string[] => {
  if (!value) return [];
  if (Array.isArray(value)) return value;
  if (typeof value === "string") {
    try {
      const parsed = JSON.parse(value);
      return Array.isArray(parsed) ? parsed : [];
    } catch {
      return [];
    }
  }
  return [];
};

/* -------------------------------------------------
   STATUS BADGES
------------------------------------------------- */
const STATUS_STYLES: Record<string, string> = {
  Alive: "bg-green-900/40 text-green-300 border border-green-500/40",
  Dead: "bg-red-900/40 text-red-300 border border-red-500/40",
  Timeout: "bg-yellow-900/40 text-yellow-300 border border-yellow-500/40",
};

/* -------------------------------------------------
   KEYWORD BADGES (EXTENSIBLE + SAFE)
------------------------------------------------- */
const DEFAULT_KEYWORD_STYLE =
  "bg-slate-800/60 text-slate-300 border border-slate-500/30";

const KEYWORD_COLORS: Record<string, string> = {
  drugs: "bg-purple-900/40 text-purple-300 border border-purple-500/40",
  fraud: "bg-red-900/40 text-red-300 border border-red-500/40",
  carding: "bg-orange-900/40 text-orange-300 border border-orange-500/40",
  hacking: "bg-blue-900/40 text-blue-300 border border-blue-500/40",
  malware: "bg-pink-900/40 text-pink-300 border border-pink-500/40",
  weapons: "bg-gray-800 text-gray-300 border border-gray-500/40",
  forum: "bg-cyan-900/40 text-cyan-300 border border-cyan-500/40",
  marketplace: "bg-indigo-900/40 text-indigo-300 border border-indigo-500/40",

  money: "bg-emerald-900/40 text-emerald-300 border border-emerald-500/40",
  mafia: "bg-rose-900/40 text-rose-300 border border-rose-500/40",
  finance: "bg-green-900/40 text-green-300 border border-green-500/40",

  other: "bg-gray-700 text-gray-300 border border-gray-500/40",
};

const keywordBadge = (kw?: string) => {
  if (!kw) return DEFAULT_KEYWORD_STYLE;
  const normalized = kw.trim().toLowerCase();
  return KEYWORD_COLORS[normalized] || DEFAULT_KEYWORD_STYLE;
};

/* =================================================
   MAIN COMPONENT
================================================= */
const SitesExplorer: React.FC = () => {
  const [sites, setSites] = useState<any[]>([]);
  const [cursor, setCursor] = useState<any>(null);
  const [hasMore, setHasMore] = useState(true);
  const [loading, setLoading] = useState(false);

  /* FILTERS */
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("all");
  const [keyword, setKeyword] = useState("");
  const [source, setSource] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");

  const [siteDetails, setSiteDetails] = useState<any>(null);

  /* -------------------------------------------------
     LOAD SITES (CURSOR PAGINATION)
  ------------------------------------------------- */
  const loadSites = async (reset = false) => {
    if (loading) return;
    setLoading(true);

    const params = new URLSearchParams({
      search,
      status,
      keyword,
      source,
      start_date: startDate,
      end_date: endDate,
      page_size: "25",
    });

    if (!reset && cursor) {
      params.set("cursor_last_seen", cursor.last_seen);
      params.set("cursor_site_id", cursor.site_id);
    }

    const res = await fetch(`${API_BASE}/sites?${params.toString()}`);
    const data = await res.json();

    if (data.success) {
      setSites(prev => (reset ? data.data : [...prev, ...data.data]));
      setCursor(data.next_cursor || null);
      setHasMore(Boolean(data.next_cursor));
    }

    setLoading(false);
  };

  /* APPLY FILTERS */
  const applyFilters = () => {
    setSites([]);
    setCursor(null);
    setHasMore(true);
    loadSites(true);
  };

  /* REFRESH */
  const refresh = () => {
    setSites([]);
    setCursor(null);
    setHasMore(true);
    loadSites(true);
  };

  /* INITIAL LOAD */
  useEffect(() => {
    loadSites(true);
    // eslint-disable-next-line
  }, []);

  const openSiteDetails = async (id: string) => {
    const res = await fetch(`${API_BASE}/site/${id}`);
    const data = await res.json();
    if (data.success) setSiteDetails(data.data);
  };

  return (
    <div className="space-y-6">

      {/* HEADER */}
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-white">Sites Explorer</h2>
        <button
          onClick={refresh}
          className="bg-cyan-600 px-4 py-2 rounded flex gap-2"
        >
          <RefreshCw size={18} /> Refresh
        </button>
      </div>

      {/* FILTER BAR */}
      <div className="bg-gray-800 p-4 rounded-xl flex flex-wrap gap-4 items-center">
        <input className="bg-gray-900 px-4 py-2 rounded w-64" placeholder="Search URL / Site ID" value={search} onChange={e => setSearch(e.target.value)} />
        <select className="bg-gray-900 px-4 py-2 rounded" value={status} onChange={e => setStatus(e.target.value)}>
          <option value="all">All Status</option>
          <option value="Alive">Alive</option>
          <option value="Dead">Dead</option>
          <option value="Timeout">Timeout</option>
        </select>
        <input className="bg-gray-900 px-4 py-2 rounded w-40" placeholder="Keyword" value={keyword} onChange={e => setKeyword(e.target.value)} />
        <input className="bg-gray-900 px-4 py-2 rounded w-40" placeholder="Source" value={source} onChange={e => setSource(e.target.value)} />
        <input type="date" className="bg-gray-900 px-3 py-2 rounded" value={startDate} onChange={e => setStartDate(e.target.value)} />
        <input type="date" className="bg-gray-900 px-3 py-2 rounded" value={endDate} onChange={e => setEndDate(e.target.value)} />
        <button onClick={applyFilters} className="bg-gray-700 px-4 py-2 rounded flex gap-2">
          <Filter size={16} /> Apply
        </button>
      </div>

      {/* TABLE */}
      <div className="bg-gray-800 rounded-xl overflow-x-auto">
        <table className="min-w-[1300px] w-full">
          <thead className="bg-gray-900">
            <tr>
              {["ID", "URL", "Keyword", "Status", "First Seen", "Last Seen", "Source", ""].map(h => (
                <th key={h} className="px-6 py-3 text-left text-cyan-400">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sites.map(site => (
              <tr key={site.id} className="border-t border-gray-700 hover:bg-gray-700/30">
                <td className="px-6 py-3 font-mono text-xs">{site.id.slice(0, 12)}…</td>
                <td className="px-6 py-3 font-mono truncate max-w-[350px]"><Globe size={14} className="inline mr-1" />{site.url}</td>
                <td className="px-6 py-3">
                  <span className={`px-3 py-1 rounded-full text-xs font-medium tracking-wide ${keywordBadge(site.category)}`}>
                    {site.category}
                  </span>
                </td>
                <td className="px-6 py-3">
                  <span className={`px-3 py-1 rounded-full text-xs ${STATUS_STYLES[site.status]}`}>
                    {site.status}
                  </span>
                </td>
                <td className="px-6 py-3 text-sm"><Clock size={14} className="inline mr-1" />{site.firstSeen}</td>
                <td className="px-6 py-3 text-sm">{site.lastSeen}</td>
                <td className="px-6 py-3">{site.source}</td>
                <td className="px-6 py-3">
                  <button onClick={() => openSiteDetails(site.id)} className="bg-cyan-600/20 p-2 rounded">
                    <Eye size={18} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* LOAD MORE */}
      {hasMore && (
        <div className="text-center">
          <button
            onClick={() => loadSites()}
            disabled={loading}
            className="bg-gray-700 px-6 py-2 rounded mt-4"
          >
            {loading ? "Loading…" : "Load More"}
          </button>
        </div>
      )}

      {/* DETAILS MODAL */}
      {siteDetails && <SiteDetailsModal data={siteDetails} onClose={() => setSiteDetails(null)} />}
    </div>
  );
};

export default SitesExplorer;


/* =================================================
   CLEAN DETAILS MODAL
================================================= */
const SiteDetailsModal = ({ data, onClose }: any) => (
  <div className="fixed inset-0 bg-black/80 flex justify-center items-center z-50">
    <div className="bg-gray-900 w-[90%] max-w-6xl rounded-xl max-h-[90vh] overflow-y-auto">

      <div className="p-6 flex justify-between border-b border-gray-700">
        <h3 className="text-xl font-bold text-cyan-400">Site Analysis</h3>
        <button onClick={onClose}><X /></button>
      </div>

      <div className="p-6 space-y-6">

        {/* SITE SUMMARY */}
        <div className="grid grid-cols-3 gap-6 bg-gray-800 p-4 rounded">
          <div>
            <div className="text-gray-400 text-sm">URL</div>
            <div className="font-mono break-all">{data.site.url}</div>
          </div>
          <div>
            <div className="text-gray-400 text-sm">Status</div>
            <div>{data.site.status}</div>
          </div>
          <div>
            <div className="text-gray-400 text-sm">Category</div>
            <div>{data.site.category}</div>
          </div>
        </div>

        {/* PAGES */}
        <div>
          <h4 className="text-cyan-400 mb-3">Pages ({data.pages.length})</h4>
          <div className="space-y-4">
            {data.pages.map((p: any) => (
              <div key={p.page_id} className="bg-gray-800 p-4 rounded">
                <div className="font-mono text-sm break-all">{p.url}</div>
                <div className="text-xs text-gray-400">{p.crawled_at}</div>

                {/* EMAILS */}
                {safeJsonArray(p.metadata?.emails).length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-2">
                    {safeJsonArray(p.metadata.emails).map(e => (
                      <span
                        key={e}
                        className="bg-green-900/30 text-green-300 px-2 py-1 rounded text-xs"
                      >
                        {e}
                      </span>
                    ))}
                  </div>
                )}

                {/* PGP */}
                {safeJsonArray(p.metadata?.pgp_keys).length > 0 && (
                  <details className="mt-3">
                    <summary className="cursor-pointer text-purple-300">
                      PGP Keys ({safeJsonArray(p.metadata.pgp_keys).length})
                    </summary>
                    <pre className="text-xs bg-black p-3 mt-2 rounded overflow-x-auto">
                      {safeJsonArray(p.metadata.pgp_keys)[0]}
                    </pre>
                  </details>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* BITCOIN */}
        {data.bitcoin_addresses.length > 0 && (
          <div>
            <h4 className="text-orange-400 mb-3">Bitcoin Addresses</h4>
            <div className="grid grid-cols-2 gap-3">
              {data.bitcoin_addresses.map((b: any) => (
                <div
                  key={b.address}
                  className="font-mono text-sm bg-gray-800 p-2 rounded break-all"
                >
                  {b.address}
                </div>
              ))}
            </div>
          </div>
        )}

      </div>
    </div>
  </div>
);
