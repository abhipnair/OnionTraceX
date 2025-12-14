import React, { useState, useEffect } from 'react';

import { 
  Search, Globe, Users, FileText, Settings, Activity, 
  Database, TrendingUp, AlertCircle, Download, Eye, Clock, 
  Network, RefreshCw, Shield, Bitcoin, Server, BarChart3,
  SearchCodeIcon
} from 'lucide-react';

// Import interfaces
import {
  Stats, LivenessData, CategoryData, KeywordData, Site, SiteDetails,
  Vendor, VendorNetwork, BitcoinData, Report, ReportConfig,
  SystemHealth, CrawlerConfig
} from './types';

import CrawlerControlPanel from "./CrawlerControlPanel";
import DashboardCharts from "./DashboardCharts";
import SitesExplorer from "./SitesExplorer";
import BitcoinAnalysis from "./BitcoinAnalysis";


// API Configuration
const API_BASE_URL = 'http://localhost:5000/api';

// API Service with TypeScript
// API Service with TypeScript - UPDATED VERSION
const apiService = {
  async fetchStats(): Promise<Stats> {
    const response = await fetch(`${API_BASE_URL}/stats`);
    if (!response.ok) throw new Error('Failed to fetch stats');
    const result = await response.json();
    if (!result.success) throw new Error(result.error || 'API request failed');
    return result.data;
  },

  async fetchLivenessData(days: number = 30): Promise<LivenessData[]> {
    const response = await fetch(`${API_BASE_URL}/liveness?days=${days}`);
    if (!response.ok) throw new Error('Failed to fetch liveness data');
    const result = await response.json();
    if (!result.success) throw new Error(result.error || 'API request failed');
    return result.data;
  },

  async fetchCategoryData(): Promise<CategoryData[]> {
    const response = await fetch(`${API_BASE_URL}/categories`);
    if (!response.ok) throw new Error('Failed to fetch category data');
    const result = await response.json();
    if (!result.success) throw new Error(result.error || 'API request failed');
    return result.data;
  },

  async fetchKeywordData(): Promise<KeywordData[]> {
    const response = await fetch(`${API_BASE_URL}/keywords`);
    if (!response.ok) throw new Error('Failed to fetch keyword data');
    const result = await response.json();
    if (!result.success) throw new Error(result.error || 'API request failed');
    return result.data;
  },

  async fetchSites(params: Record<string, string> = {}): Promise<Site[]> {
    const queryString = new URLSearchParams(params).toString();
    const response = await fetch(`${API_BASE_URL}/sites?${queryString}`);
    if (!response.ok) throw new Error('Failed to fetch sites');
    const result = await response.json();
    if (!result.success) throw new Error(result.error || 'API request failed');
    return result.data;
  },

  async fetchSiteDetails(siteId: string): Promise<SiteDetails> {
    const response = await fetch(`${API_BASE_URL}/sites/${siteId}`);
    if (!response.ok) throw new Error('Failed to fetch site details');
    const result = await response.json();
    if (!result.success) throw new Error(result.error || 'API request failed');
    return result.data;
  },

  async fetchVendors(): Promise<Vendor[]> {
    const response = await fetch(`${API_BASE_URL}/vendors`);
    if (!response.ok) throw new Error('Failed to fetch vendors');
    const result = await response.json();
    if (!result.success) throw new Error(result.error || 'API request failed');
    return result.data;
  },

  async fetchVendorNetwork(): Promise<VendorNetwork> {
    const response = await fetch(`${API_BASE_URL}/vendors/network`);
    if (!response.ok) throw new Error('Failed to fetch vendor network');
    const result = await response.json();
    if (!result.success) throw new Error(result.error || 'API request failed');
    return result.data;
  },

  async fetchBitcoinData(): Promise<BitcoinData> {
    const response = await fetch(`${API_BASE_URL}/bitcoin/wallets`);
    if (!response.ok) throw new Error('Failed to fetch bitcoin data');
    const result = await response.json();
    if (!result.success) throw new Error(result.error || 'API request failed');
    return result.data;
  },

  async fetchBitcoinTransactions(walletId: string): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/bitcoin/transactions/${walletId}`);
    if (!response.ok) throw new Error('Failed to fetch transactions');
    const result = await response.json();
    if (!result.success) throw new Error(result.error || 'API request failed');
    return result.data;
  },

  async generateReport(params: ReportConfig): Promise<{ reportId: string }> {
    const response = await fetch(`${API_BASE_URL}/reports/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params)
    });
    if (!response.ok) throw new Error('Failed to generate report');
    const result = await response.json();
    if (!result.success) throw new Error(result.error || 'API request failed');
    return result.data;
  },

  async fetchReports(): Promise<Report[]> {
    const response = await fetch(`${API_BASE_URL}/reports`);
    if (!response.ok) throw new Error('Failed to fetch reports');
    const result = await response.json();
    if (!result.success) throw new Error(result.error || 'API request failed');
    return result.data;
  },

  async downloadReport(reportId: string, format: string): Promise<Blob> {
    const response = await fetch(`${API_BASE_URL}/reports/${reportId}/download?format=${format}`);
    if (!response.ok) throw new Error('Failed to download report');
    
    // For CSV downloads, the backend returns the file directly, not JSON
    if (format === 'csv') {
      return response.blob();
    }
    
    // For JSON, it returns a JSON response
    const result = await response.json();
    if (!result.success) throw new Error(result.error || 'API request failed');
    
    // Convert JSON to blob for download
    return new Blob([JSON.stringify(result.data, null, 2)], { type: 'application/json' });
  },

  async fetchSystemHealth(): Promise<SystemHealth> {
    const response = await fetch(`${API_BASE_URL}/system/health`);
    if (!response.ok) throw new Error('Failed to fetch system health');
    const result = await response.json();
    if (!result.success) throw new Error(result.error || 'API request failed');
    return result.data;
  },

  async updateCrawlerConfig(config: CrawlerConfig): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/system/config`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config)
    });
    if (!response.ok) throw new Error('Failed to update config');
    const result = await response.json();
    if (!result.success) throw new Error(result.error || 'API request failed');
  }
};

// Navigation item type
interface NavItem {
  id: string;
  label: string;
  icon: React.ComponentType<any>;
  description: string;
}

const OnionTraceX: React.FC = () => {
  const [activeSection, setActiveSection] = useState<string>('dashboard');
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [sidebarCollapsed, setSidebarCollapsed] = useState<boolean>(false);

  // Dashboard state
  const [stats, setStats] = useState<Stats | null>(null);
  const [livenessData, setLivenessData] = useState<LivenessData[]>([]);
  const [categoryData, setCategoryData] = useState<CategoryData[]>([]);
  const [keywordData, setKeywordData] = useState<KeywordData[]>([]);


  // ========== CRAWLER STATE - ADD THIS ==========
  const [crawlerKeywords, setCrawlerKeywords] = useState<string>("");
  const [crawlerFile, setCrawlerFile] = useState<File | null>(null);
  const [crawlerProgress, setCrawlerProgress] = useState<number>(0);
  const [crawlerStatus, setCrawlerStatus] = useState<string>("idle");
  const [crawlerMessage, setCrawlerMessage] = useState<string>("");
  const [crawlerLoading, setCrawlerLoading] = useState(false);

  // Sites state
  const [sitesData, setSitesData] = useState<Site[]>([]);
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [selectedSite, setSelectedSite] = useState<Site | null>(null);
  const [siteDetails, setSiteDetails] = useState<SiteDetails | null>(null);

  // Vendors state
  const [vendorData, setVendorData] = useState<Vendor[]>([]);
  const [vendorNetwork, setVendorNetwork] = useState<VendorNetwork | null>(null);

  // Bitcoin state
  const [btcData, setBtcData] = useState<BitcoinData | null>(null);

  // Reports state
  const [reports, setReports] = useState<Report[]>([]);
  const [reportConfig, setReportConfig] = useState<ReportConfig>({
    dateRange: '',
    category: 'all',
    includeMetadata: true,
    includeVendors: true,
    includeBitcoin: true
  });

  // Settings state
  const [systemHealth, setSystemHealth] = useState<SystemHealth | null>(null);
  const [crawlerConfig, setCrawlerConfig] = useState<CrawlerConfig>({
    crawlRate: 30,
    circuitRotation: 10,
    timeout: 30
  });

  // Mock data for demonstration
  useEffect(() => {
    // Set mock data for initial display
    const mockStats: Stats = {
      totalSites: 15432,
      alivePercent: 68,
      deadPercent: 22,
      timeoutPercent: 10,
      activeCrawlers: 8,
      avgCrawlTime: 4.2
    };

    const mockLivenessData: LivenessData[] = Array.from({ length: 30 }, (_, i) => ({
      date: `2024-${String(i % 12 + 1).padStart(2, '0')}-${String(i % 28 + 1).padStart(2, '0')}`,
      alive: Math.floor(Math.random() * 100) + 800,
      dead: Math.floor(Math.random() * 50) + 200,
      timeout: Math.floor(Math.random() * 30) + 50
    }));

    const mockCategoryData: CategoryData[] = [
      { name: 'Marketplace', value: 45, color: '#06b6d4' },
      { name: 'Forum', value: 25, color: '#8b5cf6' },
      { name: 'Scam', value: 15, color: '#ef4444' },
      { name: 'Blog', value: 10, color: '#f59e0b' },
      { name: 'Other', value: 5, color: '#6b7280' }
    ];

    const mockKeywordData: KeywordData[] = [
      { keyword: 'market', discovered: 2345 },
      { keyword: 'forum', discovered: 1876 },
      { keyword: 'shop', discovered: 1543 },
      { keyword: 'carding', discovered: 987 },
      { keyword: 'crypto', discovered: 876 }
    ];

    setStats(mockStats);
    setLivenessData(mockLivenessData);
    setCategoryData(mockCategoryData);
    setKeywordData(mockKeywordData);
  }, []);

  // Load dashboard data
  const loadDashboardData = async (): Promise<void> => {
    setLoading(true);
    setError(null);
    try {
      const [statsRes, livenessRes, categoryRes, keywordRes] = await Promise.all([
        apiService.fetchStats(),
        apiService.fetchLivenessData(),
        apiService.fetchCategoryData(),
        apiService.fetchKeywordData()
      ]);
      setStats(statsRes);
      setLivenessData(livenessRes);
      setCategoryData(categoryRes);
      setKeywordData(keywordRes);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
      console.error('Error loading dashboard:', err);
    } finally {
      setLoading(false);
    }
  };

    // ========== CRAWLER FUNCTIONS - ADD THIS ==========
  const handleStartCrawler = async (): Promise<void> => {
    try {
      setCrawlerLoading(true);
      setCrawlerMessage("Starting crawler...");
      setCrawlerStatus("starting");

      const formData = new FormData();
      formData.append("keywords", crawlerKeywords);
      if (crawlerFile) formData.append("file", crawlerFile);

      const response = await fetch(`${API_BASE_URL}/crawler/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ keywords: crawlerKeywords.split(",").map(k => k.trim()) }),
      });

      const result = await response.json();
      if (result.success) {
        setCrawlerMessage(result.message);
        setCrawlerStatus("running");
        checkCrawlerStatus();
      } else {
        setCrawlerMessage(result.error || "Failed to start crawler");
        setCrawlerStatus("error");
      }
    } catch (err) {
      setCrawlerMessage("Error starting crawler");
      setCrawlerStatus("error");
    } finally {
      setCrawlerLoading(false);
    }
  };

  const checkCrawlerStatus = async (): Promise<void> => {
    try {
      const response = await fetch(`${API_BASE_URL}/crawler/status`);
      const result = await response.json();
      if (result.success) {
        setCrawlerProgress(result.progress);
        setCrawlerStatus(result.status);
        if (result.status !== "completed" && result.status !== "error") {
          setTimeout(checkCrawlerStatus, 3000);
        }
      }
    } catch {
      setCrawlerMessage("Failed to fetch crawler status");
      setCrawlerStatus("error");
    }
  };
  // ========== END CRAWLER FUNCTIONS ==========

  // Load sites data
  const loadSitesData = async (): Promise<void> => {
    setLoading(true);
    setError(null);
    try {
      const params: Record<string, string> = {};
      if (searchTerm) params.search = searchTerm;
      if (filterStatus !== 'all') params.status = filterStatus;
      const sitesRes = await apiService.fetchSites(params);
      setSitesData(sitesRes);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
      console.error('Error loading sites:', err);
    } finally {
      setLoading(false);
    }
  };

  // Load site details
  const loadSiteDetails = async (siteId: string): Promise<void> => {
    try {
      const details = await apiService.fetchSiteDetails(siteId);
      setSiteDetails(details);
    } catch (err) {
      console.error('Error loading site details:', err);
    }
  };

  // Load vendors data
  const loadVendorsData = async (): Promise<void> => {
    setLoading(true);
    setError(null);
    try {
      const [vendorsRes, networkRes] = await Promise.all([
        apiService.fetchVendors(),
        apiService.fetchVendorNetwork()
      ]);
      setVendorData(vendorsRes);
      setVendorNetwork(networkRes);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
      console.error('Error loading vendors:', err);
    } finally {
      setLoading(false);
    }
  };

  // Load bitcoin data
  const loadBitcoinData = async (): Promise<void> => {
    setLoading(true);
    setError(null);
    try {
      const btcRes = await apiService.fetchBitcoinData();
      setBtcData(btcRes);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
      console.error('Error loading bitcoin data:', err);
    } finally {
      setLoading(false);
    }
  };

  // Load reports
  const loadReports = async (): Promise<void> => {
    setLoading(true);
    setError(null);
    try {
      const reportsRes = await apiService.fetchReports();
      setReports(reportsRes);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
      console.error('Error loading reports:', err);
    } finally {
      setLoading(false);
    }
  };

  // Load system health
  const loadSystemHealth = async (): Promise<void> => {
    setLoading(true);
    setError(null);
    try {
      const healthRes = await apiService.fetchSystemHealth();
      setSystemHealth(healthRes);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
      console.error('Error loading system health:', err);
    } finally {
      setLoading(false);
    }
  };

  // Generate report
  const handleGenerateReport = async (format: string): Promise<void> => {
    try {
      const reportRes = await apiService.generateReport(reportConfig);
      const blob = await apiService.downloadReport(reportRes.reportId, format);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `report_${reportRes.reportId}.${format}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      await loadReports();
    } catch (err) {
      console.error('Error generating report:', err);
      alert('Failed to generate report: ' + (err instanceof Error ? err.message : 'Unknown error'));
    }
  };

  // Update crawler config
  const handleUpdateConfig = async (): Promise<void> => {
    try {
      await apiService.updateCrawlerConfig(crawlerConfig);
      alert('Configuration updated successfully');
    } catch (err) {
      console.error('Error updating config:', err);
      alert('Failed to update configuration: ' + (err instanceof Error ? err.message : 'Unknown error'));
    }
  };

  // Load data based on active section
  useEffect(() => {
    switch (activeSection) {
      case 'dashboard':
        loadDashboardData();
        break;
      case 'sites':
        loadSitesData();
        break;
      case 'vendors':
        loadVendorsData();
        break;
      case 'bitcoin':
        loadBitcoinData();
        break;
      case 'reports':
        loadReports();
        break;
      case 'settings':
        loadSystemHealth();
        break;
    }
  }, [activeSection]);

  // Reload sites when search/filter changes
  useEffect(() => {
    if (activeSection === 'sites') {
      const timeoutId = setTimeout(() => {
        loadSitesData();
      }, 500);
      return () => clearTimeout(timeoutId);
    }
  }, [searchTerm, filterStatus, activeSection]);

  // Load site details when selected
  useEffect(() => {
    if (selectedSite) {
      loadSiteDetails(selectedSite.id);
    }
  }, [selectedSite]);

  const renderDashboard = (): JSX.Element => (
    <div className="space-y-6 h-full">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-white">Dashboard Overview</h2>
          <p className="text-gray-400">Real-time dark web monitoring and analytics</p>
        </div>
        <button
          onClick={loadDashboardData}
          disabled={loading}
          className="px-4 py-2 bg-cyan-600 hover:bg-cyan-700 rounded-lg flex items-center gap-2 disabled:opacity-50 transition-colors"
        >
          <RefreshCw size={18} className={loading ? 'animate-spin' : ''} />
          Refresh Data
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

      {/* Metric Cards */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
          <div className="bg-gradient-to-br from-cyan-900/50 to-cyan-800/30 p-4 rounded-xl border border-cyan-500/20 hover:border-cyan-500/40 transition-all duration-300">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-400 text-sm">Total Sites</p>
                <p className="text-2xl font-bold text-cyan-400">{stats.totalSites.toLocaleString()}</p>
              </div>
              <div className="p-2 bg-cyan-500/20 rounded-lg">
                <Globe className="text-cyan-400" size={24} />
              </div>
            </div>
          </div>
          
          <div className="bg-gradient-to-br from-green-900/50 to-green-800/30 p-4 rounded-xl border border-green-500/20 hover:border-green-500/40 transition-all duration-300">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-400 text-sm">Alive Sites</p>
                <p className="text-2xl font-bold text-green-400">{stats.alivePercent}%</p>
              </div>
              <div className="p-2 bg-green-500/20 rounded-lg">
                <Activity className="text-green-400" size={24} />
              </div>
            </div>
          </div>

          <div className="bg-gradient-to-br from-red-900/50 to-red-800/30 p-4 rounded-xl border border-red-500/20 hover:border-red-500/40 transition-all duration-300">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-400 text-sm">Dead Sites</p>
                <p className="text-2xl font-bold text-red-400">{stats.deadPercent}%</p>
              </div>
              <div className="p-2 bg-red-500/20 rounded-lg">
                <AlertCircle className="text-red-400" size={24} />
              </div>
            </div>
          </div>

          <div className="bg-gradient-to-br from-yellow-900/50 to-yellow-800/30 p-4 rounded-xl border border-yellow-500/20 hover:border-yellow-500/40 transition-all duration-300">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-400 text-sm">Timeout</p>
                <p className="text-2xl font-bold text-yellow-400">{stats.timeoutPercent}%</p>
              </div>
              <div className="p-2 bg-yellow-500/20 rounded-lg">
                <Clock className="text-yellow-400" size={24} />
              </div>
            </div>
          </div>

          <div className="bg-gradient-to-br from-purple-900/50 to-purple-800/30 p-4 rounded-xl border border-purple-500/20 hover:border-purple-500/40 transition-all duration-300">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-400 text-sm">Active Crawlers</p>
                <p className="text-2xl font-bold text-purple-400">{stats.activeCrawlers}</p>
              </div>
              <div className="p-2 bg-purple-500/20 rounded-lg">
                <Server className="text-purple-400" size={24} />
              </div>
            </div>
          </div>

          <div className="bg-gradient-to-br from-blue-900/50 to-blue-800/30 p-4 rounded-xl border border-blue-500/20 hover:border-blue-500/40 transition-all duration-300">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-400 text-sm">Avg Response Time</p>
                <p className="text-2xl font-bold text-blue-400">{stats.avgCrawlTime}s</p>
              </div>
              <div className="p-2 bg-blue-500/20 rounded-lg">
                <TrendingUp className="text-blue-400" size={24} />
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Charts Grid */}
      <DashboardCharts />

      {loading && (
        <div className="flex justify-center items-center py-12">
          <div className="text-center">
            <RefreshCw size={48} className="animate-spin text-cyan-500 mx-auto mb-4" />
            <p className="text-gray-400">Loading dashboard data...</p>
          </div>
        </div>
      )}
    </div>
  );


  const renderVendors = (): JSX.Element => {
  // SVG-based vendor network graph with zoom + pan
  const VendorNetworkGraphSVG: React.FC<{ data: any }> = ({ data }) => {
    const [nodePositions, setNodePositions] = useState<{ [key: string]: { x: number; y: number } }>({});
    const [zoom, setZoom] = useState(1);
    const [pan, setPan] = useState({ x: 0, y: 0 });
    const [isPanning, setIsPanning] = useState(false);
    const [startPan, setStartPan] = useState({ x: 0, y: 0 });

    // Zoom controls
    const handleZoomIn = () => setZoom(prev => Math.min(prev * 1.3, 5));
    const handleZoomOut = () => setZoom(prev => Math.max(prev / 1.3, 0.3));
    const handleZoomReset = () => {
      setZoom(1);
      setPan({ x: 0, y: 0 });
    };

    // Panning handlers
    const handleMouseDown = (e: React.MouseEvent) => {
      setIsPanning(true);
      setStartPan({ x: e.clientX - pan.x, y: e.clientY - pan.y });
    };

    const handleMouseMove = (e: React.MouseEvent) => {
      if (!isPanning) return;
      setPan({
        x: e.clientX - startPan.x,
        y: e.clientY - startPan.y
      });
    };

    const handleMouseUp = () => {
      setIsPanning(false);
    };

    // Wheel zoom
    const handleWheel = (e: React.WheelEvent) => {
      e.preventDefault();
      const zoomFactor = e.deltaY > 0 ? 0.9 : 1.1;
      setZoom(prev => Math.max(0.3, Math.min(5, prev * zoomFactor)));
    };

    // Force layout simulation
    useEffect(() => {
      if (!data) return;

      const positions: { [key: string]: { x: number; y: number } } = {};
      const width = 1200;
      const height = 800;

      data.nodes.forEach((node: any, index: number) => {
        const angle = (index / data.nodes.length) * 2 * Math.PI;
        const radius = Math.min(width, height) * 0.4;
        positions[node.id] = {
          x: width / 2 + radius * Math.cos(angle),
          y: height / 2 + radius * Math.sin(angle)
        };
      });

      for (let iteration = 0; iteration < 100; iteration++) {
        // Node repulsion
        data.nodes.forEach((nodeA: any) => {
          data.nodes.forEach((nodeB: any) => {
            if (nodeA.id === nodeB.id) return;
            const posA = positions[nodeA.id];
            const posB = positions[nodeB.id];
            const dx = posB.x - posA.x;
            const dy = posB.y - posA.y;
            const distance = Math.sqrt(dx * dx + dy * dy);
            if (distance < 150) {
              const force = 150 / (distance * distance);
              posA.x -= dx * force * 0.2;
              posA.y -= dy * force * 0.2;
              posB.x += dx * force * 0.2;
              posB.y += dy * force * 0.2;
            }
          });
        });

        // Link attraction
        data.links.forEach((link: any) => {
          const source = positions[link.source];
          const target = positions[link.target];
          if (source && target) {
            const dx = target.x - source.x;
            const dy = target.y - source.y;
            const distance = Math.sqrt(dx * dx + dy * dy);
            const force = (distance - 200) * 0.01;
            source.x += dx * force * 0.1;
            source.y += dy * force * 0.1;
            target.x -= dx * force * 0.1;
            target.y -= dy * force * 0.1;
          }
        });

        // Keep nodes in bounds
        data.nodes.forEach((node: any) => {
          const pos = positions[node.id];
          pos.x = Math.max(50, Math.min(width - 50, pos.x));
          pos.y = Math.max(50, Math.min(height - 50, pos.y));
        });
      }

      setNodePositions(positions);
    }, [data]);

    if (!data || Object.keys(nodePositions).length === 0) {
      return (
        <div className="flex items-center justify-center h-full">
          <RefreshCw size={32} className="animate-spin text-cyan-500" />
          <span className="ml-2 text-gray-400">Calculating network layout...</span>
        </div>
      );
    }

    return (
      <div className="relative w-full h-full">
        {/* Zoom Controls */}
        <div className="absolute top-6 right-6 z-10 flex flex-col gap-3 bg-gray-900/90 backdrop-blur-sm p-3 rounded-xl border border-gray-600/50">
          <div className="text-center text-xs text-gray-400 mb-1">Zoom</div>
          <button onClick={handleZoomIn} className="p-3 bg-cyan-600/20 hover:bg-cyan-600/30 rounded-lg border border-cyan-500/30 text-cyan-400">
            +
          </button>
          <div className="text-center text-cyan-400 text-sm font-mono px-2 py-1 bg-gray-800/50 rounded">
            {Math.round(zoom * 100)}%
          </div>
          <button onClick={handleZoomOut} className="p-3 bg-cyan-600/20 hover:bg-cyan-600/30 rounded-lg border border-cyan-500/30 text-cyan-400">
            -
          </button>
          <button onClick={handleZoomReset} className="p-2 bg-gray-700/50 hover:bg-gray-600/50 rounded-lg border border-gray-500/30 text-gray-300 mt-2">
            ⟲ Reset
          </button>
        </div>

        {/* Network Info */}
        <div className="absolute top-6 left-6 z-10 bg-gray-900/90 backdrop-blur-sm px-4 py-3 rounded-xl border border-gray-600/50">
          <div className="text-xs text-gray-400 mb-2">Network Stats</div>
          <div className="flex gap-4 text-sm">
            <div className="text-cyan-400">
              <div className="font-bold">{data.nodes.length}</div>
              <div className="text-xs text-gray-400">Nodes</div>
            </div>
            <div className="text-purple-400">
              <div className="font-bold">{data.links.length}</div>
              <div className="text-xs text-gray-400">Links</div>
            </div>
          </div>
        </div>

        {/* SVG Graph */}
        <svg
          width="100%"
          height="100%"
          viewBox="0 0 1200 800"
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
          onWheel={handleWheel}
          className="w-full h-full cursor-grab active:cursor-grabbing"
          style={{
            transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
            transformOrigin: "center center",
            transition: isPanning ? "none" : "transform 0.1s ease-out"
          }}
        >
          <defs>
            <pattern id="grid" width="100" height="100" patternUnits="userSpaceOnUse">
              <path d="M 100 0 L 0 0 0 100" fill="none" stroke="rgba(75,85,99,0.2)" strokeWidth="1" />
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#grid)" />

          {/* Links */}
          {data.links.map((link: any, i: number) => {
            const s = nodePositions[link.source];
            const t = nodePositions[link.target];
            if (!s || !t) return null;
            return (
              <line
                key={i}
                x1={s.x}
                y1={s.y}
                x2={t.x}
                y2={t.y}
                stroke={link.color || "#4b5563"}
                strokeWidth={(link.value || 1) * 2}
                opacity={0.7}
              />
            );
          })}

          {/* Nodes */}
          {data.nodes.map((node: any) => {
            const pos = nodePositions[node.id];
            if (!pos) return null;
            const size = node.size || 16;
            return (
              <g key={node.id} transform={`translate(${pos.x}, ${pos.y})`}>
                <circle r={size} fill={node.color || "#06b6d4"} stroke="#1e40af" strokeWidth="3" />
                <text textAnchor="middle" dy={-size - 8} fontSize="12" fill="#e5e7eb">
                  {node.name}
                </text>
              </g>
            );
          })}
        </svg>
      </div>
    );
  };

  // Data preprocessing
  const processVendorNetwork = (networkData: any) => {
    if (!networkData || !networkData.links) return null;
    const nodeMap: Record<string, any> = {};
    const links: any[] = [];

    networkData.links.forEach((link: any) => {
      const color = link.type === "shared_marketplace" ? "#8b5cf6" : "#10b981";
      links.push({ source: link.source, target: link.target, value: link.weight || 1, color });

      [link.source, link.target].forEach(id => {
        if (!nodeMap[id]) {
          nodeMap[id] = {
            id,
            name: `Vendor ${id.split("_")[1]}`,
            size: 14 + Math.random() * 8,
            color: "#06b6d4"
          };
        }
      });
    });

    return { nodes: Object.values(nodeMap), links };
  };

  const vendorGraphData = vendorNetwork ? processVendorNetwork(vendorNetwork) : null;

  // Main return
  return (
    <div className="space-y-6 h-full">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-white">Vendor Clusters</h2>
          <p className="text-gray-400">Interactive vendor relationship mapping</p>
        </div>
        <button
          onClick={loadVendorsData}
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

      <div className="bg-gray-800/50 backdrop-blur-sm p-6 rounded-xl border border-gray-700/50">
        <div className="flex items-center gap-2 mb-4">
          <Network className="text-cyan-400" size={20} />
          <h3 className="text-lg font-semibold text-cyan-400">Vendor Network Graph</h3>
          <span className="text-gray-400 text-sm ml-2">• Scroll to zoom • Drag to pan</span>
        </div>

        <div className="bg-gradient-to-br from-gray-900/50 to-gray-800/30 rounded-xl min-h-[700px] h-[70vh] max-h-[800px] flex items-center justify-center border-2 border-gray-600/30 overflow-hidden relative shadow-2xl">
          {loading ? (
            <div className="text-center">
              <RefreshCw size={48} className="animate-spin text-cyan-500 mx-auto mb-4" />
              <p className="text-gray-400">Loading vendor network...</p>
            </div>
          ) : vendorGraphData ? (
            <div className="w-full h-full">
              <VendorNetworkGraphSVG data={vendorGraphData} />
            </div>
          ) : (
            <div className="text-center w-full h-full flex flex-col items-center justify-center text-gray-400">
              <Network className="mb-4 text-cyan-500" size={48} />
              <p className="text-lg">No vendor network data available</p>
              <p className="text-sm text-gray-500 mt-1">Try refreshing to fetch the latest network graph</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};


const renderReports = (): JSX.Element => (
  <div className="space-y-6 h-full">
    {/* Header */}
    <div className="flex justify-between items-center">
      <div>
        <h2 className="text-2xl font-bold text-white">Intelligence Reports</h2>
        <p className="text-gray-400">Generate and export comprehensive intelligence reports</p>
      </div>
      <button
        onClick={loadReports}
        disabled={loading}
        className="px-4 py-2 bg-cyan-600 hover:bg-cyan-700 rounded-lg flex items-center gap-2 disabled:opacity-50 transition-colors"
      >
        <RefreshCw size={18} className={loading ? 'animate-spin' : ''} />
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

    {/* Report Generator */}
    <div className="bg-gray-800/50 backdrop-blur-sm p-6 rounded-xl border border-gray-700/50">
      <div className="flex items-center gap-2 mb-6">
        <FileText className="text-cyan-400" size={20} />
        <h3 className="text-lg font-semibold text-cyan-400">Generate New Report</h3>
      </div>
      
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        <div>
          <label className="block text-gray-400 text-sm mb-2 font-medium">Date Range</label>
          <select
            value={reportConfig.dateRange}
            onChange={(e) => setReportConfig({...reportConfig, dateRange: e.target.value})}
            className="w-full px-4 py-3 bg-gray-900/50 border border-gray-600 rounded-lg text-white focus:outline-none focus:border-cyan-500 focus:ring-2 focus:ring-cyan-500/20 transition-all"
          >
            <option value="">All Time</option>
            <option value="7d">Last 7 Days</option>
            <option value="30d">Last 30 Days</option>
            <option value="90d">Last 90 Days</option>
            <option value="1y">Last Year</option>
          </select>
        </div>
        <div>
          <label className="block text-gray-400 text-sm mb-2 font-medium">Category Filter</label>
          <select
            value={reportConfig.category}
            onChange={(e) => setReportConfig({...reportConfig, category: e.target.value})}
            className="w-full px-4 py-3 bg-gray-900/50 border border-gray-600 rounded-lg text-white focus:outline-none focus:border-cyan-500 focus:ring-2 focus:ring-cyan-500/20 transition-all"
          >
            <option value="all">All Categories</option>
            <option value="marketplace">Marketplaces</option>
            <option value="forum">Forums</option>
            <option value="scam">Scam Sites</option>
            <option value="blog">Blogs</option>
          </select>
        </div>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <label className="flex items-center gap-3 p-3 bg-gray-900/30 rounded-lg border border-gray-600 hover:border-cyan-500/30 transition-colors cursor-pointer">
          <input
            type="checkbox"
            checked={reportConfig.includeMetadata}
            onChange={(e) => setReportConfig({...reportConfig, includeMetadata: e.target.checked})}
            className="w-4 h-4 text-cyan-500 bg-gray-700 border-gray-600 rounded focus:ring-cyan-500 focus:ring-2"
          />
          <div>
            <span className="text-gray-300 font-medium">Site Metadata</span>
            <p className="text-gray-500 text-xs">Include detailed site information</p>
          </div>
        </label>
        
        <label className="flex items-center gap-3 p-3 bg-gray-900/30 rounded-lg border border-gray-600 hover:border-cyan-500/30 transition-colors cursor-pointer">
          <input
            type="checkbox"
            checked={reportConfig.includeVendors}
            onChange={(e) => setReportConfig({...reportConfig, includeVendors: e.target.checked})}
            className="w-4 h-4 text-cyan-500 bg-gray-700 border-gray-600 rounded focus:ring-cyan-500 focus:ring-2"
          />
          <div>
            <span className="text-gray-300 font-medium">Vendor Data</span>
            <p className="text-gray-500 text-xs">Include vendor clusters and networks</p>
          </div>
        </label>
        
        <label className="flex items-center gap-3 p-3 bg-gray-900/30 rounded-lg border border-gray-600 hover:border-cyan-500/30 transition-colors cursor-pointer">
          <input
            type="checkbox"
            checked={reportConfig.includeBitcoin}
            onChange={(e) => setReportConfig({...reportConfig, includeBitcoin: e.target.checked})}
            className="w-4 h-4 text-cyan-500 bg-gray-700 border-gray-600 rounded focus:ring-cyan-500 focus:ring-2"
          />
          <div>
            <span className="text-gray-300 font-medium">Bitcoin Analysis</span>
            <p className="text-gray-500 text-xs">Include cryptocurrency tracking</p>
          </div>
        </label>
      </div>
      
      <div className="flex flex-wrap gap-4">
        <button
          onClick={() => handleGenerateReport('pdf')}
          className="px-6 py-3 bg-red-600 hover:bg-red-700 rounded-lg flex items-center gap-2 transition-colors shadow-lg shadow-red-500/10"
        >
          <FileText size={18} />
          Export PDF Report
        </button>
        <button
          onClick={() => handleGenerateReport('csv')}
          className="px-6 py-3 bg-green-600 hover:bg-green-700 rounded-lg flex items-center gap-2 transition-colors shadow-lg shadow-green-500/10"
        >
          <Download size={18} />
          Export CSV Data
        </button>
        <button
          onClick={() => handleGenerateReport('json')}
          className="px-6 py-3 bg-blue-600 hover:bg-blue-700 rounded-lg flex items-center gap-2 transition-colors shadow-lg shadow-blue-500/10"
        >
          <Database size={18} />
          Export JSON Data
        </button>
      </div>
    </div>

    {/* Previous Reports */}
    <div className="bg-gray-800/50 backdrop-blur-sm rounded-xl border border-gray-700/50 overflow-hidden">
      <div className="p-6 border-b border-gray-700/50">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-cyan-400">Generated Reports</h3>
          <span className="text-gray-400 text-sm">{reports.length} reports available</span>
        </div>
      </div>
      
      {reports.length > 0 ? (
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-900/50">
              <tr>
                <th className="px-6 py-4 text-left text-cyan-400 font-semibold">Report ID</th>
                <th className="px-6 py-4 text-left text-cyan-400 font-semibold">Generated</th>
                <th className="px-6 py-4 text-left text-cyan-400 font-semibold">Date Range</th>
                <th className="px-6 py-4 text-left text-cyan-400 font-semibold">Sites Included</th>
                <th className="px-6 py-4 text-left text-cyan-400 font-semibold">File Size</th>
                <th className="px-6 py-4 text-left text-cyan-400 font-semibold">Actions</th>
              </tr>
            </thead>
            <tbody>
              {reports.map((report, index) => (
                <tr 
                  key={report.id} 
                  className={`border-t border-gray-700/30 hover:bg-gray-700/30 transition-colors ${
                    index % 2 === 0 ? 'bg-gray-800/20' : 'bg-gray-800/10'
                  }`}
                >
                  <td className="px-6 py-4">
                    <code className="text-gray-300 font-mono text-sm bg-gray-900/50 px-2 py-1 rounded">
                      {report.id}
                    </code>
                  </td>
                  <td className="px-6 py-4 text-gray-300">{report.generatedAt}</td>
                  <td className="px-6 py-4">
                    <span className="text-gray-300 bg-gray-700/50 px-2 py-1 rounded text-sm">
                      {report.dateRange || 'All Time'}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-gray-300">{report.sitesCount.toLocaleString()}</td>
                  <td className="px-6 py-4 text-gray-300">{report.fileSize}</td>
                  <td className="px-6 py-4">
                    <div className="flex gap-2">
                      <button 
                        className="text-cyan-400 hover:text-cyan-300 p-2 hover:bg-cyan-500/10 rounded-lg transition-colors"
                        title="Preview Report"
                      >
                        <Eye size={18} />
                      </button>
                      <button 
                        className="text-green-400 hover:text-green-300 p-2 hover:bg-green-500/10 rounded-lg transition-colors"
                        title="Download Report"
                      >
                        <Download size={18} />
                      </button>
                      <button 
                        className="text-red-400 hover:text-red-300 p-2 hover:bg-red-500/10 rounded-lg transition-colors"
                        title="Delete Report"
                      >
                        ✕
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="p-12 text-center">
          <FileText className="mx-auto mb-4 text-gray-500" size={48} />
          <p className="text-gray-400 text-lg mb-2">No reports generated yet</p>
          <p className="text-gray-500">Generate your first intelligence report using the form above</p>
        </div>
      )}
    </div>
  </div>
);

const renderSettings = (): JSX.Element => (
  <div className="space-y-6 h-full">
    {/* Header */}
    <div className="flex justify-between items-center">
      <div>
        <h2 className="text-2xl font-bold text-white">System Settings</h2>
        <p className="text-gray-400">System configuration and monitoring</p>
      </div>
      <button
        onClick={loadSystemHealth}
        disabled={loading}
        className="px-4 py-2 bg-cyan-600 hover:bg-cyan-700 rounded-lg flex items-center gap-2 disabled:opacity-50 transition-colors"
      >
        <RefreshCw size={18} className={loading ? 'animate-spin' : ''} />
        Refresh Status
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

    {/* System Health */}
    {systemHealth && (
      <div className="bg-gray-800/50 backdrop-blur-sm p-6 rounded-xl border border-gray-700/50">
        <div className="flex items-center gap-2 mb-6">
          <Activity className="text-cyan-400" size={20} />
          <h3 className="text-lg font-semibold text-cyan-400">System Health</h3>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-gradient-to-br from-green-900/30 to-green-800/20 p-4 rounded-lg border border-green-500/20">
            <div className="flex items-center justify-between mb-3">
              <span className="text-gray-400 font-medium">Database</span>
              <span className={`px-2 py-1 rounded text-xs font-semibold ${
                systemHealth.database === 'healthy' ? 'bg-green-900/50 text-green-300 border border-green-500/30' :
                'bg-red-900/50 text-red-300 border border-red-500/30'
              }`}>
                {systemHealth.database}
              </span>
            </div>
            <p className="text-sm text-gray-400">Connections: <span className="text-gray-300">{systemHealth.dbConnections}</span></p>
          </div>
          
          <div className="bg-gradient-to-br from-blue-900/30 to-blue-800/20 p-4 rounded-lg border border-blue-500/20">
            <div className="flex items-center justify-between mb-3">
              <span className="text-gray-400 font-medium">Crawler</span>
              <span className={`px-2 py-1 rounded text-xs font-semibold ${
                systemHealth.crawler === 'active' ? 'bg-green-900/50 text-green-300 border border-green-500/30' :
                'bg-red-900/50 text-red-300 border border-red-500/30'
              }`}>
                {systemHealth.crawler}
              </span>
            </div>
            <p className="text-sm text-gray-400">Active: <span className="text-gray-300">{systemHealth.activeCrawlers}</span></p>
          </div>
          
          <div className="bg-gradient-to-br from-purple-900/30 to-purple-800/20 p-4 rounded-lg border border-purple-500/20">
            <div className="flex items-center justify-between mb-3">
              <span className="text-gray-400 font-medium">Tor Network</span>
              <span className={`px-2 py-1 rounded text-xs font-semibold ${
                systemHealth.tor === 'connected' ? 'bg-green-900/50 text-green-300 border border-green-500/30' :
                'bg-red-900/50 text-red-300 border border-red-500/30'
              }`}>
                {systemHealth.tor}
              </span>
            </div>
            <p className="text-sm text-gray-400">Circuits: <span className="text-gray-300">{systemHealth.torCircuits}</span></p>
          </div>
        </div>
      </div>
    )}

    {/* Crawler Configuration */}
    <div className="bg-gray-800/50 backdrop-blur-sm p-6 rounded-xl border border-gray-700/50">
      <div className="flex items-center gap-2 mb-6">
        <Settings className="text-cyan-400" size={20} />
        <h3 className="text-lg font-semibold text-cyan-400">Crawler Configuration</h3>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
        <div>
          <label className="block text-gray-400 text-sm mb-2 font-medium">Crawl Rate (requests/min)</label>
          <input
            type="number"
            value={crawlerConfig.crawlRate}
            onChange={(e) => setCrawlerConfig({...crawlerConfig, crawlRate: parseInt(e.target.value) || 0})}
            className="w-full px-4 py-3 bg-gray-900/50 border border-gray-600 rounded-lg text-white focus:outline-none focus:border-cyan-500 focus:ring-2 focus:ring-cyan-500/20 transition-all"
            min="1"
            max="100"
          />
          <p className="text-gray-500 text-xs mt-1">Higher rates may trigger rate limiting</p>
        </div>
        
        <div>
          <label className="block text-gray-400 text-sm mb-2 font-medium">Circuit Rotation (requests)</label>
          <input
            type="number"
            value={crawlerConfig.circuitRotation}
            onChange={(e) => setCrawlerConfig({...crawlerConfig, circuitRotation: parseInt(e.target.value) || 0})}
            className="w-full px-4 py-3 bg-gray-900/50 border border-gray-600 rounded-lg text-white focus:outline-none focus:border-cyan-500 focus:ring-2 focus:ring-cyan-500/20 transition-all"
            min="1"
            max="50"
          />
          <p className="text-gray-500 text-xs mt-1">Rotate Tor circuits after N requests</p>
        </div>
        
        <div>
          <label className="block text-gray-400 text-sm mb-2 font-medium">Timeout (seconds)</label>
          <input
            type="number"
            value={crawlerConfig.timeout}
            onChange={(e) => setCrawlerConfig({...crawlerConfig, timeout: parseInt(e.target.value) || 0})}
            className="w-full px-4 py-3 bg-gray-900/50 border border-gray-600 rounded-lg text-white focus:outline-none focus:border-cyan-500 focus:ring-2 focus:ring-cyan-500/20 transition-all"
            min="5"
            max="60"
          />
          <p className="text-gray-500 text-xs mt-1">Request timeout duration</p>
        </div>
      </div>
      <div className="flex gap-4">
        <button
          onClick={handleUpdateConfig}
          className="px-6 py-3 bg-cyan-600 hover:bg-cyan-700 rounded-lg flex items-center gap-2 transition-colors shadow-lg shadow-cyan-500/10"
        >
          <Settings size={18} />
          Update Configuration
        </button>
        <button className="px-6 py-3 bg-gray-600 hover:bg-gray-700 rounded-lg flex items-center gap-2 transition-colors">
          <RefreshCw size={18} />
          Reset to Defaults
        </button>
      </div>
    </div>

    {/* System Information */}
    <div className="bg-gray-800/50 backdrop-blur-sm p-6 rounded-xl border border-gray-700/50">
      <div className="flex items-center gap-2 mb-6">
        <Database className="text-cyan-400" size={20} />
        <h3 className="text-lg font-semibold text-cyan-400">System Information</h3>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-gray-900/30 p-4 rounded-lg border border-gray-600/30">
          <p className="text-gray-400 text-sm mb-1">Version</p>
          <p className="text-white font-medium">OnionTraceX v1.0.0</p>
        </div>
        <div className="bg-gray-900/30 p-4 rounded-lg border border-gray-600/30">
          <p className="text-gray-400 text-sm mb-1">Last Database Update</p>
          <p className="text-white font-medium">{new Date().toLocaleString()}</p>
        </div>
        <div className="bg-gray-900/30 p-4 rounded-lg border border-gray-600/30">
          <p className="text-gray-400 text-sm mb-1">Total Data Collected</p>
          <p className="text-white font-medium">~2.4 GB</p>
        </div>
        <div className="bg-gray-900/30 p-4 rounded-lg border border-gray-600/30">
          <p className="text-gray-400 text-sm mb-1">System Uptime</p>
          <p className="text-white font-medium">24 days, 16 hours</p>
        </div>
      </div>
      
      <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-gray-900/30 p-4 rounded-lg border border-gray-600/30">
          <p className="text-gray-400 text-sm mb-2">Database Statistics</p>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-400">Total Sites:</span>
              <span className="text-white">15,432</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Active Vendors:</span>
              <span className="text-white">892</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">BTC Wallets:</span>
              <span className="text-white">3,567</span>
            </div>
          </div>
        </div>
        
        <div className="bg-gray-900/30 p-4 rounded-lg border border-gray-600/30">
          <p className="text-gray-400 text-sm mb-2">Performance Metrics</p>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-400">Avg Response Time:</span>
              <span className="text-white">4.2s</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Success Rate:</span>
              <span className="text-green-400">94.7%</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Queue Size:</span>
              <span className="text-white">128</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
);


  // Navigation items
  const navItems: NavItem[] = [
    { id: 'dashboard', label: 'Dashboard', icon: BarChart3, description: 'Real-time analytics and overview' },
    {id: 'crawler', label: 'Crawler', icon: SearchCodeIcon, description: 'Crawler Dashboard'},
    { id: 'sites', label: 'Sites Explorer', icon: Search, description: 'Browse and search onion sites' },
    { id: 'vendors', label: 'Vendor Clusters', icon: Users, description: 'Vendor relationship mapping' },
    { id: 'bitcoin', label: 'Bitcoin Analysis', icon: Bitcoin, description: 'Cryptocurrency tracking' },
    { id: 'reports', label: 'Reports', icon: FileText, description: 'Generate intelligence reports' },
    { id: 'settings', label: 'Settings', icon: Settings, description: 'System configuration' }
  ];

  // Main render
  return (
    <div className="flex h-screen bg-gradient-to-br from-gray-900 to-gray-950 text-white overflow-hidden">
      {/* Sidebar */}
      <div className={`${sidebarCollapsed ? 'w-20' : 'w-64'} bg-gray-800/80 backdrop-blur-sm border-r border-gray-700/50 flex flex-col transition-all duration-300`}>
        {/* Logo */}
        <div className="p-6 border-b border-gray-700/50">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-cyan-500/20 rounded-lg">
              <Shield className="text-cyan-400" size={24} />
            </div>
            {!sidebarCollapsed && (
              <div>
                <h1 className="text-xl font-bold text-cyan-400">OnionTraceX</h1>
                <p className="text-gray-400 text-xs">Dark Web Intelligence</p>
              </div>
            )}
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-4 space-y-1">
          {navItems.map((item) => (
            <button
              key={item.id}
              onClick={() => setActiveSection(item.id)}
              className={`w-full flex items-center gap-3 px-3 py-3 rounded-xl transition-all duration-200 group ${
                activeSection === item.id 
                  ? 'bg-cyan-600/20 text-cyan-400 border border-cyan-500/30 shadow-lg shadow-cyan-500/10' 
                  : 'text-gray-300 hover:bg-gray-700/50 hover:text-white border border-transparent'
              }`}
              title={sidebarCollapsed ? item.label : ''}
            >
              <item.icon size={20} className="flex-shrink-0" />
              {!sidebarCollapsed && (
                <div className="flex-1 text-left">
                  <div className="font-medium">{item.label}</div>
                  <div className="text-xs text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity">
                    {item.description}
                  </div>
                </div>
              )}
            </button>
          ))}
        </nav>

        {/* System Status */}
        <div className="p-4 border-t border-gray-700/50">
          {!sidebarCollapsed && (
            <>
              <div className="flex items-center justify-between mb-2">
                <span className="text-gray-400 text-sm">System Status</span>
                <div className="w-3 h-3 bg-green-500 rounded-full animate-pulse"></div>
              </div>
              <p className="text-xs text-gray-500">All systems operational</p>
            </>
          )}
          <button
            onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
            className="w-full mt-3 p-2 text-gray-400 hover:text-white hover:bg-gray-700/50 rounded-lg transition-colors"
          >
            {sidebarCollapsed ? '→' : '←'}
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top Bar */}
        <header className="bg-gray-800/80 backdrop-blur-sm border-b border-gray-700/50 p-4">
          <div className="flex justify-between items-center">
            <div>
              <h2 className="text-xl font-semibold text-white capitalize">
                {activeSection.replace(/([A-Z])/g, ' $1').trim()}
              </h2>
              <p className="text-gray-400 text-sm">
                {navItems.find(item => item.id === activeSection)?.description}
              </p>
            </div>
            <div className="flex items-center gap-4">
              <div className="text-right">
                <p className="text-sm text-gray-300">Analyst</p>
                <p className="text-xs text-gray-500">admin@oniontracex.gov</p>
              </div>
              <div className="w-10 h-10 bg-gradient-to-br from-cyan-500 to-blue-600 rounded-full flex items-center justify-center shadow-lg">
                <span className="font-semibold text-white">A</span>
              </div>
            </div>
          </div>
        </header>

        {/* Content Area */}
        <main className="flex-1 overflow-auto p-6">
          {activeSection === 'dashboard' && renderDashboard()}
          {activeSection === "crawler" && <CrawlerControlPanel />}
          {activeSection === 'sites' && <SitesExplorer/>}
          {activeSection === 'vendors' && renderVendors()}
          {activeSection === "bitcoin" && <BitcoinAnalysis />}
          {activeSection === 'reports' && renderReports()}
          {activeSection === 'settings' && renderSettings()}
        </main>
      </div>
    </div>
  );
};

export default OnionTraceX;
