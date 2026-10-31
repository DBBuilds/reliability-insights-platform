import { ApolloClient, HttpLink, InMemoryCache } from "@apollo/client";
import { demoAsOf, demoLink } from "./demo";

// Apollo Client 4 requires app-wide defaults that change result types to be
// declared, so hooks type `data` as possibly partial when errors are allowed.
declare module "@apollo/client" {
  namespace ApolloClient {
    namespace DeclareDefaultOptions {
      interface WatchQuery {
        errorPolicy: "all";
      }
      interface Query {
        errorPolicy: "all";
      }
    }
  }
}

// Render whatever data came back even if part of the query errored. One bad
// field then degrades one panel, not the whole page.
export const defaultOptions = { watchQuery: { errorPolicy: "all" }, query: { errorPolicy: "all" } } as const;

export const client = new ApolloClient({
  link: demoAsOf ? demoLink : new HttpLink({ uri: import.meta.env.VITE_GRAPHQL_URL ?? "/graphql" }),
  cache: new InMemoryCache(),
  defaultOptions,
});
