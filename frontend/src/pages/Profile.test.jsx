import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { renderWithAuth } from "../test/renderWithAuth.jsx";
import Profile from "./Profile.jsx";

const USER = { id: 1, email: "a@example.com" };

function renderProfile(auth) {
  return renderWithAuth(
    <Routes>
      <Route path="/" element={<p>home page</p>} />
      <Route path="/profile" element={<Profile />} />
    </Routes>,
    { route: "/profile", auth: { user: USER, ...auth } },
  );
}

describe("Profile", () => {
  it("shows the registered email", () => {
    renderProfile();
    expect(
      screen.getByRole("heading", { name: "Your profile" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Email")).toBeInTheDocument();
    expect(screen.getByText("a@example.com")).toBeInTheDocument();
  });

  it("logs out and returns to the home page", async () => {
    const logout = vi.fn().mockResolvedValue(undefined);
    renderProfile({ logout });
    await userEvent.click(screen.getByRole("button", { name: "Log out" }));
    expect(logout).toHaveBeenCalledTimes(1);
    expect(await screen.findByText("home page")).toBeInTheDocument();
  });
});
