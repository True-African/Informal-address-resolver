"""Hugging Face Space interface for the informal address resolver."""

from __future__ import annotations

import gradio as gr

from resolver import resolve


EXAMPLES = [
    "inyuma ya big pharmacy on RN3, red gate",
    "derriere marche de kimironko, portail rouge",
    "hafi ya gare ya nyabugogo",
    "opposite Kimironko Market",
]


def resolve_for_demo(description: str) -> dict:
    """Run the resolver and return the dictionary expected by the challenge."""
    return resolve(description)


demo = gr.Interface(
    fn=resolve_for_demo,
    inputs=gr.Textbox(
        label="Informal address description",
        lines=3,
        placeholder="Example: inyuma ya big pharmacy on RN3, red gate",
    ),
    outputs=gr.JSON(label="Resolver output"),
    examples=EXAMPLES,
    title="T1.2 Informal Address Resolver",
    description=(
        "CPU-only rule-based resolver for informal Kigali-style delivery addresses. "
        "It uses local landmark data, fuzzy matching, direction rules, and confidence scoring."
    ),
)


if __name__ == "__main__":
    demo.launch()
