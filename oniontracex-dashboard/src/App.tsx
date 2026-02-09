import React, { useState, useEffect } from 'react';

import { 
  Search, Globe, Users, Settings, Activity, 
  Database, TrendingUp, AlertCircle, Clock,
  RefreshCw, Shield, Bitcoin, Server, BarChart3,
  SearchCodeIcon, FileText
} from 'lucide-react';

// Import interfaces
import {
  Stats, LivenessData, CategoryData, KeywordData, Site, SiteDetails,
  Vendor, VendorNetwork, BitcoinData,
  SystemHealth, CrawlerConfig
} from './types';

import CrawlerControlPanel from "./CrawlerControlPanel";
import DashboardCharts from "./DashboardCharts";
import SitesExplorer from "./SitesExplorer";
import BitcoinAnalysis from "./BitcoinAnalysis";
import VendorNetworkGraph from "./VendorNetworkGraph";
import Reports from "./Reports";




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

  async fetchVendorsOverview(): Promise<{
    vendors: Vendor[];
    network: VendorNetwork;
  }> {
    const response = await fetch(`${API_BASE_URL}/vendors/overview`);
    if (!response.ok) throw new Error("Failed to fetch vendor overview");

    const result = await response.json();
    if (!result.success) throw new Error(result.error || "API request failed");

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

  // ---------------- Vendor Network Helpers ----------------
  const vendorGraphData = vendorNetwork;



  // Bitcoin state
  const [btcData, setBtcData] = useState<BitcoinData | null>(null);


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
      const overview = await apiService.fetchVendorsOverview();

      setVendorData(overview.vendors);          // table / metadata
      setVendorNetwork(overview.network);       // graph (nodes + links)

    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred");
      console.error("Error loading vendors:", err);
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
          {activeSection === "vendors" && <VendorNetworkGraph data={vendorGraphData} loading={loading} />}
          {activeSection === "bitcoin" && <BitcoinAnalysis />}
          {activeSection === 'reports' && <Reports />}
          {activeSection === 'settings' && renderSettings()}
        </main>
      </div>
    </div>
  );
};

export default OnionTraceX;
