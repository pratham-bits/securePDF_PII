import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import App from "../App.jsx";
import { renderWithAuth } from "../test/renderWithAuth.jsx";

const PAGES = [
  ["/why-pii", "Why personal information matters"],
  ["/privacy", "How we handle your data"],
];

describe("Content pages", () => {
  it.each(PAGES)("%s is public and shows its heading", (route, heading) => {
    renderWithAuth(<App />, { route });
    expect(
      screen.getByRole("heading", { level: 1, name: heading }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { name: "Log in" }),
    ).not.toBeInTheDocument();
  });

  it.each(PAGES)("%s also opens for a logged-in user", (route, heading) => {
    renderWithAuth(<App />, {
      route,
      auth: { user: { id: 1, email: "a@example.com" } },
    });
    expect(
      screen.getByRole("heading", { level: 1, name: heading }),
    ).toBeInTheDocument();
  });

  it("the privacy page is honest about what is not detected yet", () => {
    renderWithAuth(<App />, { route: "/privacy" });
    expect(
      screen.getByRole("heading", { name: "What SecurePDF cannot promise" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Names and addresses are not found/),
    ).toBeInTheDocument();
  });

  it("each page links to the other", () => {
    renderWithAuth(<App />, { route: "/why-pii" });
    expect(
      screen.getAllByRole("link", { name: "how we handle your data" })[0],
    ).toHaveAttribute("href", "/privacy");
  });
});
