// Demo mode (the GitHub Pages build): every query is answered from static files the backend
// exporter wrote (backend/src/insights/export_demo.py), so the demo needs no server.
import { ApolloLink } from "@apollo/client";
import { from } from "rxjs";
import { PRESETS } from "./window";

/** Set at build time by `make demo-build`; the snapshot the demo data was taken at. */
export const demoAsOf: string | undefined = import.meta.env.VITE_DEMO_AS_OF || undefined;

/** The operation name, then the variable values sorted by variable name. Matches export_demo.key(). */
export function demoKey(operation: string, variables: Record<string, unknown>): string {
  const values = Object.keys(variables)
    .sort()
    .map((k) => String(variables[k]));
  return values.length ? `${operation}/${values.join("_")}` : operation;
}

const missing = {
  errors: [
    {
      message: `This demo covers the last ${PRESETS.join(", ").replace(/, (\d+)$/, ", or $1")} complete weeks before its snapshot.`,
    },
  ],
};

export const demoLink = new ApolloLink((operation) =>
  from(
    fetch(`${import.meta.env.BASE_URL}demo/${demoKey(operation.operationName ?? "", operation.variables)}.json`)
      .then((r) => (r.ok ? r.json() : missing))
      .catch(() => missing), // a dev server answers unknown paths with index.html, which isn't JSON
  ),
);
