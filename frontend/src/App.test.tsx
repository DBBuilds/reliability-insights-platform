import { MockedProvider } from "@apollo/client/testing/react";
import { fireEvent, render, screen } from "@testing-library/react";
import { App, orgTree } from "./App";
import { ORGS } from "./queries";

test("orgTree puts children under their parent, and treats an unknown parent as a root", () => {
  const orgs = [
    { __typename: "Org" as const, id: "payments", name: "Payments", parentId: "eng" },
    { __typename: "Org" as const, id: "eng", name: "Engineering", parentId: null },
    { __typename: "Org" as const, id: "orphan", name: "Orphan", parentId: "gone" },
  ];
  expect(orgTree(orgs).map((o) => [o.id, o.depth])).toEqual([
    ["eng", 0],
    ["payments", 1],
    ["orphan", 0],
  ]);
});

test("the theme picker applies and remembers the choice", async () => {
  render(
    <MockedProvider mocks={[{ request: { query: ORGS }, result: { data: { orgs: [] } } }]}>
      <App />
    </MockedProvider>,
  );
  const picker = screen.getByRole("combobox", { name: "Theme" });
  expect(picker).toHaveValue("system");
  fireEvent.change(picker, { target: { value: "dark" } });
  expect(document.documentElement.dataset.theme).toBe("dark");
  expect(localStorage.getItem("theme")).toBe("dark");
  fireEvent.change(picker, { target: { value: "system" } });
  expect(document.documentElement.hasAttribute("data-theme")).toBe(false);
});
