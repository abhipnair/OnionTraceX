import React, { useState, useEffect } from "react";
import { RefreshCw, Search, Filter, AlertCircle, Eye } from "lucide-react";

const API_BASE = "http://localhost:5000/api";

const SitesExplorer: React.FC = () => {
  const [sitesData, setSitesData] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [searchTerm, setSearchTerm] = useState("");
  const [filterStatus, setFilterStatus] = useState("all");
  const [filterKeyword, setFilterKeyword] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [pagination, setPagination] = useState({ total: 0 });
  const [selectedSite, setSelectedSite] = useState<any>(null);
  const [siteDetails, setSiteDetails] = useState<any>(null);
  const [keywords, setKeywords] = useState<string[]>([]);

  // Load available keywords for filter dropdown
  const loadKeywords = async () => {
    try {
      const res = await fetch(`${API_BASE}/keywords`);
      const data = await res.json();
      if (data.success) setKeywords(data.data.map((k: any) => k.keyword));
    } catch (e) {
      console.error("Keyword load error:", e);
    }
  };

  const loadSitesData = async () => {
    try {
      setLoading(true);
      setError("");
      const params = new URLSearchParams({
        search: searchTerm,
        status: filterStatus,
        keyword: filterKeyword,
        start_date: startDate,
        end_date: endDate,
        page: page.toString(),
        page_size: pageSize.toString(),
      });
      const res = await fetch(`${API_BASE}/sites?${params.toString()}`);
      const data = await res.json();
      if (!data.success) throw new Error(data.error || "Failed to load sites");
      setSitesData(data.data);
      setPagination(data.pagination);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleViewDetails = async (siteId: string) => {
    try {
      setSiteDetails(null);
      const res = await fetch(`${API_BASE}/site/${siteId}`);
      const data = await res.json();
      if (data.success) setSiteDetails(data.data);
    } catch (err) {
      console.error("Detail fetch error:", err);
    }
  };

  useEffect(() => {
    loadSitesData();
    loadKeywords();
  }, [page, filterStatus, filterKeyword]);

  // --- Render ---
  return (
    <div className="space-y-6 h-full">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-white">Sites Explorer</h2>
          <p className="text-gray-400">Browse and search discovered onion sites</p>
        </div>
        <button
          onClick={loadSitesData}
          disabled={loading}
          className="px-4 py-2 bg-cyan-600 hover:bg-cyan-700 rounded-lg flex items-center gap-2 disabled:opacity-50 transition-colors"
        >
          <RefreshCw size={18} className={loading ? "animate-spin" : ""} />
          Refresh
        </button>
      </div>

      {error && (
        <div className="bg-red-900/50 border border-red-500 text-red-200 p-4 rounded-lg">
          <div className="flex items-center gap-2">
            <AlertCircle size={20} />
            <span>Error: {error}</span>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="bg-gray-800/50 backdrop-blur-sm p-6 rounded-xl border border-gray-700/50 space-y-4">
        <div className="flex flex-col lg:flex-row gap-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={20} />
            <input
              type="text"
              placeholder="Search by URL or ID..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-3 bg-gray-900/50 border border-gray-600 rounded-lg text-white focus:outline-none focus:border-cyan-500 focus:ring-2 focus:ring-cyan-500/20 transition-all"
            />
          </div>
          <div className="flex gap-3">
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              className="px-4 py-3 bg-gray-900/50 border border-gray-600 rounded-lg text-white focus:outline-none focus:border-cyan-500 focus:ring-2 focus:ring-cyan-500/20 transition-all"
            >
              <option value="all">All Status</option>
              <option value="Alive">🟢 Alive</option>
              <option value="Dead">🔴 Dead</option>
              <option value="Timeout">🟡 Timeout</option>
            </select>

            <select
              value={filterKeyword}
              onChange={(e) => setFilterKeyword(e.target.value)}
              className="px-4 py-3 bg-gray-900/50 border border-gray-600 rounded-lg text-white focus:outline-none focus:border-cyan-500 focus:ring-2 focus:ring-cyan-500/20 transition-all"
            >
              <option value="">All Keywords</option>
              {keywords.map((k) => (
                <option key={k} value={k}>
                  {k}
                </option>
              ))}
            </select>

            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="px-3 py-3 bg-gray-900/50 border border-gray-600 rounded-lg text-white"
            />
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="px-3 py-3 bg-gray-900/50 border border-gray-600 rounded-lg text-white"
            />

            <button
              onClick={loadSitesData}
              className="px-4 py-3 bg-gray-700 hover:bg-gray-600 rounded-lg flex items-center gap-2 transition-colors"
            >
              <Filter size={18} /> Apply
            </button>
          </div>
        </div>
      </div>

      {/* Table */}
      {!loading && sitesData.length > 0 && (
        <div className="bg-gray-800/50 backdrop-blur-sm rounded-xl border border-gray-700/50 overflow-hidden">
          <div className="p-6 border-b border-gray-700/50 flex justify-between">
            <h3 className="text-lg font-semibold text-cyan-400">Discovered Sites</h3>
            <span className="text-gray-400 text-sm">
              {pagination.total.toLocaleString()} sites total
            </span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-900/50">
                <tr>
                  {["Site ID", "URL", "Keyword", "Status", "First Seen", "Last Seen", "Source", "Actions"].map((h) => (
                    <th key={h} className="px-6 py-4 text-left text-cyan-400 font-semibold">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {sitesData.map((site, i) => (
                  <tr
                    key={site.id}
                    className={`border-t border-gray-700/30 hover:bg-gray-700/30 transition-colors ${
                      i % 2 === 0 ? "bg-gray-800/20" : "bg-gray-800/10"
                    }`}
                  >
                    <td className="px-6 py-4">
                      <code className="text-gray-300 font-mono text-sm bg-gray-900/50 px-2 py-1 rounded">
                        {site.id}
                      </code>
                    </td>
                    <td className="px-6 py-4 text-gray-300 font-mono truncate max-w-xs">{site.url}</td>
                    <td className="px-6 py-4 text-gray-400">{site.category}</td>
                    <td className="px-6 py-4">
                      <span
                        className={`px-3 py-1 rounded-full text-xs font-semibold ${
                          site.status === "Alive"
                            ? "bg-green-900/50 text-green-300 border border-green-500/30"
                            : site.status === "Dead"
                            ? "bg-red-900/50 text-red-300 border border-red-500/30"
                            : "bg-yellow-900/50 text-yellow-300 border border-yellow-500/30"
                        }`}
                      >
                        {site.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-gray-400 text-sm">{site.firstSeen}</td>
                    <td className="px-6 py-4 text-gray-400 text-sm">{site.lastSeen}</td>
                    <td className="px-6 py-4 text-gray-400 text-sm">{site.source}</td>
                    <td className="px-6 py-4">
                      <button
                        onClick={() => {
                          setSelectedSite(site);
                          handleViewDetails(site.id);
                        }}
                        className="text-cyan-400 hover:text-cyan-300 p-2 hover:bg-cyan-500/10 rounded-lg transition-colors"
                      >
                        <Eye size={18} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="flex justify-between items-center p-4 text-gray-400 text-sm">
            <span>
              Page {page} of {Math.ceil(pagination.total / pageSize) || 1}
            </span>
            <div className="flex gap-2">
              <button
                disabled={page <= 1}
                onClick={() => setPage((p) => p - 1)}
                className="px-3 py-1 bg-gray-700 rounded-lg hover:bg-gray-600 disabled:opacity-50"
              >
                Prev
              </button>
              <button
                disabled={page * pageSize >= pagination.total}
                onClick={() => setPage((p) => p + 1)}
                className="px-3 py-1 bg-gray-700 rounded-lg hover:bg-gray-600 disabled:opacity-50"
              >
                Next
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Loading / Empty States */}
      {loading && (
        <div className="flex justify-center items-center py-12">
          <div className="text-center">
            <RefreshCw size={48} className="animate-spin text-cyan-500 mx-auto mb-4" />
            <p className="text-gray-400">Loading sites...</p>
          </div>
        </div>
      )}
      {!loading && sitesData.length === 0 && (
        <div className="bg-gray-800/50 backdrop-blur-sm p-12 rounded-xl border border-gray-700/50 text-center">
          <Search className="mx-auto mb-4 text-gray-500" size={48} />
          <p className="text-gray-400 text-lg mb-2">No sites found</p>
          <p className="text-gray-500">Try adjusting your filters or refresh the data</p>
        </div>
      )}

      {/* Details Modal */}
      {/* Site Details Modal */}
{selectedSite && (
  <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
    <div className="bg-gray-800 rounded-xl border border-gray-700/50 max-w-4xl w-full max-h-[90vh] overflow-y-auto shadow-2xl">
      {/* Header */}
      <div className="p-6 border-b border-gray-700/50 flex justify-between items-center">
        <div>
          <h3 className="text-xl font-bold text-cyan-400">Site Details</h3>
          <p className="text-gray-400 text-sm">Detailed information from database</p>
        </div>
        <button
          onClick={() => {
            setSelectedSite(null);
            setSiteDetails(null);
          }}
          className="text-gray-400 hover:text-white p-2 hover:bg-gray-700 rounded-lg transition-colors"
          title="Close"
        >
          ✕
        </button>
      </div>

      {/* Content */}
      <div className="p-6 space-y-6">
        {siteDetails ? (
          <>
            {/* Basic Info */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <p className="text-gray-400 text-sm mb-2">URL</p>
                <p className="text-white font-mono bg-gray-900/50 p-3 rounded-lg break-all border border-gray-700/50">
                  {siteDetails.url}
                </p>
              </div>
              <div>
                <p className="text-gray-400 text-sm mb-2">Category</p>
                <span
                  className={`px-3 py-2 rounded-lg text-sm font-medium border ${
                    siteDetails.category === "Marketplace"
                      ? "bg-cyan-900/50 text-cyan-300 border-cyan-500/30"
                      : siteDetails.category === "Forum"
                      ? "bg-purple-900/50 text-purple-300 border-purple-500/30"
                      : siteDetails.category === "Scam"
                      ? "bg-red-900/50 text-red-300 border-red-500/30"
                      : "bg-gray-700 text-gray-300 border-gray-600"
                  }`}
                >
                  {siteDetails.category || "Other"}
                </span>
              </div>
              <div>
                <p className="text-gray-400 text-sm mb-2">Status</p>
                <span
                  className={`px-3 py-2 rounded-lg text-sm font-semibold border ${
                    siteDetails.status === "Alive"
                      ? "bg-green-900/50 text-green-300 border-green-500/30"
                      : siteDetails.status === "Dead"
                      ? "bg-red-900/50 text-red-300 border-red-500/30"
                      : "bg-yellow-900/50 text-yellow-300 border-yellow-500/30"
                  }`}
                >
                  {siteDetails.status}
                </span>
              </div>
              <div>
                <p className="text-gray-400 text-sm mb-2">Source</p>
                <span className="text-white bg-gray-900/50 border border-gray-700/50 rounded-lg px-3 py-2 text-sm">
                  {siteDetails.source || "Unknown"}
                </span>
              </div>
              <div>
                <p className="text-gray-400 text-sm mb-2">First Seen</p>
                <p className="text-white bg-gray-900/50 p-3 rounded-lg border border-gray-700/50">
                  {siteDetails.firstSeen || "N/A"}
                </p>
              </div>
              <div>
                <p className="text-gray-400 text-sm mb-2">Last Seen</p>
                <p className="text-white bg-gray-900/50 p-3 rounded-lg border border-gray-700/50">
                  {siteDetails.lastSeen || "N/A"}
                </p>
              </div>
            </div>

            {/* Title (optional) */}
            {siteDetails.title && (
              <div>
                <p className="text-gray-400 text-sm mb-2">Title</p>
                <p className="text-white bg-gray-900/50 p-3 rounded-lg border border-gray-700/50">
                  {siteDetails.title}
                </p>
              </div>
            )}

            {/* Metadata */}
            {siteDetails.metadata && (
              <div>
                <p className="text-gray-400 text-sm mb-3">Metadata</p>
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
                  {Object.entries(siteDetails.metadata).map(([key, value]) => (
                    <div
                      key={key}
                      className="bg-gray-900/50 border border-gray-700/50 p-3 rounded-lg"
                    >
                      <p className="text-gray-400 text-xs uppercase mb-1">{key}</p>
                      <p className="text-white text-sm break-all">{value?.toString() || "N/A"}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        ) : (
          <div className="flex justify-center py-12">
            <RefreshCw size={32} className="animate-spin text-cyan-500" />
          </div>
        )}
      </div>
    </div>
  </div>
)}

    </div>
  );
};

export default SitesExplorer;
