# アイコン & アセットカタログ

> 出典: Refactoring UI — Working with Images / アイコン・CSS アセット

---

## 核心原則

**アイコンは装飾ではなくコミュニケーションツール。一貫したサイズ・色・スタイルで使え。**

---

## 1. アイコン設計原則

### サイズの統一

| 用途 | サイズ | 例 |
|:---|:---|:---|
| **インラインテキスト** | 16px - 20px | リスト項目のアイコン |
| **ボタン内** | 16px - 20px | 送信ボタンのアイコン |
| **ナビゲーション** | 20px - 24px | サイドバーメニュー |
| **フィーチャーセクション** | 32px - 48px | 機能紹介 |
| **ヒーロー / 空状態** | 48px - 64px | 大きな図解 |

### 色の使い方

- **Primary（塗り面）**: 淡い色（メインの面積を占める部分）
- **Secondary（線・アクセント）**: 濃い色（ディテール・輪郭）
- アイコン全体の色は周囲のテキストと同系色にする
- **アイコンだけで意味を伝えない**: 必ずラベルやツールチップを併用

### デュアルトーンアイコン

Refactoring UI のアイコンセットは **Primary + Secondary** の 2 色で構成される。
CSS クラスで色を制御可能。

---

## 2. CSS カラーサンプル

Refactoring UI 同梱の 4 つのカラースキーム:

### sample1.css — クール（Blue Grey）

```css
.primary   { fill: #A5B3BB; }
.secondary { fill: #0D2B3E; }
```

### sample2.css — ティール

```css
.primary   { fill: #64D5CA; }
.secondary { fill: #20504F; }
```

### sample3.css — インディゴ

```css
.primary   { fill: #B2B7FF; }
.secondary { fill: #2F365F; }
```

### sample4.css — ピンク

```css
.primary   { fill: #FFBBCA; }
.secondary { fill: #6F213F; }
```

### カスタムカラーの適用

```css
/* プロジェクトに合わせて自由にカスタマイズ */
.primary   { fill: var(--icon-primary, #A5B3BB); }
.secondary { fill: var(--icon-secondary, #0D2B3E); }
```

---

## 3. アイコン一覧（200 個）

すべて `icon-*.svg` 形式、デュアルトーン SVG。
ソースファイルは `01_inbox/icons/` に保管。

### カテゴリ別一覧

#### ナビゲーション・操作

| アイコン名 | 用途 |
|:---|:---|
| `icon-menu` | ハンバーガーメニュー |
| `icon-close` | 閉じる |
| `icon-close-circle` | 丸枠の閉じる |
| `icon-close-square` | 角枠の閉じる |
| `icon-check` | チェックマーク |
| `icon-search` | 検索 |
| `icon-refresh` | リフレッシュ |
| `icon-external-window` | 外部リンク |
| `icon-launch` | 起動 |
| `icon-link` | リンク |
| `icon-zoom-in` | ズームイン |
| `icon-zoom-out` | ズームアウト |

#### 矢印・方向

| アイコン名 | 用途 |
|:---|:---|
| `icon-arrow-thick-down-circle` | 太矢印下（丸枠） |
| `icon-arrow-thick-left-circle` | 太矢印左（丸枠） |
| `icon-arrow-thick-right-circle` | 太矢印右（丸枠） |
| `icon-arrow-thick-up-circle` | 太矢印上（丸枠） |
| `icon-arrow-thin-down-circle` | 細矢印下（丸枠） |
| `icon-arrow-thin-left-circle` | 細矢印左（丸枠） |
| `icon-arrow-thin-right-circle` | 細矢印右（丸枠） |
| `icon-arrow-thin-up-circle` | 細矢印上（丸枠） |
| `icon-cheveron-down` | シェブロン下 |
| `icon-cheveron-down-circle` | シェブロン下（丸枠） |
| `icon-cheveron-left-circle` | シェブロン左（丸枠） |
| `icon-cheveron-right-circle` | シェブロン右（丸枠） |
| `icon-cheveron-up` | シェブロン上 |
| `icon-cheveron-up-circle` | シェブロン上（丸枠） |
| `icon-cheveron-selection` | セレクション |
| `icon-arrows-merge` | マージ |
| `icon-arrows-split` | スプリット |
| `icon-sort-ascending` | 昇順ソート |
| `icon-sort-decending` | 降順ソート |
| `icon-order-horizontal` | 横方向並び替え |
| `icon-order-vertical` | 縦方向並び替え |

#### 追加・削除・編集

