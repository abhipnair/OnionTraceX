import React, { useEffect, useState } from "react";
import {
  RefreshCw,
  AlertTriangle,
  Activity,
  Database,
  Server,
  ShieldCheck,
  Clock,
  Cpu,
  HardDrive,
  Zap,
  CheckCircle2,
  XCircle
} from "lucide-react";

const API_BASE_URL = "http://localhost:5000/api";

/* ============================
   Types (Preserved)
============================ */

const safeUpper = (value?: string, fallback = "UNKNOWN") =>
  typeof value === "string" ? value.toUpperCase() : fallback;

const safeNumber = (value?: number, fallback = 0) =>
  typeof value === "number" && !isNaN(value) ? value : fallback;



interface SystemHealth {
  database: "healthy" | "degraded" | "down";
  dbConnections: number;
  crawler: "active" | "idle" | "down";
  activeCrawlers: number;
  tor: "connected" | "disconnected";
  torCircuits: number;
}

interface SystemInfo {
  version: string;
  uptime: string;
  totalDataGB: number;
  lastUpdate: string;
}

interface SystemResources {
  cpu: number;
  ram: { used: number; total: number };
  disk: { used: number; total: number };
}

/* ============================
   Custom UI Components
============================ */

const CircularGauge = ({ value, label, color = "cyan" }: { value: number; label: string; color?: string }) => {
  const radius = 36;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (value / 100) * circumference;

  const colorMap: Record<string, string> = {
    cyan: "stroke-cyan-400",
    emerald: "stroke-emerald-400",
    yellow: "stroke-yellow-400",
    red: "stroke-red-500",
  };

  const strokeColor = value > 85 ? colorMap.red : value > 60 ? colorMap.yellow : colorMap[color] || colorMap.cyan;

  return (
    <div className="relative flex flex-col items-center justify-center">
      <div className="relative w-32 h-32">
        {/* Background Circle */}
        <svg className="w-full h-full transform -rotate-90">
          <circle
            cx="64"
            cy="64"
            r={radius}
            stroke="currentColor"
            strokeWidth="8"
            fill="transparent"
            className="text-gray-800"
          />
          {/* Progress Circle */}
          <circle
            cx="64"
            cy="64"
            r={radius}
            stroke="currentColor"
            strokeWidth="8"
            fill="transparent"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            strokeLinecap="round"
            className={`${strokeColor} transition-all duration-1000 ease-out`}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-2xl font-mono font-bold text-white">{value}%</span>
        </div>
      </div>
      <span className="mt-2 text-sm uppercase tracking-widest text-gray-400 font-semibold">{label}</span>
    </div>
  );
};

const TechCard = ({ children, className = "" }: { children: React.ReactNode; className?: string }) => (
  <div className={`relative overflow-hidden bg-slate-900/80 backdrop-blur-md border border-slate-700/50 rounded-xl p-6 shadow-xl ${className}`}>
    {/* Decorative corner accents */}
    <div className="absolute top-0 left-0 w-2 h-2 border-t-2 border-l-2 border-cyan-500/50 rounded-tl-sm"></div>
    <div className="absolute top-0 right-0 w-2 h-2 border-t-2 border-r-2 border-cyan-500/50 rounded-tr-sm"></div>
    <div className="absolute bottom-0 left-0 w-2 h-2 border-b-2 border-l-2 border-cyan-500/50 rounded-bl-sm"></div>
    <div className="absolute bottom-0 right-0 w-2 h-2 border-b-2 border-r-2 border-cyan-500/50 rounded-br-sm"></div>
    {children}
  </div>
);

const GlowingBadge = ({ status, activeText, inactiveText }: { status: boolean; activeText: string; inactiveText: string }) => {
  return (
    <div className={`flex items-center gap-2 px-3 py-1 rounded-full border text-xs font-bold tracking-wider uppercase transition-colors duration-300
      ${status 
        ? "bg-emerald-950/50 border-emerald-500/50 text-emerald-400 shadow-[0_0_10px_rgba(16,185,129,0.2)]" 
        : "bg-red-950/50 border-red-500/50 text-red-400"
      }`}>
      <span className={`relative flex h-2 w-2`}>
        {status && <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>}
        <span className={`relative inline-flex rounded-full h-2 w-2 ${status ? "bg-emerald-500" : "bg-red-500"}`}></span>
      </span>
      {status ? activeText : inactiveText}
    </div>
  );
};

/* ============================
   Main Component
============================ */

