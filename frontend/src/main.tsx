import { ApolloProvider } from "@apollo/client/react";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { client } from "./apollo";
import { App } from "./App";
import "./styles.css";
import { setTheme, storedTheme } from "./theme";

setTheme(storedTheme()); // before the first paint, so a stored dark theme never flashes light

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ApolloProvider client={client}>
      <App />
    </ApolloProvider>
  </StrictMode>,
);
