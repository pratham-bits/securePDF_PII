import { screen } from "@testing-library/react";
import { Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { renderWithAuth } from "../test/renderWithAuth.jsx";
import Layout from "./Layout.jsx";

function renderLayout(auth) {
  return renderWithAuth(
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<p>home page</p>} />
      </Route>
    </Routes>,
    { auth },
  );
}

describe("Layout navigation", () => {
  it("offers Dashboard and Profile, but no Log out, to a logged-in user", () => {
    renderLayout({ user: { id: 1, email: "a@example.com" } });
    expect(screen.getByRole("link", { name: "Dashboard" })).toHaveAttribute(
      "href",
      "/dashboard",
    );
    expect(screen.getByRole("link", { name: "Profile" })).toHaveAttribute(
      "href",
      "/profile",
    );
    expect(
      screen.queryByRole("button", { name: "Log out" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("link", { name: "Log in" }),
    ).not.toBeInTheDocument();
  });

  it("offers only Log in and Get started to a visitor", () => {
    renderLayout({ user: null });
    expect(screen.getByRole("link", { name: "Log in" })).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Get started" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("link", { name: "Profile" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("link", { name: "Dashboard" }),
    ).not.toBeInTheDocument();
  });

  it("links to the information pages for everyone", () => {
    renderLayout({ user: null });
    expect(
      screen.getByRole("link", { name: "Why PII matters" }),
    ).toHaveAttribute("href", "/why-pii");
    expect(
      screen.getByRole("link", { name: "How we handle your data" }),
    ).toHaveAttribute("href", "/privacy");
  });
});
