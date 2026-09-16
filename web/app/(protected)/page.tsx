"use client";

import { useMemo, useState } from "react";

import { CourseVideoPlayer } from "../CourseVideoPlayer";

type Division = "女子" | "男子";
type CourseVideo = { division: Division; leg: number; distance: string; file: string; route: string; note: string };

const videos: CourseVideo[] = [
  { division: "女子", leg: 1, distance: "3.000km", file: "/videos/women-leg1.mp4", route: "D → B", note: "スタート・中継地点と500mごとの確認停止" },
  { division: "女子", leg: 2, distance: "1.855km", file: "/videos/women-leg2.mp4", route: "B → D", note: "500mごとの確認停止" },
  { division: "女子", leg: 3, distance: "2.000km", file: "/videos/women-leg3.mp4", route: "D → A", note: "500mごとの確認停止" },
  { division: "女子", leg: 4, distance: "2.000km", file: "/videos/women-leg4.mp4", route: "A → C", note: "曲がり角と500mごとの確認停止" },
  { division: "女子", leg: 5, distance: "3.000km", file: "/videos/women-leg5.mp4", route: "C → ゴール", note: "曲がり角と500mごとの確認停止" },
  { division: "男子", leg: 1, distance: "3.000km", file: "/videos/men-leg1.mp4", route: "C → A", note: "500mごとの確認停止" },
  { division: "男子", leg: 2, distance: "2.855km", file: "/videos/men-leg2.mp4", route: "A → D", note: "実測GPX・500mごとの確認停止" },
  { division: "男子", leg: 3, distance: "3.000km", file: "/videos/men-leg3.mp4", route: "D → B", note: "500mごとの確認停止" },
  { division: "男子", leg: 4, distance: "3.000km", file: "/videos/men-leg4.mp4", route: "B → E", note: "曲がり角と500mごとの確認停止" },
  { division: "男子", leg: 5, distance: "2.855km", file: "/videos/men-leg5.mp4", route: "E → C", note: "500mごとの確認停止" },
  { division: "男子", leg: 6, distance: "3.000km", file: "/videos/men-leg6.mp4", route: "C → ゴール", note: "曲がり角と500mごとの確認停止" },
];

export default function Home() {
  const [division, setDivision] = useState<"すべて" | Division>("すべて");
  const filteredVideos = useMemo(() => division === "すべて" ? videos : videos.filter((video) => video.division === division), [division]);

  return (
    <main className="site-shell">
      <section className="hero">
        <div className="eyebrow">ARATAMA EKIDEN 2026 / COURSE PLAYER</div>
        <h1>荒玉駅伝<br /><span>コース動画ライブラリ</span></h1>
        <p className="hero-copy">衛星写真の上で、各区の走行ラインと地点を確認できます。500mポイントと曲がり角では3秒静止するので、次の動きを見失わずにコースを追えます。</p>
        <div className="hero-stats"><span><strong>11</strong>区間動画</span><span><strong>3秒</strong>確認停止</span><span><strong>1km30秒</strong>再生ペース</span></div>
      </section>

      <section className="library" aria-labelledby="library-title">
        <div className="section-heading"><div><div className="eyebrow">COURSE BY LEG</div><h2 id="library-title">区間を選んで再生</h2></div>
          <div className="filters" role="group" aria-label="部門で絞り込み">
            {(["すべて", "女子", "男子"] as const).map((item) => <button className={division === item ? "filter active" : "filter"} key={item} onClick={() => setDivision(item)} type="button">{item}</button>)}
          </div>
        </div>
        <div className="video-grid">
          {filteredVideos.map((video) => <article className="video-card" key={`${video.division}-${video.leg}`}>
            <div className="video-frame"><CourseVideoPlayer src={video.file} /><span className={`division-badge ${video.division === "女子" ? "women" : "men"}`}>{video.division}</span></div>
            <div className="card-body"><div className="card-kicker">{video.division} {video.leg}区</div><h3>{video.distance}<span>{video.route}</span></h3><p>{video.note}</p></div>
          </article>)}
        </div>
      </section>

      <section className="method" aria-labelledby="method-title"><div><div className="eyebrow">HOW TO READ</div><h2 id="method-title">動画の見方</h2></div>
        <div className="method-grid"><div><span className="method-number">01</span><strong>青・黄のライン</strong><p>青はこれから走る区間、黄は通過済みの区間です。</p></div><div><span className="method-number">02</span><strong>地点 A〜E</strong><p>簡易地図の地点記号を、実際のGPS区間の始終点へ対応付けています。</p></div><div><span className="method-number">03</span><strong>静止表示</strong><p>500mポイントと大きな曲がり角で3秒止まり、距離と確認対象を表示します。</p></div></div>
      </section>
      <footer>荒玉駅伝2026 · GPSコース動画 · 衛星写真: Esri, Maxar, Earthstar Geographics, GIS User Community</footer>
    </main>
  );
}
