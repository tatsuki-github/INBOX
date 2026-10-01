import { describe, expect, it, beforeEach } from "vitest";
import {
  loadPreparedQa,
  matchPreparedAnswer,
  normalizePreparedQuestion,
  resetPreparedQaCache,
} from "../src/domain/preparedQa.js";
import { answerQuestion } from "../src/domain/answer.js";

describe("preparedQa catalog", { timeout: 30_000 }, () => {
  beforeEach(async () => {
    // Large catalogs rebuild their index in synchronous tests. Yield between
    // cases so the test worker can send progress and service its RPC channel.
    await new Promise(resolve => setTimeout(resolve, 0));
    resetPreparedQaCache();
  });

  it("loads prepared catalog entries", () => {
    const entries = loadPreparedQa();
    expect(entries.length).toBeGreaterThanOrEqual(28000);
    expect(entries[0]?.id).toBeTruthy();
    expect(entries[0]?.answer.length).toBeGreaterThan(10);
  });

  it("keeps audited annual records and prediction scopes factual", () => {
    const entries = new Map(loadPreparedQa().map((e) => [e.id, e]));
    const sato = entries.get("records-athlete-2025-佐藤央琉")!;
    expect(sato.answer).toContain("全9件");
    expect(sato.answer).toContain("2025/09/21 3区 10:42");
    expect(sato.answer).not.toMatch(/3区 0:42/);
    const matsumoto = entries.get("records-athlete-2025-松本空羽")!;
    expect(matsumoto.answer).toContain("全4件");
    expect(matsumoto.answer).not.toMatch(/4区 2:37/);
    expect(entries.get("formula-2026-男子-荒尾三中-order")!.answer).toContain("3区間のみの小計 32:13");
    expect(entries.get("formula-2026-男子-荒尾三中-order")!.answer).toContain("総合タイムは算出できません");
    expect(entries.get("records-team-ATRC")!.answer).toContain("2026年度の収録件数は67件");
    expect(entries.get("aragyoku-winner-pace")!.answer).toContain("3:11/km");
    expect(entries.get("records-athlete-3y-佐藤央琉")!.sources.some((s) => s.endsWith("岱明の結果.md"))).toBe(true);
  });

  it("keeps annual SB distinct from lifetime PB and past meet questions dated", () => {
    const entries = loadPreparedQa();
    for (const e of entries.filter((e) => /^sb-20\d{2}-/.test(e.id))) {
      expect(e.answer, e.id).toContain("シーズンベスト");
      expect(e.answer, e.id).toContain(e.id.split("-")[1]);
    }
    for (const e of entries.filter((e) => /^race-202[45]-/.test(e.id))) {
      expect(e.questions.every((q) => q.includes(e.id.split("-")[1]!)), e.id).toBe(true);
    }
  });

  it("does not fuzzy-match a dated historical result to a yearless current query", () => {
    const historical = {
      id: "race-2024-選手甲-記録会",
      questions: ["2024年選手甲の記録会の結果は？"],
      answer: "2024年度の選手甲の1500m記録は5:00です。",
      sources: ["fixture.csv"],
      tags: ["2024"],
    };
    expect(matchPreparedAnswer("選手甲の記録会の結果は？", { defaultYear: 2026, entries: [historical] })).toBeNull();
    expect(matchPreparedAnswer("2024年選手甲の記録会の結果は？", { defaultYear: 2026, entries: [historical] })?.id).toBe(historical.id);
    const latestKnown = { ...historical, questions: ["選手甲の直近の記録会の結果は？"] };
    expect(matchPreparedAnswer("選手甲の直近の記録会の結果は？", { defaultYear: 2026, entries: [latestKnown] })?.id).toBe(historical.id);
  });

  it("keeps user-facing answers free of repo-path jargon", () => {
    const entries = loadPreparedQa();
    const bad = entries.filter((e) => {
      const a = e.answer || "";
      return (
        /(?:^|[\s「])(?:input|out|docs|scripts)\//.test(a) ||
        /出典:\s*(?:out\/|input\/)/.test(a) ||
        /状態:\s*\w+/.test(a) ||
        /チーム別正本/.test(a)
      );
    });
    expect(bad.slice(0, 5).map((e) => e.id)).toEqual([]);
    expect(bad.length).toBe(0);
  });

  it("omits non-link bibliographic references in answers", () => {
    const entries = loadPreparedQa();
    const bad = entries.filter((e) => {
      const a = e.answer || "";
      return (
        /（[^）]*徹底対策ガイド[^）]*）/.test(a) ||
        /出場枠は[^。\n]*要項/.test(a) ||
        /詳しくは[^。\n]*(?:ガイド|徹底対策)/.test(a)
      );
    });
    expect(bad.slice(0, 5).map((e) => e.id)).toEqual([]);
    expect(bad.length).toBe(0);

    const core = matchPreparedAnswer("荒玉駅伝は何位までが県駅伝に出場できる？", {
      defaultYear: 2026,
    });
    expect(core?.text).toContain("男女上位2校");
    expect(core?.text).not.toContain("徹底対策ガイド");
    expect(core?.text).not.toContain("大会要項");
  });

  it("covers diversified bulk ids beyond the first 100", () => {
    const entries = loadPreparedQa();
    const ids = new Set(entries.map((e) => e.id));
    expect(ids.has("aragyoku-what")).toBe(true);
    // bulk generators + aragyoku athlete SB bank + knowledge cover
    expect([...ids].some((id) => id.startsWith("sb-2026-"))).toBe(true);
    expect([...ids].some((id) => id.startsWith("sb-2012-"))).toBe(true);
    expect([...ids].some((id) => id.startsWith("cal-"))).toBe(true);
    expect([...ids].some((id) => id.includes("-leg"))).toBe(true);
    expect([...ids].some((id) => id.startsWith("meet-result-"))).toBe(true);
    expect([...ids].some((id) => id.startsWith("records-team-"))).toBe(true);
    expect([...ids].some((id) => id.startsWith("profile-"))).toBe(true);
    expect([...ids].some((id) => id.startsWith("topic-"))).toBe(true);
    expect([...ids].some((id) => id.startsWith("sb-school-"))).toBe(true);
    expect([...ids].some((id) => id.startsWith("records-athlete-2026-"))).toBe(true);
    expect(ids.has("records-athlete-2026-南本幸治郎")).toBe(true);
    expect([...ids].some((id) => id.startsWith("race-2026-"))).toBe(true);
    expect([...ids].some((id) => id.startsWith("aragyoku-career-"))).toBe(true);
    expect([...ids].some((id) => id.endsWith("-order"))).toBe(true);
    expect([...ids].some((id) => id.endsWith("-splitrank"))).toBe(true);
    expect(ids.has("guide-2026-what")).toBe(true);
    expect(ids.has("trial-2026-daiming-aragyoku")).toBe(true);
  });

  it(
    "covers knowledge topics via prepared answers",
    () => {
      const cases: Array<[string, RegExp]> = [
        ["南関中の記録一覧は？", /南関中/],
        ["松野凛空のプロフィールは？", /岱明中/],
        ["岱明の1500m最速は誰？", /4:22\.33|松野凛空/],
        ["玉名郡ナイター中・長距離記録会の結果は？", /4:29\.8|松野凛空/],
        ["選手記録はどこで分かる？", /自己ベスト|選手名/],
        ["南本幸治郎の今年度の全ての記録", /5:23\.50|kumariku\.org/],
      ];
      for (const [q, re] of cases) {
        const hit = matchPreparedAnswer(q, { defaultYear: 2026 });
        expect(hit, q).toBeTruthy();
        expect(hit?.text, q).toMatch(re);
        expect(hit?.text, q).not.toContain("コーチに直接聞いてください");
      }
    },
    60_000,
  );
});

