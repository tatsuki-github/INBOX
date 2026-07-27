# 検索クエリ設計パターン集

> 効果的な Web 検索クエリの設計パターン。
> 情報ギャップの種別に応じた戦略で検索精度を最大化する。

---

## 基本パターン

### P1: 日本語直接検索

最もシンプルな検索。国内事例・日本語レポートの発見に有効。

```
「生成AI 企業導入 ROI 2025」
「マイクロプラスチック 人体 影響 研究 最新」
「React Vue 比較 2025 企業」
```

**適用場面**: 日本市場のデータ、日本語の解説記事、国内事例

---

### P2: 英語変換検索

テーマを英語に変換して検索。海外の一次ソース・学術文献の発見に不可欠。

```
"generative AI enterprise ROI 2025 case study"
"microplastics human health impact systematic review"
"React vs Vue vs Svelte benchmark 2025"
```

**変換のコツ**:
| 日本語 | 英語変換 | NG 変換 |
|:---|:---|:---|
| 生成 AI | generative AI | generation AI |
| 企業導入 | enterprise adoption | company introduction |
| 最新動向 | latest trends / state of | newest movement |
| 比較調査 | comparative study / benchmark | comparison research |
| 市場規模 | market size / TAM | market scale |

---

### P3: ドメイン指定検索

信頼性の高いソースに絞り込む。ソース信頼性 ★4 以上を狙う。

```
site:mckinsey.com OR site:gartner.com "generative AI ROI"
site:arxiv.org OR site:pubmed.ncbi.nlm.nih.gov "microplastics health"
site:gov.uk OR site:europa.eu "AI regulation 2025"
```

**ドメイン指定リスト（分野別）**:

| 分野 | 高信頼ドメイン |
|:---|:---|
| **テクノロジー** | `site:arxiv.org`, `site:acm.org`, `site:ieee.org` |
| **ビジネス** | `site:mckinsey.com`, `site:hbr.org`, `site:gartner.com` |
| **政策・規制** | `site:europa.eu`, `site:gov.uk`, `site:meti.go.jp` |
| **医療・健康** | `site:who.int`, `site:pubmed.ncbi.nlm.nih.gov`, `site:nature.com` |
| **統計** | `site:e-stat.go.jp`, `site:worldbank.org`, `site:oecd.org` |
| **開発者** | `site:engineering.fb.com`, `site:blog.google`, `site:aws.amazon.com/blogs` |

---

### P4: 年号フィルタ検索

最新情報に限定する。「最新」「トレンド」「動向」のテーマで必須。

```
「生成AI 市場規模 2025」 after:2025-01-01
"AI regulation" after:2024-06-01
「WebAssembly 本番運用」 after:2024-01-01
```

**注意**: `after:` 構文は Google 検索で有効。他の検索エンジンでは Daterange や Tools のフィルタを使用。

---

### P5: Boolean 演算検索

複数条件の組み合わせで精度を上げる。

| 演算子 | 用途 | 例 |
|:---|:---|:---|
| `AND` | 両方含む | `"generative AI" AND "ROI" AND "enterprise"` |
| `OR` | いずれか含む | `"React" OR "Vue" OR "Svelte" comparison 2025` |
| `-` | 除外 | `"generative AI" ROI -advertisement -sponsored` |
| `""` | 完全一致 | `"EU AI Act" "risk classification"` |
| `*` | ワイルドカード | `"generative AI * adoption rate"` |

---

## ギャップ種別ごとの検索戦略

### 空白ギャップ（情報が見つからない）

| 戦略 | 例 |
|:---|:---|
| 類義語・関連語で拡大 | 「失敗事例」→ "failure" OR "abandoned" OR "discontinued" OR "lessons learned" |
| 上位概念に拡大 | 「Wasm 本番事例」→ 「Wasm 事例」→ 「新技術 本番事例」 |
| 英語に切り替え | 日本語で見つからない → 英語で再検索 |
| 関連分野から推測 | 直接的な情報がない → 隣接領域の知見から類推 |

### 矛盾ギャップ（情報が対立）

| 戦略 | 例 |
|:---|:---|
| 一次ソースを追跡 | 二次ソースが引用している原典を直接検索 |
| 調査方法論に焦点 | "methodology" OR "survey design" OR "sample size" |
| 批判記事を検索 | "critique" OR "criticism" OR "debunk" + テーマ |

### 深さギャップ（表面的すぎる）

| 戦略 | 例 |
|:---|:---|
| 学術 DB に絞る | `site:arxiv.org` OR `site:scholar.google.com` |
| ロングフォームコンテンツ | "whitepaper" OR "technical report" OR "case study" |
| 専門メディアに絞る | `site:hbr.org` OR `site:wired.com/tag/` |

### 時間ギャップ（古い情報）

| 戦略 | 例 |
|:---|:---|
| 年号を明示 | クエリに「2025」「2026」を含める |
| after フィルタ | `after:2025-01-01` |
| ニュースタブ | Google News タブで最新記事に絞る |
| プレプリントサーバー | `site:arxiv.org` で最新の査読前論文を確認 |

---

## 検索クエリ記録テンプレート

調査の再現性確保のため、全検索クエリを記録する（徹底レベルでは付録に収録）:

| # | クエリ | 言語 | エンジン | 結果件数 | 採用ソース数 | メモ |
|:---|:---|:---|:---|:---:|:---:|:---|
| Q-1 | 「生成AI 市場規模 2025」 | JP | Google | 約 50万 | 3 | 矢野経済、IDC を発見 |
| Q-2 | "generative AI market size 2025" | EN | Google | 約 200万 | 4 | Gartner, McKinsey を発見 |
| Q-3 | site:arxiv.org "LLM enterprise" | EN | Google | 約 500 | 1 | 学術レビュー論文を発見 |
