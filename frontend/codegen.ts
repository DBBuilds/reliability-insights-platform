import type { CodegenConfig } from "@graphql-codegen/cli";

// Types come from the committed contract, not a live server, so codegen works
// offline and in CI. The backend's tests keep ../schema/schema.graphql current.
const config: CodegenConfig = {
  schema: "../schema/schema.graphql",
  documents: ["src/**/*.{ts,tsx}", "!src/gql/**"],
  ignoreNoDocuments: false,
  generates: {
    "src/gql/": {
      preset: "client",
      config: { scalars: { Date: "string" }, enumsAsTypes: true, useTypeImports: true },
    },
  },
};

export default config;
