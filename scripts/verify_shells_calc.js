/**
 * Проверка формул калькулятора shells-charts.html против официальных данных CSV.
 * Запуск: node scripts/verify_shells_calc.js
 */
const WIN = { E: 1250, D: 1750, C: 2400, B: 3300, A: 4700, S: 7000 };
const LOSE = { E: 250, D: 500, C: 800, B: 1200, A: 1800, S: 3000 };
const OFF = { win: 2400, lose: 800 };
const RECORDS = { '3w': [1, 1, 1], '2w1l': [1, 1, 0], '1w2l': [1, 0, 0], '3l': [0, 0, 0] };

function stageShells(mode, rank, win) {
  return mode === 'off' ? (win ? OFF.win : OFF.lose) : (win ? WIN[rank] : LOSE[rank]);
}
function dayTotal(mode, rank, rec) {
  return RECORDS[rec].reduce((s, w) => s + stageShells(mode, rank, !!w), 0);
}
function brawlStage(pool, maxP, minShare, clanPct, playerPct = 100) {
  if (clanPct < minShare) return 0;
  return Math.min(maxP, Math.round(pool * clanPct / 100 * playerPct / 100));
}
function comb(n, k) {
  if (k < 0 || k > n) return 0;
  let r = 1;
  for (let i = 0; i < k; i++) r = r * (n - i) / (i + 1);
  return r;
}
function binomProb(n, k, p) {
  return comb(n, k) * Math.pow(p, k) * Math.pow(1 - p, n - k);
}
function outcomeProbs(wp) {
  const p = wp / 100;
  return Object.keys(RECORDS).map(key => ({
    key,
    prob: binomProb(3, RECORDS[key].filter(Boolean).length, p),
  }));
}
function expectedDayLinear(mode, rank, wp) {
  const w = stageShells(mode, rank, true);
  const l = stageShells(mode, rank, false);
  const p = wp / 100;
  return Math.round(3 * (p * w + (1 - p) * l));
}
function dayTreasury(mode, rank, rec) {
  return RECORDS[rec].reduce((s, w) => s + stageTreasury(mode, rank, !!w), 0);
}
function stageTreasury(mode, rank, win) {
  const TW = { E: 600_000, D: 650_000, C: 700_000, B: 750_000, A: 800_000, S: 850_000 };
  const TL = { E: 300_000, D: 325_000, C: 350_000, B: 375_000, A: 400_000, S: 425_000 };
  return mode === 'off' ? (win ? 700_000 : 350_000) : (win ? TW[rank] : TL[rank]);
}
function buildOutcomes(mode, rank, wp) {
  const p = wp / 100;
  return Object.keys(RECORDS).map(key => {
    const wins = RECORDS[key].filter(Boolean).length;
    return { key, prob: binomProb(3, wins, p), shells: dayTotal(mode, rank, key), treasury: dayTreasury(mode, rank, key) };
  });
}
function expectedDayBinomial(mode, rank, wp, field) {
  return Math.round(buildOutcomes(mode, rank, wp).reduce((s, o) => s + o.prob * o[field], 0));
}
function expectedTreasuryLinear(mode, rank, wp) {
  const w = stageTreasury(mode, rank, true);
  const l = stageTreasury(mode, rank, false);
  const p = wp / 100;
  return Math.round(3 * (p * w + (1 - p) * l));
}

const tests = [
  ['C win stage', stageShells('rank', 'C', true), 2400],
  ['C lose stage', stageShells('rank', 'C', false), 800],
  ['S win stage', stageShells('rank', 'S', true), 7000],
  ['E 3l day', dayTotal('rank', 'E', '3l'), 750],
  ['C 2w1l day', dayTotal('rank', 'C', '2w1l'), 5600],
  ['C 3w day', dayTotal('rank', 'C', '3w'), 7200],
  ['S 2w1l day', dayTotal('rank', 'S', '2w1l'), 17000],
  ['off 2w1l day', dayTotal('off', 'C', '2w1l'), 5600],
  ['off 3l day', dayTotal('off', 'C', '3l'), 2400],
  ['patch 51.4%×67.6%', brawlStage(1500, 1000, 5, 51.4, 67.6), 521],
  ['brawl 100% clan', brawlStage(1500, 1000, 5, 100, 100), 1000],
  ['brawl <5%', brawlStage(1500, 1000, 5, 3, 100), 0],
  ['brawl treasury 48%', Math.round(1_500_000 * 0.48), 720000],
  ['C E[day] 26% linear', expectedDayLinear('rank', 'C', 26), 3648],
  ['C E[day] 26% binomial', expectedDayBinomial('rank', 'C', 26, 'shells'), 3648],
  ['C E[day] 67% both match', expectedDayLinear('rank', 'C', 67), expectedDayBinomial('rank', 'C', 67, 'shells')],
  ['C E[treasury] 26%', expectedTreasuryLinear('rank', 'C', 26), expectedDayBinomial('rank', 'C', 26, 'treasury')],
  ['C E[treasury] 67%', expectedTreasuryLinear('rank', 'C', 67), expectedDayBinomial('rank', 'C', 67, 'treasury')],
  ['S E[day] 50%', expectedDayLinear('rank', 'S', 50), 15000],
  ['prob outcomes sum', Math.round(outcomeProbs(67).reduce((s, o) => s + o.prob, 0) * 10000), 10000],
  ['C 2w1l binom prob', Math.round(binomProb(3, 2, 0.67) * 1000), Math.round(3 * Math.pow(0.67, 2) * 0.33 * 1000)],
  ['C 3w static day', dayTotal('rank', 'C', '3w'), 3 * WIN.C],
  ['C 3l static day', dayTotal('rank', 'C', '3l'), 3 * LOSE.C],
  ['C 2w1l static day', dayTotal('rank', 'C', '2w1l'), 2 * WIN.C + LOSE.C],
  ['C 1w2l static day', dayTotal('rank', 'C', '1w2l'), WIN.C + 2 * LOSE.C],
];

let failed = 0;
for (const [name, got, want] of tests) {
  if (got !== want) {
    console.error(`FAIL ${name}: got ${got}, want ${want}`);
    failed++;
  } else {
    console.log(`OK   ${name}: ${got}`);
  }
}
if (failed) {
  console.error(`\n${failed} test(s) failed`);
  process.exit(1);
}
console.log(`\nAll ${tests.length} checks passed.`);
