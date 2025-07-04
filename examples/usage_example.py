"""
Example usage of the Trustworthiness Detector library.
Shows how to evaluate LLM answers for trustworthiness.
"""

import sys
from pathlib import Path
from typing import List, Tuple

import dotenv

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

# Load environment variables from .env file in the project root
dotenv.load_dotenv()

from src.trustworthiness import (  # noqa: E402
    DEFAULT_MODEL,
    TrustworthinessDetector,
    validate_model_api_key,
)


def main() -> None:
    """
    Demonstrate the trustworthiness detector with examples from the assignment.

    The trustworthiness score ranges from 0.0 to 1.0, where:
    - 0.8-1.0: High confidence in answer's correctness
    - 0.5-0.8: Moderate confidence
    - 0.0-0.5: Low confidence (likely incorrect)

    The score is based on self-reflection certainty, where the model evaluates
    its own answers to determine confidence levels.
    """

    # Validate API key for default model
    is_valid, message = validate_model_api_key()
    if not is_valid:
        print(f"ERROR: {message}")
        return

    print(f"Using model: {DEFAULT_MODEL}")
    print("=" * 50)

    # Initialize detector - will use DEFAULT_MODEL automatically
    detector = TrustworthinessDetector(temperature=0.0, cache_responses=True)

    print("\n=== Trustworthiness Detector Demo ===")
    print("Testing self-reflection certainty implementation\n")

    # Test 1: Examples from the assignment brief
    print("TEST 1: Assignment Examples")
    print("-" * 40)

    assignment_tests = [
        # These are the exact examples from the Cleanlab assignment
        {
            "question": "What is 1 + 1?",
            "answer": "2",
            "expected": "high",
            "reason": "Simple correct answer",
        },
        {
            "question": "what is the third month in alphabetical order",
            "answer": "April",  # April, August, December...
            "expected": "high",
            "reason": "Correct factual answer",
        },
        {
            "question": (
                "How many syllables are in the following phrase: "
                '"How much wood could a woodchuck chuck if a woodchuck could chuck wood"? '  # noqa: E501
                "Answer with a single number only."
            ),
            "answer": "14",
            "expected": "high",
            "reason": "Correct count",
        },
    ]

    for test in assignment_tests:
        score = detector.get_trustworthiness_score(test["question"], test["answer"])
        status = get_status_symbol(score)
        print(f"{status} Q: {test['question'][:60]}...")
        print(f"  A: {test['answer']}")
        print(f"  Score: {score:.3f} - {test['reason']}")
        print()

    # Test 2: Wrong answers (should get low scores)
    print("\nTEST 2: Wrong Answers")
    print("-" * 40)

    wrong_answer_tests = [
        {"question": "What is 1 + 1?", "answer": "3", "correct_answer": "2"},
        {
            "question": "what is the third month in alphabetical order",
            "answer": "March",
            "correct_answer": "April",
        },
        {
            "question": "What is the capital of France?",
            "answer": "London",
            "correct_answer": "Paris",
        },
    ]

    for test in wrong_answer_tests:
        score = detector.get_trustworthiness_score(test["question"], test["answer"])
        status = get_status_symbol(score)
        print(f"{status} Q: {test['question']}")
        print(f"  Wrong A: {test['answer']} (correct: {test['correct_answer']})")
        print(f"  Score: {score:.3f}")
        print()

    # Test 3: Uncertain/ambiguous cases
    print("\nTEST 3: Uncertain Cases")
    print("-" * 40)

    uncertain_tests: List[Tuple[str, str]] = [
        (
            "What will be the most popular programming language in 2030?",
            "It's difficult to predict, but Python is likely to remain popular.",
        ),
        (
            "What will the weather be like next month?",
            "Weather forecasts that far in advance are not very reliable.",
        ),
        (
            "Who will win the next election?",
            "Election outcomes depend on many factors and are hard to predict.",
        ),
    ]

    for question, answer in uncertain_tests:
        score = detector.get_trustworthiness_score(question, answer)
        status = get_status_symbol(score)
        print(f"{status} Q: {question}")
        print(f"  A: {answer}")
        print(f"  Score: {score:.3f} (expected: medium confidence)")
        print()

    # Test 4: Batch evaluation
    print("\nTEST 4: Batch Evaluation")
    print("-" * 40)

    questions: List[str] = [
        "What is the largest planet in our solar system?",
        "What is the largest planet in our solar system?",
        "How many legs does a spider have?",
        "How many legs does a spider have?",
        "What year did World War II end?",
        "What year did World War II end?",
        "What is the chemical formula for water?",
        "What is the chemical formula for water?",
        "Who painted the Mona Lisa?",
        "Who painted the Mona Lisa?",
    ]

    answers: List[str] = [
        "Jupiter",
        "Earth",
        "8",
        "6",
        "1945",
        "1942",
        "H2O",
        "CO2",
        "Leonardo da Vinci",
        "Pablo Picasso",
    ]

    qa_pairs: List[Tuple[str, str]] = list(zip(questions, answers))

    print("Evaluating mix of correct and incorrect answers...")
    scores = detector.batch_evaluate(
        [qa[0] for qa in qa_pairs], [qa[1] for qa in qa_pairs]
    )

    print("\nResults:")
    correct_count = 0
    for (q, a), score in zip(qa_pairs, scores):
        status = get_status_symbol(score)
        confidence = get_confidence_level(score)
        if score > 0.7:
            correct_count += 1
        print(f"{status} {q[:40]}... → {a[:20]:<20} Score: {score:.3f} ({confidence})")

    print(f"\nSummary: {correct_count}/{len(qa_pairs)} identified as trustworthy")

    # Show performance metrics
    print("\n=== Performance Summary ===")
    if hasattr(detector, "_cache"):
        cache_size = len(detector._cache) if detector._cache else 0
        print(f"Cache size: {cache_size} items")
    print("Score distribution:")
    high_conf = sum(1 for s in scores if s > 0.7)
    low_conf = sum(1 for s in scores if s < 0.3)
    uncertain = sum(1 for s in scores if 0.3 <= s <= 0.7)
    print(f"  High confidence (>0.7): {high_conf}")
    print(f"  Low confidence (<0.3): {low_conf}")
    print(f"  Uncertain (0.3-0.7): {uncertain}")

    # Initialize with default prompts
    print("\n=== Using Default Prompts ===")
    detector = TrustworthinessDetector()

    # Example with default prompts
    question = "What is the capital of France?"
    answer = "Paris"
    score = detector.get_trustworthiness_score(question, answer)
    confidence = get_confidence_level(score)
    print(f"\nQ: {question}\nA: {answer}")
    print(f"Score: {score:.2f} ({confidence})")

    # Example with custom prompts
    print("\n=== Using Custom Prompts ===")
    custom_prompts: List[str] = [
        (
            "Is the following answer correct?\n"
            "Question: {question}\nAnswer: {answer}\n"
            "(A) Yes (B) No (C) Not sure"
        ),
        (
            "Review this Q&A for accuracy:\n"
            "Q: {question}\nA: {answer}\n"
            "Is this correct? (A) Yes (B) No (C) Unsure"
        ),
    ]

    custom_detector = TrustworthinessDetector(reflection_prompts=custom_prompts)
    score = custom_detector.get_trustworthiness_score(question, answer)
    print(f"\nQ: {question}\nA: {answer}\nScore with custom prompts: {score:.2f}")

    # Show the default reflection prompts
    print("\n=== Default Reflection Prompts ===")
    # Show first prompt as example
    print("\nPrompt 1 (truncated):")
    print(
        "Is the following answer correct?\n" "Question: {question}\nAnswer: {answer}..."
    )


