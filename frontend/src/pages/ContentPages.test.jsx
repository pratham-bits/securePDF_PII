import { screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "../api/client.js";
import { resetConfigCache } from "../api/config.js";
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


describe("Privacy page retention", () => {
  beforeEach(() => {
    resetConfigCache();
    vi.restoreAllMocks();
  });

  it("states the retention time the server actually uses", async () => {
    vi.spyOn(api, "get").mockResolvedValue({ retention_hours: 2 });
    renderWithAuth(<App />, { route: "/privacy" });
    expect(
      await screen.findByText(/deleted automatically after 2 hours/),
    ).toBeInTheDocument();
  });

  it("does not guess a number when the server cannot be reached", async () => {
    vi.spyOn(api, "get").mockRejectedValue(new Error("down"));
    renderWithAuth(<App />, { route: "/privacy" });
    expect(
      await screen.findByText(/deleted automatically after a short time/),
    ).toBeInTheDocument();
  });
});
