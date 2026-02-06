import { useEffect, useState } from "react"
import {
  Bitcoin,
  RefreshCw,
  AlertCircle,
  Activity,
  TrendingUp,
  Network
} from "lucide-react"

import BitcoinTransactionNetwork from "./BitcoinTransactionNetwork"

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

interface BitcoinNetwork {
  nodes: any[]
  links: any[]
}

interface BitcoinData {
  stats: BitcoinStats
  wallets: Wallet[]
  network: BitcoinNetwork | null
}

const WALLET_API = "http://localhost:5000/api/bitcoin/wallets"
const NETWORK_API = "http://localhost:5000/api/bitcoin/network"

const BitcoinAnalysis = (): JSX.Element => {
  const [btcData, setBtcData] = useState<BitcoinData | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const loadBitcoinData = async () => {
    try {
      setLoading(true)
      setError(null)

      const [walletRes, networkRes] = await Promise.all([
        fetch(WALLET_API),
        fetch(NETWORK_API)
      ])

      if (!walletRes.ok) throw new Error("Wallet API failed")
      if (!networkRes.ok) throw new Error("Network API failed")

      const walletJson = await walletRes.json()
      const networkJson = await networkRes.json()

      if (!walletJson.success) throw new Error(walletJson.error)
      if (!networkJson.success) throw new Error(networkJson.error)

      setBtcData({
        stats: {
          totalWallets: walletJson.data.stats.totalWallets,
          totalTransactions: walletJson.data.stats.totalTransactions,
          suspectedMixers: walletJson.data.stats.suspectedMixers,
          totalVolume: walletJson.data.stats.totalVolume
        },
        wallets: walletJson.data.wallets,
        network: networkJson.data
      })
    } catch (e: any) {
      setError(e.message || "Unknown error")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadBitcoinData()
  }, [])

  return (
    <div className="space-y-6 h-full">

      {/* HEADER */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-white">Bitcoin Analysis</h2>
          <p className="text-gray-400">
            Real blockchain transaction flow visualization
          </p>
        </div>

        <button
          onClick={loadBitcoinData}
          disabled={loading}
          className="px-4 py-2 bg-cyan-600 hover:bg-cyan-700 rounded-lg flex items-center gap-2"
        >
          <RefreshCw size={18} className={loading ? "animate-spin" : ""} />
          Refresh
        </button>
      </div>

      {/* ERROR */}
      {error && (
        <div className="bg-red-900/40 border border-red-600 text-red-200 p-4 rounded-lg flex items-center gap-2">
          <AlertCircle size={18} />
          {error}
        </div>
      )}

      {/* STATS */}
      {btcData?.stats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {[
            ["Wallets", btcData.stats.totalWallets, Bitcoin, "yellow"],
            ["Transactions", btcData.stats.totalTransactions, Activity, "green"],
            ["Mixers", btcData.stats.suspectedMixers, AlertCircle, "red"],
            ["Volume", `${btcData.stats.totalVolume} BTC`, TrendingUp, "blue"]
          ].map(([label, value, Icon, color]: any, i) => (
            <div
              key={i}
              className={`bg-${color}-900/30 border border-${color}-600/30 rounded-xl p-4`}
            >
              <div className="flex justify-between">
                <div>
                  <p className="text-gray-400 text-sm">{label}</p>
                  <p className={`text-2xl font-bold text-${color}-400`}>
                    {value}
                  </p>
                </div>
                <Icon className={`text-${color}-400`} />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* NETWORK GRAPH */}
      <div className="bg-gray-800/50 p-6 rounded-xl border border-gray-700/50">
        <div className="flex items-center gap-2 mb-4">
          <Network className="text-cyan-400" />
          <h3 className="text-lg font-semibold text-cyan-400">
            Bitcoin Transaction Network
          </h3>
        </div>

        <BitcoinTransactionNetwork data={btcData?.network ?? null} />
      </div>

      {/* WALLET TABLE */}
      {btcData?.wallets?.length && (
        <div className="bg-gray-800/50 rounded-xl border border-gray-700/50 overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-900/50">
              <tr>
                {["Wallet", "Balance", "Txns", "First Seen", "Last Activity", "Risk"]
                  .map(h => (
                    <th key={h} className="px-6 py-4 text-cyan-400 text-left">
                      {h}
                    </th>
                  ))}
              </tr>
            </thead>
            <tbody>
              {btcData.wallets.map((w, i) => (
                <tr key={w.address} className="border-t border-gray-700/30">
                  <td className="px-6 py-3 font-mono">
                    {w.address.slice(0, 12)}…{w.address.slice(-8)}
                  </td>
                  <td className="px-6 py-3 text-yellow-400">{w.balance}</td>
                  <td className="px-6 py-3">{w.transactionCount}</td>
                  <td className="px-6 py-3">{w.firstSeen}</td>
                  <td className="px-6 py-3">{w.lastActivity}</td>
                  <td className="px-6 py-3">
                    <span className={`px-3 py-1 rounded-full text-xs ${
                      w.riskScore >= 80
                        ? "bg-red-900/50 text-red-300"
                        : w.riskScore >= 60
                        ? "bg-yellow-900/50 text-yellow-300"
                        : "bg-green-900/50 text-green-300"
                    }`}>
                      {w.riskScore}/100
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

    </div>
  )
}

export default BitcoinAnalysis
