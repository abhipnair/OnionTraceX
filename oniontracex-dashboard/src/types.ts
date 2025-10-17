export interface Stats {
  totalSites: number;
  alivePercent: number;
  deadPercent: number;
  timeoutPercent: number;
  activeCrawlers: number;
  avgCrawlTime: number;
  totalVendors?: number;        // Added from backend
  totalWallets?: number;        // Added from backend
}

export interface LivenessData {
  date: string;
  alive: number;
  dead: number;
  timeout: number;
}

export interface CategoryData {
  name: string;
  value: number;
  color: string;
}

export interface KeywordData {
  keyword: string;
  discovered: number;
}

export interface Site {
  id: string;
  url: string;
  category: string;
  status: 'Alive' | 'Dead' | 'Timeout'; // Made more specific
  firstSeen: string;
  lastSeen: string;
  source: string;
  title?: string;               // Moved from SiteDetails since backend includes it
  metadata?: any;               // Moved from SiteDetails since backend includes it
}

export interface SiteDetails extends Site {
  // These are now in the base Site interface since backend returns them
}

export interface Vendor {
  id: string;
  alias: string;
  marketplaces: string[];       // Changed from optional to required
  wallets: string[];            // Changed from optional to required
  pgpKey: string | null;        // Made more specific (can be null)
  status: 'Active' | 'Inactive' | 'Suspended' | 'Banned'; // Made more specific
  lastSeen: string;
  joinDate?: string;            // Added from backend
  reputation?: number;          // Added from backend
  totalListings?: number;       // Added from backend
  totalSales?: number;          // Added from backend
  avgRating?: number;           // Added from backend
  followers?: number;           // Added from backend
  description?: string;         // Added from backend
}

export interface VendorNetwork {
  nodes: Array<{
    id: string;
    alias: string;
    status: string;
    reputation: number;
    size: number;
  }>;
  edges: Array<{
    source: string;
    target: string;
    weight: number;
    type: string;
  }>;
  nodeCount?: number;
  edgeCount?: number;
}

export interface BitcoinData {
  stats: {
    totalWallets: number;
    totalTransactions: number;
    suspectedMixers: number;
    totalVolume: number;
    highRiskWallets?: number;   // Added from backend
    averageBalance?: number;    // Added from backend
  };
  wallets: BitcoinWallet[];
  network?: {
    totalNodes: number;
    totalTransactions: number;
    densityScore: number;
  };
}

export interface BitcoinWallet {
  address: string;
  balance: number;
  transactionCount: number;
  firstSeen: string;
  lastActivity: string;
  linkedSites: string[];        // Changed from optional to required
  riskScore: number;
  totalReceived?: number;       // Added from backend
  totalSent?: number;           // Added from backend
  usedInTransactions?: number;  // Added from backend
  isMixer?: boolean;            // Added from backend
  exchangeLinks?: string[];     // Added from backend
  illicitActivity?: string;     // Added from backend
}

export interface Report {
  id: string;
  generatedAt: string;
  dateRange: string;
  sitesCount: number;
  fileSize: string;
  status?: string;              // Added from backend
  vendorCount?: number;         // Added from backend
  bitcoinAnalyzed?: number;     // Added from backend
}

export interface ReportConfig {
  dateRange: string;
  category: string;
  includeMetadata: boolean;
  includeVendors: boolean;
  includeBitcoin: boolean;
}

export interface SystemHealth {
  database: string;
  dbConnections: number;
  crawler: string;
  activeCrawlers: number;
  tor: string;
  torCircuits: number;
  memoryUsage?: number;         // Added from backend
  cpuUsage?: number;            // Added from backend
  diskSpace?: number;           // Added from backend
  uptime?: string;              // Added from backend
}

export interface CrawlerConfig {
  crawlRate: number;
  circuitRotation: number;
  timeout: number;
}

// Optional: Add API response wrapper interface
export interface ApiResponse<T> {
  success: boolean;
  data: T;
  error?: string;
  pagination?: {
    page: number;
    page_size: number;
    total: number;
    pages: number;
  };
}