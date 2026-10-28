import { describe, expect, it } from "vitest";
import { defaultObject, rawSpecToSchema, schemaToFields, splitAdvanced } from "./schemaForm";

// Shapes as produced by the backend's /api/catalog (pydantic v2 JSON schema).
const buttonProps = {
  $defs: {
    PageAction: {
      additionalProperties: false,
      properties: { type: { const: "page", default: "page", type: "string" }, page: { minimum: 0, type: "integer", description: "Page to open" } },
      required: ["page"], title: "PageAction", type: "object",
    },
    SetAction: {
      properties: { type: { const: "set", default: "set", type: "string" }, value: { type: "integer" } },
      required: ["value"], title: "SetAction", type: "object",
    },
  },
  properties: {
    label: { default: "", title: "Label", type: "string" },
    icon: { anyOf: [{ type: "string" }, { type: "null" }], default: null, title: "Icon" },
    style: { default: "filled", enum: ["filled", "outline", "ghost"], title: "Style", type: "string" },
    color: { default: "primary", title: "Color", type: "string" },
    text_color: { anyOf: [{ type: "string" }, { type: "null" }], default: null, title: "Text Color" },
    radius: { anyOf: [{ type: "integer" }, { type: "null" }], default: null, title: "Radius" },
    action: {
      anyOf: [
        { discriminator: { mapping: {}, propertyName: "type" }, oneOf: [{ $ref: "#/$defs/PageAction" }, { $ref: "#/$defs/SetAction" }] },
        { type: "null" },
      ],
      default: null, title: "Action",
    },
    states: { type: "array", items: { $ref: "#/$defs/SetAction" } },
    gradient: { anyOf: [{ items: { type: "string" }, type: "array" }, { type: "null" }], default: null },
    points: { items: { type: "integer" }, type: "array" },
    vertical: { default: false, type: "boolean" },
    opacity: { default: 1, maximum: 1, minimum: 0, type: "number" },
  },
  type: "object",
};

const byKey = (fs: ReturnType<typeof schemaToFields>) => Object.fromEntries(fs.map((f) => [f.key, f]));

describe("schema -> form fields", () => {
  const f = byKey(schemaToFields(buttonProps));

  it("maps primitive types", () => {
    expect(f.label.kind).toBe("string");
    expect(f.vertical.kind).toBe("boolean");
    expect(f.opacity.kind).toBe("number");
    expect(f.opacity.max).toBe(1);
  });

  it("maps enums to selects", () => {
    expect(f.style.kind).toBe("enum");
    expect(f.style.enum!.map((o) => o.value)).toEqual(["filled", "outline", "ghost"]);
  });

  it("detects colours and icons by key, keeping nullability", () => {
    expect(f.color.kind).toBe("color");
    expect(f.color.nullable).toBe(false);
    expect(f.text_color.kind).toBe("color");
    expect(f.text_color.nullable).toBe(true);
    expect(f.icon.kind).toBe("icon");
    expect(f.icon.nullable).toBe(true);
    expect(f.radius).toMatchObject({ kind: "integer", nullable: true });
  });

  it("maps discriminated unions with resolved $refs", () => {
    expect(f.action.kind).toBe("union");
    expect(f.action.nullable).toBe(true);
    expect(f.action.discriminator).toBe("type");
    expect(f.action.variants!.map((v) => v.tag)).toEqual(["page", "set"]);
    const page = f.action.variants![0];
    expect(page.fields.map((x) => x.key)).toEqual(["page"]);
    expect(page.fields[0]).toMatchObject({ kind: "integer", min: 0, required: true });
  });

  it("maps arrays", () => {
    expect(f.states.kind).toBe("array");
    expect(f.states.item!.fields!.map((x) => x.key)).toEqual(["type", "value"]);
    expect(f.gradient.kind).toBe("colorList");
    expect(f.points.kind).toBe("intList");
  });

  it("supports exclude and custom icon keys", () => {
    const fs = schemaToFields(
      { properties: { id: { type: "string" }, name: { type: "string" }, x: { type: "integer" } } },
      { exclude: ["id", "x"], iconKeys: ["name"] },
    );
    expect(fs.map((x) => [x.key, x.kind])).toEqual([["name", "icon"]]);
  });

  it("builds default objects including required fields", () => {
    expect(defaultObject(buttonProps.$defs.PageAction)).toEqual({ type: "page", page: 0 });
  });

  it("converts raw DGUS spec schemas, hiding geometry and splitting advanced", () => {
    const js = rawSpecToSchema({
      properties: {
        x: { type: "integer", role: "x" },
        vp: { type: "integer" },
        mode: { type: "integer", enum: [0, 1], enumNames: ["Off", "On"], default: 0 },
        icon_lib: { type: "integer", default: 48, advanced: true },
      },
    });
    const fs = schemaToFields(js);
    expect(fs.map((x) => x.key)).toEqual(["mode", "icon_lib"]);
    expect(fs[0].enum).toEqual([{ value: 0, label: "Off" }, { value: 1, label: "On" }]);
    const [basic, adv] = splitAdvanced(fs);
    expect(basic.map((x) => x.key)).toEqual(["mode"]);
    expect(adv.map((x) => x.key)).toEqual(["icon_lib"]);
  });
});
