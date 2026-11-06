import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { AuthContext } from "../auth/AuthContext.js";

const NOT_LOGGED_IN = { user: null, loading: false };

// Renders a component inside a router and a fake auth context.
// `auth` overrides user, loading, login, register and logout.
export function renderWithAuth(ui, { route = "/", auth = {} } = {}) {
  const value = {
    ...NOT_LOGGED_IN,
    login: async () => {},
    register: async () => {},
    logout: async () => {},
    ...auth,
  };
  const entry = typeof route === "string" ? { pathname: route } : route;
  return render(
    <AuthContext.Provider value={value}>
      <MemoryRouter initialEntries={[entry]}>{ui}</MemoryRouter>
    </AuthContext.Provider>,
  );
}