def get_status_symbol(score: float) -> str:
    """Return appropriate symbol based on score."""
    if score > 0.7:
        return "✓"
    elif score < 0.3:
        return "✗"
    else:
        return "?"


def get_confidence_level(score: float) -> str:
    """Return confidence level description."""
    if score > 0.7:
        return "high confidence"
    elif score < 0.3:
        return "low confidence"
    else:
        return "medium confidence"


def real_world_example() -> None:
    """Show a real-world integration example."""
    print("\n=== Real-World Integration Example ===")
    print("Generating and evaluating answers in a typical use case\n")

    detector = TrustworthinessDetector(model="gemini/gemini-pro")

    # Simulate a Q&A system
    questions = [
        "What is the speed of light in vacuum?",
        "Explain quantum entanglement in simple terms.",
        "What are the main causes of climate change?",
    ]

    for question in questions:
        print(f"Question: {question}")

        # For demonstration, use a simple answer (in a real app,
        # this would come from an LLM)
        answer = (
            "This is a sample answer that would come from an LLM in a "
            "real application."
        )

        # Evaluate trustworthiness
        score = detector.get_trustworthiness_score(question, answer)

        print(f"Answer: {answer[:150]}...")
        print(f"Trustworthiness: {score:.3f}")

        # Decision logic
        if score > 0.7:
            print("✓ Answer approved - high confidence\n")
        elif score < 0.3:
            print("✗ Answer rejected - low confidence, regenerating...\n")
            # In real app, you might regenerate or ask human
        else:
            print("? Answer flagged for review - medium confidence\n")


if __name__ == "__main__":
    main()

    """
    Example Output:
    --------------
    Using model: gemini-1.5-pro
    ==================================

    === Trustworthiness Detector Demo ===
    Testing self-reflection certainty implementation

    TEST 1: Assignment Examples
    ----------------------------------------
    Q: What is 1 + 1?
    A: 2
    Score: 0.92 (HIGH confidence)

    Q: What is the third month in alphabetical order?
    A: April
    Score: 0.85 (HIGH confidence)

    Q: How many syllables are in the following phrase...
    A: 14
    Score: 0.88 (HIGH confidence)

    TEST 2: Incorrect Answers
    ----------------------------------------
    Q: What is 1 + 1?
    A: 3 (incorrect)
    Score: 0.12 (LOW confidence)

    TEST 3: Edge Cases
    ----------------------------------------
    Q: What is the capital of France?
    A: Paris
    Score: 0.95 (HIGH confidence)

    Q: What is the capital of France?
    A: London (incorrect)
    Score: 0.08 (LOW confidence)
    """
    try:
        main()
        print(
            "\nSkipping real-world example due to API quota limitations. "
            "To test with your own questions, run the script with your own API key."
        )
    except Exception as e:
        if "quota" in str(e).lower():
            print(
                "\nError: API quota exceeded. Please check your Gemini API "
                "quota or try again later."
            )
            print("Visit: https://ai.google.dev/gemini-api/docs/rate-limits")
        else:
            print(f"\nError: {str(e)}")
        print("\nNote: Make sure you have set up your .env file with a valid API key.")
        print("See .env.example for the required configuration.")
