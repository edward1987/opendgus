import { useEffect, useMemo, useState } from "react";
import { useShallow } from "zustand/react/shallow";
import { useTranslation } from "react-i18next";
import { arrangeItems, AlignMode, duplicateItems, isControl, isLine, Item, makePreset, removeItems, updateItems, updatePage } from "../lib/project";
import { JsonSchema } from "../lib/types";
import { FieldDesc, rawSpecToSchema, schemaToFields, splitAdvanced } from "../lib/schemaForm";
import type { Control, Page } from "../lib/types";
import { currentPage, selectedItems, useStore } from "../store";
import { ColorField, FieldEditor, NumberInput, Row, SchemaForm, Switch, VarField } from "./fields";
import { Icon, IconName } from "./Icons";
import { itemIcon } from "./LeftPanel";

const rawSchemaCache = new Map<string, JsonSchema>();

/** Fields for an item: element_schema def, widget props schema, or (async) raw DGUS spec. */
function useItemFields(it: Item | null): { fields: FieldDesc[]; loading: boolean } {
  const catalog = useStore((s) => s.catalog)!;
  const api = useStore((s) => s.api);
  const [raw, setRaw] = useState<JsonSchema | null>(null);
  const type = it?.type ?? "";
  useEffect(() => {
    if (!type.startsWith("raw:")) return;
    const cached = rawSchemaCache.get(type);
    if (cached) return setRaw(cached);
    setRaw(null);
    api?.tool<{ properties: Record<string, JsonSchema> }>("get_widget_schema", { type }).then((s) => {
      const js = rawSpecToSchema(s);
      rawSchemaCache.set(type, js);
      setRaw(js);
    }).catch(() => setRaw({ type: "object", properties: {} }));
  }, [type, api]);

  return useMemo(() => {
    if (!it) return { fields: [], loading: false };
    if (isControl(it)) {
      if (type.startsWith("raw:")) return { fields: raw ? schemaToFields(raw) : [], loading: !raw };
      const w = catalog.widgets.find((x) => x.type === type);
      return { fields: w ? schemaToFields(w.props) : [], loading: false };
    }
    const root = catalog.element_schema;
    const def = Object.values<JsonSchema>(root.$defs ?? {}).find((d) => d.properties?.type?.const === type);
    if (!def) return { fields: [], loading: false };
    return {
      fields: schemaToFields(def, { root, exclude: ["id", "type", "x", "y", "w", "h", "visible"], iconKeys: type === "icon" ? ["name"] : ["icon"] }),
      loading: false,
    };
  }, [it?.type, raw, catalog]);
}

export function PropertiesPanel() {
  const items = useStore(useShallow(selectedItems));
  if (items.length === 0) return <PageProperties />;
  if (items.length > 1) return <MultiProperties items={items} />;
  return <ItemProperties key={items[0].id} it={items[0]} />;
}

function SavePreset({ ids }: { ids: string[] }) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const save = () => {
    const s = useStore.getState();
    if (!s.project || !name.trim()) return;
    const preset = makePreset(s.project, ids, name);
    s.commit({ ...s.project, presets: [...(s.project.presets ?? []), preset] });
    setName("");
    setOpen(false);
  };
  return open ? <div className="row gap">
    <input autoFocus value={name} placeholder={t("insert.presetName")} onChange={(e) => setName(e.target.value)}
      onKeyDown={(e) => { if (e.key === "Enter") save(); if (e.key === "Escape") setOpen(false); }} />
    <button className="btn sm primary" disabled={!name.trim()} onClick={save}>{t("common.save")}</button>
  </div> : <button className="btn sm" onClick={() => setOpen(true)}><Icon name="star" size={14} /> {t("insert.savePreset")}</button>;
}

