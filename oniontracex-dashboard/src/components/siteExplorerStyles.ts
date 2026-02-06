export const STATUS_STYLES: Record<string, string> = {
  Alive: "bg-green-900/40 text-green-300 border border-green-500/40",
  Dead: "bg-red-900/40 text-red-300 border border-red-500/40",
  Timeout: "bg-yellow-900/40 text-yellow-300 border border-yellow-500/40",
};

export const KEYWORD_COLORS: Record<string, string> = {
  drugs: "bg-purple-900/40 text-purple-300",
  fraud: "bg-red-900/40 text-red-300",
  carding: "bg-orange-900/40 text-orange-300",
  hacking: "bg-blue-900/40 text-blue-300",
  weapons: "bg-gray-800 text-gray-300",
  malware: "bg-pink-900/40 text-pink-300",
  forum: "bg-cyan-900/40 text-cyan-300",
  Other: "bg-gray-700 text-gray-300",
};

export const keywordBadge = (kw?: string) =>
  KEYWORD_COLORS[kw?.toLowerCase() || "Other"] || KEYWORD_COLORS.Other;
