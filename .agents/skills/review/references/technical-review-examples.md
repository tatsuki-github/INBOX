# Verify スキル リファレンス: 技術仕様レビュー詳細例

> SKILL.md から Progressive Disclosure で分離した詳細なコード例・指摘パターンです。

---

## B-2: Accounting Integrity（会計・数値整合性）詳細例

### 通貨精度の検証

```typescript
// NG: 浮動小数点型（丸め誤差が発生）
amount: number;  // Float64 → 0.1 + 0.2 ≠ 0.3

// OK: 整数型（最小通貨単位で保存）
amountInYen: bigint;  // 1円単位で保存

// OK: 高精度ライブラリ
import Decimal from 'decimal.js';
amount: Decimal;  // new Decimal('1234.00')
```

### closing_flag の考慮

```typescript
// NG: closing_flag を無視
function getAccountingValue(data: MonthlyData): number {
  return data.actual;  // 見込の場合も actual を返してしまう
}

// OK: closing_flag を考慮
function getAccountingValue(data: MonthlyData): number {
  return data.closingFlag ? data.actual : data.forecast;
}
```

---

## B-3: Edge Case Attack（境界値攻撃）詳細例

### 攻撃パターン

```typescript
// Null/Undefined 攻撃
processData(null);
processData(undefined);
processData({ value: null });

// 境界値攻撃
processData({ value: 0 });
processData({ value: -1 });
processData({ value: Number.MAX_SAFE_INTEGER });

// 型攻撃
processData({ value: "100" });   // 文字列
processData({ value: NaN });     // NaN
processData({ value: Infinity });// 無限
processData({ value: [] });      // 配列

// 並行処理攻撃
await Promise.all([
  closeMonth('0001', '2025-01'),
  closeMonth('0001', '2025-01'),  // 同一リソースへの同時アクセス
]);
```

**期待される動作**:
- すべてのケースでクラッシュせず、適切なエラーハンドリング
- バリデーションエラー時は明確なエラーメッセージを返却
- 並行処理では楽観的/悲観的ロックで整合性を担保

---

## B-4: Privacy Violation（プライバシー侵害）詳細例

```typescript
// NG: パスワードをログに出力
logger.info({ message: 'User login', email, password });

// OK: パスワードをログに含めない
logger.info({ message: 'User login', email, loginResult: 'success' });
```

---

## B-5: Performance & Scalability 詳細例

```typescript
// NG: N+1クエリ
async function getStudentsWithGrades() {
  const students = await studentRepo.find();
  for (const s of students) {
    s.grades = await gradeRepo.findByStudent(s.id);  // N回クエリ
  }
  return students;
}

// OK: JOIN で一度に取得
async function getStudentsWithGrades() {
  return await studentRepo.find({ relations: ['grades'] });
}
```

---

## B-6: Test Coverage 詳細例

```typescript
// NG: 実装の詳細に依存
it('should call repository.save', async () => {
  await service.createStudent(data);
  expect(repository.save).toHaveBeenCalled();  // HOW をテスト
});

// OK: 結果（WHAT）を検証
it('should create a new student with valid code', async () => {
  const student = await service.createStudent(data);
  expect(student).toHaveProperty('id');
  expect(student.studentCode).toBe(data.studentCode);
  expect(student.isActive).toBe(true);
});
```

---

## レポートテンプレート

```markdown
## Red Team Review Report

### メタ情報
- **案件名**: projects/<案件名>
- **レビュー種別**: 提案書 / 技術仕様 / ソースコード
- **レビュー対象**: [ファイルパスのリスト]
- **仕様参照**: [projects/<案件名>/02_notes/ の該当箇所]
- **レビュー日**: YYYY-MM-DD

### レビュー結果サマリー
- **総合判定**: Approved / Conditional / Rejected
- **Critical**: 0件
- **Major**: 1件
- **Minor**: 3件
- **Info**: 2件

---

### 検出された問題

#### [Critical] データ損失の可能性
**箇所**: `04_development.md §3.2` / `src/services/student.ts:45`
**基準**: B-1 Semantic Drift / B-2 Accounting Integrity
**問題**: （問題の具体的な説明）
**影響**: （ビジネスへの影響度）
**修正案**: （具体的な修正内容）
**仕様参照**: `02_notes/business-rules.md#BR-STU-001`

---

#### [Major] RFP 要件の未対応
**箇所**: `05_operation_maintenance.md`
**基準**: A-1 Requirements Coverage
**問題**: RFP §3.4「災害時復旧手順」に対応する章が存在しない
**影響**: 評価で15点失う可能性
**修正案**: DR章を追加（RPO: 1時間, RTO: 4時間 の根拠含む）

---

### 推奨アクション
1. **Critical** と **Major** の問題を修正
2. 修正後、再度 `review` スキルを実行
3. すべての問題が解決したら提出可能
```

---

## 指摘例: 提案書レビュー

### A-1: 要件カバレッジの欠落

```markdown
要件カバレッジの欠落

**RFP 要件**: §3.4「災害時のデータ復旧手順」（配点: 15点）
**提案書**: 05_operation_maintenance.md に該当章なし

**影響**: 配点15点を失う可能性
**修正案**: DR（ディザスタリカバリ）章を追加し、RPO/RTO/復旧手順を明記
```

### A-2: 章間矛盾

```markdown
章間矛盾を検出

**04_development.md**: 「8つのサブシステムを構築」
**08_schedule.md**: 「6つのサブシステムの開発工程」

**問題**: 開発章で8つ定義されたサブシステムが、スケジュールでは6つしか計上されていない
**影響**: 2つのサブシステムのスケジュールが欠落 → 納期超過リスク
**修正案**: スケジュール章に残り2サブシステムの工程を追加
```

### B-1: 仕様乖離

```markdown
仕様乖離を検出

**仕様** (`02_notes/domain-model.md#E-001`):
  - student_code: VARCHAR(10), UNIQUE, NOT NULL

**実装** (`src/models/student.ts:10`):
  @Column({ length: 50 })  // 10文字ではなく50文字
  student_code: string;

**修正案**:
  @Column({ length: 10, unique: true, nullable: false })
  student_code: string;
```
