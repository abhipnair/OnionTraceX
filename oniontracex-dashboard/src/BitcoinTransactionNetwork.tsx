import ForceGraph2D from "react-force-graph-2d"
import { AlertTriangle, Circle } from "lucide-react"

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
  }
}

const BitcoinTransactionNetwork = ({ data }: Props): JSX.Element => {
  if (!data || !data.nodes?.length) {
    return (
      <div className="text-center text-gray-500 py-16">
        No transaction network data available
      </div>
    )
  }

  return (
    <div className="relative w-full h-[420px] bg-gray-900/40 rounded-lg border border-gray-700/50">
      
      {/* ================= GRAPH ================= */}
      <ForceGraph2D
        graphData={data}
        backgroundColor="transparent"
        nodeLabel={(n: any) =>
          `Wallet: ${n.id}
Fan-In: ${n.fanIn}
Fan-Out: ${n.fanOut}
Risk Score: ${n.riskScore}
${n.isMixer ? "⚠ Suspected Mixer" : "Normal Wallet"}`
        }
        nodeCanvasObject={(node: any, ctx) => {
          const radius = node.isMixer ? 10 : 6

          ctx.beginPath()
          ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI)

          // Mixer → red, normal → green
          ctx.fillStyle = node.isMixer ? "#ef4444" : "#22c55e"
          ctx.fill()

          // Outline
          ctx.lineWidth = 1
          ctx.strokeStyle = "#0f172a"
          ctx.stroke()
        }}
        linkColor={() => "#f59e0b"}
        linkWidth={(l: any) => Math.max(1, Math.log(l.amount + 1))}
        cooldownTicks={100}
      />

      {/* ================= LEGEND ================= */}
      <div className="absolute top-4 right-4 bg-gray-900/80 backdrop-blur-md border border-gray-700 rounded-lg p-3 space-y-2 text-xs text-gray-300">
        <div className="font-semibold text-cyan-400 mb-1">
          Network Indicators
        </div>

        <div className="flex items-center gap-2">
          <Circle size={10} className="text-green-500 fill-green-500" />
          <span>Normal Wallet</span>
        </div>

        <div className="flex items-center gap-2">
          <AlertTriangle size={12} className="text-red-400" />
          <span>Suspected Mixer</span>
        </div>

        <div className="flex items-center gap-2">
          <div className="w-4 h-[2px] bg-yellow-400"></div>
          <span>Transaction Flow</span>
        </div>

        <div className="text-gray-400 pt-1 border-t border-gray-700">
          Node size ↑ = mixer likelihood
        </div>
      </div>
    </div>
  )
}

export default BitcoinTransactionNetwork
