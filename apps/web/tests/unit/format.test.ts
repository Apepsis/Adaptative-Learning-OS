import { describe, expect, it } from "vitest";
import { formatBytes } from "@/lib/format";

describe("formatBytes", () => {
  it("renders small sizes in bytes", () => {
    expect(formatBytes(512)).toBe("512 B");
  });

  it("renders mid sizes in kilobytes", () => {
    expect(formatBytes(2048)).toBe("2 KB");
  });

  it("renders large sizes in megabytes", () => {
    expect(formatBytes(5 * 1024 * 1024)).toBe("5.0 MB");
  });
});
