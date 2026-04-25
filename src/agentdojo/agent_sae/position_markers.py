from __future__ import annotations

from collections.abc import Sequence

from agentdojo.types import ChatMessage, get_text_content_as_str


def _message_text(message: ChatMessage) -> str:
    content = message.get("content")
    if content is None:
        return ""
    return get_text_content_as_str(content)


def mark_positions(messages: Sequence[ChatMessage], high_risk_tool_names: set[str], decision_window_tokens: int = 64) -> dict:
    message_offsets: list[dict] = []
    cursor = 0
    attack_exposure = None
    high_risk_positions: list[dict] = []

    for idx, message in enumerate(messages):
        text = _message_text(message)
        start = cursor
        end = start + len(text)
        cursor = end + 1
        entry = {
            "message_index": idx,
            "role": message["role"],
            "content": text,
            "char_start": start,
            "char_end": end,
            "token_start": None,
            "token_end": None,
        }
        message_offsets.append(entry)

        if message["role"] == "tool" and attack_exposure is None:
            lowered = text.lower()
            if any(token in lowered for token in ["injection", "override", "attacker@"]):
                attack_exposure = {
                    "message_index": idx,
                    "attack_exposure_start_token": None,
                    "attack_exposure_end_token": None,
                    "attack_exposure_start_char": start,
                    "attack_exposure_end_char": end,
                }

        if message["role"] == "assistant":
            for tool_call in message.get("tool_calls") or []:
                if tool_call.function in high_risk_tool_names:
                    high_risk_positions.append(
                        {
                            "message_index": idx,
                            "tool_name": tool_call.function,
                            "tool_call_start_token": None,
                            "tool_call_end_token": None,
                            "tool_call_start_char": start,
                            "tool_call_end_char": end,
                            "decision_window_tokens": decision_window_tokens,
                            "decision_window_start_token": None,
                            "decision_window_end_token": None,
                            "decision_window_start_char": max(0, start - decision_window_tokens),
                            "decision_window_end_char": start,
                        }
                    )

    final_decision = None
    for idx in range(len(messages) - 1, -1, -1):
        if messages[idx]["role"] == "assistant":
            offset = message_offsets[idx]
            final_decision = {
                "message_index": idx,
                "final_decision_start_token": None,
                "final_decision_end_token": None,
                "final_decision_start_char": offset["char_start"],
                "final_decision_end_char": offset["char_end"],
            }
            break

    return {
        "messages": message_offsets,
        "attack_exposure": attack_exposure,
        "high_risk_tool_calls": high_risk_positions,
        "final_decision": final_decision,
    }
