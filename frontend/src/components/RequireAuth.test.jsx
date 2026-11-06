import { screen } from "@testing-library/react";
import { Route, Routes, useLocation } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { renderWithAuth } from "../test/renderWithAuth.jsx";
import RequireAuth from "./RequireAuth.jsx";

function LoginProbe() {
  const location = useLocation();
  return <p>login page, from: {location.state?.from}</p>;
}

function renderGuarded(auth) {
  return renderWithAuth(
    <Routes>
      <Route path="/login" element={<LoginProbe />} />
      <Route element={<RequireAuth />}>
        <Route path="/secret" element={<p>secret content</p>} />
      </Route>
    </Routes>,
    { route: "/secret", auth },
  );
}

describe("RequireAuth", () => {
  it("shows a placeholder, not the page, while the session is being checked", () => {
    renderGuarded({ user: null, loading: true });
    expect(screen.getByText("Loading…")).toBeInTheDocument();
    expect(screen.queryByText("secret content")).not.toBeInTheDocument();
  });

  it("sends a logged-out visitor to the login page and remembers where they were going", () => {
    renderGuarded({ user: null });
    expect(screen.getByText("login page, from: /secret")).toBeInTheDocument();
    expect(screen.queryByText("secret content")).not.toBeInTheDocument();
  });

  it("shows the page to a logged-in user", () => {
    renderGuarded({ user: { id: 1, email: "a@example.com" } });
    expect(screen.getByText("secret content")).toBeInTheDocument();
  });
});
