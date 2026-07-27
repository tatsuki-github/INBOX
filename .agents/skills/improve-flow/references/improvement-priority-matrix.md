# 改善課題 優先付けマトリクス

> improve-flow の Phase 2 で使用する Impact × Effort マトリクスと判定基準

---

## Impact × Effort マトリクス

```
High  │  P2（計画的に）  │  P1（今すぐ）  │
      │  High Impact     │  High Impact   │
      │  High Effort     │  Low Effort    │
Impact│─────────────────────────────────
      │  P4（保留）      │  P3（余力で）  │
      │  Low Impact      │  Low Impact    │
Low   │  High Effort     │  Low Effort    │
      └──────────────────────────────────
              High                Low
                      Effort
```

| 優先度 | 象限 | アクション |
|:---|:---|:---|
| **P1（今すぐ）** | High Impact × Low Effort | このワークフローで最優先実施 |
| **P2（計画的に）** | High Impact × High Effort | このワークフローで実施（P1 の後） |
| **P3（余力で）** | Low Impact × Low Effort | 時間があれば実施、なければ次サイクル |
| **P4（保留）** | Low Impact × High Effort | このワークフローでは対応しない |

---

## Impact の判定基準

| Impact | 条件 |
|:---|:---|
| **High** | ユーザーが頻繁に触れる機能 / セキュリティリスク / パフォーマンスに直接影響 |
| **Low** | ほとんど使われない機能 / 見た目のみ / バックエンドのみの改善 |

**High Impact の例**:
- ログインフォームの離脱率改善（全ユーザーが使う）
- 商品一覧の LCP 改善（購買に直結）
- Critical バグ / セキュリティ脆弱性の修正
- any が多すぎてコードが変更できない（開発速度阻害）

**Low Impact の例**:
- 管理者しか使わない設定画面のデザイン改善
- コメントのリファクタリング
- 使用頻度が低い機能の型エラー修正

---

## Effort の判定基準

| Effort | 条件 |
|:---|:---|
| **Low** | 1 コンポーネント以内・数ファイルの変更・リグレッションリスク低 |
| **High** | 複数機能にまたがる変更・アーキテクチャ変更・リグレッションリスク高 |

**Low Effort の例**:
- ハードコード色値 → CSS 変数置換（検索→置換で完了）
- aria-label の追加（独立した変更）
- enum → リテラルユニオン置換（find/replace で可能）

**High Effort の例**:
- 状態管理ライブラリの移行
- boolean フラグ → タグ付きユニオン型への移行（全利用箇所の修正が必要）
- コンポーネントの大規模分割（依存関係が多い場合）

---

## 改善ドメイン別の典型的な優先度

### UX 改善

| 課題 | Impact | Effort | 優先度 |
|:---|:---|:---|:---|
| 主要フローの離脱率原因（バリデーション過剰等） | High | Low | P1 |
| 重要情報の視覚的強調（KPI, エラーメッセージ） | High | Low | P1 |
| タッチターゲットサイズ修正 | High | Low | P1 |
| 全フローのピーク体験設計 | High | High | P2 |
| 管理画面のナビゲーション改善 | Low | Low | P3 |

### UI/ビジュアル改善

| 課題 | Impact | Effort | 優先度 |
|:---|:---|:---|:---|
| コントラスト比 WCAG AA 対応 | High | Low | P1 |
| ハードコード色値 → CSS 変数化 | Medium | Low | P1 |
| 空の状態（Empty State）追加 | Medium | Low | P1 |
| スペーシングの完全統一 | Low | High | P4 |

### コード品質改善

| 課題 | Impact | Effort | 優先度 |
|:---|:---|:---|:---|
| セキュリティ脆弱性（XSS 等） | High | Low-Medium | P1 |
| Critical/High バグ修正 | High | Low-Medium | P1 |
| any 使用の削除（スコープ内） | Medium | Low | P1 |
| enum → リテラルユニオン置換 | Medium | Low | P1 |
| boolean フラグ → タグ付きユニオン | High | High | P2 |
| 大規模アーキテクチャ改善 | High | High | P2 |

### パフォーマンス改善

| 課題 | Impact | Effort | 優先度 |
|:---|:---|:---|:---|
| N+1 クエリ解消 | High | Low | P1 |
| React.memo の適切な適用 | High | Low | P1 |
| 仮想スクロール導入（1000+件） | High | Medium | P2 |
| バンドル分割（大規模） | Medium | High | P2 |

---

## ADR 記録テンプレート

Phase 2 で改善方針を記録する ADR のテンプレート:

```markdown
## ADR-00N: <改善方針のタイトル>

### 状況
<なぜこの決定が必要か。Phase 1 の診断結果を引用する>

### 決定
<採用する改善アプローチ>

### 理由
<なぜこのアプローチを選んだか（Impact/Effort の観点を含む）>

### 不採用オプション
| 選択肢 | 不採用理由 |
|:---|:---|
| <オプション A> | <理由> |

### リグレッションリスク
<この改善による影響範囲と、リスクを軽減する対策>

### 成功基準（Before/After）
- Before: <現状の数値・状態>
- After（目標）: <改善後の目標>
```
