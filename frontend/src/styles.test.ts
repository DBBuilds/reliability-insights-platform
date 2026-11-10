// @vitest-environment node
import { readFileSync } from "node:fs";

// Read from disk: Vitest replaces CSS imports, `?raw` included, with an empty string.
const css = readFileSync(new URL("./styles.css", import.meta.url), "utf8");

const rules = css.replace(/\/\*[\s\S]*?\*\//g, "");
const root = rules.slice(rules.indexOf(":root {"), rules.indexOf("}", rules.indexOf(":root {")) + 1);
const rest = rules.replace(root, "");
const declarations = [...rest.matchAll(/([a-z-]+)\s*:\s*([^;}]+)/g)].map(([, prop, value]) => ({
  prop: prop as string,
  value: (value as string).trim(),
}));

test("the stylesheet was read", () => {
  expect(declarations.length).toBeGreaterThan(50);
});

test("spacing, type sizes, and corner radii use the scales in :root", () => {
  const scaled = /^(margin|padding|gap|row-gap|column-gap|font-size|border-radius)(-|$)/;
  const literal = declarations.filter((d) => scaled.test(d.prop) && /\d(px|rem|em)\b/.test(d.value));
  expect(literal).toEqual([]);
});

test("colors are tokens: no hex or rgb() outside :root", () => {
  expect(declarations.filter((d) => /#[0-9a-f]{3,8}\b|rgba?\(/i.test(d.value))).toEqual([]);
});

test("every color token has a dark value or is meant to be the same in both themes", () => {
  const colors = [...root.matchAll(/(--[a-z0-9-]+):\s*([^;]+);/g)].filter(([, , v]) => v?.includes("#"));
  const same = ["--good", "--warning", "--serious", "--critical"]; // status hues, validated in both modes
  expect(colors.filter(([, name, v]) => !v?.startsWith("light-dark(") && !same.includes(name as string))).toEqual([]);
});
