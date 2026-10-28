// Center canvas: the exact device render (from the backend) as background, with transparent Konva hit-boxes on top
// for selecting, dragging (with grid/edge snapping and guides) and resizing items.
import type Konva from "konva";
import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { Group, Image as KImage, Layer, Line, Rect, Stage, Transformer } from "react-konva";
import { useTranslation } from "react-i18next";
import { allItems, bbox, Item, moveBy, updateItems, withBox } from "../lib/project";
import { anchorEdges, Guide, snapMove, snapResize } from "../lib/snap";
import type { Box } from "../lib/types";
import { currentPage, useStore } from "../store";
import { Icon } from "./Icons";

const GRID = 8;
const PAD = 40;
const ACCENT = "#38bdf8";
const GUIDE = "#f472b6";

interface DragState {
  ids: string[];
  start: Record<string, Box>;
  anchorId: string;
}

export function CanvasView() {
  const { t } = useTranslation();
  const wrapRef = useRef<HTMLDivElement>(null);
  const stageRef = useRef<Konva.Stage>(null);
  const trRef = useRef<Konva.Transformer>(null);
  const [size, setSize] = useState({ w: 800, h: 600 });
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [guides, setGuides] = useState<Guide[]>([]);
  const [hover, setHover] = useState<string | null>(null);
  const [drag, setDrag] = useState<DragState | null>(null);
  const [marquee, setMarquee] = useState<Box | null>(null);
  // after a move, keep showing the moved pixels until the backend re-rendered the page
  const [ghost, setGhost] = useState<(DragState & { url: string }) | null>(null);
  const [snapOn, setSnapOn] = useState(true);
  const marqueeStart = useRef<{ x: number; y: number; additive: boolean } | null>(null);
  const panStart = useRef<{ x: number; y: number; px: number; py: number } | null>(null);

  const project = useStore((s) => s.project)!;
  const page = useStore(currentPage);
  const preview = useStore((s) => s.preview);
  const selection = useStore((s) => s.selection);
  const zoom = useStore((s) => s.zoom);
  const st = useStore.getState;

  const W = project.display.width;
  const H = project.display.height;

  useLayoutEffect(() => {
    const el = wrapRef.current!;
    const ro = new ResizeObserver(() => setSize({ w: el.clientWidth, h: el.clientHeight }));
    ro.observe(el);
    setSize({ w: el.clientWidth, h: el.clientHeight });
    return () => ro.disconnect();
  }, []);

  const fit = Math.max(0.05, Math.min((size.w - 2 * PAD) / W, (size.h - 2 * PAD) / H));
  const scale = zoom ?? fit;
  useEffect(() => setPan({ x: 0, y: 0 }), [zoom === null, W, H]);
  const ox = Math.round((size.w - W * scale) / 2 + (zoom === null ? 0 : pan.x));
  const oy = Math.round((size.h - H * scale) / 2 + (zoom === null ? 0 : pan.y));

  // keep the store informed of the view centre (new items are placed there)
  useEffect(() => {
    const cx = Math.min(W, Math.max(0, (size.w / 2 - ox) / scale));
    const cy = Math.min(H, Math.max(0, (size.h / 2 - oy) / scale));
    st().setViewCenter({ x: Math.round(cx), y: Math.round(cy) });
  }, [ox, oy, scale, size.w, size.h, W, H]);

  const items = useMemo(() => (page ? allItems(page).filter((i) => i.visible !== false) : []), [page]);
  const selSet = useMemo(() => new Set(selection), [selection]);
  const previewOk = preview && page && preview.pageId === page.id;

  // smoke screenshot / first paint signal
  useEffect(() => {
    if (previewOk) requestAnimationFrame(() => requestAnimationFrame(() => st().markRendered()));
  }, [previewOk]);

  // attach transformer to selected nodes
  useEffect(() => {
    const tr = trRef.current;
    const stage = stageRef.current;
    if (!tr || !stage) return;
    const nodes = selection.map((id) => stage.findOne(`#hb-${id}`)).filter(Boolean) as Konva.Node[];
    tr.nodes(nodes);
    tr.getLayer()?.batchDraw();
  }, [selection, items, drag]);

  const snapTargets = useCallback(
    (exclude: Set<string>): Box[] => [{ x: 0, y: 0, w: W, h: H }, ...items.filter((i) => !exclude.has(i.id)).map(bbox)],
    [items, W, H],
  );

  const toPage = (p: { x: number; y: number }) => ({ x: (p.x - ox) / scale, y: (p.y - oy) / scale });

  // ---------------------------------------------------------------- drag (move), fully controlled
  // (Konva's own draggable + Transformer would also move the other selected nodes, fighting the snapping.)
  const dragRef = useRef<(DragState & { p0: { x: number; y: number }; moved: boolean }) | null>(null);

  const beginDrag = (e: Konva.KonvaEventObject<MouseEvent>, it: Item) => {
    if (e.evt.button !== 0) return;
    e.cancelBubble = true;
    let ids: string[];
    if (e.evt.shiftKey || e.evt.ctrlKey) {
      st().select([it.id], true);
      ids = st().selection;
      if (!ids.includes(it.id)) return;
    } else if (selSet.has(it.id)) {
      ids = selection;
    } else {
      st().select([it.id]);
      ids = [it.id];
    }
    const start: Record<string, Box> = {};
    for (const id of ids) {
      const i = items.find((x) => x.id === id);
      if (i) start[id] = bbox(i);
    }
    dragRef.current = { ids, start, anchorId: it.id, p0: toPage(stageRef.current!.getPointerPosition()!), moved: false };
  };

  const moveDrag = (e: Konva.KonvaEventObject<MouseEvent>) => {
    const d = dragRef.current!;
    const p = toPage(stageRef.current!.getPointerPosition()!);
    const ddx = p.x - d.p0.x, ddy = p.y - d.p0.y;
    if (!d.moved) {
      if (Math.hypot(ddx, ddy) * scale < 3) return;
      d.moved = true;
      setDrag({ ids: d.ids, start: d.start, anchorId: d.anchorId });
    }
    const b0 = d.start[d.anchorId];
    const raw = { x: b0.x + ddx, y: b0.y + ddy, w: b0.w, h: b0.h };
    const r = !snapOn || e.evt.altKey
      ? { x: Math.round(raw.x), y: Math.round(raw.y), guides: [] as Guide[] }
      : snapMove(raw, { grid: GRID, threshold: 6 / scale, targets: snapTargets(new Set(d.ids)) });
    const dx = r.x - b0.x, dy = r.y - b0.y;
    for (const id of d.ids) {
      const s = d.start[id];
      stageRef.current?.findOne(`#hb-${id}`)?.position({ x: s.x + dx, y: s.y + dy });
    }
    setGuides(r.guides);
  };

  const endDrag = () => {
    const d = dragRef.current;
    dragRef.current = null;
    if (!d || !d.moved) return;
    const n = stageRef.current?.findOne(`#hb-${d.anchorId}`);
    const b0 = d.start[d.anchorId];
    const dx = n ? Math.round(n.x() - b0.x) : 0, dy = n ? Math.round(n.y() - b0.y) : 0;
    setDrag(null);
    setGuides([]);
    if (dx || dy) {
      if (preview) setGhost({ ids: d.ids, start: d.start, anchorId: d.anchorId, url: preview.url });
      const moved = items.filter((i) => d.ids.includes(i.id)).map((i) => moveBy(i, dx, dy));
      st().commit(updateItems(st().project!, moved));
    }
  };

  // ---------------------------------------------------------------- resize
  type TBox = { x: number; y: number; width: number; height: number; rotation: number };
  const boundBox = (oldBox: TBox, newBox: TBox): TBox => {
    if (newBox.width < 3 || newBox.height < 3) return oldBox;
    const tr = trRef.current;
    if (!snapOn || !tr) return newBox;
    const edges = anchorEdges(tr.getActiveAnchor());
    const pb = { x: (newBox.x - ox) / scale, y: (newBox.y - oy) / scale, w: newBox.width / scale, h: newBox.height / scale };
    const r = snapResize(pb, edges, { grid: GRID, threshold: 6 / scale, targets: snapTargets(new Set(selection)) });
    setGuides(r.guides);
    return { ...newBox, x: r.box.x * scale + ox, y: r.box.y * scale + oy, width: r.box.w * scale, height: r.box.h * scale };
  };

  const onTransformEnd = () => {
    const tr = trRef.current;
    if (!tr) return;
    const changed: Item[] = [];
    for (const node of tr.nodes()) {
      const id = node.id().replace(/^hb-/, "");
      const it = items.find((i) => i.id === id);
      if (!it) continue;
      const box = { x: node.x(), y: node.y(), w: node.width() * node.scaleX(), h: node.height() * node.scaleY() };
      node.scale({ x: 1, y: 1 });
      changed.push(withBox(it, box));
    }
    setGuides([]);
    if (changed.length) st().commit(updateItems(st().project!, changed));
  };

  // ---------------------------------------------------------------- stage mouse: marquee, pan, zoom
  const onStageMouseDown = (e: Konva.KonvaEventObject<MouseEvent>) => {
    if (e.evt.button === 1) {
      panStart.current = { x: e.evt.clientX, y: e.evt.clientY, px: pan.x, py: pan.y };
      if (zoom === null) st().setZoom(scale);
      return;
    }
    const target = e.target;
    const isBackground = target === target.getStage() || target.name() === "page-bg";
    if (!isBackground || e.evt.button !== 0) return;
    const p = toPage(stageRef.current!.getPointerPosition()!);
    marqueeStart.current = { ...p, additive: e.evt.shiftKey || e.evt.ctrlKey };
  };

  const onStageMouseMove = (e: Konva.KonvaEventObject<MouseEvent>) => {
    if (dragRef.current) {
      moveDrag(e);
      return;
    }
    if (panStart.current) {
      const s = panStart.current;
      setPan({ x: s.px + e.evt.clientX - s.x, y: s.py + e.evt.clientY - s.y });
      return;
    }
    const m = marqueeStart.current;
    if (!m) return;
    const p = toPage(stageRef.current!.getPointerPosition()!);
    setMarquee({ x: Math.min(m.x, p.x), y: Math.min(m.y, p.y), w: Math.abs(p.x - m.x), h: Math.abs(p.y - m.y) });
  };

  const onStageMouseUp = () => {
    if (dragRef.current) {
      endDrag();
      return;
    }
    if (panStart.current) {
      panStart.current = null;
      return;
    }
    const m = marqueeStart.current;
    marqueeStart.current = null;
    if (!m) return;
    if (marquee && (marquee.w > 3 || marquee.h > 3)) {
      const hit = items.filter((i) => {
        const b = bbox(i);
        return b.x < marquee.x + marquee.w && b.x + b.w > marquee.x && b.y < marquee.y + marquee.h && b.y + b.h > marquee.y;
      });
      st().select(hit.map((i) => i.id), m.additive);
    } else if (!m.additive) {
      st().select([]);
    }
    setMarquee(null);
  };

  const onWheel = (e: Konva.KonvaEventObject<WheelEvent>) => {
    e.evt.preventDefault();
    if (e.evt.ctrlKey || e.evt.metaKey) {
      const pointer = stageRef.current!.getPointerPosition()!;
      const u = toPage(pointer);
      const ns = Math.min(8, Math.max(0.05, scale * (e.evt.deltaY < 0 ? 1.12 : 1 / 1.12)));
      const nox = pointer.x - u.x * ns, noy = pointer.y - u.y * ns;
      setPan({ x: nox - (size.w - W * ns) / 2, y: noy - (size.h - H * ns) / 2 });
      st().setZoom(ns);
    } else {
      if (zoom === null) st().setZoom(scale);
      setPan((p) => ({ x: p.x - (e.evt.shiftKey ? e.evt.deltaY : e.evt.deltaX), y: p.y - (e.evt.shiftKey ? 0 : e.evt.deltaY) }));
    }
  };

  const zoomBy = (f: number) => st().setZoom(Math.min(8, Math.max(0.05, scale * f)));

  // ---------------------------------------------------------------- render
  const activeGhost = drag ?? (ghost && preview && ghost.url === preview.url ? ghost : null);
  const dragging = activeGhost ? new Set(activeGhost.ids) : null;
  const bgColor = page?.background.color && project.theme.colors[page.background.color]
    ? project.theme.colors[page.background.color]
    : page?.background.color?.startsWith("#") ? page.background.color : "#000";

  return (
    <main className="canvas-wrap" ref={wrapRef}>
      <Stage ref={stageRef} width={size.w} height={size.h} onMouseDown={onStageMouseDown} onMouseMove={onStageMouseMove}
        onMouseUp={onStageMouseUp} onMouseLeave={onStageMouseUp} onWheel={onWheel}>
        <Layer imageSmoothingEnabled={scale < 1} listening={true}>
          <Group x={ox} y={oy} scaleX={scale} scaleY={scale}>
            <Rect name="page-bg" x={0} y={0} width={W} height={H} fill={bgColor} shadowColor="#000" shadowBlur={30}
              shadowOpacity={0.5} shadowOffsetY={8} />
            {previewOk && <KImage name="page-bg" image={preview!.img} x={0} y={0} width={W} height={H} />}
            {dragging && previewOk &&
              activeGhost!.ids.map((id) => {
                const b = activeGhost!.start[id];
                return b ? <Rect key={`hole-${id}`} x={b.x} y={b.y} width={b.w} height={b.h} fill="#000" opacity={0.45} listening={false} /> : null;
              })}
          </Group>
        </Layer>
        <Layer>
          <Group x={ox} y={oy} scaleX={scale} scaleY={scale}>
            {items.map((it) => {
              const b = bbox(it);
              const isSel = selSet.has(it.id);
              const showPattern = !!(dragging?.has(it.id) && previewOk && activeGhost!.start[it.id]);
              return (
                <Rect key={it.id} id={`hb-${it.id}`} x={b.x} y={b.y} width={Math.max(1, b.w)} height={Math.max(1, b.h)}
                  fill={showPattern ? undefined : "transparent"}
                  fillPatternImage={showPattern ? preview!.img : undefined}
                  fillPatternOffset={showPattern ? { x: activeGhost!.start[it.id].x, y: activeGhost!.start[it.id].y } : undefined}
                  fillPatternRepeat="no-repeat"
                  stroke={isSel ? undefined : hover === it.id ? ACCENT : undefined}
                  strokeWidth={1.5} strokeScaleEnabled={false} dash={it.type === "line" ? [4, 3] : undefined}
                  onMouseEnter={(e) => { setHover(it.id); e.target.getStage()!.container().style.cursor = "move"; }}
                  onMouseLeave={(e) => { setHover((h) => (h === it.id ? null : h)); e.target.getStage()!.container().style.cursor = "default"; }}
                  onMouseDown={(e) => beginDrag(e, it)}
                />
              );
            })}
            {selection.length > 1 && items.filter((i) => selSet.has(i.id)).map((i) => {
              const b = bbox(i);
              return <Rect key={`sel-${i.id}`} x={b.x} y={b.y} width={b.w} height={b.h} stroke={ACCENT} strokeWidth={1} strokeScaleEnabled={false} dash={[3, 3]} listening={false} />;
            })}
            {guides.map((g, i) =>
              g.orientation === "v"
                ? <Line key={i} points={[g.pos, -20, g.pos, H + 20]} stroke={GUIDE} strokeWidth={1} strokeScaleEnabled={false} listening={false} />
                : <Line key={i} points={[-20, g.pos, W + 20, g.pos]} stroke={GUIDE} strokeWidth={1} strokeScaleEnabled={false} listening={false} />)}
            {marquee && (
              <Rect x={marquee.x} y={marquee.y} width={marquee.w} height={marquee.h} fill="rgba(56,189,248,0.08)" stroke={ACCENT}
                strokeWidth={1} strokeScaleEnabled={false} dash={[4, 4]} listening={false} />
            )}
          </Group>
          <Transformer ref={trRef} rotateEnabled={false} keepRatio={false} flipEnabled={false} ignoreStroke
            borderStroke={ACCENT} anchorStroke={ACCENT} anchorFill="#0b1220" anchorSize={9} anchorCornerRadius={2}
            boundBoxFunc={boundBox} onTransformEnd={onTransformEnd} />
        </Layer>
      </Stage>

      {!previewOk && <div className="canvas-loading"><div className="spinner" /></div>}

      <div className="canvas-hud">
        <button className="icon-btn sm" title={t("canvas.zoomOut")} onClick={() => zoomBy(1 / 1.25)}>−</button>
        <button className="hud-zoom" title={t("toolbar.fit")} onClick={() => st().setZoom(null)}>{Math.round(scale * 100)}%</button>
        <button className="icon-btn sm" title={t("canvas.zoomIn")} onClick={() => zoomBy(1.25)}>+</button>
        <span className="hud-sep" />
        <button className={`hud-toggle ${snapOn ? "on" : ""}`} title={t("canvas.snapHint")} onClick={() => setSnapOn(!snapOn)}>
          <Icon name="fit" size={14} /> {t("canvas.snap")}
        </button>
      </div>
    </main>
  );
}
