import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { bridge } from "../lib/api";
import { insertPreset, nextId, uniqueVarName, updatePage } from "../lib/project";
import type { Control, Element, Project } from "../lib/types";
import { useStore } from "../store";
import { Icon, WIDGET_ICON } from "./Icons";

const ELEMENTS: { type: string; w: number; h: number; extra: Record<string, unknown> }[] = [
  { type: "rect", w: 240, h: 140, extra: { fill: "surface" } },
  { type: "ellipse", w: 120, h: 120, extra: { fill: "primary" } },
  { type: "line", w: 200, h: 0, extra: { color: "muted", width: 2 } },
  { type: "text", w: 280, h: 48, extra: { text: "Text", size: 28, color: "text", valign: "middle" } },
  { type: "icon", w: 64, h: 64, extra: { name: "star", color: "primary" } },
  { type: "image", w: 200, h: 150, extra: { fit: "contain" } },
];

const WIDGET_SIZE: Record<string, [number, number]> = {
  button: [200, 64], toggle: [240, 160], number: [180, 64], progress: [320, 28], indicator: [140, 44], slider: [320, 48],
  live_text: [280, 48], clock: [180, 48], qr: [180, 180], choice: [300, 56], curve: [320, 160],
};

const WIDGET_PROPS: Record<string, Record<string, unknown>> = {
  button: { label: "Button" },
  toggle: { label: "Toggle", icon: "bulb" },
};

const clampPos = (p: Project, x: number, y: number, w: number, h: number) => ({
  x: Math.round(Math.max(0, Math.min(p.display.width - w, x - w / 2)) / 8) * 8,
  y: Math.round(Math.max(0, Math.min(p.display.height - h, y - h / 2)) / 8) * 8,
});

