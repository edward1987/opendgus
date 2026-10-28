// Small inline stroke icons (no icon-font dependency).
import type { SVGProps } from "react";

const P: Record<string, string> = {
  undo: "M9 14 4 9l5-5M4 9h10.5a5.5 5.5 0 0 1 0 11H11",
  redo: "m15 14 5-5-5-5M20 9H9.5a5.5 5.5 0 0 0 0 11H13",
  plus: "M12 5v14M5 12h14",
  trash: "M4 7h16M10 11v6M14 11v6M5 7l1 12a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2l1-12M9 7V4h6v3",
  copy: "M8 8h11v11H8zM5 16V5h11",
  eye: "M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12zM12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6z",
  eyeOff: "M3 3l18 18M10.6 10.6a2 2 0 0 0 2.8 2.8M9.9 5.2A10 10 0 0 1 12 5c6.5 0 10 7 10 7a17 17 0 0 1-3.2 4M6.6 6.6C3.9 8.4 2 12 2 12s3.5 7 10 7a9.7 9.7 0 0 0 5.4-1.6",
  up: "m6 15 6-6 6 6",
  down: "m6 9 6 6 6-6",
  check: "m5 12 5 5 9-10",
  build: "M14 6l4 4M3 21l9-9M15 3l6 6-9 9-6-6z",
  upload: "M12 16V4M7 9l5-5 5 5M4 17v3h16v-3",
  fit: "M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5",
  globe: "M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM3 12h18M12 3c2.5 2.5 3.8 5.5 3.8 9S14.5 18.5 12 21c-2.5-2.5-3.8-5.5-3.8-9S9.5 5.5 12 3z",
  palette: "M12 3a9 9 0 0 0 0 18c1.1 0 2-.9 2-2 0-.5-.2-1-.5-1.3-.3-.4-.5-.8-.5-1.3 0-1.1.9-2 2-2h2.4A4.6 4.6 0 0 0 21 9.8C21 6 17 3 12 3zM7.5 12.5h.01M9.5 7.5h.01M14.5 7.5h.01",
  folder: "M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z",
  file: "M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9zM14 3v6h6",
  close: "M6 6l12 12M18 6 6 18",
  layers: "m12 3 9 5-9 5-9-5zM3 13l9 5 9-5",
  pages: "M7 3h10v18H7zM4 6v12M20 6v12",
  sliders: "M4 6h10M18 6h2M4 12h4M12 12h8M4 18h12M20 18h0M14 4v4M8 10v4M16 16v4",
  shapes: "M4 4h7v7H4zM17.5 4a3.5 3.5 0 1 1 0 7 3.5 3.5 0 0 1 0-7zM4 20l3.5-6 3.5 6zM14 14h6v6h-6z",
  variable: "M8 4c-2 3-2 13 0 16M16 4c2 3 2 13 0 16M10 9l4 6M14 9l-4 6",
  sparkles: "M12 3l1.8 4.7L18.5 9.5l-4.7 1.8L12 16l-1.8-4.7L5.5 9.5l4.7-1.8zM19 15l.8 2.2 2.2.8-2.2.8L19 21l-.8-2.2L16 18l2.2-.8z",
  search: "M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14zM20 20l-4-4",
  rect: "M4 6h16v12H4z",
  ellipse: "M12 5c4.4 0 8 3.1 8 7s-3.6 7-8 7-8-3.1-8-7 3.6-7 8-7z",
  line: "M5 19 19 5",
  text: "M5 6V4h14v2M12 4v16M9 20h6",
  image: "M4 5h16v14H4zM4 16l5-5 4 4 3-3 4 4M15.5 8.5h.01",
  star: "m12 3 2.8 5.6 6.2.9-4.5 4.4 1 6.1-5.5-2.9L6.5 20l1-6.1L3 9.5l6.2-.9z",
  button: "M3 8h18v8H3zM8 12h8",
  toggle: "M7 7h10a5 5 0 0 1 0 10H7A5 5 0 0 1 7 7zM16 9.5a2.5 2.5 0 1 0 0 5 2.5 2.5 0 0 0 0-5z",
  number: "M4 9h16M4 15h16M10 3 8 21M16 3l-2 18",
  progress: "M3 10h18v4H3zM3 12h10",
  indicator: "M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8zM12 3v2M12 19v2M3 12h2M19 12h2",
  slider: "M3 12h18M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8z",
  chip: "M7 7h10v10H7zM9 3v4M15 3v4M9 17v4M15 17v4M3 9h4M3 15h4M17 9h4M17 15h4",
  warning: "M12 4 2.5 20h19zM12 10v4M12 17h.01",
  error: "M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM9 9l6 6M15 9l-6 6",
  plug: "M9 3v5M15 3v5M6 8h12v3a6 6 0 0 1-12 0zM12 17v4",
  refresh: "M20 11a8 8 0 0 0-14.9-3.9L4 9M4 4v5h5M4 13a8 8 0 0 0 14.9 3.9L20 15M20 20v-5h-5",
  alignLeft: "M4 3v18M8 7h10v4H8zM8 14h6v4H8z",
  alignCenterX: "M12 3v18M6 7h12v4H6zM9 14h6v4H9z",
  alignRight: "M20 3v18M6 7h10v4H6zM10 14h6v4h-6z",
  alignTop: "M3 4h18M7 8h4v10H7zM14 8h4v6h-4z",
  alignCenterY: "M3 12h18M7 6h4v12H7zM14 9h4v6h-4z",
  alignBottom: "M3 20h18M7 6h4v10H7zM14 10h4v6h-4z",
  distX: "M4 3v18M20 3v18M10 8h4v8h-4z",
  distY: "M3 4h18M3 20h18M8 10h8v4H8z",
  more: "M5 12h.01M12 12h.01M19 12h.01",
  edit: "M4 20h4L19 9l-4-4L4 16zM14 6l4 4",
  display: "M3 5h18v12H3zM8 21h8M12 17v4",
  logo: "M4 6a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2zM9 21h6M8 13l3-3 2 2 3-3",
  arrowRight: "M5 12h14M13 6l6 6-6 6",
  arrowLeft: "M19 12H5M11 6l-6 6 6 6",
  play: "M7 4.5v15l12-7.5z",
  stop: "M6 6h12v12H6z",
  send: "M4 12 20 4l-4 16-4-6zM12 14l8-10",
  gear: "M12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6zM19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z",
  key: "M15 3a6 6 0 1 1-5.7 7.9L3 17.2V21h3.8l1-1v-2h2v-2h2l1.3-1.3A6 6 0 0 1 15 3zM16.5 7.5h.01",
  lock: "M6 11h12v10H6zM8 11V7a4 4 0 0 1 8 0v4",
  info: "M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM12 11v6M12 7.5h.01",
  brain: "M9 4a3 3 0 0 0-3 3 3 3 0 0 0-2 5 3 3 0 0 0 2 5 3 3 0 0 0 6 1V5a3 3 0 0 0-3-1zM15 4a3 3 0 0 1 3 3 3 3 0 0 1 2 5 3 3 0 0 1-2 5 3 3 0 0 1-6 1",
  newChat: "M4 5h16v11H9l-5 4zM12 8v5M9.5 10.5h5",
};

export type IconName = keyof typeof P;

export function Icon({ name, size = 16, ...rest }: { name: IconName | string; size?: number } & SVGProps<SVGSVGElement>) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8}
      strokeLinecap="round" strokeLinejoin="round" aria-hidden {...rest}>
      <path d={P[name] ?? P.star} />
    </svg>
  );
}

export const WIDGET_ICON: Record<string, IconName> = {
  button: "button", toggle: "toggle", number: "number", progress: "progress", indicator: "indicator", slider: "slider",
  rect: "rect", ellipse: "ellipse", line: "line", text: "text", icon: "star", image: "image",
};
