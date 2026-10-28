import { useTranslation } from "react-i18next";
import { allocateVps, hex4, uniqueVarName } from "../lib/project";
import type { Project, Variable, VarType } from "../lib/types";
import { useStore } from "../store";
import { NumberInput } from "./fields";
import { Icon } from "./Icons";

const TYPES: VarType[] = ["int16", "uint16", "int32", "uint32", "text", "bits"];

export function VariablesPanel() {
  const { t } = useTranslation();
  const project = useStore((s) => s.project)!;
  const vpMap = useStore((s) => s.vpMap);
  const st = useStore.getState;
  const vps = allocateVps(project.variables);
  const usage = (name: string) => project.pages.flatMap((p) => p.controls.filter((c) => c.var === name).map((c) => c.id));

  const setVar = (i: number, patch: Partial<Variable>, key: string) => {
    const p = st().project!;
    const old = p.variables[i];
    const variables = p.variables.map((v, j) => (j === i ? { ...v, ...patch } : v));
    let next: Project = { ...p, variables };
    if (patch.name && patch.name !== old.name) {
      // keep controls pointing at the renamed variable
      next = { ...next, pages: next.pages.map((pg) => ({ ...pg, controls: pg.controls.map((c) => (c.var === old.name ? { ...c, var: patch.name! } : c)) })) };
    }
    st().commit(next, `var${i}:${key}`);
  };

  const add = () => {
    const p = st().project!;
    const name = uniqueVarName(p, "value");
    st().commit({ ...p, variables: [...p.variables, { name, type: "int16", vp: null, init: 0, length: 16, decimals: 0, doc: "" }] });
  };

  const remove = (i: number) => {
    const v = project.variables[i];
    const users = usage(v.name);
    if (users.length) {
      st().toast(t("vars.inUse", { name: v.name, ids: users.join(", ") }), "error");
      return;
    }
    st().commit({ ...project, variables: project.variables.filter((_, j) => j !== i) });
  };

  return (
    <div className="vars-panel">
      <div className="row between">
        <p className="muted small">{t("vars.hint")}</p>
        <button className="btn sm primary" onClick={add}><Icon name="plus" size={14} /> {t("vars.add")}</button>
      </div>
      {project.variables.length === 0 && <div className="list-empty">{t("vars.empty")}</div>}
      {project.variables.map((v, i) => {
        const used = usage(v.name);
        const nameOk = /^[A-Za-z_][A-Za-z0-9_]*$/.test(v.name) && project.variables.filter((x) => x.name === v.name).length === 1;
        return (
          <div key={i} className="var-card">
            <div className="var-top">
              <input className={`var-name mono ${nameOk ? "" : "invalid"}`} value={v.name} onChange={(e) => setVar(i, { name: e.target.value }, "name")} />
              <span className="vp mono" title={vpMap ? t("vars.vpBuilt") : t("vars.vpAuto")}>{vpMap?.[v.name] ?? hex4(vps[v.name] ?? 0)}</span>
              <button className="icon-btn xs" title={used.length ? t("vars.usedBy", { ids: used.join(", ") }) : t("common.delete")} onClick={() => remove(i)}>
                <Icon name="trash" size={14} />
              </button>
            </div>
            <div className="var-grid">
              <label>
                <span>{t("vars.type")}</span>
                <select value={v.type} onChange={(e) => setVar(i, { type: e.target.value as VarType, init: e.target.value === "text" ? "" : 0 }, "type")}>
                  {TYPES.map((x) => <option key={x}>{x}</option>)}
                </select>
              </label>
              <label>
                <span>{t("vars.init")}</span>
                {v.type === "text" ? (
                  <input value={String(v.init)} onChange={(e) => setVar(i, { init: e.target.value }, "init")} />
                ) : (
                  <NumberInput value={typeof v.init === "number" ? v.init : 0} onChange={(n) => n !== null && setVar(i, { init: n }, "init")} />
                )}
              </label>
              {v.type === "text" ? (
                <label>
                  <span>{t("vars.length")}</span>
                  <NumberInput value={v.length} min={1} max={255} onChange={(n) => n !== null && setVar(i, { length: n }, "length")} />
                </label>
              ) : (
                <label>
                  <span>{t("vars.decimals")}</span>
                  <NumberInput value={v.decimals} min={0} max={6} onChange={(n) => n !== null && setVar(i, { decimals: n }, "decimals")} />
                </label>
              )}
            </div>
            <input className="var-doc" placeholder={t("vars.doc")} value={v.doc} onChange={(e) => setVar(i, { doc: e.target.value }, "doc")} />
            {used.length > 0 && <div className="var-used">{t("vars.usedBy", { ids: used.join(", ") })}</div>}
          </div>
        );
      })}
    </div>
  );
}
