import { setTheme, storedTheme } from "./theme";

afterEach(() => {
  vi.restoreAllMocks();
  localStorage.clear();
  document.documentElement.removeAttribute("data-theme");
});

test("a choice is applied to the page and remembered; system clears both", () => {
  setTheme("dark");
  expect(document.documentElement.dataset.theme).toBe("dark");
  expect(storedTheme()).toBe("dark");
  setTheme("system");
  expect(document.documentElement.hasAttribute("data-theme")).toBe(false);
  expect(localStorage.getItem("theme")).toBeNull();
  expect(storedTheme()).toBe("system");
});

test("an unknown stored value means system", () => {
  localStorage.setItem("theme", "sepia");
  expect(storedTheme()).toBe("system");
});

test("blocked storage still applies the theme and reads as system", () => {
  vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
    throw new Error("blocked");
  });
  vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
    throw new Error("blocked");
  });
  expect(storedTheme()).toBe("system");
  setTheme("light");
  expect(document.documentElement.dataset.theme).toBe("light");
});
