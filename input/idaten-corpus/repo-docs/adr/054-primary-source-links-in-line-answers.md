# ADR 054: LINE回答への一次資料リンク付与

- Status: Accepted
- Date: 2026-09-21

## Context

LINE Messaging API は PDF をファイルメッセージとして送信できない。一方、結果の文字起こしだけでは原本との照合性が弱く、結果質問では一次資料へすぐ辿れることが重要である。

## Decision

結果・成績・順位などの質問で、回答に対応する正本PDFがコーパスにある場合は、回答本文に一次資料PDFの公開リンクを追加する。大会フォルダが分かる場合は、元のGoogle Driveフォルダも併記する。

PDF自体はリポジトリの公開Raw URLで取得できるようにし、Driveフォルダを原本の所在として示す。性別指定がなければ該当する男女のPDFを、指定があれば該当するPDFだけを添える。

## Consequences

- 「昨日のなごみ駅伝の結果のPDF渡して」のような質問でも、文字起こしと原本PDFを同じ回答から確認できる。
- LINE上ではPDFファイルカードではなくURL表示になる。これはMessaging APIの仕様上の制約である。
- PDFの追加・移動時は `backend/src/domain/primarySourceArtifacts.ts` の対応表を更新する。

