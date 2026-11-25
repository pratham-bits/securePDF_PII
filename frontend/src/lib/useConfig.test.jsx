import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "../api/client.js";
import { resetConfigCache } from "../api/config.js";
import { describeRetention, useConfig } from "./useConfig.js";

function Probe() {
  const config = useConfig();
  return <p>{`${config.retention_hours}|${config.max_pages}|${config.invite_required}`}</p>;
}

beforeEach(() => {
  resetConfigCache();
  vi.restoreAllMocks();
});

describe("useConfig", () => {
  it("shows the limits published by the server", async () => {
    vi.spyOn(api, "get").mockResolvedValue({
      retention_hours: 2,
      max_upload_mb: 10,
      max_pages: 15,
      invite_required: true,
    });
    render(<Probe />);
    expect(await screen.findByText("2|15|true")).toBeInTheDocument();
  });

  it("falls back to safe defaults when the server cannot be reached", async () => {
    const get = vi.spyOn(api, "get").mockRejectedValue(new Error("down"));
    render(<Probe />);
    await waitFor(() => expect(get).toHaveBeenCalled());
    expect(screen.getByText("null|30|false")).toBeInTheDocument();
  });

  it("asks the server only once", async () => {
    const get = vi.spyOn(api, "get").mockResolvedValue({ retention_hours: 2 });
    const { unmount } = render(<Probe />);
    await screen.findByText(/^2\|/);
    unmount();
    render(<Probe />);
    await screen.findByText(/^2\|/);
    expect(get).toHaveBeenCalledTimes(1);
  });
});

describe("describeRetention", () => {
  it("words the retention time for people", () => {
    expect(describeRetention(1)).toBe("1 hour");
    expect(describeRetention(2)).toBe("2 hours");
    expect(describeRetention(null)).toBe("a short time");
  });
});
