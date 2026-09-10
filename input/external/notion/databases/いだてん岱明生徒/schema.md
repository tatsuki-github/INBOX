# いだてん岱明生徒

- URL: https://app.notion.com/p/3d3a38e830348023a011d8ece7451e47?pvs=204
- Data source: `collection://3d3a38e8-3034-807e-9a80-000b41555366`
- View: `view://3d3a38e8-3034-8056-b8e2-000c7ea39f48` (table)

## Properties
| Name | Type | Notes |
|------|------|-------|
| 名前 | title | |
| 学年 | number | |
| 800mPB | text | |
| 1500mPB | text | |
| 3000mPB | text | |
| タイプ | select | スピード型 / スタミナ型 / バランス型 |
| 備考 | text | |

## SQLite
```sql
CREATE TABLE IF NOT EXISTS "collection://3d3a38e8-3034-807e-9a80-000b41555366" (
  url TEXT UNIQUE,
  createdTime TEXT,
  "タイプ" TEXT,
  "1500mPB" TEXT,
  "800mPB" TEXT,
  "学年" FLOAT,
  "3000mPB" TEXT,
  "備考" TEXT,
  "名前" TEXT
)
```