export function InsertPanel() {
  const { t } = useTranslation();
  const catalog = useStore((s) => s.catalog)!;
  const presets = useStore((s) => s.project?.presets ?? []);
  const [q, setQ] = useState("");
  const [expert, setExpert] = useState(false);
  const st = useStore.getState;

  const add = (make: (p: Project, c: { x: number; y: number }) => [Project, string]) => {
    const s = st();
    if (!s.project) return;
    const [p, id] = make(s.project, s.viewCenter);
    s.commit(p);
    s.select([id]);
    s.setRightTab("props");
  };

  const addElement = async (def: (typeof ELEMENTS)[number]) => {
    let extra = def.extra;
    if (def.type === "image") {
      const file = await bridge.openImage(t("insert.chooseImage"));
      if (!file) return;
      const src = await bridge.importAsset(st().folder!, file);
      extra = { ...extra, src };
    }
    add((p, c) => {
      const id = nextId(p, "e");
      const { x, y } = clampPos(p, c.x, c.y, def.w, def.h);
      const el = (def.type === "line"
        ? { type: "line", id, points: [x, y, x + def.w, y], visible: true, ...extra }
        : { type: def.type, id, x, y, w: def.w, h: def.h, visible: true, opacity: 1, ...extra }) as Element;
      return [updatePage(p, st().pageId, (pg) => ({ ...pg, elements: [...pg.elements, el] })), id];
    });
  };

  const addControl = (type: string, needsVar: boolean) => {
    add((p, c) => {
      const [w, h] = WIDGET_SIZE[type] ?? [160, 60];
      const id = nextId(p, "c");
      const { x, y } = clampPos(p, c.x, c.y, w, h);
      let project = p;
      let v: string | null = null;
      if (needsVar) {
        v = uniqueVarName(p, type.replace(/^raw:/, ""));
        const text = type === "live_text" || type === "qr";
        project = { ...p, variables: [...p.variables, { name: v, type: text ? "text" : "int16", vp: null,
          init: text ? "" : 0, length: text ? 64 : 16, decimals: 0, doc: "" }] };
      }
      const ctl: Control = { id, type, x, y, w, h, var: v, props: { ...(WIDGET_PROPS[type] ?? {}) }, visible: true };
      return [updatePage(project, st().pageId, (pg) => ({ ...pg, controls: [...pg.controls, ctl] })), id];
    });
  };

  const ql = q.trim().toLowerCase();
  const match = (...s: string[]) => !ql || s.join(" ").toLowerCase().includes(ql);

  const widgetGroups = useMemo(() => {
    const g: Record<string, typeof catalog.widgets> = {};
    for (const w of catalog.widgets) if (match(w.type, w.title, w.description, w.category)) (g[w.category] ||= []).push(w);
    return g;
  }, [catalog.widgets, ql]);

  const dgusGroups = useMemo(() => {
    const g: Record<string, typeof catalog.dgus_controls> = {};
    for (const d of catalog.dgus_controls) if (match(d.type, d.title, d.description, d.category)) (g[d.category] ||= []).push(d);
    return g;
  }, [catalog.dgus_controls, ql]);

  return (
    <div className="insert-panel">
      <div className="search">
        <Icon name="search" />
        <input placeholder={t("insert.search")} value={q} onChange={(e) => setQ(e.target.value)} />
      </div>
      <h4 className="group-title">{t("insert.shapes")}</h4>
      <div className="tile-grid">
        {ELEMENTS.filter((e) => match(e.type, t(`insert.el.${e.type}`))).map((e) => (
          <button key={e.type} className="tile" onClick={() => void addElement(e)} title={t(`insert.elDesc.${e.type}`)}>
            <Icon name={WIDGET_ICON[e.type]} size={22} />
            <span>{t(`insert.el.${e.type}`)}</span>
          </button>
        ))}
      </div>
      {presets.length > 0 && <>
        <h4 className="group-title">{t("insert.presets")}</h4>
        <div className="widget-list">
          {presets.filter((p) => match(p.name)).map((preset, index) => (
            <div key={`${preset.name}-${index}`} className="row gap">
              <button className="widget-card grow" onClick={() => {
                const s = st();
                if (!s.project) return;
                const [next, ids] = insertPreset(s.project, s.pageId, preset, s.viewCenter);
                s.commit(next); s.select(ids); s.setRightTab("props");
              }}><Icon name="star" size={18} /> {preset.name}</button>
              <button className="icon-btn xs" title={t("common.delete")} onClick={() => {
                const s = st();
                if (s.project) s.commit({ ...s.project, presets: (s.project.presets ?? []).filter((p) => p !== preset) });
              }}><Icon name="trash" size={14} /></button>
            </div>
          ))}
        </div>
      </>}
      {Object.entries(widgetGroups).map(([cat, ws]) => (
        <div key={cat}>
          <h4 className="group-title">{t(`insert.cat.${cat}`, { defaultValue: cat })}</h4>
          <div className="widget-list">
            {ws.map((w) => (
              <button key={w.type} className="widget-card" onClick={() => addControl(w.type, w.needs_var)}>
                <div className="widget-icon"><Icon name={WIDGET_ICON[w.type] ?? "chip"} size={20} /></div>
                <div className="widget-text">
                  <div className="widget-title">{t(`widgets.${w.type}.title`, { defaultValue: w.title })}</div>
                  <div className="widget-desc">{t(`widgets.${w.type}.desc`, { defaultValue: w.description })}</div>
                  {w.verified !== "hardware" && <div className="muted small">{t(`insert.verified.${w.verified}`, { defaultValue: w.verified })}</div>}
                </div>
              </button>
            ))}
          </div>
        </div>
      ))}
      <button className="expert-toggle" onClick={() => setExpert(!expert)}>
        <Icon name={expert ? "down" : "arrowRight"} size={14} /> {t("insert.expert")} <span className="count">{catalog.dgus_controls.length}</span>
      </button>
      {(expert || ql) && (
        <div className="expert">
          <p className="muted small">{t("insert.expertHint")}</p>
          {Object.entries(dgusGroups).map(([cat, ds]) => (
            <div key={cat}>
              <h5 className="subgroup-title">{cat}</h5>
              {ds.map((d) => (
                <button key={d.type} className="dgus-row" title={d.description} onClick={() => addControl(d.type, false)}>
                  <Icon name="chip" size={14} />
                  <span className="grow">{d.title}</span>
                  <span className={`chip tiny ${d.verified === "hardware" ? "ok" : ""}`}>{d.kind}</span>
                </button>
              ))}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
