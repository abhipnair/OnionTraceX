import React, { useEffect, useState } from "react";
import { RefreshCw } from "lucide-react";

interface VendorNetworkGraphProps {
  data: {
    nodes: any[];
    links: any[];
  } | null;
  loading?: boolean;
}

/* ================== CONSTANTS ================== */

const EDGE_COLORS: Record<string, string> = {
  pgp: "#ef4444",    // red
  xmr: "#10b981",    // green
  email: "#3b82f6"   // blue
};

const VendorNetworkGraph: React.FC<VendorNetworkGraphProps> = ({ data, loading }) => {
  const [nodePositions, setNodePositions] = useState<Record<string, { x: number; y: number }>>({});
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isPanning, setIsPanning] = useState(false);
  const [startPan, setStartPan] = useState({ x: 0, y: 0 });

  /* ================== ZOOM / PAN ================== */

  const handleZoomIn = () => setZoom(z => Math.min(z * 1.3, 5));
  const handleZoomOut = () => setZoom(z => Math.max(z / 1.3, 0.3));
  const handleZoomReset = () => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
  };

  const handleMouseDown = (e: React.MouseEvent) => {
    setIsPanning(true);
    setStartPan({ x: e.clientX - pan.x, y: e.clientY - pan.y });
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isPanning) return;
    setPan({ x: e.clientX - startPan.x, y: e.clientY - startPan.y });
  };

  const handleMouseUp = () => setIsPanning(false);

  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    const factor = e.deltaY > 0 ? 0.9 : 1.1;
    setZoom(z => Math.max(0.3, Math.min(5, z * factor)));
  };

  /* ================== FORCE LAYOUT ================== */

  useEffect(() => {
    if (!data || !data.nodes?.length) return;

    const width = 1200;
    const height = 800;
    const positions: Record<string, { x: number; y: number }> = {};

    data.nodes.forEach((node, i) => {
      const angle = (i / data.nodes.length) * 2 * Math.PI;
      const radius = Math.min(width, height) * 0.4;
      positions[node.id] = {
        x: width / 2 + radius * Math.cos(angle),
        y: height / 2 + radius * Math.sin(angle)
      };
    });

    for (let i = 0; i < 100; i++) {
      data.nodes.forEach(a => {
        data.nodes.forEach(b => {
          if (a.id === b.id) return;
          const dx = positions[b.id].x - positions[a.id].x;
          const dy = positions[b.id].y - positions[a.id].y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < 150) {
            const f = 150 / (dist * dist);
            positions[a.id].x -= dx * f * 0.2;
            positions[a.id].y -= dy * f * 0.2;
          }
        });
      });

      data.links.forEach(link => {
        const s = positions[link.source];
        const t = positions[link.target];
        if (!s || !t) return;
        const dx = t.x - s.x;
        const dy = t.y - s.y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        const f = (dist - 200) * 0.01;
        s.x += dx * f * 0.1;
        s.y += dy * f * 0.1;
        t.x -= dx * f * 0.1;
        t.y -= dy * f * 0.1;
      });
    }

    setNodePositions(positions);
  }, [data]);

  /* ================== CLUSTER STATS ================== */

  const vendorEdgeStats: Record<string, { pgp: number; xmr: number; email: number }> = {};

  data?.links.forEach(l => {
    [l.source, l.target].forEach(v => {
      if (!vendorEdgeStats[v]) {
        vendorEdgeStats[v] = { pgp: 0, xmr: 0, email: 0 };
      }
      if (l.type && l.type in vendorEdgeStats[v]) {
        vendorEdgeStats[v][l.type]++;
      }
    });
  });

  /* ================== LOADING ================== */

  if (loading || !data || !Object.keys(nodePositions).length) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-gray-400">
        <RefreshCw className="animate-spin text-cyan-500 mb-3" size={36} />
        <p>Rendering vendor network…</p>
      </div>
    );
  }

  /* ================== RENDER ================== */

  return (
    <div className="relative w-full h-full">
      {/* Controls */}
      <div className="absolute top-4 right-4 z-10 flex flex-col gap-2 bg-gray-900/90 p-3 rounded-xl">
        <button onClick={handleZoomIn}>+</button>
        <button onClick={handleZoomOut}>−</button>
        <button onClick={handleZoomReset}>⟲</button>
      </div>

      {/* Legend */}
      <div className="absolute bottom-4 left-4 bg-gray-900/90 p-4 rounded-xl text-sm border border-gray-700 space-y-2 z-10">
        <div className="font-semibold text-cyan-400">Legend</div>
        <div className="flex items-center gap-2">
          <span className="w-4 h-1 bg-red-500"></span> PGP Shared
        </div>
        <div className="flex items-center gap-2">
          <span className="w-4 h-1 bg-green-500"></span> XMR Reuse
        </div>
        <div className="flex items-center gap-2">
          <span className="w-4 h-1 bg-blue-500"></span> Email Reuse
        </div>
      </div>

      <svg
        viewBox="0 0 1200 800"
        className="w-full h-full"
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        onWheel={handleWheel}
        style={{
          transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
          transformOrigin: "center"
        }}
      >
        {/* Links */}
        {data.links.map((l, i) => {
          const s = nodePositions[l.source];
          const t = nodePositions[l.target];
          if (!s || !t) return null;
          return (
            <line
              key={i}
              x1={s.x}
              y1={s.y}
              x2={t.x}
              y2={t.y}
              stroke={EDGE_COLORS[l.type] || "#4b5563"}
              strokeWidth={Math.min(6, (l.value || 1) * 2)}
              opacity={0.75}
            />
          );
        })}

        {/* Nodes */}
        {data.nodes.map(n => {
          const p = nodePositions[n.id];
          if (!p) return null;

          const stats = vendorEdgeStats[n.id] || { pgp: 0, xmr: 0, email: 0 };

          return (
            <g key={n.id} transform={`translate(${p.x}, ${p.y})`}>
              <circle r={n.size || 14} fill={n.color || "#06b6d4"} />

              <text y={-(n.size || 14) - 6} textAnchor="middle" fontSize="12" fill="#e5e7eb">
                {n.name}
              </text>

              {stats.pgp >= 3 && (
                <text y={(n.size || 14) + 14} textAnchor="middle" fontSize="10" fill="#ef4444">
                  PGP Cluster
                </text>
              )}

              {stats.xmr >= 3 && (
                <text y={(n.size || 14) + 26} textAnchor="middle" fontSize="10" fill="#10b981">
                  XMR Reuse
                </text>
              )}

              {stats.email >= 3 && (
                <text y={(n.size || 14) + 38} textAnchor="middle" fontSize="10" fill="#3b82f6">
                  Email Reuse
                </text>
              )}
            </g>
          );
        })}
      </svg>
    </div>
  );
};

export default VendorNetworkGraph;
