import { describe, it, expect, vi, afterEach } from "vitest";
import { screen, fireEvent, waitFor } from "@testing-library/react";
import { renderWithProviders } from "@/test/common_setup";
import {
  AgentCommunicationCard,
  type AgentCommunicationSubmitPayload,
} from "./index";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (_k: string, fallback?: string) => fallback ?? _k }),
}));

describe("AgentCommunicationCard", () => {
  afterEach(() => vi.clearAllMocks());

  it("renders the agent name and message", () => {
    renderWithProviders(
      <AgentCommunicationCard
        agentName="Researcher"
        message="Hello user, what do you want to do?"
        kind="info"
      />,
    );
    expect(screen.getByText("Researcher")).toBeInTheDocument();
    expect(
      screen.getByText("Hello user, what do you want to do?"),
    ).toBeInTheDocument();
  });

  it("calls onSubmit with text payload when send is clicked", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    renderWithProviders(
      <AgentCommunicationCard
        agentName="Researcher"
        message="Reply please"
        kind="text"
        onSubmit={onSubmit}
      />,
    );

    const textarea = screen.getByRole("textbox");
    fireEvent.change(textarea, { target: { value: "  ok then  " } });
    fireEvent.click(screen.getByRole("button", { name: /Send/i }));

    await waitFor(() => expect(onSubmit).toHaveBeenCalledTimes(1));
    const payload = onSubmit.mock.calls[0][0] as AgentCommunicationSubmitPayload;
    expect(payload.kind).toBe("text");
    expect(payload.text).toBe("ok then");
  });

  it("renders confirm choices and emits the right value", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    renderWithProviders(
      <AgentCommunicationCard
        agentName="Reviewer"
        message="Approve change?"
        kind="confirm"
        onSubmit={onSubmit}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /Yes/i }));
    await waitFor(() => expect(onSubmit).toHaveBeenCalledTimes(1));
    expect(onSubmit.mock.calls[0][0]).toEqual({ kind: "confirm", value: "yes" });
  });

  it("renders custom choices and emits the chosen value", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    renderWithProviders(
      <AgentCommunicationCard
        agentName="Planner"
        message="Pick one"
        kind="choices"
        choices={[
          { value: "a", label: "Option A" },
          { value: "b", label: "Option B", type: "primary" },
        ]}
        onSubmit={onSubmit}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /Option B/i }));
    await waitFor(() => expect(onSubmit).toHaveBeenCalledTimes(1));
    expect(onSubmit.mock.calls[0][0]).toEqual({ kind: "choices", value: "b" });
  });

  it("does not render send button in info kind", () => {
    renderWithProviders(
      <AgentCommunicationCard
        agentName="Notifier"
        message="Read-only message"
        kind="info"
      />,
    );
    expect(screen.queryByRole("button", { name: /Send/i })).toBeNull();
  });

  it("disables Send when required and empty", () => {
    renderWithProviders(
      <AgentCommunicationCard
        agentName="Researcher"
        message="Need input"
        kind="text"
        required
        onSubmit={vi.fn()}
      />,
    );
    expect(screen.getByRole("button", { name: /Send/i })).toBeDisabled();
  });
});
