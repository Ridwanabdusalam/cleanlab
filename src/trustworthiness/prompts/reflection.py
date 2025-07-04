"""
Reflection prompts for self-reflection certainty.

These prompts are used to evaluate the trustworthiness of LLM outputs
by asking the model to reflect on its own answers.
"""

# Default reflection prompts from the BSDetector paper (Figure 6b)
REFLECTION_PROMPTS = [
    """Question: {question}
Proposed Answer: {answer}
Is the proposed answer: (A) Correct (B) Incorrect (C) I am not sure.
The output should strictly use the following template:
explanation: [insert analysis], answer: [A/B/C]""",
    """Question: {question}
Proposed Answer: {answer}
Are you really sure the proposed answer is correct?
Choose again: (A) Correct (B) Incorrect (C) I am not sure.
The output should strictly use the following template:
explanation: [insert analysis], answer: [A/B/C]""",
]
