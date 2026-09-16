"use client";

import { useCallback, useRef } from "react";

type Props = {
  src: string;
  className?: string;
};

function enterFullscreen(video: HTMLVideoElement) {
  if (video.requestFullscreen) {
    void video.requestFullscreen().catch(() => {});
    return;
  }
  const legacy = video as HTMLVideoElement & {
    webkitEnterFullscreen?: () => void;
    webkitRequestFullscreen?: () => void;
  };
  if (legacy.webkitEnterFullscreen) {
    legacy.webkitEnterFullscreen();
    return;
  }
  if (legacy.webkitRequestFullscreen) {
    void legacy.webkitRequestFullscreen();
  }
}

export function CourseVideoPlayer({ src, className }: Props) {
  const videoRef = useRef<HTMLVideoElement>(null);

  const handlePlay = useCallback(() => {
    const video = videoRef.current;
    if (!video) return;
    if (document.fullscreenElement === video) return;
    enterFullscreen(video);
  }, []);

  return (
    <video
      ref={videoRef}
      className={className}
      controls
      onPlay={handlePlay}
      playsInline
      preload="metadata"
      src={src}
    />
  );
}