describe("normalizePreparedQuestion", () => {
  it("expands relative years and strips trailing noise", () => {
    expect(normalizePreparedQuestion("去年の荒玉女子優勝は誰？", { defaultYear: 2026 })).toContain(
      "2025",
    );
    expect(normalizePreparedQuestion("コース図を見せて", { defaultYear: 2026 })).toMatch(/画像|コース/);
  });
});

describe("matchPreparedAnswer", { timeout: 30_000 }, () => {
  beforeEach(async () => {
    // Large catalogs rebuild their index in synchronous tests. Yield between
    // cases so the test worker can send progress and service its RPC channel.
    await new Promise(resolve => setTimeout(resolve, 0));
    resetPreparedQaCache();
  });

  it("hits canonical questions", () => {
    const hit = matchPreparedAnswer("荒玉駅伝って何？", { defaultYear: 2026 });
    expect(hit?.id).toBe("aragyoku-what");
    expect(hit?.text).toContain("中体連駅伝");
  });

  it("hits paraphrases", () => {
    const hit = matchPreparedAnswer("県ジュニアの結果PDFを見せて", { defaultYear: 2026 });
    // 年なしは今年度（2026）の PDF/フォルダ案内
    expect(hit?.id).toBe("junior-2026-pdf");
    expect(hit?.text).toMatch(/2026|drive\.google\.com/);
  });

  it(
    "hits coach-oriented analysis questions from focus / SB / trial facts",
    () => {
      const cases: Array<[string, RegExp]> = [
        ["岱明男子の前年比は？", /15位.*59:08|65:15.*6位/],
        ["岱明男子のボトルネック区間は？", /案浦竜士|6区/],
        ["2025年岱明男子で一番よかった区間は？", /山本哲瑠|5区/],
        ["天水の区間新は？", /山本悠斗|8:37/],
        ["連続出場した岱明男子は？", /松野凛空|今村昇磨|倉田裕斗/],
        ["2024から2025で一番伸びたのはどの校？", /岱明男子|15位→6位/],
        ["どの学校が2位以内が多い？", /玉名.*15|荒尾三/],
        ["1500mの学校別ランキングは？", /玉陵|4:23/],
        ["岱明の試走タイムは？", /9:48|松野/],
        ["岱明男子の2026区間予想は？", /58:55|松野凛空/],
      ];
      for (const [q, re] of cases) {
        const hit = matchPreparedAnswer(q, { defaultYear: 2026 });
        expect(hit, q).toBeTruthy();
        expect(hit?.text, q).toMatch(re);
        expect(hit?.text, q).not.toContain("コーチに直接聞いてください");
      }
    },
    120_000,
  );

  it(
    "hits slight wording variants via synonyms and expanded questions",
    () => {
      const cases: Array<[string, string | RegExp]> = [
        ["松野凛空のベストタイムは？", /^sb-2026-松野凛空$/],
        ["松野凛空の自己記録は？", /^sb-2026-松野凛空$/],
        ["2025年の荒玉男子の優勝チームは？", /aragyoku-2025-.*men.*winner|aragyoku-2025-men-winner/],
        ["去年荒玉男子誰が勝った？", /aragyoku-2025-men-winner|gap1000-winner-2025-男子/],
        ["荒玉駅伝ってどんな大会？", /^aragyoku-what$/],
        ["荒玉はどういう大会？", /^aragyoku-what$/],
        ["荒玉の地図見せて", /^aragyoku-course-image$/],
        ["南関の陸上部名簿見せて", /^roster-aff-南関中$/],
        ["荒玉で2位まで県に出れる？", /^aragyoku-pref-top2-core$/],
        ["男子の荒玉の距離は？", /^aragyoku-men-distance$/],
        ["去年岱明男子何位？", /^aragyoku-2025-daiming-men$/],
        ["なごみはいつ開催？", /nagomi|cal-2026-.*なごみ/],
        ["田上颯人の1500のベストは？", /^sb-2026-田上颯人-1500m$/],
        ["通信陸上の結果URLは？", /meet-.*通信陸上/],
      ];
      for (const [q, idRe] of cases) {
        const hit = matchPreparedAnswer(q, { defaultYear: 2026 });
        expect(hit, q).toBeTruthy();
        expect(hit!.id, q).toMatch(idRe);
      }
    },
    120_000,
  );

  it("hits relative-year wording", () => {
    const hit = matchPreparedAnswer("去年の荒玉男子優勝は誰？", { defaultYear: 2026 });
    expect(hit?.id).toBe("aragyoku-2025-men-winner");
    expect(hit?.text).toContain("菊水");
  });

  it("maps 昨年/去年 junior results to 2025, not 2026", () => {
    for (const q of ["昨年のジュニア駅伝の結果", "去年のジュニア駅伝の結果", "昨年の県ジュニア駅伝の結果は？"]) {
      const hit = matchPreparedAnswer(q, { defaultYear: 2026 });
      expect(hit?.id, q).toBe("junior-2025-result");
      expect(hit?.text, q).toContain("2025");
      expect(hit?.text, q).toContain("36:47");
      expect(hit?.text, q).not.toContain("36:52");
    }
  });

  it("maps 昨年/前年 aragyoku winners to 2025, not 2024", () => {
    for (const q of ["昨年の荒玉男子優勝は誰？", "前年の荒玉男子優勝は誰？", "昨年度の荒玉男子優勝は誰？"]) {
      const hit = matchPreparedAnswer(q, { defaultYear: 2026 });
      expect(hit?.id, q).toBe("aragyoku-2025-men-winner");
      expect(hit?.text, q).toContain("2025");
      expect(hit?.text, q).toContain("菊水");
      expect(hit?.text, q).not.toMatch(/2024年荒玉駅伝男子の優勝は南関/);
    }
  });

  it("does not expand 前年比 into a 2025-year question", () => {
    expect(normalizePreparedQuestion("岱明男子の前年比は？", { defaultYear: 2026 })).toContain("同比");
    expect(normalizePreparedQuestion("岱明男子の前年比は？", { defaultYear: 2026 })).not.toContain("2025年比");
  });

  it("does not double-replace into 区間区間距離", () => {
    expect(normalizePreparedQuestion("区間距離", { defaultYear: 2026 })).toBe("区間距離");
    expect(normalizePreparedQuestion("荒玉男子の区間距離は？", { defaultYear: 2026 })).not.toContain(
      "区間区間",
    );
  });

  it(
    "covers edge-5000 niche facts (who-rank / split-rank / historical race / pace)",
    () => {
      const cases: Array<[string, RegExp, RegExp]> = [
        ["2025年荒玉男子の6位はどの学校？", /^edge5k-who-rank-2025-男子-6$/, /岱明|59:08/],
        // 既存の leg2-best 定型が先に当たっても事実（山本悠斗 8:37）は同じ
        ["2025年荒玉男子2区の区間賞は誰？", /leg2-(best|r1)|splitrank-2025-男子-leg2/, /山本悠斗|8:37/],
        ["2023年岩根正太朗の熊本市陸上競技記録会の記録は？", /^race-2023-岩根正太朗-/, /4:34\.83/],
        ["2025年荒玉女子岱明の平均ペースは？", /^edge5k-pace-2025-女子-rank7-岱明$/, /3:49\.6\/km|45:22/],
        ["2018年荒玉男子の10位はどの学校？", /^edge5k-who-rank-2018-男子-10$/, /.+/],
      ];
      for (const [q, idRe, textRe] of cases) {
        const hit = matchPreparedAnswer(q, { defaultYear: 2026 });
        expect(hit, q).toBeTruthy();
        expect(hit!.id, q).toMatch(idRe);
        expect(hit!.text, q).toMatch(textRe);
        expect(hit!.text, q).not.toMatch(/(?:input|out|docs)\//);
      }
    },
    120_000,
  );


  it(
    "returns corrected 2024 Daimei men leg names from the result board",
    () => {
      const hit = matchPreparedAnswer("2024年の岱明男子の区間詳細", { defaultYear: 2026 });
      expect(hit?.id).toBe("aragyoku-2024-男子-岱明-leg-detail");
      expect(hit?.text).toContain("南本和顕");
      expect(hit?.text).toContain("浦田桐生");
      expect(hit?.text).not.toContain("根本和樹");
      expect(hit?.text).not.toContain("満田樹生");
      const leg1 = matchPreparedAnswer("2024年荒玉男子岱明の1区は誰？", { defaultYear: 2026 });
      expect(leg1?.text).toContain("南本和顕");
      expect(leg1?.text).not.toContain("根本和樹");
    },
    120_000,
  );


  it(
    "routes formula/preview away from OCR dumps and hits per-leg distances",
    () => {
      const cases: Array<[string, RegExp, RegExp]> = [
        ["今年の荒玉男子の数式予想は？", /^meet-2026-aragyoku-school-expand$/, /玉陵|56:01/],
        ["荒玉男子の戦力分析は？", /^meet-2026-aragyoku-school-expand$/, /校別展開|数式予想/],
        ["荒玉女子の数式予想は？", /^meet-2026-aragyoku-school-expand$/, /荒尾三|42:53/],
        [
          "今年の荒玉駅伝の女子2区までの順位予想",
          /^aragyoku-2026-pass-rank-女子-through2$/,
          /荒尾三中（17:23）|岱明中（17:44）/,
        ],
        [
          "今年の荒玉駅伝の男子3区までの順位予想",
          /^aragyoku-2026-pass-rank-男子-through3$/,
          /玉陵中（27:46）|岱明中（28:35）/,
        ],
        [
          "荒玉駅伝の女子の順位予想は？",
          /^aragyoku-2026-pass-rank-女子-through5$/,
          /荒尾三中（42:53）/,
        ],
        [
          "今年の荒玉駅伝の順位予想",
          /^aragyoku-2026-pass-rank-both-overall$/,
          /男子:.*玉陵中|女子:.*荒尾三中/,
        ],
        ["荒玉男子2区の距離は？", /^aragyoku-distance-current-男子-leg2$/, /2\.855km/],
        ["荒玉男子の区間距離は？", /^aragyoku-men-distance$/, /17\.71km/],
        ["荒玉の総距離は？", /^gap1000-overview-distance$/, /17\.71km|11\.855km/],
        ["2区の距離は？", /^aragyoku-distance-current-both-leg2$/, /男子.*2\.855km|女子.*1\.855km/],
        ["2026年荒玉男子の分析PDFは？", /^analysis-ocr-2026-男子$/, /drive\.google\.com/],
      ];
      for (const [q, idRe, textRe] of cases) {
        const hit = matchPreparedAnswer(q, { defaultYear: 2026 });
        expect(hit, q).toBeTruthy();
        expect(hit!.id, q).toMatch(idRe);
        expect(hit!.text, q).toMatch(textRe);
        expect(hit!.text, q).not.toMatch(/パート\d+|OCR生/);
      }
    },
    120_000,
  );

  it("keeps yearless junior result on current-year entry", () => {
    const hit = matchPreparedAnswer("ジュニア駅伝の結果は？", { defaultYear: 2026 });
    expect(hit?.id).toBe("junior-2026-result");
  });

  it("returns current SB for 田上颯人, not stale 4:58.03", () => {
    const hit = matchPreparedAnswer("田上颯人の自己ベストは？", { defaultYear: 2026 });
    expect(hit?.id).toBe("sb-2026-田上颯人");
    expect(hit?.text).toContain("4:37.20");
    expect(hit?.text).toContain("10:24.08");
    expect(hit?.text).toMatch(/大会結果:\s*https?:\/\//);
    expect(hit?.text).not.toContain("4:58.03");
    expect(hit?.text).not.toMatch(/自己ベストは 10:41\.62/);
  });

  it("returns current SB for 松野凛空, not stale 4:36.05", () => {
    const hit = matchPreparedAnswer("松野凛空の自己ベストは？", { defaultYear: 2026 });
    expect(hit?.id).toBe("sb-2026-松野凛空");
    expect(hit?.text).toContain("4:22.33");
    expect(hit?.text).toContain("9:37.84");
    expect(hit?.text).toContain("http://www.kumariku.org/26/26,7,4long/rel015.html");
    expect(hit?.text).toContain("http://www.kumariku.org/26/26,6,13tsushin/rel196.html");
    expect(hit?.text).not.toContain("4:36.05");
  });

  it("includes meet result link on distance-specific SB answers", () => {
    const hit = matchPreparedAnswer("松野凛空の1500mSBは？", { defaultYear: 2026 });
    expect(hit?.id).toBe("sb-2026-松野凛空-1500m");
    expect(hit?.text).toContain("4:22.33");
    expect(hit?.text).toContain("大会結果: http://www.kumariku.org/26/26,7,4long/rel015.html");
  });

  it(
    "lists いだてん岱明 students instead of who-is-daiming",
    () => {
      for (const q of [
        "いだてん岱明の生徒一覧",
        "いだてん岱明の部員は誰？",
        "岱明中の生徒一覧",
        "岱明の部員名簿は？",
      ]) {
        const hit = matchPreparedAnswer(q, { defaultYear: 2026 });
        expect(hit?.id, q).toBe("roster");
        expect(hit?.text, q).toContain("部員名簿（15名）");
        expect(hit?.text, q).toContain("松野凛空");
        expect(hit?.text, q).toContain("村上咲稀");
        expect(hit?.text, q).toContain("中尾快叶");
        expect(hit?.text, q).not.toContain("玉名市の中学校チーム");
      }
    },
    60_000,
  );

  it(
    "returns school/club roster for 玉名附属・南関・ATRC, not 岱明",
    () => {
      for (const q of ["玉名附属中の生徒一覧", "玉名高校附属中の部員名簿", "玉高附属の選手一覧"]) {
        const hit = matchPreparedAnswer(q, { defaultYear: 2026 });
        expect(hit?.id, q).toBe("roster-aff-玉名附中");
        expect(hit?.text, q).toContain("玉名高校附属中");
        expect(hit?.text, q).toContain("草野瑠唯");
        expect(hit?.text, q).toContain("小倉十和");
        expect(hit?.text, q).not.toContain("いだてん岱明");
        expect(hit?.text, q).not.toContain("村上咲稀");
      }

      const nankan = matchPreparedAnswer("南関中の生徒一覧", { defaultYear: 2026 });
      expect(nankan?.id).toBe("roster-aff-南関中");
      expect(nankan?.text).toContain("南関中");
      expect(nankan?.text).not.toContain("いだてん岱明");

      const atrc = matchPreparedAnswer("ATRCの生徒一覧", { defaultYear: 2026 });
      expect(atrc?.id).toBe("roster-aff-ATRC");
      expect(atrc?.text).toContain("ATRC");
      expect(atrc?.text).toMatch(/今村昇磨|米谷慶吾|猿渡愛梨/);
      expect(atrc?.text).not.toContain("いだてん岱明");
    },
    60_000,
  );

  it("keeps who-is-daiming for team-identity questions", () => {
    const hit = matchPreparedAnswer("いだてん岱明とはどんなチーム？", { defaultYear: 2026 });
    expect(hit?.id).toBe("who-is-daiming");
    expect(hit?.text).toContain("玉名市の中学校チーム");
  });

  it("returns user-friendly 荒玉 calendar answer without repo jargon", () => {
    for (const q of ["荒玉中体連駅伝はいつ？", "荒玉中体連駅伝について教えて"]) {
      const hit = matchPreparedAnswer(q, { defaultYear: 2026 });
      expect(hit?.text, q).toContain("2026-10-14");
      expect(hit?.text, q).toContain("drive.google.com/drive/folders/1G8IlaBp9xVmXUynBAjV9ZZQPfFqzj4Yi");
      expect(hit?.text, q).not.toContain("状態:");
      expect(hit?.text, q).not.toContain("input/idaten-corpus");
      expect(hit?.text, q).not.toContain("coverage.csv");
      expect(hit?.text, q).not.toContain("docs/aragyoku");
    }
  });

  it("returns 2026 玉名郡ナイター 岱明結果 for short yearless and dated asks", () => {
    for (const q of [
      "2026年の玉名郡ナイターの岱明の結果",
      "玉名郡ナイターの岱明の結果",
      "今年の玉名郡ナイターの岱明の結果",
      "2026年玉名郡ナイターの岱明の結果は？",
    ]) {
      const hit = matchPreparedAnswer(q, { defaultYear: 2026 });
      expect(hit?.id, q).toMatch(/nighter-2026-result|meet-result-2026-玉名郡ナイター/);
      expect(hit?.text, q).toMatch(/松野凛空|4:29\.8/);
      expect(hit?.text, q).not.toMatch(/4分48秒1|倉田裕斗　4分48/);
    }
  });

  it("returns 2026 玉名郡ナイター result with Drive links", () => {
    for (const q of ["玉名郡ナイターの結果", "今年の玉名郡ナイターの結果", "玉名郡ナイター中・長距離記録会の結果"]) {
      const hit = matchPreparedAnswer(q, { defaultYear: 2026 });
      expect(hit?.id, q).toBe("nighter-2026-result");
      expect(hit?.text, q).toContain("drive.google.com/drive/folders/1L9RE6ZK_qmehh9sj7bYK7W5A4wKZU82t");
      expect(hit?.text, q).toContain("docs.google.com/document/d/1k4ka2olKO0ZQPgwTYKxOzMlGaHFjWwAzQsx3uanjMf4");
      expect(hit?.text, q).toContain("4:29.8");
      expect(hit?.text, q).not.toContain("2025年度/0830_玉名郡ナイター");
    }
  });

  it("returns junior detail for 南関中 and 玉名附属中, not coach fallback", () => {
    for (const q of [
      "ジュニア駅伝の南関中と玉名附属中の結果の詳細",
      "ジュニア駅伝の南関と玉名附属の結果の詳細",
      "今年のジュニアで玉名附属はどうだった？",
    ]) {
      const hit = matchPreparedAnswer(q, { defaultYear: 2026 });
      expect(hit?.id, q).toBe("junior-2026-nankan-tamafz-detail");
      expect(hit?.text, q).toContain("35:09");
      expect(hit?.text, q).toContain("43:11");
      expect(hit?.text, q).toContain("44:15");
      expect(hit?.text, q).not.toContain("コーチに直接聞いてください");
    }
  });

  it("treats yearless questions as current fiscal year", () => {
    const nagomi = matchPreparedAnswer("なごみ駅伝はいつ？", { defaultYear: 2026 });
    expect(nagomi?.id).toMatch(/cal-2026-.*なごみ|20260920/);
    expect(nagomi?.text).toContain("2026");
    expect(nagomi?.text).not.toContain("2025-09-21");

    const pdf = matchPreparedAnswer("ジュニア駅伝の結果PDF", { defaultYear: 2026 });
    expect(pdf?.id).toBe("junior-2026-pdf");
    expect(pdf?.text).toContain("2026");

    const tsushin = matchPreparedAnswer("通信陸上はいつ？", { defaultYear: 2026 });
    expect(tsushin?.id).toMatch(/cal-2026-/);
    expect(tsushin?.text).toContain("2026");
  });

  it("returns all season races with meet links for 南本幸治郎", () => {
    for (const q of [
      "南本幸治郎の今年度の全ての記録",
      "南本幸治郎の全ての記録",
      "南本幸治郎の全記録は？",
    ]) {
      const hit = matchPreparedAnswer(q, { defaultYear: 2026 });
      expect(hit?.id, q).toBe("records-athlete-2026-南本幸治郎");
      expect(hit?.text, q).toMatch(/全7件/);
      expect(hit?.text, q).toContain("5:23.50");
      expect(hit?.text, q).toContain("5:43.60");
      expect(hit?.text, q).toContain("なごみ駅伝");
      expect(hit?.text, q).toContain("玉名郡ナイター");
      expect(hit?.text, q).toContain("5:24.8");
      expect(hit?.text, q).toMatch(/大会結果:\s*https?:\/\//);
      expect(hit?.text, q).toContain("http://www.kumariku.org/26/26,7,18chutairen/rel075.html");
      // 距離別SB定型へ誤吸しない
      expect(hit?.id, q).not.toMatch(/^sb-/);
    }
  });

  it("includes ekiden/road meets in 村上咲稀 all-season records", () => {
    const hit = matchPreparedAnswer("村上咲稀の今年度の全ての記録", { defaultYear: 2026 });
    expect(hit?.id).toBe("records-athlete-2026-村上咲稀");
    expect(hit?.text).toMatch(/駅伝/);
    expect(hit?.text).toContain("なごみ駅伝");
    expect(hit?.text).toContain("県ジュニア駅伝");
    expect(hit?.text).toContain("7:07");
    expect(hit?.text).toContain("9:58");
    expect(hit?.text).toContain("2:20.11");
    expect(hit?.text).toContain("4:53.85");
    expect(hit?.text).not.toContain("トラックCSVに加え");
    expect(hit?.text).not.toContain("トラックに加え駅伝・ロード等も含みます");
  });

  it("includes 玉名郡ナイター in all-records when the athlete raced there", () => {
    const matsuno = matchPreparedAnswer("松野凛空の全ての記録", { defaultYear: 2026 });
    expect(matsuno?.id).toBe("records-athlete-2026-松野凛空");
    expect(matsuno?.text).toContain("玉名郡ナイター");
    expect(matsuno?.text).toContain("4:29.8");
    expect(matsuno?.text).toContain(
      "drive.google.com/drive/folders/1L9RE6ZK_qmehh9sj7bYK7W5A4wKZU82t",
    );

    const tanoue = matchPreparedAnswer("田上颯人の今年度の全ての記録", { defaultYear: 2026 });
    expect(tanoue?.id).toBe("records-athlete-2026-田上颯人");
    expect(tanoue?.text).toContain("玉名郡ナイター");
    expect(tanoue?.text).toContain("4:33.6");

    const past = matchPreparedAnswer("松野凛空の過去3年の全ての記録", { defaultYear: 2026 });
    expect(past?.id).toBe("records-athlete-3y-松野凛空");
    expect(past?.text).toContain("玉名郡ナイター");
    expect(past?.text).toMatch(/4:47\.9|4:29\.8/);
  });

  it("covers gap-crush-1000 samples that previously missed", () => {
    const tensui = matchPreparedAnswer("荒玉女子の天水の順位は？", { defaultYear: 2026 });
    expect(tensui?.id).toMatch(/gap1000-aragyoku-yearless-女子-天水-rank|aragyoku-.*天水/);
    expect(tensui?.text).toMatch(/位/);

    const career = matchPreparedAnswer("三滝拓海の荒玉出走歴は？", { defaultYear: 2026 });
    expect(career?.id, career?.text?.slice(0, 80)).toMatch(/aragyoku-career-三滝拓海|gap1000/);
  });

  it("returns past-3-year all records for aragyoku athletes", () => {
    const hit = matchPreparedAnswer("松野凛空の過去3年の全ての記録", { defaultYear: 2026 });
    expect(hit?.id).toBe("records-athlete-3y-松野凛空");
    expect(hit?.text).toMatch(/2024|2025|2026/);
    expect(hit?.text).toMatch(/大会結果:\s*https?:\/\//);
  });

  it("returns meet-specific race result with link", () => {
    const hit = matchPreparedAnswer("南本幸治郎の通信陸上の記録は？", { defaultYear: 2026 });
    expect(hit?.id).toBe("race-2026-南本幸治郎-通信陸上");
    expect(hit?.text).toContain("5:44.50");
    expect(hit?.text).toContain("http://www.kumariku.org/26/26,6,13tsushin/rel178.html");
  });

  it("returns aragyoku team order for 岱明 2025 men", () => {
    const hit = matchPreparedAnswer("2025年荒玉駅伝男子の岱明のオーダーは？", { defaultYear: 2026 });
    expect(hit?.id).toBe("aragyoku-2025-男子-team-岱明-order");
    expect(hit?.text).toContain("松野凛空");
    expect(hit?.text).toContain("6位");
  });

  it("returns 2026 岱明暫定オーダー with named legs, not hollow links", () => {
    const hit = matchPreparedAnswer("岱明の2026荒玉暫定オーダーは？", { defaultYear: 2026 });
    expect(hit?.id).toBe("meet-2026-aragyoku-daiming-order");
    expect(hit?.text).toContain("村上咲稀");
    expect(hit?.text).toContain("松野凛空");
    expect(hit?.text).toContain("山本哲瑠");
    expect(hit?.text).not.toContain("「」");
  });

  it("answers 岱明女子800m平均 with school ranking facts", () => {
    const hit = matchPreparedAnswer("岱明女子800mの平均は？", { defaultYear: 2026 });
    expect(hit?.id).toBe("sb-women800-daiming");
    expect(hit?.text).toContain("2:28.81");
    expect(hit?.text).toContain("岱明");
  });

  it("returns aragyoku career history", () => {
    const hit = matchPreparedAnswer("松野凛空の荒玉出走歴は？", { defaultYear: 2026 });
    expect(hit?.id).toBe("aragyoku-career-松野凛空");
    expect(hit?.text).toContain("2025年男子・岱明2区");
  });

  it("returns last-year split rank for 岱明 men leg2", () => {
    for (const q of [
      "昨年の荒玉男子岱明2区の区間順位は？",
      "2025年荒玉男子の岱明2区の区間順位は？",
    ]) {
      const hit = matchPreparedAnswer(q, { defaultYear: 2026 });
      expect(hit?.id, q).toBe("aragyoku-2025-男子-岱明-leg2-splitrank");
      expect(hit?.text, q).toContain("松野凛空");
      expect(hit?.text, q).toContain("区間6位");
    }
  });

  it(
    "maps 去年の岱明女子の結果 to 2025 facts, not 2024",
    () => {
      for (const q of [
        "去年の岱明の女子の結果は？",
        "昨年の岱明女子の結果は？",
        "去年の荒玉駅伝の岱明の女子の結果は？",
        "2025年の岱明の女子の結果は？",
      ]) {
        const hit = matchPreparedAnswer(q, { defaultYear: 2026 });
        expect(hit, q).toBeTruthy();
        expect(hit?.text, q).toContain("2025年荒玉駅伝女子");
        expect(hit?.text, q).toContain("7位");
        expect(hit?.text, q).toContain("45:22");
        expect(hit?.text, q).toContain("村上咲稀");
        expect(hit?.text, q).toContain("増岡里俐");
        expect(hit?.text, q).not.toContain("角田里奈");
        expect(hit?.text, q).not.toContain("瀧下那奈");
        expect(hit?.text, q).not.toContain("45:06");
      }

      const y2024 = matchPreparedAnswer("2024年の岱明の女子の結果は？", {
        defaultYear: 2026,
      });
      expect(y2024?.text).toContain("2024年荒玉駅伝女子");
      expect(y2024?.text).toContain("6位");
      expect(y2024?.text).toContain("45:06");
      expect(y2024?.text).toContain("角田里奈");
    },
    60_000,
  );

  it(
    "maps 去年/昨年 men leg2 board to 2025, not 2024",
    () => {
      for (const q of [
        "去年の男子2区の荒玉駅伝の区間順位",
        "去年の荒玉駅伝男子2区の区間順位",
        "昨年の男子2区の荒玉駅伝の区間順位",
        "2025年男子2区の荒玉駅伝の区間順位",
      ]) {
        const hit = matchPreparedAnswer(q, { defaultYear: 2026 });
        expect(hit?.id, q).toBe("aragyoku-2025-男子-leg2-board");
        expect(hit?.text, q).toContain("2025年");
        expect(hit?.text, q).toContain("山本悠斗");
        expect(hit?.text, q).toContain("8:37");
        expect(hit?.text, q).not.toContain("荒木琉琉");
        expect(hit?.text, q).not.toContain("2024年荒玉駅伝男子2区");
        expect(hit?.id, q).not.toBe("aragyoku-2024-男子-leg2-board");
      }

      const y2024 = matchPreparedAnswer("2024年男子2区の荒玉駅伝の区間順位", {
        defaultYear: 2026,
      });
      expect(y2024?.id).toBe("aragyoku-2024-男子-leg2-board");
      expect(y2024?.text).toContain("荒木琉琉");
    },
    60_000,
  );

  it("answers course-point start questions from the common-points diagram", () => {
    const hit = matchPreparedAnswer("荒玉駅伝の女子4区は何地点から？", { defaultYear: 2026 });
    expect(hit?.id).toBe("course-leg-女子4-start");
    expect(hit?.text).toContain("A地点");
    expect(hit?.text).toContain("drive.google.com");

    const men1 = matchPreparedAnswer("男子1区は何地点から？", { defaultYear: 2026 });
    expect(men1?.id).toBe("course-leg-男子1-start");
    expect(men1?.text).toContain("145m");

    const relay = matchPreparedAnswer("女子4→5区の中継所は？", { defaultYear: 2026 });
    expect(relay?.id).toBe("course-leg-女子4-relay");
    expect(relay?.text).toContain("C地点");
  });

  it(
    "answers 荒玉 top-2 → 県駅伝出場 questions",
    () => {
      for (const q of [
        "荒玉駅伝は何位までが県駅伝に出場できる？",
        "荒玉駅伝で何位まで県駅伝に出られる？",
        "荒玉は2位まで県駅伝？",
        "荒玉駅伝の県駅伝出場条件は？",
        "県駅伝に出るには荒玉で何位必要？",
      ]) {
        const hit = matchPreparedAnswer(q, { defaultYear: 2026 });
        expect(hit?.id, q).toMatch(/^aragyoku-pref-top2-/);
        expect(hit?.text, q).toContain("男女上位2校");
        expect(hit?.text, q).toMatch(/県駅伝/);
      }

      const not3 = matchPreparedAnswer("荒玉駅伝で3位でも県駅伝に出られる？", {
        defaultYear: 2026,
      });
      expect(not3?.id).toBe("aragyoku-pref-top2-not-3rd");
      expect(not3?.text).toContain("3位");
      expect(not3?.text).toContain("2位まで");
    },
    60_000,
  );

  it("answers 岱明 rival-school questions from analysis", () => {
    const hit = matchPreparedAnswer("荒玉駅伝で岱明中とライバルになりそうな学校は？", {
      defaultYear: 2026,
    });
    expect(hit?.id).toBe("daiming-rivals-core");
    expect(hit?.text).toContain("荒尾三");
    expect(hit?.text).toContain("南関");
    expect(hit?.text).toContain("長洲");

    const men = matchPreparedAnswer("岱明男子のライバル校は？", { defaultYear: 2026 });
    expect(men?.id).toBe("daiming-rivals-men");
    expect(men?.text).toContain("南関");

    const women = matchPreparedAnswer("岱明女子のライバル校は？", { defaultYear: 2026 });
    expect(women?.id).toBe("daiming-rivals-women");
    expect(women?.text).toContain("長洲");
  });

  it("returns 徹底対策 guide overview", () => {
    const hit = matchPreparedAnswer("荒玉の完全ガイドは？", { defaultYear: 2026 });
    expect(hit?.id).toBe("guide-2026-what");
    expect(hit?.text).toContain("徹底対策");
    expect(hit?.text).toContain("117");
  });

  it(
    "answers aragyoku rank-to-rank time gaps, not runner-up school",
    () => {
      for (const q of [
        "去年の荒玉駅伝の男子の2位と3位の差は？",
        "2025年荒玉男子の2位と3位の差",
        "2025年荒玉駅伝男子の準優勝と3位の差は？",
      ]) {
        const hit = matchPreparedAnswer(q, { defaultYear: 2026 });
        expect(hit?.id, q).toBe("aragyoku-rankgap-2025-男子-2-3");
        expect(hit?.text, q).toContain("35秒");
        expect(hit?.text, q).toContain("玉陵");
        expect(hit?.text, q).toContain("玉高附属");
        expect(hit?.text, q).toContain("58:02");
        expect(hit?.text, q).toContain("58:37");
        expect(hit?.id, q).not.toBe("aragyoku-2025-男子-runnerup");
      }

      const winGap = matchPreparedAnswer("2025年荒玉駅伝男子の優勝と準優勝の差は？", {
        defaultYear: 2026,
      });
      expect(winGap?.id).toBe("aragyoku-rankgap-2025-男子-1-2");
      expect(winGap?.text).toContain("1分45秒");
      expect(winGap?.text).toContain("菊水");

      const women = matchPreparedAnswer("去年の荒玉女子の1位と2位のタイム差", {
        defaultYear: 2026,
      });
      expect(women?.id).toBe("aragyoku-rankgap-2025-女子-1-2");
      expect(women?.text).toContain("1分47秒");
      expect(women?.text).not.toMatch(/^2025年荒玉駅伝女子の優勝は/);
    },
    60_000,
  );

  it("returns 2026 course trial results", () => {
    const hit = matchPreparedAnswer("岱明の荒玉試走タイムは？", { defaultYear: 2026 });
    expect(hit?.id).toBe("trial-2026-daiming-aragyoku");
    expect(hit?.text).toContain("松野凛空");
    expect(hit?.text).toContain("9:48");
  });

  it("returns なごみ team result for 荒尾第四 / 荒尾四", () => {
    for (const q of ["荒尾第四のなごみ駅伝の結果は？", "荒尾四のなごみ駅伝の結果は？"]) {
      const hit = matchPreparedAnswer(q, { defaultYear: 2026 });
      expect(hit?.id, q).toBe("nagomi-team-2026-荒尾第四");
      expect(hit?.text, q).toContain("37:25");
      expect(hit?.text, q).toContain("藤井祐吏");
      expect(hit?.text, q).toContain("drive.google.com/drive/folders/1k-zW0irJ-OjDjqQwUQLZIs4C6PfuR211");
      expect(hit?.text, q).not.toContain("コーチに直接聞いてください");
    }
  });

  it("returns なごみ荒玉地区の結果 with document body and Drive link", () => {
    for (const q of [
      "なごみ駅伝の荒玉地区の結果",
      "なごみの荒玉地区の結果は？",
      "荒玉地区のなごみ結果",
    ]) {
      const hit = matchPreparedAnswer(q, { defaultYear: 2026 });
      expect(hit?.id, q).toBe("nagomi-2026-aragyoku-area-result");
      expect(hit?.text, q).toContain(
        "docs.google.com/document/d/1TujEJG7vAeyQCWqZ5735CIHu69H0e3zyPkFgytpHgJ0",
      );
      expect(hit?.text, q).toContain("drive.google.com/drive/folders/1k-zW0irJ-OjDjqQwUQLZIs4C6PfuR211");
      expect(hit?.text, q).toContain("ATRC");
      expect(hit?.text, q).toContain("岱明A");
      expect(hit?.text, q).toContain("30:18");
      expect(hit?.text, q).toContain("42:39");
      expect(hit?.id, q).not.toBe("nagomi-what");
    }
  });

  it("covers gap-crush batch B samples (top2 / meet record / formula)", () => {
    const top2 = matchPreparedAnswer("玉名は荒玉で2位以内何回？", { defaultYear: 2026 });
    expect(top2?.id).toBe("gap1000b-top2-玉名");
    expect(top2?.text).toContain("15回");

    const meet = matchPreparedAnswer("2012荒玉女子ボードの大会記録", { defaultYear: 2026 });
    expect(meet?.id).toBe("gap1000b-meetrec-2012-女子");
    expect(meet?.text).toContain("40:58");

    const formula = matchPreparedAnswer("荒玉男子玉名中の5区予想タイムは？", { defaultYear: 2026 });
    expect(formula?.id).toBe("gap1000b-formula-男子-玉名中-leg5");
    expect(formula?.text).toContain("10:10");
  });

  it(
    "answers yearless 荒玉男女の区間歴代記録（ボード上部一覧）",
    () => {
      const men = matchPreparedAnswer("荒玉駅伝の男子の区間歴代記録は？", {
        defaultYear: 2026,
      });
      expect(men?.id).toBe("aragyoku-leg-records-男子-current");
      expect(men?.text).toContain("米村和真");
      expect(men?.text).toContain("9:01");
      expect(men?.text).toContain("56:38");
      expect(men?.text).toContain("2024");

      const women = matchPreparedAnswer("荒玉駅伝の女子の区間歴代記録は？", {
        defaultYear: 2026,
      });
      expect(women?.id).toBe("aragyoku-leg-records-女子-current");
      expect(women?.text).toContain("西川侑里");
      expect(women?.text).toContain("井上智世");
      expect(women?.text).toContain("40:58");

      const both = matchPreparedAnswer("荒玉駅伝の区間歴代記録は？", {
        defaultYear: 2026,
      });
      expect(both?.id).toBe("aragyoku-leg-records-both-current");
      expect(both?.text).toContain("男子");
      expect(both?.text).toContain("女子");

      const oldMen = matchPreparedAnswer("荒玉男子の旧コース区間記録は？", {
        defaultYear: 2026,
      });
      expect(oldMen?.id).toBe("aragyoku-leg-records-男子-pre2024");
      expect(oldMen?.text).toContain("田上建");
      expect(oldMen?.text).toContain("62:49");
    },
    60_000,
  );

  it(
    "answers leg-time → split-rank estimates for men and women",
    () => {
      const men = matchPreparedAnswer(
        "荒玉駅伝男子の1区を9:30で走ると区間何位くらいになる？",
        { defaultYear: 2026 },
      );
      expect(men?.id).toBe("aragyoku-leg-time-rank-男子-leg1-9-30");
      expect(men?.text).toContain("2025年なら区間5位相当");
      expect(men?.text).toContain("松浦眞大");
      expect(men?.text).toContain("2024年なら区間9位相当");

      const nearby = matchPreparedAnswer("荒玉男子1区を9:32で走ったら区間何位？", {
        defaultYear: 2026,
      });
      expect(nearby?.id).toBe("aragyoku-leg-time-rank-男子-leg1-9-32");
      expect(nearby?.text).toContain("倉田裕斗");

      const women = matchPreparedAnswer(
        "荒玉駅伝の女子2区を6:40で走ると区間何位くらいになる？",
        { defaultYear: 2026 },
      );
      expect(women?.id).toBe("aragyoku-leg-time-rank-女子-leg2-6-40");
      expect(women?.text).toMatch(/2025年なら区間1位級|2024年なら区間/);
    },
    60_000,
  );

  it("returns null for unrelated chatter without prepared entry", () => {
    // deliberately odd; if someday prepared, this assertion should be updated
    const hit = matchPreparedAnswer("宇宙の果てはどこ？", { defaultYear: 2026 });
    expect(hit).toBeNull();
  });
});

describe("answerQuestion prepared path", () => {
  it("short-circuits without LLM for prepared FAQ", async () => {
    let llmCalled = false;
    const result = await answerQuestion("2025年荒玉駅伝の岱明男子は何位？", {
      defaultYear: 2026,
      llm: {
        complete: async () => {
          llmCalled = true;
          return "should not run";
        },
      },
      retrieve: () => {
        throw new Error("retrieve should not run");
      },
    });
    expect(llmCalled).toBe(false);
    expect(result.kind).toBe("answered");
    if (result.kind === "answered") {
      expect(result.sources[0]).toBe("prepared:aragyoku-2025-daiming-men");
      expect(result.text).toContain("6位");
      expect(result.text).toContain("59:08");
      expect(result.text).not.toContain("コーチに直接聞いてください");
    }
  });

  it("returns junior result prepared answer instead of coach fallback", async () => {
    const result = await answerQuestion("ジュニア駅伝の結果は？", {
      defaultYear: 2026,
      llm: null,
      retrieve: () => [],
    });
    expect(result.kind).toBe("answered");
    expect(result.text).toMatch(/ジュニア|36:52|44:23|Drive|drive\.google/);
    expect(result.text).not.toContain("コーチに直接聞いてください");
    expect(result.sources?.[0]).toMatch(/^prepared:/);
  });

  it("keeps dynamic course-video canned ahead of prepared", async () => {
    const result = await answerQuestion("荒玉駅伝のコース動画は？", {
      defaultYear: 2026,
      llm: null,
    });
    expect(result.kind).toBe("answered");
    if (result.kind === "answered") {
      expect(result.sources[0]).toBe("canned:aragyoku-course-videos");
    }
  });
});
