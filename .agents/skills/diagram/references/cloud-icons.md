# Cloud Icons Reference (クラウドアイコン・リファレンス)

## ⚠️ Critical: Azure Icon Format (重要)

**VS Code Draw.io Integration では `mxgraph.azure.*` 形式が正しく表示されません（青い四角形になります）。**

必ず `img/lib/azure2/**/*.svg` 形式を使用してください。

| 形式 | Web 版 | VS Code 版 | 推奨状況 |
|:---|:---|:---|:---|
| `shape=mxgraph.azure.*` | ✅ | ❌ **青い四角** | **使用禁止 (Deprecated)** |
| `image=img/lib/azure2/**/*.svg` | ✅ | ✅ **正常表示** | **推奨 (Official)** |

## 🔧 Initial Setup (初期設定：必須)

Azure/AWS アイコンを使うには、**事前にシェイプライブラリを有効化**する必要があります。

1. `.drawio` ファイルを VS Code で開く
2. 左下の **「+ その他の図形」** をクリック
3. **Azure** および **AWS** にチェックを入れる
4. **「適用」** をクリック

---

## ☁️ Azure Icons (Azure2 形式)

### Common Azure Icons (よく使うアイコン)

| Service | SVG Path | Category |
|:---|:---|:---|
| **Compute** | | |
| Virtual Machine | `img/lib/azure2/compute/Virtual_Machine.svg` | compute |
| VM Scale Sets | `img/lib/azure2/compute/VM_Scale_Sets.svg` | compute |
| App Service | `img/lib/azure2/compute/App_Services.svg` | compute |
| Function Apps | `img/lib/azure2/compute/Function_Apps.svg` | compute |
| AKS | `img/lib/azure2/compute/Azure_Kubernetes_Service.svg` | compute |
| **Networking** | | |
| Virtual Network | `img/lib/azure2/networking/Virtual_Networks.svg` | networking |
| Subnet | `img/lib/azure2/networking/Subnet.svg` | networking |
| Load Balancer | `img/lib/azure2/networking/Load_Balancers.svg` | networking |
| Application Gateway | `img/lib/azure2/networking/Application_Gateways.svg` | networking |
| Front Door | `img/lib/azure2/networking/Front_Doors.svg` | networking |
| Firewall | `img/lib/azure2/networking/Firewalls.svg` | networking |
| Private Endpoint | `img/lib/azure2/networking/Private_Endpoint.svg` | networking |
| **Databases** | | |
| SQL Database | `img/lib/azure2/databases/SQL_Database.svg` | databases |
| Cosmos DB | `img/lib/azure2/databases/Azure_Cosmos_DB.svg` | databases |
| **Storage** | | |
| Storage Account | `img/lib/azure2/storage/Storage_Accounts.svg` | storage |
| **Security** | | |
| Key Vault | `img/lib/azure2/security/Key_Vaults.svg` | security |
| Azure AD / Entra ID | `img/lib/azure2/identity/Azure_Active_Directory.svg` | identity |

### Azure Icon Style Example (✅ 正しいスタイル例)

```xml
<mxCell id="vm1" value="VM-01"
        style="aspect=fixed;html=1;points=[];align=center;image;fontSize=12;image=img/lib/azure2/compute/Virtual_Machine.svg;verticalLabelPosition=bottom;verticalAlign=top;"
        vertex="1" parent="1">
  <mxGeometry x="100" y="100" width="68" height="68" as="geometry"/>
</mxCell>
```

### 🚫 Non-Existent Icons & Alternatives (存在しないアイコンと代替案)

以下のアイコンは draw.io の azure2 ライブラリに**存在しない**か、**パスが直感的でない**ものです。代替案を使用してください。

| サービス | ❌ よくある間違い | ✅ 正しいパス / 代替案 |
|:---|:---|:---|
| **GitHub / GitHub Actions** | `other/GitHub.svg` | ライブラリに存在しません。角丸ボックスで代用してください。 |
| **Internet** | `networking/Internet.svg` | `shape=cloud` (汎用の雲形) を使用してください。 |

---

## ☁️ AWS Icons (AWS4 形式)

### Common AWS Icons (よく使うアイコン)

| Service | resIcon Value | Category |
|:---|:---|:---|
| EC2 | `mxgraph.aws4.ec2` | Compute |
| Lambda | `mxgraph.aws4.lambda` | Compute |
| S3 | `mxgraph.aws4.s3` | Storage |
| RDS | `mxgraph.aws4.rds` | Database |
| VPC | `mxgraph.aws4.vpc` | Networking |

### AWS Icon Style Example

```xml
<mxCell id="ec2" value="EC2"
        style="sketch=0;outlineConnect=0;fontColor=#232F3E;gradientColor=none;strokeColor=#ffffff;fillColor=#232F3E;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;fontSize=12;fontStyle=0;aspect=fixed;shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.ec2;"
        vertex="1" parent="1">
  <mxGeometry x="100" y="100" width="50" height="50" as="geometry"/>
</mxCell>
```

---

## ✅ Validation Checklist (検証チェックリスト)

生成後に以下を確認してください：

- [ ] Azure アイコンが `img/lib/azure2/` パスを使用している
- [ ] `shape=mxgraph.azure.*` が含まれて**いない**
- [ ] VS Code Draw.io Integration で正しく表示される