| アイコン名 | 用途 |
|:---|:---|
| `icon-add` | 追加 |
| `icon-add-circle` | 追加（丸枠） |
| `icon-add-square` | 追加（角枠） |
| `icon-remove` | 削除 |
| `icon-remove-circle` | 削除（丸枠） |
| `icon-remove-square` | 削除（角枠） |
| `icon-edit` | 編集 |
| `icon-trash` | ゴミ箱 |
| `icon-dupicate` | 複製 |

#### ユーザー

| アイコン名 | 用途 |
|:---|:---|
| `icon-user` | ユーザー |
| `icon-user-add` | ユーザー追加 |
| `icon-user-check` | ユーザー確認済み |
| `icon-user-circle` | ユーザー（丸枠） |
| `icon-user-couple` | カップル |
| `icon-user-group` | グループ |
| `icon-user-remove` | ユーザー削除 |
| `icon-identification` | 身分証 |

#### ドキュメント・ファイル

| アイコン名 | 用途 |
|:---|:---|
| `icon-document` | ドキュメント |
| `icon-document-add` | ドキュメント追加 |
| `icon-document-notes` | メモ付きドキュメント |
| `icon-document-remove` | ドキュメント削除 |
| `icon-folder` | フォルダ |
| `icon-folder-add` | フォルダ追加 |
| `icon-folder-remove` | フォルダ削除 |
| `icon-archive` | アーカイブ |
| `icon-attach` | 添付 |
| `icon-print` | 印刷 |
| `icon-collection` | コレクション |

#### コミュニケーション

| アイコン名 | 用途 |
|:---|:---|
| `icon-mail` | メール |
| `icon-chat` | チャット |
| `icon-chat-group` | グループチャット |
| `icon-chat-group-alt` | グループチャット（別） |
| `icon-send` | 送信 |
| `icon-announcement` | アナウンス |
| `icon-notification` | 通知 |
| `icon-notification-off` | 通知オフ |
| `icon-phone-incoming-call` | 着信 |
| `icon-phone-outgoing-call` | 発信 |
| `icon-phone-ring` | 着信中 |

#### メディア

| アイコン名 | 用途 |
|:---|:---|
| `icon-camera` | カメラ |
| `icon-photo` | 写真 |
| `icon-film` | 動画 |
| `icon-videocam` | ビデオカメラ |
| `icon-play` | 再生 |
| `icon-pause` | 一時停止 |
| `icon-stop` | 停止 |
| `icon-fast-forward` | 早送り |
| `icon-fast-rewind` | 巻き戻し |
| `icon-microphone` | マイク |
| `icon-headphones` | ヘッドフォン |
| `icon-volume-up` | 音量上げ |
| `icon-volume-down` | 音量下げ |
| `icon-volume-mute` | ミュート |

#### デバイス・テクノロジー

| アイコン名 | 用途 |
|:---|:---|
| `icon-desktop` | デスクトップ |
| `icon-monitor` | モニター |
| `icon-device-smartphone` | スマートフォン |
| `icon-device-tablet` | タブレット |
| `icon-hard-drive` | ハードドライブ |
| `icon-server` | サーバー |
| `icon-cloud-download` | クラウドダウンロード |
| `icon-cloud-upload` | クラウドアップロード |
| `icon-clouds` | クラウド |
| `icon-wifi` | Wi-Fi |
| `icon-wifi-off` | Wi-Fi オフ |
| `icon-battery-full` | バッテリー満 |
| `icon-battery-half` | バッテリー半分 |
| `icon-code` | コード |
| `icon-bug` | バグ |

#### ビジネス・コマース

| アイコン名 | 用途 |
|:---|:---|
| `icon-shopping-cart` | ショッピングカート |
| `icon-shopping-bag` | ショッピングバッグ |
| `icon-shopping-basket` | ショッピングバスケット |
| `icon-credit-card` | クレジットカード |
| `icon-currency-dollar` | ドル |
| `icon-currency-euro` | ユーロ |
| `icon-money` | お金 |
| `icon-wallet` | 財布 |
| `icon-receipt` | レシート |
| `icon-discount` | ディスカウント |
| `icon-tag` | タグ |
| `icon-store` | ストア |
| `icon-factory` | 工場 |
| `icon-office` | オフィス |
| `icon-work` | 仕事 |
| `icon-deliver` | 配達 |
| `icon-package` | パッケージ |
| `icon-box` | 箱 |
| `icon-scale` | スケール |

