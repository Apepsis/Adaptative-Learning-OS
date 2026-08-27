import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { StatusBadge } from "@/components/StatusBadge";

describe("StatusBadge", () => {
  it("renders the QUEUED label", () => {
    render(<StatusBadge status="QUEUED" />);
    expect(screen.getByText("QUEUED")).toBeInTheDocument();
  });

  it("renders the FAILED label", () => {
    render(<StatusBadge status="FAILED" />);
    expect(screen.getByText("FAILED")).toBeInTheDocument();
  });
});