function ItemProperties({ it }: { it: Item }) {
  const { t } = useTranslation();
  const catalog = useStore((s) => s.catalog)!;
  const { fields, loading } = useItemFields(it);
  const [showAdv, setShowAdv] = useState(false);
  const st = useStore.getState;

  const change = (patch: Partial<Item> | Record<string, unknown>, key: string) => {
    const s = st();
    const cur = s.project && selectedItems(s).find((x) => x.id === it.id);
    if (!cur) return;
    s.commit(updateItems(s.project!, [{ ...cur, ...patch } as Item]), `${it.id}:${key}`);
  };

  const ctl = isControl(it) ? (it as Control) : null;
  const widget = ctl ? catalog.widgets.find((w) => w.type === ctl.type) : null;
  const dgus = ctl?.type.startsWith("raw:") ? catalog.dgus_controls.find((d) => d.type === ctl.type) : null;
  const title = widget ? t(`widgets.${widget.type}.title`, { defaultValue: widget.title }) : dgus ? dgus.title : t(`insert.el.${it.type}`, { defaultValue: it.type });
  const description = widget ? t(`widgets.${widget.type}.desc`, { defaultValue: widget.description }) : dgus?.description;
  const [basic, adv] = splitAdvanced(fields);
  const values = ctl ? ctl.props : (it as Record<string, any>);

  const onFormChange = (next: Record<string, any>, key: string) => {
    if (ctl) change({ props: next }, `props.${key}`);
    else change({ [key]: next[key] }, key);
  };

  return (
    <div className="props">
      <div className="props-head">
        <div className="props-icon"><Icon name={itemIcon(it) as IconName} size={18} /></div>
        <div className="grow">
          <div className="props-title">{title}</div>
          <div className="props-sub">{it.id} · {ctl ? t("props.dynamic") : t("props.static")}</div>
        </div>
        <button className="icon-btn sm" title={`${t("common.duplicate")} (Ctrl+D)`} onClick={() => { const [p, ids] = duplicateItems(st().project!, [it.id]); st().commit(p); st().select(ids); }}><Icon name="copy" /></button>
        <button className="icon-btn sm danger" title={`${t("common.delete")} (Del)`} onClick={() => st().commit(removeItems(st().project!, [it.id]))}><Icon name="trash" /></button>
      </div>
      {description && <p className="props-desc">{description}</p>}
      {widget?.runtime_input && <p className="muted small">{widget.runtime_input}</p>}
      <SavePreset ids={[it.id]} />

      <h4 className="group-title">{t("props.layout")}</h4>
      {isLine(it) ? (
        <FieldEditor field={{ key: "points", label: t("props.points"), kind: "intList", nullable: false, required: true }} value={it.points} onChange={(v) => change({ points: v as number[] }, "points")} />
      ) : (
        <div className="geo-grid">
          {(["x", "y", "w", "h"] as const).map((k) => (
            <label key={k} className="geo">
              <span>{k.toUpperCase()}</span>
              <NumberInput value={(it as any)[k]} min={k === "w" || k === "h" ? 1 : undefined} onChange={(n) => n !== null && change({ [k]: n }, k)} />
            </label>
          ))}
        </div>
      )}
      <Row label={t("props.visible")}><Switch checked={it.visible !== false} onChange={(v) => change({ visible: v }, "visible")} /></Row>

      {ctl && (
        <>
          <h4 className="group-title">{t("props.data")}</h4>
          <Row label={t("props.variable")} hint={t("props.variableHint")}>
            <VarField value={ctl.var} onChange={(v) => change({ var: v }, "var")}
              onCreate={(name, type) => {
                const s = st();
                const p = { ...s.project!, variables: [...s.project!.variables, { name, type: type as any, vp: null, init: type === "text" ? "" : 0, length: 16, decimals: 0, doc: "" }] };
                s.commit(updateItems(p, [{ ...ctl, var: name }]));
              }} />
          </Row>
          {widget?.needs_var && !ctl.var && <div className="alert warn small">{t("props.needsVar")}</div>}
        </>
      )}

      {fields.length > 0 && <h4 className="group-title">{ctl ? t("props.widget") : t("props.style")}</h4>}
      {loading && <div className="muted small">{t("common.loading")}</div>}
      <SchemaForm fields={basic} value={values} onChange={onFormChange} />
      {adv.length > 0 && (
        <>
          <button className="expert-toggle" onClick={() => setShowAdv(!showAdv)}>
            <Icon name={showAdv ? "down" : "arrowRight"} size={14} /> {t("props.advanced")} <span className="count">{adv.length}</span>
          </button>
          {showAdv && <SchemaForm fields={adv} value={values} onChange={onFormChange} />}
        </>
      )}
    </div>
  );
}

const ALIGN: { mode: AlignMode; icon: IconName }[] = [
  { mode: "left", icon: "alignLeft" }, { mode: "center_x", icon: "alignCenterX" }, { mode: "right", icon: "alignRight" },
  { mode: "top", icon: "alignTop" }, { mode: "center_y", icon: "alignCenterY" }, { mode: "bottom", icon: "alignBottom" },
  { mode: "distribute_x", icon: "distX" }, { mode: "distribute_y", icon: "distY" },
];

