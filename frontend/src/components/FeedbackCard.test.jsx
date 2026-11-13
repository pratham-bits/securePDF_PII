import { screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { renderWithAuth } from "../test/renderWithAuth.jsx";
import FeedbackCard from "./FeedbackCard.jsx";

const USER = { id: 1, email: "a@example.com" };
const FORM = "https://forms.gle/abc123";

afterEach(() => vi.unstubAllEnvs());

describe("FeedbackCard", () => {
  it("shows a feedback link and the reason for it to a logged-in user", () => {
    renderWithAuth(<FeedbackCard url={FORM} />, { auth: { user: USER } });
    const link = screen.getByRole("link", { name: /give feedback/i });
    expect(link).toHaveAttribute("href", FORM);
    expect(link).toHaveAttribute("target", "_blank");
    expect(link.getAttribute("rel")).toContain("noopener");
    expect(screen.getByText(/gets better from what you tell us/i)).toBeInTheDocument();
    expect(screen.getByText(/do not include personal details/i)).toBeInTheDocument();
  });

  it("is not shown to someone who is logged out", () => {
    renderWithAuth(<FeedbackCard url={FORM} />);
    expect(screen.queryByRole("link", { name: /give feedback/i })).not.toBeInTheDocument();
  });

  it.each([
    ["no address", undefined],
    ["an empty address", ""],
    ["an http address", "http://forms.gle/abc123"],
    ["a script address", "javascript:alert(1)"],
    ["text that is not an address", "not a url"],
  ])("shows nothing when the form has %s", (_name, url) => {
    vi.stubEnv("VITE_FEEDBACK_FORM_URL", "");
    renderWithAuth(<FeedbackCard url={url} />, { auth: { user: USER } });
    expect(screen.queryByRole("complementary")).not.toBeInTheDocument();
  });

  it("reads the address from VITE_FEEDBACK_FORM_URL when none is passed", () => {
    vi.stubEnv("VITE_FEEDBACK_FORM_URL", FORM);
    renderWithAuth(<FeedbackCard />, { auth: { user: USER } });
    expect(screen.getByRole("link", { name: /give feedback/i })).toHaveAttribute("href", FORM);
  });
});
