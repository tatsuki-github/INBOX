# Style Guide (スタイルガイド)

## Node Colors (ノード配色)

| 用途 | fillColor | strokeColor | 使用例 |
|:---|:---|:---|:---|
| **Standard (標準)** | `#dae8fc` | `#6c8ebf` | 一般的な処理、ステップ |
| **Start/End (開始/終了)** | `#d5e8d4` | `#82b366` | フローの開始と終了 |
| **Decision (判定)** | `#fff2cc` | `#d6b656` | 条件分岐 |
| **Error/Warning (異常)** | `#f8cecc` | `#b85450` | エラー状態、例外処理 |
| **External (外部)** | `#e1d5e7` | `#9673a6` | 外部システム、アクター |
| **Neutral (中立)** | `#f5f5f5` | `#666666` | グループ、コンテナ |

## Edge Styles (エッジスタイル)

### Orthogonal (直角 - 推奨)

```
edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;
```

一般的なフローチャートやシステム構成図ではこれを使用します。

### Straight (直線)

```
endArrow=classic;html=1;
```

シンプルな接続に使用します。

## Shape Styles (形状スタイル)

### Rounded Rectangle (角丸四角形)

```
rounded=1;whiteSpace=wrap;html=1;
```

### Ellipse (楕円)

```
ellipse;whiteSpace=wrap;html=1;
```

### Diamond (ひし形)

```
rhombus;whiteSpace=wrap;html=1;
```

### Swimlane/Container (スイムレーン)

```
swimlane;horizontal=1;startSize=30;
```

## Layout Recommendations (レイアウト推奨値)

- **Grid**: グリッド `10px` にスナップさせる (`gridSize=10`)
- **Spacing**:
    - 水平間隔: `50-80px`
    - 垂直間隔: `40-60px`
    - グループ内マージン: `20px`
- **Font**:
    - 英語: `Helvetica`
    - 日本語: `Meiryo` または指定なし (システムデフォルト)
    - サイズ: ノード `12px` / ラベル `10px` / タイトル `14-16px`
