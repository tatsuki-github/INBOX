# mxCell Structure Reference (mxCell 構造リファレンス)

## mxfile Structure (ファイル構造)

```xml
<mxfile host="app.diagrams.net" generator="diagram-forge">
  <diagram id="..." name="Page-1">
    <mxGraphModel dx="..." dy="..." grid="1" gridSize="10">
      <root>
        <mxCell id="0" />
        <mxCell id="1" parent="0" />
        <!-- Nodes and edges here -->
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>
```

## Required Elements (必須要素)

| Element | Description | Required |
|:---|:---|:---|
| `mxCell id="0"` | Root cell (ルート) | ✅ |
| `mxCell id="1" parent="0"` | Default parent (デフォルト親) | ✅ |
| Node mxCell | `vertex="1"` を持つこと | ✅ |
| Edge mxCell | `edge="1"` を持つこと | ✅ |

## Node Examples (ノード例)

### Rectangle (四角形)

```xml
<mxCell id="node1" value="Node Name"
        style="rounded=1;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;"
        vertex="1" parent="1">
  <mxGeometry x="100" y="100" width="120" height="60" as="geometry"/>
</mxCell>
```

### Ellipse (開始/終了)

```xml
<mxCell id="start" value="Start"
        style="ellipse;whiteSpace=wrap;html=1;fillColor=#d5e8d4;strokeColor=#82b366;"
        vertex="1" parent="1">
  <mxGeometry x="100" y="100" width="80" height="50" as="geometry"/>
</mxCell>
```

### Diamond (条件判定)

```xml
<mxCell id="decision1" value="Condition?"
        style="rhombus;whiteSpace=wrap;html=1;fillColor=#fff2cc;strokeColor=#d6b656;"
        vertex="1" parent="1">
  <mxGeometry x="100" y="100" width="100" height="80" as="geometry"/>
</mxCell>
```

## Edge Examples (エッジ例)

### Arrow (矢印)

```xml
<mxCell id="edge1" value=""
        style="edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;"
        edge="1" parent="1" source="node1" target="node2">
  <mxGeometry relative="1" as="geometry"/>
</mxCell>
```

### Labeled Edge (ラベル付き矢印)

```xml
<mxCell id="edge2" value="Yes"
        style="edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;"
        edge="1" parent="1" source="decision1" target="node3">
  <mxGeometry relative="1" as="geometry"/>
</mxCell>
```

## Group (Container) (グルーピング)

```xml
<!-- Container -->
<mxCell id="group1" value="Group Name"
        style="swimlane;horizontal=1;startSize=30;fillColor=#f5f5f5;strokeColor=#666666;"
        vertex="1" parent="1">
  <mxGeometry x="50" y="50" width="300" height="200" as="geometry"/>
</mxCell>

<!-- Child node (parent="group1") -->
<mxCell id="child1" value="Child Node"
        style="rounded=1;whiteSpace=wrap;html=1;"
        vertex="1" parent="group1">
  <mxGeometry x="20" y="40" width="100" height="50" as="geometry"/>
</mxCell>
```

## HTML Encoding (HTMLエンコード)

`value` 属性などのテキストコンテンツは HTML エンコードが必要です：

| 文字 | エンコード後 |
|:---|:---|
| `<` | `&lt;` |
| `>` | `&gt;` |
| `"` | `&quot;` |
| `&` | `&amp;` |