const SystemSettings: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [info, setInfo] = useState<SystemInfo | null>(null);
  const [resources, setResources] = useState<SystemResources | null>(null);

  /* ============================
     API FUNCTIONS
  ============================ */
  // (Mocking functions for display purposes if API is down, strictly keeping your logic structure)
  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      // Parallel execution for speed
      await Promise.all([
        fetch(`${API_BASE_URL}/system/health`).then(res => res.json()).then(json => { if(json.success) setHealth(json.data); }),
        fetch(`${API_BASE_URL}/system/info`).then(res => res.json()).then(json => { if(json.success) setInfo(json.data); }),
        fetch(`${API_BASE_URL}/system/resources`).then(res => res.json()).then(json => { if(json.success) setResources(json.data); })
      ]);
    } catch (e) {
      setError("System Unreachable - Check Network Uplink");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  /* ============================
     UI HELPERS
  ============================ */

  const ResourceBar = ({ label, value, total, unit, icon: Icon }: any) => {
    const percent = Math.min(100, Math.round((value / total) * 100));
    const isHigh = percent > 85;
    
    return (
      <div className="group">
        <div className="flex justify-between items-end mb-2">
            <div className="flex items-center gap-2 text-gray-400 group-hover:text-cyan-400 transition-colors">
                <Icon size={16} />
                <span className="text-xs font-bold uppercase tracking-wider">{label}</span>
            </div>
            <div className="text-xs font-mono">
                <span className={isHigh ? "text-red-400" : "text-white"}>{value}</span>
                <span className="text-gray-600">/</span>
                <span className="text-gray-500">{total}{unit}</span>
            </div>
        </div>
        <div className="h-2 w-full bg-gray-800 rounded-full overflow-hidden relative">
            <div 
                className={`h-full absolute left-0 top-0 rounded-full transition-all duration-1000 ${
                    isHigh ? "bg-gradient-to-r from-red-600 to-orange-500" : "bg-gradient-to-r from-cyan-600 to-blue-500"
                }`}
                style={{ width: `${percent}%` }}
            >
                {/* Glare effect on bar */}
                <div className="absolute top-0 left-0 right-0 h-[1px] bg-white/30"></div>
            </div>
        </div>
      </div>
    );
  };

  /* ============================
     Render
  ============================ */

  return (
    <div className="min-h-screen bg-slate-950 text-slate-200 p-6 md:p-12 relative overflow-hidden font-sans selection:bg-cyan-500/30">
      
      {/* Background Grid FX */}
      <div 
        className="absolute inset-0 opacity-[0.03] pointer-events-none"
        style={{
            backgroundImage: `linear-gradient(#06b6d4 1px, transparent 1px), linear-gradient(to right, #06b6d4 1px, transparent 1px)`,
            backgroundSize: '40px 40px'
        }}
      />
      
      {/* Ambient Glows */}
      <div className="absolute top-0 left-1/4 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl -translate-y-1/2 pointer-events-none"></div>
      <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-blue-600/10 rounded-full blur-3xl translate-y-1/2 pointer-events-none"></div>

      <div className="max-w-6xl mx-auto space-y-8 relative z-10">

        {/* ================= Header ================= */}
        <div className="flex flex-col md:flex-row justify-between items-start md:items-end border-b border-slate-800 pb-6 gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
                <div className="w-2 h-6 bg-cyan-500 rounded-sm"></div>
                <h2 className="text-3xl font-bold text-white tracking-tight uppercase">
                System Control <span className="text-cyan-500">Plane</span>
                </h2>
            </div>
            <p className="text-slate-400 flex items-center gap-2 text-sm">
               <Activity size={14} className="text-emerald-500 animate-pulse" />
               Realtime Infrastructure Monitoring
            </p>
          </div>

          <button
            onClick={fetchData}
            disabled={loading}
            className={`
                group relative px-6 py-2 bg-slate-900 border border-cyan-500/30 text-cyan-400 rounded-lg 
                hover:bg-cyan-950/30 hover:border-cyan-400 transition-all duration-300
                disabled:opacity-50 disabled:cursor-not-allowed overflow-hidden
            `}
          >
            <div className="absolute inset-0 w-0 bg-cyan-500/10 transition-all duration-[250ms] ease-out group-hover:w-full"></div>
            <span className="relative flex items-center gap-2 font-mono text-sm">
                <RefreshCw size={16} className={loading ? "animate-spin" : "group-hover:rotate-180 transition-transform duration-500"} />
                {loading ? "SYNCING..." : "SYSTEM SYNC"}
            </span>
          </button>
        </div>

        {error && (
          <div className="bg-red-950/30 border border-red-500/50 p-4 rounded-lg flex items-center gap-3 text-red-200 animate-pulse">
            <AlertTriangle className="text-red-500" />
            <span className="font-mono">{error}</span>
          </div>
        )}

        {/* ================= GRID LAYOUT ================= */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

            {/* --- COLUMN 1 & 2: HEALTH & RESOURCES --- */}
            <div className="lg:col-span-2 space-y-6">
                
                {/* Health Section */}
                {health && (
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <TechCard className="flex flex-col items-center justify-between gap-4">
                            <div className="p-3 bg-slate-800 rounded-full border border-slate-700 shadow-inner">
                                <Database className="text-cyan-400" size={24} />
                            </div>
                            <div className="text-center">
                                <h4 className="text-slate-400 text-xs uppercase font-bold tracking-widest mb-1">Database</h4>
                                <div className="font-mono text-xl text-white font-bold">{health.dbConnections} <span className="text-xs text-slate-500 font-sans font-normal">conn</span></div>
                            </div>
                            <GlowingBadge
                                status={health.database === "healthy"}
                                activeText="ONLINE"
                                inactiveText={safeUpper(health?.database)}
                                />

                        </TechCard>

                        <TechCard className="flex flex-col items-center justify-between gap-4">
                            <div className="p-3 bg-slate-800 rounded-full border border-slate-700 shadow-inner">
                                <Server className="text-violet-400" size={24} />
                            </div>
                            <div className="text-center">
                                <h4 className="text-slate-400 text-xs uppercase font-bold tracking-widest mb-1">Crawler</h4>
                                <div className="font-mono text-xl text-white font-bold">{health.activeCrawlers} <span className="text-xs text-slate-500 font-sans font-normal">threads</span></div>
                            </div>
                            <GlowingBadge
                            status={health.crawler === "active"}
                            activeText="ACTIVE"
                            inactiveText={safeUpper(health?.crawler)}
                            />

                        </TechCard>

                        <TechCard className="flex flex-col items-center justify-between gap-4">
                            <div className="p-3 bg-slate-800 rounded-full border border-slate-700 shadow-inner">
                                <ShieldCheck className="text-emerald-400" size={24} />
                            </div>
                            <div className="text-center">
                                <h4 className="text-slate-400 text-xs uppercase font-bold tracking-widest mb-1">Tor Net</h4>
                                <div className="font-mono text-xl text-white font-bold">{health.torCircuits} <span className="text-xs text-slate-500 font-sans font-normal">nodes</span></div>
                            </div>
                            <GlowingBadge
                            status={health.tor === "connected"}
                            activeText="SECURE"
                            inactiveText={safeUpper(health?.tor)}
                            />

                        </TechCard>
                    </div>
                )}

                {/* Resources Section */}
                {resources && (
                    <TechCard>
                         <div className="flex items-center gap-2 mb-6 border-b border-slate-700/50 pb-4">
                            <Zap className="text-yellow-400" size={20} />
                            <h3 className="text-lg font-bold text-white tracking-wide">HARDWARE TELEMETRY</h3>
                        </div>

                        <div className="flex flex-col md:flex-row gap-8 items-center">
                            {/* CPU Gauge */}
                            <div className="flex-shrink-0">
                                <CircularGauge value={resources.cpu} label="CPU LOAD" />
                            </div>

                            {/* Linear Bars */}
                            <div className="flex-grow w-full space-y-6">
                                <ResourceBar 
                                    label="Memory Allocation" 
                                    value={resources.ram.used} 
                                    total={resources.ram.total} 
                                    unit="GB"
                                    icon={Cpu}
                                />
                                <ResourceBar 
                                    label="Storage Volume" 
                                    value={resources.disk.used} 
                                    total={resources.disk.total} 
                                    unit="GB"
                                    icon={HardDrive}
                                />
                            </div>
                        </div>
                    </TechCard>
                )}
            </div>

            {/* --- COLUMN 3: SYSTEM INFO (TERMINAL STYLE) --- */}
            <div className="lg:col-span-1 h-full">
                {info && (
                    <TechCard className="h-full min-h-[300px] flex flex-col">
                        <div className="flex items-center gap-2 mb-4">
                            <Clock className="text-cyan-400" size={18} />
                            <h3 className="text-sm font-bold text-slate-300 uppercase tracking-widest">Runtime Log</h3>
                        </div>
                        
                        <div className="flex-grow bg-black/40 rounded-lg p-4 font-mono text-xs leading-relaxed border border-white/5 shadow-inner overflow-hidden relative">
                             {/* Scanline effect */}
                             <div className="absolute inset-0 bg-gradient-to-b from-transparent to-white/5 opacity-10 pointer-events-none" style={{backgroundSize: '100% 4px'}}></div>

                            <div className="space-y-4">
                                <div>
                                    <span className="text-slate-500">$ sys_ver --check</span>
                                    <div className="text-emerald-400 mt-1">v{info.version} (STABLE)</div>
                                </div>
                                
                                <div>
                                    <span className="text-slate-500">$ uptime --current</span>
                                    <div className="text-cyan-300 mt-1 pl-2 border-l-2 border-slate-700">{info.uptime}</div>
                                </div>

                                <div>
                                    <span className="text-slate-500">$ data_agg --total</span>
                                    {safeNumber(info?.totalDataGB).toFixed(2)} GB</div>

                                <div>
                                    <span className="text-slate-500">$ last_sync</span>
                                    <div className="text-slate-300 mt-1">{info.lastUpdate}</div>
                                </div>
                                
                                <div className="pt-4 border-t border-slate-800/50 mt-4">
                                    <div className="flex items-center gap-2">
                                        <div className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse"></div>
                                        <span className="text-emerald-500">SYSTEM OPERATIONAL</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </TechCard>
                )}
            </div>

        </div>
      </div>
    </div>
  );
};

export default SystemSettings;