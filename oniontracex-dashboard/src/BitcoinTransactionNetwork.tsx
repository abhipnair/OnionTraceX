import ForceGraph2D from "react-force-graph-2d"
import {
  AlertTriangle,
  ArrowDownLeft,
  ArrowUpRight,
  ArrowRightLeft
} from "lucide-react"

interface NetworkNode {
  id: string
  fanIn: number
  fanOut: number
  isMixer: boolean
  riskScore: number
}

interface NetworkLink {
  source: string
  target: string
  amount: number
}

interface Props {
  data: {
    nodes: NetworkNode[]
    links: NetworkLink[]
  } | null
}

const BitcoinTransactionNetwork = ({ data }: Props): JSX.Element => {
  if (!data || !data.nodes.length || !data.links.length) {
    return (
      <div className="h-[360px] flex items-center justify-center text-gray-500">
        No transaction network available
      </div>
    )
  }

  /* ---------- FLOW BALANCE PER NODE ---------- */
  const flowBalance: Record<string, number> = {}

  data.links.forEach(l => {
    flowBalance[l.target] = (flowBalance[l.target] || 0) + l.amount
    flowBalance[l.source] = (flowBalance[l.source] || 0) - l.amount
  })

  /* ---------- NODE COLOR ---------- */
  const nodeColor = (n: any) => {
    if (n.isMixer) return "#ef4444"        // Mixer
    if (flowBalance[n.id] > 0) return "#22c55e" // Inbound
    if (flowBalance[n.id] < 0) return "#f97316" // Outbound
    return "#facc15" // Balanced
  }

  return (
    <div className="relative w-full h-[380px] rounded-xl overflow-hidden bg-gradient-to-br from-gray-900/70 to-gray-800/40 border border-gray-700/50">

      <ForceGraph2D
        graphData={data}

        /* ================= PHYSICS ================= */
        warmupTicks={250}
        cooldownTicks={400}
        d3AlphaDecay={0.015}
        d3VelocityDecay={0.35}
        nodeRelSize={6}
        enableNodeDrag={true}

        d3Force="charge"
        d3ForceConfig={{
          strength: -280,
          distanceMax: 420
        }}

        /* ================= NODE LABEL ================= */
        nodeLabel={(n: any) => `
Wallet: ${n.id}
────────────────
Fan-In: ${n.fanIn}
Fan-Out: ${n.fanOut}
Risk Score: ${n.riskScore}/100
${flowBalance[n.id] > 0 ? "⬇ Mostly Receiving BTC" : ""}
${flowBalance[n.id] < 0 ? "⬆ Mostly Sending BTC" : ""}
${n.isMixer ? "⚠ Suspected Mixer" : ""}
        `}

        /* ================= NODE DRAW ================= */
        nodeCanvasObject={(node: any, ctx, scale) => {
          const radius = 6 + (node.riskScore / 100) * 12

          ctx.beginPath()
          ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI)
          ctx.fillStyle = nodeColor(node)
          ctx.fill()

          // Mixer glow
          if (node.isMixer) {
            ctx.shadowColor = "#ef4444"
            ctx.shadowBlur = 14
          } else {
            ctx.shadowBlur = 0
          }

          ctx.lineWidth = 1.5 / scale
          ctx.strokeStyle = "#020617"
          ctx.stroke()
        }}

        /* ================= LINKS ================= */
        linkColor={(l: any) =>
          flowBalance[l.source] < 0 ? "#ef4444" : "#22c55e"
        }

        linkWidth={(l: any) =>
          Math.max(1.5, Math.log(l.amount + 1))
        }

        linkDirectionalParticles={2}
        linkDirectionalParticleSpeed={(l: any) =>
          Math.min(0.03, l.amount / 30)
        }
      />

      {/* ================= LEGEND ================= */}
      <div className="absolute top-3 right-3 bg-gray-900/85 border border-gray-700 rounded-lg p-3 text-xs text-gray-300 space-y-2 w-[220px]">

        <div className="text-cyan-400 font-semibold">
          Transaction Flow Legend
        </div>

        <div className="flex items-center gap-2">
          <ArrowDownLeft size={12} className="text-green-400" />
          Mostly Receiving BTC
        </div>

        <div className="flex items-center gap-2">
          <ArrowUpRight size={12} className="text-orange-400" />
          Mostly Sending BTC
        </div>

        <div className="flex items-center gap-2">
          <ArrowRightLeft size={12} className="text-yellow-400" />
          Balanced Activity
        </div>

        <div className="flex items-center gap-2">
          <AlertTriangle size={12} className="text-red-400" />
          Suspected Mixer
        </div>

        <div className="pt-2 border-t border-gray-700 text-gray-400 leading-snug">
          • Node size → Risk score<br />
          • Line width → BTC amount<br />
          • Moving dots → Money direction
        </div>
      </div>
    </div>
  )
}

export default BitcoinTransactionNetwork
