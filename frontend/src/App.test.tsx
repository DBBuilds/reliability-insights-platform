import { orgTree } from "./App";

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
