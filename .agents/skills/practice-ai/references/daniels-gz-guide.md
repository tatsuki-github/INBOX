# Daniels 基準 GZ / サブ閾値ペース回答ガイド

> **エージェント向け必須ルール**: ユーザーが GZ・ゴールデンゾーン・サブ閾値・閾値ペースを聞いた場合、
> **必ず Daniels 計算ツールを実行**し、その出力を根拠に回答する。
> 10K 換算・Web 検索・頭の中の概算でペースを出してはならない。

## 実行コマンド

```bash
# レースタイムから（推奨）
python3 scripts/daniels_pace.py --race 1500m 4:20

# 既知の Daniels T ペースから
python3 scripts/daniels_pace.py --t-pace 3:29

# 選手メモ形式（events.yaml と同じブロック）
python3 scripts/daniels_pace.py --race 1500m 4:20 --format block
```

## 計算パイプライン

```
レースタイム
  → VDOT（Daniels-Gilbert 式）
  → E/M/T/I/R ペース（Daniels 3rd ed. テーブル補間）
  → T ペース
  → GZ ブロック（pace_calculator.py: T + 8〜25秒/km、距離別）
```

## 用語の対応

| 用語 | Daniels | ノルウェー |
|------|---------|-----------|
| 閾値 | T ペース（〜4 mmol/L、約1時間走） | 個人閾値 2.5–3.0 mmol/L |
| サブ閾値 / GZ | **T より遅い**（T+8〜25秒/km） | 乳酸 2.3–3.0 mmol/L |
| イージー | E ペース | 最大心拍 70% 以下 |

**重要**: GZ は Daniels T ペースより**遅い**。T ペースや 5K ペース（I）と混同しない。

## 回答テンプレート

1. `daniels_pace.py` を実行
2. VDOT と Daniels T ペースを明示
3. GZ はインターバル長別（600m / 1000m 等）に提示
4. 心拍・乳酸は補足（ペースの主根拠は Daniels 計算結果）

## 例: 1500m 4:20

```
VDOT 64.0
T (Threshold): 3:29/km
GZ 600m: 2:10〜2:13（T+8〜12秒/km）
GZ 1000m: 3:41〜3:47（T+12〜18秒/km）
```

## 実装参照

- [`scripts/ai/daniels_calculator.py`](../../../scripts/ai/daniels_calculator.py)
- [`scripts/ai/pace_calculator.py`](../../../scripts/ai/pace_calculator.py)
- [`input/daniels_vdot_paces.yaml`](../../../input/daniels_vdot_paces.yaml)
- [docs/adr/008-daniels-vdot-gz-guidance.md](../../../docs/adr/008-daniels-vdot-gz-guidance.md)
