import React, { useEffect, useState } from "react";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
} from "recharts";
import { BarChart3, PieChart as PieIcon, TrendingUp } from "lucide-react";

const API_BASE = "http://localhost:5000/api";

const DashboardCharts: React.FC = () => {
  const [livenessData, setLivenessData] = useState<any[]>([]);
  const [categoryData, setCategoryData] = useState<any[]>([]);
  const [keywordData, setKeywordData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchAllCharts = async () => {
    try {
      setLoading(true);
      const [livenessRes, categoryRes, keywordRes] = await Promise.all([
        fetch(`${API_BASE}/liveness?days=30`),
        fetch(`${API_BASE}/categories`),
        fetch(`${API_BASE}/keywords`),
      ]);

      const livenessJson = await livenessRes.json();
      const categoryJson = await categoryRes.json();
      const keywordJson = await keywordRes.json();

      setLivenessData(livenessJson.data || []);
      setCategoryData(categoryJson.data || []);
      setKeywordData(keywordJson.data || []);
    } catch (err) {
      console.error("Error loading chart data:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAllCharts();
  }, []);

  if (loading) {
    return (
      <div className="flex justify-center items-center py-12 text-gray-400">
        Loading charts...
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
      {/* Liveness Over Time */}
      <div className="bg-gray-800/50 backdrop-blur-sm p-6 rounded-xl border border-gray-700/50">
        <div className="flex items-center gap-2 mb-4">
          <BarChart3 className="text-cyan-400" size={20} />
          <h3 className="text-lg font-semibold text-cyan-400">
            Liveness Over Time
          </h3>
        </div>
        <ResponsiveContainer width="100%" height={300}>
          <AreaChart data={livenessData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.3} />
            <XAxis dataKey="date" stroke="#9CA3AF" fontSize={12} />
            <YAxis stroke="#9CA3AF" fontSize={12} />
            <Tooltip
              contentStyle={{
                backgroundColor: "rgba(17, 24, 39, 0.9)",
                border: "1px solid #374151",
                borderRadius: "8px",
                backdropFilter: "blur(8px)",
              }}
            />
            <Legend />
            <Area
              type="monotone"
              dataKey="alive"
              stackId="1"
              stroke="#10b981"
              fill="#10b981"
              fillOpacity={0.6}
              strokeWidth={2}
            />
            <Area
              type="monotone"
              dataKey="dead"
              stackId="1"
              stroke="#ef4444"
              fill="#ef4444"
              fillOpacity={0.6}
              strokeWidth={2}
            />
            <Area
              type="monotone"
              dataKey="timeout"
              stackId="1"
              stroke="#f59e0b"
              fill="#f59e0b"
              fillOpacity={0.6}
              strokeWidth={2}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Domain Categories */}
      <div className="bg-gray-800/50 backdrop-blur-sm p-6 rounded-xl border border-gray-700/50">
        <div className="flex items-center gap-2 mb-4">
          <PieIcon className="text-cyan-400" size={20} />
          <h3 className="text-lg font-semibold text-cyan-400">
            Domain Categories
          </h3>
        </div>
        <ResponsiveContainer width="100%" height={300}>
          <PieChart>
            <Pie
              data={categoryData}
              cx="50%"
              cy="50%"
              labelLine={false}
              label={({ name, percent }) =>
                `${name} ${(percent * 100).toFixed(0)}%`
              }
              outerRadius={100}
              fill="#8884d8"
              dataKey="value"
            >
              {categoryData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip
              contentStyle={{
                backgroundColor: "rgba(17, 24, 39, 0.9)",
                border: "1px solid #374151",
                borderRadius: "8px",
                backdropFilter: "blur(8px)",
              }}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>

      {/* Keyword Effectiveness */}
      <div className="bg-gray-800/50 backdrop-blur-sm p-6 rounded-xl border border-gray-700/50 xl:col-span-2">
        <div className="flex items-center gap-2 mb-4">
          <TrendingUp className="text-cyan-400" size={20} />
          <h3 className="text-lg font-semibold text-cyan-400">
            Keyword Effectiveness
          </h3>
        </div>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={keywordData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.3} />
            <XAxis dataKey="keyword" stroke="#9CA3AF" fontSize={12} />
            <YAxis stroke="#9CA3AF" fontSize={12} />
            <Tooltip
              contentStyle={{
                backgroundColor: "rgba(17, 24, 39, 0.9)",
                border: "1px solid #374151",
                borderRadius: "8px",
                backdropFilter: "blur(8px)",
              }}
            />
            <Bar
              dataKey="discovered"
              fill="url(#colorDiscovered)"
              radius={[4, 4, 0, 0]}
            />
            <defs>
              <linearGradient id="colorDiscovered" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.8} />
                <stop offset="95%" stopColor="#06b6d4" stopOpacity={0.2} />
              </linearGradient>
            </defs>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export default DashboardCharts;
