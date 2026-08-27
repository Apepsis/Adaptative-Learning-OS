import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { StatusBadge } from "@/components/StatusBadge";

describe("StatusBadge", () => {
  it("renders the READY label", () => {
    render(<StatusBadge status="READY" />);
    expect(screen.getByText("READY")).toBeInTheDocument();
  });

  it("renders the FAILED label", () => {
    render(<StatusBadge status="FAILED" />);
    expect(screen.getByText("FAILED")).toBeInTheDocument();
  });
});
