// Level system based on the provided chop ranges
export interface LevelInfo {
  level: number;
  rank: string;
  badge: string;
  minChops: number;
  maxChops: number;
}

export interface UserLevelInfo {
  currentLevel: LevelInfo;
  nextLevel: LevelInfo | null;
  totalChops: number;
  chopsInCurrentLevel: number;
  pointsToNextLevel: number;
  progressPercentage: number;
}

const LEVELS: LevelInfo[] = [
  { level: 1, rank: "Builder", badge: "🏗️", minChops: 0, maxChops: 999 },
  { level: 2, rank: "Initiate", badge: "🌱", minChops: 1000, maxChops: 1999 },
  { level: 3, rank: "Apprentice", badge: "📚", minChops: 2000, maxChops: 3999 },
  { level: 4, rank: "Forgehand", badge: "🔨", minChops: 4000, maxChops: 7999 },
  { level: 5, rank: "Pioneer", badge: "🚀", minChops: 8000, maxChops: 11999 },
  { level: 6, rank: "Vision Crafter", badge: "👁️", minChops: 12000, maxChops: 16999 },
  { level: 7, rank: "Operator", badge: "⚙️", minChops: 17000, maxChops: 21999 },
  { level: 8, rank: "Trailblazer", badge: "🎯", minChops: 22000, maxChops: 30999 },
  { level: 9, rank: "Strategist", badge: "♟️", minChops: 31000, maxChops: 34999 },
  { level: 10, rank: "Groundbreaker", badge: "⛏️", minChops: 35000, maxChops: 40999 },
  { level: 11, rank: "Connector", badge: "🔗", minChops: 41000, maxChops: 50999 },
  { level: 12, rank: "Catalyst", badge: "⚡", minChops: 51000, maxChops: 61999 },
  { level: 13, rank: "Innovator", badge: "💡", minChops: 62000, maxChops: 73999 },
  { level: 14, rank: "Navigator", badge: "🧭", minChops: 74000, maxChops: 86999 },
  { level: 15, rank: "Signal Weaver", badge: "🕸️", minChops: 87000, maxChops: 101999 },
  { level: 16, rank: "Momentum Maker", badge: "🌊", minChops: 102000, maxChops: 118999 },
  { level: 17, rank: "Orchestrator", badge: "🎼", minChops: 119000, maxChops: 137999 },
  { level: 18, rank: "Insight Sculptor", badge: "🗿", minChops: 138000, maxChops: 159999 },
  { level: 19, rank: "Opportunity Engineer", badge: "🔧", minChops: 160000, maxChops: 185999 },
  { level: 20, rank: "Alchemist", badge: "⚗️", minChops: 186000, maxChops: 214999 },
  { level: 21, rank: "Growth Architect", badge: "🏛️", minChops: 215000, maxChops: 250999 },
  { level: 22, rank: "Commerce Marshal", badge: "🎖️", minChops: 251000, maxChops: 301999 },
  { level: 23, rank: "Mentor Maven", badge: "🎓", minChops: 302000, maxChops: 365999 },
  { level: 24, rank: "Blueprint Maker", badge: "📐", minChops: 366000, maxChops: 444999 },
  { level: 25, rank: "Insight Sage", badge: "🧙", minChops: 445000, maxChops: 537999 },
  { level: 26, rank: "Community Leader", badge: "👑", minChops: 538000, maxChops: 654999 },
  { level: 27, rank: "Strategy Guardian", badge: "🛡️", minChops: 655000, maxChops: 798999 },
  { level: 28, rank: "Network Navigator", badge: "🌐", minChops: 799000, maxChops: 966999 },
  { level: 29, rank: "Ecosystem Builder", badge: "🌳", minChops: 967000, maxChops: 1169999 },
  { level: 30, rank: "Market Sculptor", badge: "🎨", minChops: 1170000, maxChops: 1436999 },
  { level: 31, rank: "Culture Steward", badge: "🏺", minChops: 1437000, maxChops: 1865999 },
  { level: 32, rank: "Ecosystem Keeper", badge: "🌍", minChops: 1866000, maxChops: 2398999 },
  { level: 33, rank: "Market Commander", badge: "⚔️", minChops: 2399000, maxChops: 3078999 },
  { level: 34, rank: "Vision Chancellor", badge: "🔮", minChops: 3079000, maxChops: 3927999 },
  { level: 35, rank: "Growth Sage", badge: "🧘", minChops: 3928000, maxChops: 4947999 },
  { level: 36, rank: "Opportunity Sentinel", badge: "🗼", minChops: 4948000, maxChops: 6172999 },
  { level: 37, rank: "Innovation Regent", badge: "👸", minChops: 6173000, maxChops: 7699999 },
  { level: 38, rank: "Legacy Maker", badge: "📜", minChops: 7700000, maxChops: 9549999 },
  { level: 39, rank: "Empire Guardian", badge: "🦅", minChops: 9550000, maxChops: 11931999 },
  { level: 40, rank: "Luminary", badge: "✨", minChops: 11932000, maxChops: 14916999 },
  { level: 41, rank: "Vision Keeper", badge: "🔭", minChops: 14917000, maxChops: 18645999 },
  { level: 42, rank: "Momentum Master", badge: "🌪️", minChops: 18646000, maxChops: 23880999 },
  { level: 43, rank: "Domain Sage", badge: "🏰", minChops: 23881000, maxChops: 30711999 },
  { level: 44, rank: "The Chairman", badge: "💼", minChops: 30712000, maxChops: 39460999 },
  { level: 45, rank: "Reality Shaper", badge: "🌌", minChops: 39461000, maxChops: 50000999 },
  { level: 46, rank: "Epoch Driver", badge: "🚗", minChops: 50001000, maxChops: 65501299 },
  { level: 47, rank: "Ascendant Visionary", badge: "🦋", minChops: 65501300, maxChops: 86951699 },
  { level: 48, rank: "Super Creator", badge: "🌟", minChops: 86951700, maxChops: 100000999 },
  { level: 49, rank: "Supreme Creator", badge: "💫", minChops: 100001000, maxChops: 249999999 },
  { level: 50, rank: "Top Boss (Oga at The Top)", badge: "👑", minChops: 250000000, maxChops: 49999999999 },
  { level: 51, rank: "The Oracle", badge: "🔱", minChops: 50000000000, maxChops: Infinity },
];

export function calculateUserLevel(totalChops: number): UserLevelInfo {
  // Find current level
  let currentLevel = LEVELS[0];
  for (const level of LEVELS) {
    if (totalChops >= level.minChops && totalChops <= level.maxChops) {
      currentLevel = level;
      break;
    }
  }

  // Find next level
  const currentLevelIndex = LEVELS.findIndex(l => l.level === currentLevel.level);
  const nextLevel = currentLevelIndex < LEVELS.length - 1 ? LEVELS[currentLevelIndex + 1] : null;

  // Calculate chops in current level (relative to level start)
  const chopsInCurrentLevel = totalChops - currentLevel.minChops;

  // Calculate points to next level
  const pointsToNextLevel = nextLevel ? nextLevel.minChops - totalChops : 0;

  // Calculate progress percentage within current level
  const levelRange = currentLevel.maxChops - currentLevel.minChops + 1;
  const progressPercentage = nextLevel 
    ? Math.min(100, Math.round((chopsInCurrentLevel / levelRange) * 100))
    : 100;

  return {
    currentLevel,
    nextLevel,
    totalChops,
    chopsInCurrentLevel,
    pointsToNextLevel,
    progressPercentage
  };
}