#### ステータス・フィードバック

| アイコン名 | 用途 |
|:---|:---|
| `icon-heart` | お気に入り |
| `icon-star` | スター |
| `icon-thumbs-up` | いいね |
| `icon-thumbs-down` | よくない |
| `icon-mood-happy` | 嬉しい |
| `icon-mood-neutral` | 普通 |
| `icon-mood-sad` | 悲しい |
| `icon-flag` | フラグ |
| `icon-pin` | ピン |
| `icon-bolt` | 稲妻 |
| `icon-trophy` | トロフィー |
| `icon-certificate` | 証明書 |
| `icon-important` | 重要 |
| `icon-information` | 情報 |
| `icon-help` | ヘルプ |
| `icon-trending-up` | 上昇トレンド |
| `icon-trending-down` | 下降トレンド |

#### その他ユーティリティ

| アイコン名 | 用途 |
|:---|:---|
| `icon-cog` | 設定 |
| `icon-tune` | 調整 |
| `icon-key` | 鍵 |
| `icon-lock` | ロック |
| `icon-lock-open` | ロック解除 |
| `icon-security` | セキュリティ |
| `icon-security-check` | セキュリティ確認 |
| `icon-security-important` | セキュリティ警告 |
| `icon-view-visible` | 表示 |
| `icon-view-hidden` | 非表示 |
| `icon-door-enter` | 入室 |
| `icon-door-exit` | 退室 |
| `icon-home` | ホーム |
| `icon-globe` | グローブ |
| `icon-compass` | コンパス |
| `icon-map` | 地図 |
| `icon-location-pin` | 位置ピン |
| `icon-calendar` | カレンダー |
| `icon-calendar-add` | カレンダー追加 |
| `icon-calendar-date` | カレンダー日付 |
| `icon-calendar-remove` | カレンダー削除 |
| `icon-time` | 時間 |
| `icon-hour-glass` | 砂時計 |
| `icon-history` | 履歴 |
| `icon-calculator` | 電卓 |
| `icon-chart` | チャート |
| `icon-pie-chart` | 円グラフ |
| `icon-dashboard` | ダッシュボード |
| `icon-presentation` | プレゼン |
| `icon-presentation-play` | プレゼン再生 |
| `icon-survey` | アンケート |
| `icon-news` | ニュース |
| `icon-book-closed` | 閉じた本 |
| `icon-book-open` | 開いた本 |
| `icon-library` | ライブラリ |
| `icon-layers` | レイヤー |
| `icon-widget-add` | ウィジェット追加 |
| `icon-interface` | インターフェース |
| `icon-application` | アプリケーション |
| `icon-brick` | ブロック |
| `icon-puzzle` | パズル |
| `icon-swatch` | スウォッチ |
| `icon-paint` | ペイント |
| `icon-light` | ライト |
| `icon-umbrella` | 傘 |
| `icon-airplane` | 飛行機 |
| `icon-sign` | サイン |
| `icon-buoy` | ブイ |
| `icon-target` | ターゲット |
| `icon-click-target` | クリックターゲット |
| `icon-text-cursor` | テキストカーソル |
| `icon-translate` | 翻訳 |
| `icon-ticket` | チケット |
| `icon-thermostat-full` | 温度計（満） |
| `icon-thermostat-half` | 温度計（半分） |
| `icon-dots-horizontal` | 横ドット |
| `icon-dots-vertical` | 縦ドット |
| `icon-asterisk` | アスタリスク |
| `icon-at` | アットマーク |
| `icon-inbox-check` | 受信確認 |
| `icon-inbox-download` | 受信ダウンロード |
| `icon-inbox-full` | 受信箱フル |
| `icon-inbox-upload` | 受信アップロード |

---

## 4. インライン SVG の使い方

### HTML での埋め込み

```html
<!-- SVG ファイルを直接埋め込み -->
<svg class="icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
  <path class="primary" d="..." />
  <path class="secondary" d="..." />
</svg>
```

### CSS でサイズ・色を制御

```css
.icon {
  width: 24px;
  height: 24px;
}

.icon .primary {
  fill: var(--icon-primary, #A5B3BB);
}

.icon .secondary {
  fill: var(--icon-secondary, #0D2B3E);
}
```

---

## チェックリスト

- [ ] アイコンサイズが用途に応じた統一サイズか
- [ ] アイコンの色がテキストと同系色か
- [ ] アイコン単体でなくラベルも併用しているか
- [ ] デュアルトーンの Primary/Secondary が適切か
