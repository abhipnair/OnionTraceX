import React, { useEffect, useState } from "react";
import {
  FileText,
  RefreshCw,
  AlertCircle,
  Download,
  Eye,
  ShieldCheck,
  Layers,
  Coins,
  Users,
  Network,
  Globe,
  UploadCloud
} from "lucide-react";

const API_BASE_URL = "http://localhost:5000/api";

/* ============================
   Types
============================ */

interface ReportRow {
  report_id: string;
  report_type: string;
  generated_at: string;
}

type ReportType =
  | "SITE_DOSSIER"
  | "BTC_ADDRESS_REPORT"
  | "VENDOR_PROFILE"
  | "CATEGORY_INTEL"
  | "ALL_SITES";

/* ============================
   Component
============================ */

const Reports: React.FC = () => {
  const [reports, setReports] = useState<ReportRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  /* ---------- generation ---------- */
  const [reportType, setReportType] = useState<ReportType>("SITE_DOSSIER");
  const [siteId, setSiteId] = useState("");
  const [addressId, setAddressId] = useState("");
  const [vendorId, setVendorId] = useState("");
  const [category, setCategory] = useState("");

  /* ---------- verification ---------- */
  const [verifyFile, setVerifyFile] = useState<File | null>(null);
  const [verifyResult, setVerifyResult] = useState<any>(null);

  /* ============================
     Fetch Reports
  ============================ */

  const fetchReports = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE_URL}/reports`);
      const json = await res.json();
      if (!json.success) throw new Error(json.error);
      setReports(json.data);
    } catch {
      setError("Failed to load reports");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReports();
  }, []);

  /* ============================
     Generate Report
  ============================ */

  const generateReport = async () => {
    setLoading(true);
    try {
      let endpoint = "";
      let payload: any = {};

      switch (reportType) {
        case "SITE_DOSSIER":
          endpoint = "/reports/site";
          payload.site_id = siteId;
          break;
        case "BTC_ADDRESS_REPORT":
          endpoint = "/reports/bitcoin";
          payload.address_id = addressId;
          break;
        case "VENDOR_PROFILE":
          endpoint = "/reports/vendor";
          payload.vendor_id = vendorId;
          break;
        case "CATEGORY_INTEL":
          endpoint = "/reports/category";
          payload.category = category;
          break;
        case "ALL_SITES":
          endpoint = "/reports/all";
          break;
      }

      const res = await fetch(`${API_BASE_URL}${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      const json = await res.json();
      if (!json.success) throw new Error(json.error);

      await fetchReports();
      alert("Report generated successfully");
    } catch (e: any) {
      alert(e.message || "Failed to generate report");
    } finally {
      setLoading(false);
    }
  };

  /* ============================
     Verify PDF
  ============================ */

  const verifyPdf = async () => {
    if (!verifyFile) return;

    const form = new FormData();
    form.append("file", verifyFile);

    const res = await fetch(`${API_BASE_URL}/reports/verify/pdf`, {
      method: "POST",
      body: form
    });

    const json = await res.json();
    setVerifyResult(json);
  };

  /* ============================
     UI Helpers
  ============================ */

  const ReportCard = ({
    type,
    icon: Icon,
    label
  }: {
    type: ReportType;
    icon: any;
    label: string;
  }) => (
    <button
      onClick={() => setReportType(type)}
      className={`p-4 rounded-xl border transition-all text-left
        ${
          reportType === type
            ? "border-cyan-500 bg-cyan-900/30"
            : "border-gray-700 bg-gray-900/40 hover:bg-gray-800/60"
        }`}
    >
      <div className="flex items-center gap-3">
        <Icon className="text-cyan-400" />
        <span className="text-gray-200 font-medium">{label}</span>
      </div>
    </button>
  );

  /* ============================
     Render
  ============================ */

  return (
    <div className="space-y-8 h-full">

      {/* ================= Header ================= */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-white">
            Intelligence Reports
          </h2>
          <p className="text-gray-400">
            Forensic-grade, signed & verifiable intelligence artifacts
          </p>
        </div>
        <button
          onClick={fetchReports}
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

      {/* ================= Report Type Selector ================= */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        <ReportCard type="SITE_DOSSIER" icon={FileText} label="Site Dossier" />
        <ReportCard type="BTC_ADDRESS_REPORT" icon={Coins} label="Bitcoin Address" />
        <ReportCard type="VENDOR_PROFILE" icon={Users} label="Vendor Profile" />
        <ReportCard type="CATEGORY_INTEL" icon={Layers} label="Category Intel" />
        <ReportCard type="ALL_SITES" icon={Globe} label="All Sites (Mega)" />
      </div>

      {/* ================= Input Panel ================= */}
      <div className="bg-gray-800/60 p-6 rounded-xl border border-gray-700 space-y-4">
        {reportType === "SITE_DOSSIER" && (
          <input
            value={siteId}
            onChange={(e) => setSiteId(e.target.value)}
            placeholder="site_id"
            className="input"
          />
        )}

        {reportType === "BTC_ADDRESS_REPORT" && (
          <input
            value={addressId}
            onChange={(e) => setAddressId(e.target.value)}
            placeholder="address_id"
            className="input"
          />
        )}

        {reportType === "VENDOR_PROFILE" && (
          <input
            value={vendorId}
            onChange={(e) => setVendorId(e.target.value)}
            placeholder="vendor_id"
            className="input"
          />
        )}

        {reportType === "CATEGORY_INTEL" && (
          <input
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            placeholder="category (e.g. drugs, fraud)"
            className="input"
          />
        )}

        <button
          onClick={generateReport}
          className="px-6 py-2 bg-red-600 hover:bg-red-700 rounded-lg"
        >
          Generate PDF
        </button>
      </div>

      {/* ================= Verification ================= */}
      <div className="bg-gray-800/60 p-6 rounded-xl border border-gray-700">
        <div className="flex items-center gap-2 mb-4">
          <ShieldCheck className="text-emerald-400" />
          <h3 className="text-lg font-semibold text-emerald-400">
            Verify Report Integrity
          </h3>
        </div>

        <label className="flex flex-col items-center justify-center border-2 border-dashed border-gray-600 rounded-xl p-6 cursor-pointer hover:border-emerald-500 transition">
          <UploadCloud className="text-gray-400 mb-2" />
          <span className="text-gray-400 text-sm">
            Upload PDF report for verification
          </span>
          <input
            type="file"
            accept="application/pdf"
            className="hidden"
            onChange={(e) => setVerifyFile(e.target.files?.[0] || null)}
          />
        </label>

        <button
          onClick={verifyPdf}
          className="mt-4 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 rounded-lg"
        >
          Verify
        </button>

        {verifyResult && (
          <div className="mt-4 p-4 bg-gray-900 rounded border border-gray-700">
            <p className="text-gray-300">
              Status:{" "}
              <span
                className={
                  verifyResult.status === "VALID"
                    ? "text-green-400"
                    : "text-red-400"
                }
              >
                {verifyResult.status}
              </span>
            </p>
            {verifyResult.report_hash && (
              <p className="text-xs text-gray-400 mt-1">
                SHA-256: {verifyResult.report_hash}
              </p>
            )}
          </div>
        )}
      </div>

      {/* ================= Reports Table ================= */}
      <div className="bg-gray-800/60 rounded-xl border border-gray-700 overflow-hidden">
        <div className="p-6 border-b border-gray-700 flex justify-between">
          <h3 className="text-lg font-semibold text-cyan-400">
            Evidence Archive
          </h3>
          <span className="text-gray-400 text-sm">
            {reports.length} artifacts
          </span>
        </div>

        <table className="w-full">
          <thead className="bg-gray-900">
            <tr>
              <th className="px-6 py-3 text-left text-cyan-400">ID</th>
              <th className="px-6 py-3 text-left text-cyan-400">Type</th>
              <th className="px-6 py-3 text-left text-cyan-400">Generated</th>
              <th className="px-6 py-3 text-left text-cyan-400">Actions</th>
            </tr>
          </thead>
          <tbody>
            {reports.map((r) => (
              <tr
                key={r.report_id}
                className="border-t border-gray-700 hover:bg-gray-700/40"
              >
                <td className="px-6 py-3 font-mono text-gray-300">
                  {r.report_id.slice(0, 12)}…
                </td>
                <td className="px-6 py-3 text-gray-300">
                  {r.report_type}
                </td>
                <td className="px-6 py-3 text-gray-300">
                  {new Date(r.generated_at).toLocaleString()}
                </td>
                <td className="px-6 py-3 flex gap-3">
                  <Eye
                    className="text-cyan-400 cursor-pointer"
                    onClick={() =>
                      window.open(
                        `${API_BASE_URL}/reports/${r.report_id}/view`,
                        "_blank"
                      )
                    }
                  />
                  <Download
                    className="text-green-400 cursor-pointer"
                    onClick={() =>
                      window.location.href =
                        `${API_BASE_URL}/reports/${r.report_id}/download`
                    }
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

    </div>
  );
};

export default Reports;
