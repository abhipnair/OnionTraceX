import { useEffect, useState } from "react"
import {
  Bitcoin,
  RefreshCw,
  AlertCircle,
  Activity,
  TrendingUp,
  Network
} from "lucide-react"

interface BitcoinStats {
  totalWallets: number
  totalTransactions: number
  suspectedMixers: number
  totalVolume: number
}

interface Wallet {
  address: string
  balance: number | string
  transactionCount: number
  firstSeen: string
  lastActivity: string
  linkedSites?: string[]
  riskScore: number
}

interface BitcoinData {
  stats: BitcoinStats
  wallets: Wallet[]
  network?: any
}

const API_URL = "http://localhost:5000/api/bitcoin/wallets"

const BitcoinAnalysis = (): JSX.Element => {
  const [btcData, setBtcData] = useState<BitcoinData | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const loadBitcoinData = async () => {
    try {
      setLoading(true)
      setError(null)

      const res = await fetch(API_URL)
      if (!res.ok) throw new Error("Failed to fetch bitcoin data")

      const json = await res.json()
      if (!json.success) throw new Error(json.error || "Bitcoin API error")

      // ---- Normalize API → UI ----
      setBtcData({
        stats: {
          totalWallets: json.data.stats?.totalWallets ?? 0,
          totalTransactions: json.data.stats?.totalTransactions ?? 0,
          suspectedMixers: json.data.stats?.suspectedMixers ?? 0,
          totalVolume: json.data.stats?.totalVolume ?? 0
        },
        wallets: (json.data.wallets || []).map((w: any) => ({
          address: w.address,
          balance: w.balance ?? "N/A",
          transactionCount: w.transactionCount ?? 0,
          firstSeen: w.firstSeen ?? "N/A",
          lastActivity: w.lastActivity ?? "N/A",
          linkedSites: w.linkedSites ?? [],
          riskScore:
            w.riskScore ??
            Math.min(95, 20 + (w.transactionCount || 1) * 4)
        })),
        network: json.data.network ?? null
      })
    } catch (err: any) {
      setError(err.message || "Unknown error")
    } finally {
      setLoading(false)
    }
  }

  // Auto-load on mount
  useEffect(() => {
    loadBitcoinData()
  }, [])

  /* ===================== UI ===================== */

  return (
    <div className="space-y-6 h-full">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-white">Bitcoin Analysis</h2>
          <p className="text-gray-400">
            Cryptocurrency transaction tracking and analysis
          </p>
        </div>
        <button
          onClick={loadBitcoinData}
          disabled={loading}
          className="px-4 py-2 bg-cyan-600 hover:bg-cyan-700 rounded-lg flex items-center gap-2 disabled:opacity-50 transition-colors"
        >
          <RefreshCw size={18} className={loading ? "animate-spin" : ""} />
          Refresh
        </button>
      </div>

      {error && (
        <div className="bg-red-900/50 border border-red-500 text-red-200 p-4 rounded-lg flex items-center gap-2">
          <AlertCircle size={20} />
          <span>Error: {error}</span>
        </div>
      )}

      {/* Stats */}
      {btcData?.stats && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {[
            ["Tracked Wallets", btcData.stats.totalWallets, Bitcoin, "yellow"],
            [
              "Total Transactions",
              btcData.stats.totalTransactions,
              Activity,
              "green"
            ],
            [
              "Suspected Mixers",
              btcData.stats.suspectedMixers,
              AlertCircle,
              "purple"
            ],
            ["Total Volume", `${btcData.stats.totalVolume} BTC`, TrendingUp, "blue"]
          ].map(([label, value, Icon, color]: any, i) => (
            <div
              key={i}
              className={`bg-${color}-900/40 p-4 rounded-xl border border-${color}-500/30`}
            >
              <div className="flex justify-between items-center">
                <div>
                  <p className="text-gray-400 text-sm">{label}</p>
                  <p className={`text-2xl font-bold text-${color}-400`}>
                    {value}
                  </p>
                </div>
                <div className={`p-2 bg-${color}-500/20 rounded-lg`}>
                  <Icon className={`text-${color}-400`} size={24} />
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Network Graph (placeholder) */}
      <div className="bg-gray-800/50 p-6 rounded-xl border border-gray-700/50">
        <div className="flex items-center gap-2 mb-4">
          <Network className="text-cyan-400" size={20} />
          <h3 className="text-lg font-semibold text-cyan-400">
            Bitcoin Transaction Network
          </h3>
        </div>
        <div className="min-h-[300px] flex items-center justify-center text-gray-500">
          {loading ? "Loading network…" : "Graph rendering coming next"}
        </div>
      </div>

      {/* Wallet Table */}
      {btcData?.wallets?.length ? (
        <div className="bg-gray-800/50 rounded-xl border border-gray-700/50 overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-900/50">
              <tr>
                {[
                  "Wallet",
                  "Balance",
                  "Txns",
                  "First Seen",
                  "Last Activity",
                  "Risk"
                ].map(h => (
                  <th
                    key={h}
                    className="px-6 py-4 text-left text-cyan-400"
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {btcData.wallets.map((w, i) => (
                <tr
                  key={w.address}
                  className={`border-t border-gray-700/30 ${
                    i % 2 ? "bg-gray-800/10" : "bg-gray-800/20"
                  }`}
                >
                  <td className="px-6 py-4 font-mono text-sm">
                    {w.address.slice(0, 12)}…{w.address.slice(-8)}
                  </td>
                  <td className="px-6 py-4 text-yellow-400">{w.balance}</td>
                  <td className="px-6 py-4">{w.transactionCount}</td>
                  <td className="px-6 py-4">{w.firstSeen}</td>
                  <td className="px-6 py-4">{w.lastActivity}</td>
                  <td className="px-6 py-4">
                    <span
                      className={`px-3 py-1 rounded-full text-xs ${
                        w.riskScore >= 80
                          ? "bg-red-900/50 text-red-300"
                          : w.riskScore >= 60
                          ? "bg-yellow-900/50 text-yellow-300"
                          : "bg-green-900/50 text-green-300"
                      }`}
                    >
                      {w.riskScore}/100
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        !loading && (
          <div className="text-center text-gray-500 py-12">
            No bitcoin data available
          </div>
        )
      )}
    </div>
  )
}

export default BitcoinAnalysis
