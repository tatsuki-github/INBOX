/** Scope guard: refuse only clearly external topics; otherwise answer from repo corpus. */

export type ScopeDecision =
  | { kind: "in_scope"; reason: string }
  | { kind: "out_of_scope"; message: string; hard?: boolean };

/**
 * Repo-grounded weather ops (docs/tamana-weather.md) stay in scope.
 * Live "今日の天気は？" etc. still hard-refuse via /天気/.
 */
const REPO_WEATHER_ALLOW =
  /天気データ|天気の更新|どう更新|update_tamana_weather|Open-Meteo|tamana-forecast|tamana-weather|天気ファイル|1時間間隔|3時間間隔|保存先/;

/** Hard refuse — external live data / unrelated chat, even if other tokens appear. */
const HARD_OUT_OF_SCOPE_PATTERNS = [
  /天気/,
  /ニュース/,
  /株価/,
  /レシピ/,
  /作り方/,
  /chatgpt/i,
  /\bgpt\b/i,
  /あなたは誰/,
  /プログラミング/,
  /宿題手伝/,
  /宿題の数学/,
  /トランプ/,
  /大統領/,
  /ホワイトハウス/,
  /内閣/,
  /国会/,
  /選挙/,
  /官僚/,
  /議会/,
  /政党/,
  /野球/,
  /サッカー/,
  /バスケ/,
  /テニス/,
  /バレー/,
  /ゴルフ/,
  /ラグビー/,
  /卓球/,
  /バドミントン/,
  /翻訳して/,
  /英語翻訳/,
  /韓国語翻訳/,
  /中国語翻訳/,
  /フランス語翻訳/,
  /ドイツ語翻訳/,
  /スペイン語翻訳/,
  /イタリア語翻訳/,
  /ポルトガル語翻訳/,
  /占い/,
  /タロット/,
  /四柱推命/,
  /血液型占い/,
  /手相/,
  /姓名判断/,
  /夢占い/,
  /漫画/,
  /アニメ/,
  /ラノベ/,
  /映画おすすめ/,
  /ドラマおすすめ/,
  /小説おすすめ/,
  /ゲームおすすめ/,
  /音楽おすすめ/,
  /夕食/,
  /夕飯/,
  /小説書/,
  /競馬/,
  /暗号通貨/,
  /仮想通貨/,
  /ビットコイン/,
  /ドル円/,
  /日経平均/,
  /為替/,
  /金利/,
  /金相場/,
  /原油/,
  /恋の相談/,
  /恋愛相談/,
  /コード書いて/,
  /Java宿題/,
  /Python書いて/,
  /TypeScript書いて/,
  /Rust書いて/,
  /Go言語書いて/,
  /SQL書いて/,
  /シェル書いて/,
  /Geminiとは/,
  /Claudeとは/,
  /OpenAIとは/,
  /Anthropicとは/,
  /LLMとは/,
  /Soraとは/,
] as const;

export const OUT_OF_SCOPE_MESSAGE =
  "このボットはリポジトリに書いてある内容（練習・駅伝・記録・分析・ドキュメント等）について答えます。天気・ニュースなど外部の話題は対象外です。";

/**
 * Classify whether to attempt a corpus-backed answer.
 * Default is in_scope for any non-empty question — grounding and refusals for
 * missing facts happen at retrieval / LLM time. Hard patterns always refuse.
 */
export function classifyScope(question: string): ScopeDecision {
  const q = question.trim();
  if (!q) {
    return { kind: "out_of_scope", message: OUT_OF_SCOPE_MESSAGE };
  }

  const allowRepoWeather = REPO_WEATHER_ALLOW.test(q);

  for (const pat of HARD_OUT_OF_SCOPE_PATTERNS) {
    if (pat.source === "天気" && allowRepoWeather) continue;
    if (pat.test(q)) {
      return { kind: "out_of_scope", message: OUT_OF_SCOPE_MESSAGE, hard: true };
    }
  }

  return { kind: "in_scope", reason: "repo_corpus" };
}
