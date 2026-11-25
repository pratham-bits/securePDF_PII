import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "../api/client.js";
import { resetConfigCache } from "../api/config.js";
import { renderWithAuth } from "../test/renderWithAuth.jsx";
import AuthForm from "./AuthForm.jsx";

function renderForm(mode, options) {
  return renderWithAuth(
    <Routes>
      <Route path="/login" element={<AuthForm mode="login" />} />
      <Route path="/register" element={<AuthForm mode="register" />} />
      <Route path="/dashboard" element={<p>dashboard page</p>} />
      <Route path="/documents/:id" element={<p>review page</p>} />
    </Routes>,
    { route: `/${mode}`, ...options },
  );
}

describe("AuthForm (login)", () => {
  it("submits the trimmed email and the password", async () => {
    const login = vi.fn().mockResolvedValue({});
    renderForm("login", { auth: { login } });
    await userEvent.type(screen.getByLabelText("Email"), "  a@example.com ");
    await userEvent.type(
      screen.getByLabelText(/^Password/),
      "correct-horse-battery",
    );
    await userEvent.click(screen.getByRole("button", { name: "Log in" }));
    expect(login).toHaveBeenCalledWith(
      "a@example.com",
      "correct-horse-battery",
    );
  });

  it("shows the server error and lets the user try again", async () => {
    const login = vi
      .fn()
      .mockRejectedValue(new Error("Invalid email or password"));
    renderForm("login", { auth: { login } });
    await userEvent.type(screen.getByLabelText("Email"), "a@example.com");
    await userEvent.type(
      screen.getByLabelText(/^Password/),
      "wrong-password-here",
    );
    await userEvent.click(screen.getByRole("button", { name: "Log in" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Invalid email or password",
    );
    expect(screen.getByRole("button", { name: "Log in" })).toBeEnabled();
  });

  it("sends an already logged-in user to the dashboard", () => {
    renderForm("login", { auth: { user: { id: 1, email: "a@example.com" } } });
    expect(screen.getByText("dashboard page")).toBeInTheDocument();
  });

  it("returns a user to the page they were headed for", () => {
    renderForm("login", {
      route: { pathname: "/login", state: { from: "/documents/abc" } },
      auth: { user: { id: 1, email: "a@example.com" } },
    });
    expect(screen.getByText("review page")).toBeInTheDocument();
  });

  it("shows the password only when asked", async () => {
    renderForm("login");
    const password = screen.getByLabelText(/^Password/);
    expect(password).toHaveAttribute("type", "password");
    await userEvent.click(screen.getByLabelText("Show password"));
    expect(password).toHaveAttribute("type", "text");
  });
});

describe("AuthForm (register)", () => {
  it("refuses mismatched passwords without calling the server", async () => {
    const register = vi.fn();
    renderForm("register", { auth: { register } });
    await userEvent.type(screen.getByLabelText("Email"), "a@example.com");
    await userEvent.type(
      screen.getByLabelText(/^Password/),
      "correct-horse-battery",
    );
    await userEvent.type(
      screen.getByLabelText("Confirm password"),
      "something-else-entirely",
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Create account" }),
    );
    expect(await screen.findByRole("alert")).toHaveTextContent("do not match");
    await waitFor(() => expect(register).not.toHaveBeenCalled());
  });

  it("registers when the passwords match", async () => {
    const register = vi.fn().mockResolvedValue({});
    renderForm("register", { auth: { register } });
    await userEvent.type(screen.getByLabelText("Email"), "a@example.com");
    await userEvent.type(
      screen.getByLabelText(/^Password/),
      "correct-horse-battery",
    );
    await userEvent.type(
      screen.getByLabelText("Confirm password"),
      "correct-horse-battery",
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Create account" }),
    );
    expect(register).toHaveBeenCalledWith(
      "a@example.com",
      "correct-horse-battery",
    );
  });
});


describe("AuthForm (invite code)", () => {
  beforeEach(() => {
    resetConfigCache();
    vi.restoreAllMocks();
  });

  async function fillRegister() {
    await userEvent.type(screen.getByLabelText("Email"), "a@example.com");
    await userEvent.type(
      screen.getByLabelText(/^Password/),
      "correct-horse-battery",
    );
    await userEvent.type(
      screen.getByLabelText("Confirm password"),
      "correct-horse-battery",
    );
  }

  it("asks for the invite code when the server requires one", async () => {
    vi.spyOn(api, "get").mockResolvedValue({ invite_required: true });
    const register = vi.fn().mockResolvedValue({});
    renderForm("register", { auth: { register } });
    const field = await screen.findByLabelText(/^Invite code/);
    await fillRegister();
    await userEvent.type(field, " tester-2026 ");
    await userEvent.click(screen.getByRole("button", { name: "Create account" }));
    expect(register).toHaveBeenCalledWith(
      "a@example.com",
      "correct-horse-battery",
      "tester-2026",
    );
  });

  it("hides the field when registration is open", async () => {
    const get = vi.spyOn(api, "get").mockResolvedValue({ invite_required: false });
    renderForm("register");
    await waitFor(() => expect(get).toHaveBeenCalled());
    expect(screen.queryByLabelText(/^Invite code/)).not.toBeInTheDocument();
  });

  it("never shows the field on the login form", async () => {
    vi.spyOn(api, "get").mockResolvedValue({ invite_required: true });
    renderForm("login");
    await waitFor(() => expect(api.get).toHaveBeenCalled());
    expect(screen.queryByLabelText(/^Invite code/)).not.toBeInTheDocument();
  });

  it("shows the server message when a code is wrong or attempts are throttled", async () => {
    vi.spyOn(api, "get").mockResolvedValue({ invite_required: true });
    const register = vi.fn().mockRejectedValue(new Error("Invalid invite code"));
    renderForm("register", { auth: { register } });
    await userEvent.type(await screen.findByLabelText(/^Invite code/), "nope");
    await fillRegister();
    await userEvent.click(screen.getByRole("button", { name: "Create account" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Invalid invite code");
  });
});
