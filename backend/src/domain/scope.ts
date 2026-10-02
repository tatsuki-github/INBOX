/** Scope guard: refuse only clearly external topics; otherwise answer from repo corpus. */

export type ScopeDecision =
  | { kind: "in_scope"; reason: string }
  | { kind: "out_of_scope"; message: string; hard?: boolean };

/**
 * Repo-grounded weather ops (docs/tamana-weather.md) stay in scope.
 * Live "今日の天気は？" etc. still hard-refuse via /天気/.
 */
const REPO_WEATHER_ALLOW =
  /天気データ|天気の更新|更新スクリプト|どう更新|更新.*コマンド|天気.*コマンド|update_tamana_weather|Open-Meteo|tamana-forecast|tamana-weather|天気ファイル|予報ファイル|天気.*(?:JSON|CSV)|1時間間隔|3時間間隔|保存先/;

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

export const REMUNERATION_PRIVATE_MESSAGE = "謝礼・謝金の金額は回答対象外です。";

export const PERSONAL_PRIVATE_MESSAGE = "口座・認証情報・個人の健康情報・識別番号や私的な評価は回答対象外です。";

const PERSONAL_HEALTH_QUESTION = /(?:の|は|が)(?:体調|健康状態|病歴|持病|診断結果|治療歴|けがの状態|怪我の状態)(?:は|が|を|って|について)?(?:どう|何|どんな|[?？]|教えて|知りたい|いつ|良|悪|回復)|(?:誰|だれ).*(?:病気|気管支炎|発熱|持病|診断)|(?:選手|生徒|本人|保護者).*(?:病歴|持病|診断結果|治療歴)/;

export function isPrivatePersonalQuestion(question: string): boolean {
  const normalized = question.normalize("NFKC");
  return /口座|バックアップコード|認証コード|予約番号|確認番号|confirmation\s*(?:number|code)|会員番号|登録\s*(?:番号|id|no\.?)|マイナンバー|運転免許|免許証.*番号|給与|年収|月給|資産|残高|性格|人物評|人間性|家庭事情|(?:保護者|選手|生徒).*(?:私見|印象|評判)/i.test(normalized) || PERSONAL_HEALTH_QUESTION.test(normalized);
}

export function isPrivateRemunerationQuestion(question: string): boolean {
  return /謝礼|謝金|報酬|指導者.*時給|コーチ.*時給/.test(question.normalize("NFKC"));
}

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

  if (isPrivateRemunerationQuestion(q)) {
    return { kind: "out_of_scope", message: REMUNERATION_PRIVATE_MESSAGE, hard: true };
  }

  if (isPrivatePersonalQuestion(q)) {
    return { kind: "out_of_scope", message: PERSONAL_PRIVATE_MESSAGE, hard: true };
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
