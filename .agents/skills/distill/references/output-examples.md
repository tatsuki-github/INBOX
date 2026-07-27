# Design スキル リファレンス: 出力例テンプレート

> SKILL.md から Progressive Disclosure で分離した詳細な出力例です。

---

## glossary.md 出力例

```markdown
# 用語集（Glossary）

> 本ドキュメントは教育データ利活用基盤プロジェクトのドメイン用語を定義する。
> 提案書および技術仕様書で使用する用語は、すべて本用語集に準拠すること。

## 業務用語

| ID | 用語 | 英語名 | 定義 | 同義語 | 出典 |
|:---|:---|:---|:---|:---|:---|
| G-BIZ-001 | 学籍情報 | Student Registry | 児童生徒の基本情報（氏名、生年月日、住所、保護者情報等）を管理するデータセット | 児童生徒台帳 | 01_inbox/Request.md §2.1 |
| G-BIZ-002 | 指導要録 | Student Guidance Record | 各学年における学習状況・行動の記録。法定保存期間あり | — | 01_inbox/Request.md §3.2 |
| G-BIZ-003 | 校務支援システム | School Administration System | 学校運営に関する業務を支援する情報システムの総称 | 校務システム | 01_inbox/Material_list.md |

## 技術用語

| ID | 用語 | 英語名 | 定義 | 文脈 |
|:---|:---|:---|:---|:---|
| G-TECH-001 | メダリオンアーキテクチャ | Medallion Architecture | Bronze→Silver→Gold の3層でデータ品質を段階的に向上させるデータレイク設計パターン | Databricks |
| G-TECH-002 | Unity Catalog | Unity Catalog | Databricks のデータガバナンス機能。アクセス制御・データリネージを提供 | Databricks |
```

---

## domain-model.md 出力例

```markdown
# ドメインモデル定義

## エンティティ一覧

### E-001: 児童生徒（Student）

| 属性 | 型 | 制約 | 説明 |
|:---|:---|:---|:---|
| student_id | UUID | PK, NOT NULL | システム内部ID |
| student_code | VARCHAR(10) | UNIQUE, NOT NULL | 学籍番号 |
| family_name | VARCHAR(50) | NOT NULL | 姓 |
| given_name | VARCHAR(50) | NOT NULL | 名 |
| birth_date | DATE | NOT NULL | 生年月日 |
| gender | ENUM('M','F','X') | NOT NULL | 性別 |
| enrollment_date | DATE | NOT NULL | 入学日 |
| school_id | UUID | FK→School | 所属学校 |
| class_id | UUID | FK→Class, NULLABLE | 所属クラス |
| is_active | BOOLEAN | DEFAULT TRUE | 在籍フラグ |
| created_at | TIMESTAMP | NOT NULL | 作成日時 |
| updated_at | TIMESTAMP | NOT NULL | 更新日時 |

**ビジネスルール参照**: BR-STU-001, BR-STU-002, BR-STU-003

**関係**:
- Student 1 --- N GradeRecord（成績）
- Student N --- 1 School（学校）
- Student N --- 1 Class（クラス）
- Student 1 --- N Guardian（保護者）※中間テーブル経由

**インデックス戦略**:
- `idx_student_school` on (school_id, is_active) — 学校別在籍生徒検索
- `idx_student_code` on (student_code) — 学籍番号検索

**データ保持ポリシー**:
- 在籍中: 無期限保持
- 卒業後: 指導要録は20年保存（法定）、その他は5年後に匿名化
```

---

## business-rules.md 出力例

```markdown
# ビジネスルール定義

## BR-STU-001: 学籍番号の一意性

| 項目 | 内容 |
|:---|:---|
| **ルールID** | BR-STU-001 |
| **カテゴリ** | データ整合性 |
| **優先度** | Critical |
| **出典** | 01_inbox/Request.md §2.1.3 |
| **エンティティ** | Student (E-001) |

**ルール定義**:
学籍番号（student_code）は学校内で一意でなければならない。
転入生が既存の学籍番号と重複する場合、新番号を自動採番する。

**検証ロジック**:
```python
def validate_student_code(school_id: str, student_code: str) -> bool:
    existing = db.query(
        "SELECT COUNT(*) FROM students WHERE school_id = ? AND student_code = ? AND is_active = TRUE",
        [school_id, student_code]
    )
    return existing == 0
```

**例外ケース**:
- 転校先で同一番号が使用されている場合: `{学校コード}-{連番4桁}` で再採番
- 再入学の場合: 旧番号を再利用可（`is_active` フラグで管理）

**テストケース**:
| ケース | 入力 | 期待結果 |
|:---|:---|:---|
| 正常 | 新規番号 | 登録成功 |
| 重複 | 既存番号 | バリデーションエラー |
| 再入学 | 旧番号（非在籍） | 再有効化 |
```

---

## non-functional-requirements.md 出力例

```markdown
# 非機能要件定義

## NFR-001: パフォーマンス要件

| 指標 | 目標値 | 計測条件 |
|:---|:---|:---|
| **画面応答時間** | 3秒以内（95パーセンタイル） | 同時100ユーザー、通常業務時間帯 |
| **バッチ処理** | 2時間以内 | 全校（200校）の日次集計 |
| **データ取込** | 10,000レコード/分 | CSV アップロード |
| **検索応答** | 1秒以内 | 学校内児童検索（500件未満） |

## NFR-002: セキュリティ要件

| 項目 | 要件 | 根拠 |
|:---|:---|:---|
| **認証** | SAML 2.0 / OpenID Connect（既存IdP連携） | RFP §5.2 |
| **認可** | RBAC（ロールベースアクセス制御）、学校単位のデータ分離 | 個人情報保護条例 |
| **暗号化（通信）** | TLS 1.3 | 情報セキュリティポリシー |
| **暗号化（保存）** | AES-256（Databricks 暗号化ボリューム） | RFP §5.3 |
| **監査ログ** | 全操作ログを1年保持、改ざん防止 | RFP §5.4 |
```

---

## tech-decisions.md 出力例

```markdown
# 技術選定根拠

## TD-001: データ基盤 — Databricks

| 項目 | 内容 |
|:---|:---|
| **選定技術** | Databricks (Unified Analytics Platform) |
| **代替案** | Snowflake, Azure Synapse, BigQuery |
| **選定理由** | 1. RFP でメダリオンアーキテクチャが指定 2. Unity Catalog による統合ガバナンス 3. 既存 Azure 環境との親和性 4. ML/AI 拡張への対応力 |
| **リスク** | ライセンスコスト（DBU課金）の見積精度 |
| **ADR参照** | 05_decision_log/ADR-XXX |
```

---

## トレーサビリティマトリクス例

```markdown
## 要件トレーサビリティマトリクス

| RFP 要件ID | 01_inbox ファイル | 02_notes 仕様 | 03_spec 章 | ステータス |
|:---|:---|:---|:---|:---|
| REQ-001 | Request.md §2.1 | domain-model.md#E-001 | 04_development.md §3 | 反映済 |
| REQ-002 | Request.md §3.2 | business-rules.md#BR-STU-001 | 04_development.md §4 | 反映済 |
| REQ-003 | Material_list.md §1 | non-functional-requirements.md#NFR-002 | 09_sla.md §2 | 要確認 |
```