function MultiProperties({ items }: { items: Item[] }) {
  const { t } = useTranslation();
  const st = useStore.getState;
  return (
    <div className="props">
      <div className="props-head">
        <div className="props-icon"><Icon name="layers" size={18} /></div>
        <div className="grow">
          <div className="props-title">{t("props.multi", { count: items.length })}</div>
          <div className="props-sub">{items.map((i) => i.id).join(", ")}</div>
        </div>
        <button className="icon-btn sm danger" title={t("common.delete")} onClick={() => st().commit(removeItems(st().project!, items.map((i) => i.id)))}><Icon name="trash" /></button>
      </div>
      <SavePreset ids={items.map((i) => i.id)} />
      <h4 className="group-title">{t("props.align")}</h4>
      <div className="align-grid">
        {ALIGN.map((a) => (
          <button key={a.mode} className="icon-btn" title={t(`align.${a.mode}`)} disabled={a.mode.startsWith("distribute") && items.length < 3}
            onClick={() => st().commit(updateItems(st().project!, arrangeItems(items, a.mode)))}>
            <Icon name={a.icon} />
          </button>
        ))}
      </div>
      <p className="muted small">{t("props.multiHint")}</p>
    </div>
  );
}

function PageProperties() {
  const { t } = useTranslation();
  const page = useStore(currentPage);
  const project = useStore((s) => s.project)!;
  const st = useStore.getState;
  if (!page) return null;
  const set = (fn: (p: Page) => Page, key: string) => st().commit(updatePage(st().project!, page.id, fn), `page${page.id}:${key}`);
  const bg = page.background;
  const d = project.display;
  return (
    <div className="props">
      <div className="props-head">
        <div className="props-icon"><Icon name="pages" size={18} /></div>
        <div className="grow">
          <div className="props-title">{page.name || t("pages.unnamed")}</div>
          <div className="props-sub">{t("props.pageId", { id: page.id })}</div>
        </div>
      </div>
      <p className="props-desc">{t("props.pageHint")}</p>
      <h4 className="group-title">{t("props.page")}</h4>
      <Row label={t("props.name")}><input value={page.name} onChange={(e) => set((p) => ({ ...p, name: e.target.value }), "name")} /></Row>
      <Row label={t("props.background")}>
        <ColorField value={bg.color} nullable onChange={(c) => set((p) => ({ ...p, background: { ...p.background, color: c } }), "bg")} />
      </Row>
      <FieldEditor field={{ key: "gradient", label: t("props.gradient"), kind: "colorList", nullable: true, required: false }} value={bg.gradient}
        onChange={(g) => set((p) => ({ ...p, background: { ...p.background, gradient: (g as string[] | null)?.length ? (g as string[]) : null } }), "grad")} />

      <h4 className="group-title">{t("props.display")}</h4>
      <dl className="specs">
        <dt>{t("props.resolution")}</dt><dd>{d.width} × {d.height}</dd>
        <dt>{t("props.profile")}</dt><dd>{d.profile ?? t("wizard.custom")}</dd>
        <dt>CPU</dt><dd>{d.cpu} · {d.flash_mb} MB</dd>
      </dl>
      <Row label={t("props.backlight")}>
        <NumberInput value={d.backlight} min={0} max={100} onChange={(n) => n !== null && st().commit({ ...st().project!, display: { ...st().project!.display, backlight: n } }, "backlight")} />
        <span className="unit">%</span>
      </Row>
      <Row label={t("settings.autoDim")}>
        <button className="link small" onClick={() => st().setDialog("settings")}>
          {d.standby?.enabled ? t("props.dimSummary", { level: d.standby.level, s: d.standby.timeout_s }) : t("props.off")}
          {project.screensaver?.enabled ? ` · ${t("settings.screensaver")}` : ""} ›
        </button>
      </Row>
      <Row label={t("props.beep")}><Switch checked={!!d.touch_beep} onChange={(v) => st().commit({ ...st().project!, display: { ...st().project!.display, touch_beep: v } })} /></Row>
      <Row label={t("props.baud")}>
        <select value={d.baud} onChange={(e) => st().commit({ ...st().project!, display: { ...st().project!.display, baud: Number(e.target.value) } })}>
          {[9600, 19200, 38400, 57600, 115200, 230400, 460800, 921600].map((b) => <option key={b} value={b}>{b}</option>)}
        </select>
      </Row>
    </div>
  );
}
