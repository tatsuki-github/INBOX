# Phase 0 作業種別ルーター（work-type-routing）

implementation-flow Phase 0c で適用する作業種別判定・Lite Path・リダイレクトの詳細リファレンス。

---

## 作業種別一覧

| コード | 名称 | 実行パス | 扱い |
|:---|:---|:---|:---|
| `bug-fix` | バグ修正のみ | Redirected | [bug-triage-fix](../../bug-triage-fix/SKILL.md) へリダイレクト |
| `perf-only` | パフォーマンス/UX改善のみ | Redirected | [improve-flow](../../improve-flow/SKILL.md) へリダイレクト |
| `greenfield-new` | 新規機能（グリーンfield） | Full | Phase 1〜6 フル実行 |
| `extend` | 既存機能の非破壊拡張 | Lite | Phase 1/3 簡略化、回帰テスト必須 |
| `modify-breaking` | 破壊的 API/契約変更 | Lite | 互換性計画 + 互換性 ADR 必須 |
| `legacy-integration` | レガシーへの段階的組み込み | Lite | Strangler/Adapter ADR + スライス単位完了 |

---

## 判定手順（4 問）

Phase 0a の直後に実施。**上から順に評価し、最初に該当した種別で確定**する。

```
Q1: 再現可能な不具合か？（期待動作 vs 実際の乖離、再現手順またはログがある）
  └─ Yes → bug-fix → implementation-flow 中断 → bug-triage-fix

Q2: 新機能追加なし、既存の速さ / UX / 品質 / コード構造の改善のみか？
  └─ Yes → perf-only → implementation-flow 中断 → improve-flow

Q3: 既存コードベースへの変更か？（新規ファイル・新規モジュール追加を含む既存プロジェクト内の変更）
  └─ No → greenfield-new → Full Path

Q4: 既存の契約（API レスポンス / 型 / DB スキーマ / 公開インターフェース）を破壊するか？
  └─ Yes → modify-breaking → Lite Path
  └─ No かつレガシー層へ段階的に差し込む（Strangler / Adapter が必要）→ legacy-integration → Lite Path
  └─ それ以外 → extend → Lite Path
```

### 判定のヒント

| シグナル | 向き |
|:---|:---|
| 「〜するとエラーになる」「以前は動いていた」 | bug-fix |
| 「遅い」「使いにくい」「きれいにしたい」（新機能なし） | perf-only |
| 新規画面・新規 API・新規ドメイン概念 | greenfield-new |
| 既存 API にフィールド追加（optional）、後方互換あり | extend |
| レスポンス形式変更、必須フィールド削除、URL 変更 | modify-breaking |
| 古いモジュールを触らず新層で置き換え、段階移行 | legacy-integration |

### 迷ったとき

- バグと機能要求が混在 → **再現手順が取れる不具合部分を bug-triage-fix**、残りを別ワークフロー
- 改善 + 小さな機能追加 → **extend**（新機能は拡張として扱う）
- レガシー全置換を 1 ワークフローに → **分割**（legacy-integration をスライスごとに複数回）

---

## Lite Path: extend（非破壊拡張）

### Phase 別マトリクス

| Phase | 実行 | 内容 |
|:---|:---|:---|
| 0 | 必須 | 作業種別 `extend` 記録、既存コード調査 |
| 1 | 簡略化 | 既存実装調査 + **差分**受け入れ条件 + テストマッピング + **回帰テスト要件** |
| 2 | 部分 | **新規 UI タッチ箇所のみ**。全体 UX 再設計は不要 |
| 3 | 簡略化 | 差分コンポーネント + ADR（既存パターン踏襲）+ テスト戦略 ADR |
| 4 | 部分 | 既存デザインシステム準拠（新規トークン最小） |
| 5 | 必須 | TDD + **既存テスト Green 維持** |
| 6 | 必須 | A-1 に「**既存振る舞い退行なし**」を追加検証 |

### チェックリスト

- [ ] 既存 API / UI の契約を破壊していない
- [ ] 受け入れ条件に「既存機能が従来通り動く」が含まれる
- [ ] テストマッピングに回帰テスト（既存テストスイート Green）が含まれる
- [ ] Phase 3 ADR に「既存パターン踏襲」の根拠がある
- [ ] QE5-7: 変更箇所の doc 更新 + 回帰として既存 doc の矛盾がない

### Docs Sync 必須範囲（extend）

| 変更 | 更新対象 |
|:---|:---|
| 既存 API フィールド追加 | 該当 API doc |
| 既存 UI 変更 | 該当 page / component doc |
| 新規ファイル追加 | 新規 doc + インデックス |

---

## Lite Path: modify-breaking（破壊的変更）

### Phase 1 必須: 互換性計画

