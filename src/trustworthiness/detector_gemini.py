"""
Trustworthiness Detector for LLM outputs using Google's Gemini API directly.
Implements self-reflection certainty from BSDetector paper
"""

import random
import re
import time
from typing import Any, Dict, List, Optional

import requests

from . import settings
from .prompts import REFLECTION_PROMPTS as DEFAULT_REFLECTION_PROMPTS


class TrustworthinessDetector:
    """
    Detects trustworthiness of LLM answers using self-reflection certainty.

    Based on "Quantifying Uncertainty in Answers from any Language Model
    and Enhancing their Trustworthiness" (Chen & Mueller, ACL'24)
    """

    # Default reflection prompts from the paper (Figure 6b)
    DEFAULT_REFLECTION_PROMPTS = DEFAULT_REFLECTION_PROMPTS

    def __init__(
        self,
        model: Optional[str] = None,
        reflection_prompts: Optional[List[str]] = None,
        temperature: float = 0.0,
        cache_responses: bool = True,
    ) -> None:
        """
        Initialize the trustworthiness detector.

        Args:
            model: LLM model to use (currently only Gemini is supported)
            reflection_prompts: Custom reflection prompts (uses defaults if None)
            temperature: Temperature for LLM responses (0 for deterministic)
            cache_responses: Whether to cache reflection responses
        """
        self.model = model or settings.DEFAULT_MODEL
        self.reflection_prompts = reflection_prompts or self.DEFAULT_REFLECTION_PROMPTS
        self.temperature = temperature
        self.cache_responses = cache_responses
        self._cache: Optional[Dict[str, Any]] = {} if cache_responses else None

    def evaluate_trustworthiness_batch(
        self,
        questions: List[str],
        answers: List[str],
    ) -> List[float]:
        """
        Evaluate the trustworthiness of multiple question-answer pairs in a batch.

        Args:
            questions: List of questions
            answers: List of answers corresponding to the questions

        Returns:
            List of trustworthiness scores (0-1) for each Q&A pair

        Raises:
            ValueError: If the number of questions and answers don't match
        """
        if len(questions) != len(answers):
            raise ValueError(
                f"Number of questions ({len(questions)}) does not match "
                f"number of answers ({len(answers)})"
            )

        if not questions:
            return []

        return [
            self.get_trustworthiness_score(q, a) for q, a in zip(questions, answers)
        ]

    def get_trustworthiness_score(self, question: str, answer: str) -> float:
        """
        Calculate trustworthiness score for a question-answer pair.

        Args:
            question: The original question
            answer: The answer to evaluate

        Returns:
            Trustworthiness score between 0 and 1
        """
        reflection_scores = self._get_self_reflection_scores(question, answer)
        return sum(reflection_scores) / len(reflection_scores)

    def _get_self_reflection_scores(self, question: str, answer: str) -> List[float]:
        """Get scores from multiple self-reflection prompts."""
        scores: List[float] = []

        for i, prompt_template in enumerate(self.reflection_prompts):
            # Format the prompt
            prompt = prompt_template.format(question=question, answer=answer)

            # Check cache if enabled
            cache_key = f"{question}|{answer}|{i}"
            if (
                self.cache_responses
                and self._cache is not None
                and cache_key in self._cache
            ):
                score = self._cache[cache_key]
            else:
                # Query LLM and get response
                response = self._query_llm(prompt)
                # Parse response to get score
                score = self._parse_reflection_response(response)
                # Cache the result if enabled
                if self.cache_responses and self._cache is not None:
                    self._cache[cache_key] = score

            scores.append(score)

        return scores

    def _query_llm(self, prompt: str) -> str:
        """Query the Gemini API with error handling and retries.

        Args:
            prompt: The prompt to send to the LLM

        Returns:
            str: The response from the LLM, or a default response if all retries fail

        Raises:
            Exception: If the API request fails after all retries
        """
        for attempt in range(settings.RATE_LIMIT_MAX_RETRIES):
            try:
                response = requests.post(
                    f"{settings.GEMINI_API_URL}?key={settings.GEMINI_API_KEY}",
                    json={
                        "contents": [{"parts": [{"text": prompt}]}],
                        "generationConfig": {
                            "temperature": self.temperature,
                            "maxOutputTokens": 1024,
                        },
                    },
                    timeout=30,
                )

                if response.status_code != 200:
                    error_msg = (
                        f"API request failed with status {response.status_code}: "
                        f"{response.text}"
                    )
                    raise ValueError(error_msg)

                data = response.json()
                if not data.get("candidates"):
                    raise ValueError("No candidates in API response")

                # Safely access the response text with proper error handling
                try:
                    return str(data["candidates"][0]["content"]["parts"][0]["text"])
                except (KeyError, IndexError) as e:
                    raise ValueError(f"Unexpected API response format: {str(e)}") from e

            except Exception as e:
                if attempt == settings.RATE_LIMIT_MAX_RETRIES - 1:  # Last attempt
                    error_msg = (
                        f"Error: LLM query failed after {settings.RATE_LIMIT_MAX_RETRIES} attempts: "
                        f"{str(e)}"
                    )
                    print(error_msg)
                    return "answer: [C]"  # Default to uncertain if all retries fail

                # Exponential backoff with jitter
                time.sleep(
                    (2**attempt)
                    * (1 + settings.RATE_LIMIT_JITTER * (random.random() - 0.5))
                )

        # This should never be reached due to the return in the except block.
        # It's here for type checking purposes.
        return "answer: [C]"  # Default to uncertain

    def _parse_reflection_response(self, response: str) -> float:
        """
        Parse LLM response to extract choice and convert to score.
        Handles various response formats flexibly.

        Returns:
            1.0 for (A) Correct
            0.0 for (B) Incorrect
            0.5 for (C) I am not sure or parsing failure
        """
        if not response or not isinstance(response, str):
            print("Warning: Empty or invalid response from LLM")
            return 0.5

        # Normalize response to handle different formats
        response = response.strip().upper()

        # Try multiple patterns in order of specificity
        patterns = [
            # Pattern 1: "answer: [A]" or "answer: A" (most specific)
            r"answer\s*:?\s*[\[\(]?([ABC])[\]\)]?",
            # Pattern 2: "[A]" or "(A)" in the response
            r"[\[\(]([ABC])[\]\)]",
            # Pattern 3: Standalone A/B/C
            r"^\s*([ABC])\s*$",
            # Pattern 4: "The answer is A" or similar
            r"(?:answer|choice|select(?:ion)?|option)\s*(?:is|:)?\s*[\[\(]?([ABC])[\]\)]?",
            # Pattern 5: Contains words like "correct", "incorrect", "unsure"
            (r"(correct|right|yes|true)", "A"),
            (r"(incorrect|wrong|no|false)", "B"),
            (r"(unsure|uncertain|maybe|not sure|don\'?t know)", "C"),
        ]

        for pattern in patterns:
            if isinstance(pattern, tuple):
                pattern, choice = pattern
                if re.search(pattern, response, re.IGNORECASE):
                    return {"A": 1.0, "B": 0.0, "C": 0.5}.get(choice, 0.5)
            else:
                match = re.search(pattern, response, re.IGNORECASE)
                if match:
                    choice = (
                        match.group(1) if len(match.groups()) > 0 else match.group(0)
                    )
                    return {"A": 1.0, "B": 0.0, "C": 0.5}.get(choice.upper(), 0.5)

        # If no pattern matches, try to infer from the content
        if any(word in response for word in ["CORRECT", "RIGHT", "YES", "TRUE"]):
            return 1.0
        elif any(word in response for word in ["INCORRECT", "WRONG", "NO", "FALSE"]):
            return 0.0
        elif any(
            word in response for word in ["UNSURE", "UNCERTAIN", "MAYBE", "NOT SURE"]
        ):
            return 0.5

        # Default to uncertain if we can't determine the answer
        return 0.5

    def batch_evaluate(
        self, questions: List[str], answers: List[str], show_progress: bool = True
    ) -> List[float]:
        """
        Evaluate multiple question-answer pairs.

        Args:
            questions: List of questions
            answers: List of answers (must be same length as questions)
            show_progress: Whether to show progress

        Returns:
            List of trustworthiness scores

        Raises:
            ValueError: If questions and answers have different lengths
        """
        if len(questions) != len(answers):
            raise ValueError("Questions and answers must have the same length")

        scores = []

        for i, (question, answer) in enumerate(zip(questions, answers)):
            if show_progress:
                print(f"Evaluating {i+1}/{len(questions)}...", end="\r")

            score = self.get_trustworthiness_score(question, answer)
            scores.append(score)

        if show_progress and len(questions) > 0:
            print(f"Evaluated {len(questions)} Q&A pairs.    ")

        return scores

    def clear_cache(self) -> None:
        """Clear the response cache."""
        if self._cache is not None:
            self._cache.clear()


def evaluate_trustworthiness(
    question: str, answer: str, model: Optional[str] = None
) -> float:
    """
    Quick function to evaluate a single Q&A pair.

    Args:
        question: The question
        answer: The answer to evaluate
        model: LLM model to use (if None, uses DEFAULT_MODEL from config)

    Returns:
        Trustworthiness score between 0 and 1
    """
    detector = TrustworthinessDetector(model=model)
    return detector.get_trustworthiness_score(question, answer)
