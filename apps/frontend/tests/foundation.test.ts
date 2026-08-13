import { describe, expect, it } from "vitest";

import { buildHealthMessage, getFrontendFoundationHealth } from "../src/foundation";

describe("frontend foundation", () => {
  it("consumes the shared health contract", () => {
    const health = getFrontendFoundationHealth();

    expect(health.service).toBe("opspilot-backend");
    expect(buildHealthMessage(health)).toBe("opspilot-backend 1.2.1 is ok");
  });
});