- 影響 consumer 一覧（frontend / 外部 API 利用者 / 内部呼び出し元）
- バージョニング方針（URL パス / ヘッダ / 並行稼働期間）
- マイグレーション手順とロールバック条件
- 受け入れ条件: **旧契約 deprecate** + **新契約動作** の両方

### Phase 3 必須: 互換性 ADR

テスト戦略 ADR と併記可。含める項目:

- 並行稼働（v1/v2）or 一括切替の判断と根拠
- Feature flag / 段階ロールアウトの要否
- 非採用案と理由

### Phase 別マトリクス

| Phase | 実行 | 内容 |
|:---|:---|:---|
| 1 | 必須（拡張） | 互換性計画 + テストマッピング（契約テスト / マイグレーションテスト） |
| 2 | スキップ可 | API のみ変更で UI 不変の場合 |
| 3 | 必須（拡張） | 互換性 ADR + テスト戦略 ADR |
| 4 | スキップ可 | UI 変更なしの場合 |
| 5 | 必須 | 契約テスト / マイグレーションテスト（TDD または実装後） |
| 6 | 必須（強化） | B-3: 旧クライアント互換期間中の境界値 |

### チェックリスト

- [ ] 互換性計画が Phase 1 に記載されている
- [ ] 互換性 ADR が Phase 3 に記載されている
- [ ] 並行稼働期間と deprecate スケジュールが明確
- [ ] 契約テストで新旧両方の期待値が検証されている
- [ ] QE5-7: API doc に新旧契約・deprecate スケジュールを反映。互換性 ADR を永続化

### Docs Sync 必須範囲（modify-breaking）

| 変更 | 更新対象 |
|:---|:---|
| API 契約変更 | 該当 API doc（旧契約は履歴節） |
| 互換性計画 | 互換性 ADR + 関連 architecture doc |

---

## Lite Path: legacy-integration（段階的組み込み）

### Phase 1 必須: 現状アーキテクチャ診断

- レガシー境界（触ってはいけない層）
- **最初の Strangler スライス**（1 ワークフロー分に収まる範囲）
- 完了定義（全部置換ではなく **スライス単位**）
- Out of Scope: 次スライス以降の置換

### Phase 3 必須: Strangler / Adapter ADR

- Humble Object / Anti-Corruption Layer の配置
- 新旧データフロー（テキストまたは diagram スキル参照）
- 次スライスへの拡張ポイント

### Phase 5 実装順序（上書き）

```
1. adapter/       — レガシー境界のアダプタ（TDD: Red→Green→Refactor）
2. 新モジュール    — utils/services（TDD）
3. 既存呼び出し側  — 最小差分でアダプタ経由に切替
4. UI             — 触る場合のみ（hooks/components）
5. 振る舞いテスト  — 新旧経路の切替確認
```

### Phase 別マトリクス

| Phase | 実行 | 内容 |
|:---|:---|:---|
| 1 | 必須（拡張） | レガシー境界 + Strangler スライス定義 |
| 2 | スキップ可 | レガシー UI を触らないスライス |
| 3 | 必須（拡張） | Strangler/Adapter ADR + テスト戦略 ADR |
| 4 | スキップ可 | 新 UI 表面がないスライス |
| 5 | 必須 | adapter 先行 TDD、段階切替 |
| 6 | 必須 | スライス完了定義の充足 + 次スライスは Out of Scope 確認 |

### チェックリスト

- [ ] 1 スライスに収まっている（全置換を試みていない）
- [ ] レガシー層への直接変更が最小限
- [ ] アダプタ経由のデータフローが ADR に記載されている
- [ ] 次スライスが Out of Scope に明記されている
- [ ] QE5-7: スライス範囲の doc のみ更新（全置換を doc に書かない）

### Docs Sync 必須範囲（legacy-integration）

| 変更 | 更新対象 |
|:---|:---|
| アダプタ / 新モジュール | スライス範囲の API・サービス doc |
| Strangler ADR | 永続 ADR ファイル |

---

## リダイレクト時の G-0 完了条件

`bug-fix` / `perf-only` と判定した場合:

1. 作業種別記録テンプレートに **Redirected** を記録
2. リダイレクト先スキルと理由をユーザーに明示
3. **implementation-flow は Phase 0 で終了**（G-0 完了 = リダイレクト記録済み）

---

## エスカレーション（姉妹スキル → implementation-flow）

| 元スキル | エスカレーション条件 | 先の Lite Path |
|:---|:---|:---|
| bug-triage-fix | Step 5 で設計変更・新規コンポーネントが必要と判明 | extend / modify-breaking |
| improve-flow | Phase 2 で新規機能追加が必要と判明 | extend |
| improve-flow | 既存 API 契約の破壊的変更が必要 | modify-breaking |

エスカレーション時は Phase 0c を **再実行**し、作業種別を確定してから Phase 1 へ。
