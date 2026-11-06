import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import App from "./App.jsx";
import { renderWithAuth } from "./test/renderWithAuth.jsx";

describe("App routing", () => {
  it.each(["/dashboard", "/profile", "/documents/abc"])(
    "sends a logged-out visitor from %s to the login page",
    (route) => {
      renderWithAuth(<App />, { route });
      expect(
        screen.getByRole("heading", { name: "Log in" }),
      ).toBeInTheDocument();
    },
  );
  it("shows a logged-in user their profile", () => {
    renderWithAuth(<App />, {
      route: "/profile",
      auth: { user: { id: 1, email: "a@example.com" } },
    });
    expect(
      screen.getByRole("heading", { name: "Your profile" }),
    ).toBeInTheDocument();
    expect(screen.getByText("a@example.com")).toBeInTheDocument();
  });

  it("keeps the home page public", () => {
    renderWithAuth(<App />, { route: "/" });
    expect(
      screen.queryByRole("heading", { name: "Log in" }),
    ).not.toBeInTheDocument();
  });
});
