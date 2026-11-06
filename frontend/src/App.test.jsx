import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import App from "./App.jsx";
import { renderWithAuth } from "./test/renderWithAuth.jsx";

describe("App routing", () => {
  it.each(["/dashboard", "/documents/abc"])(
    "sends a logged-out visitor from %s to the login page",
    (route) => {
      renderWithAuth(<App />, { route });
      expect(
        screen.getByRole("heading", { name: "Log in" }),
      ).toBeInTheDocument();
    },
  );

  it("keeps the home page public", () => {
    renderWithAuth(<App />, { route: "/" });
    expect(
      screen.queryByRole("heading", { name: "Log in" }),
    ).not.toBeInTheDocument();
  });
});
