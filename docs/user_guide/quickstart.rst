.. _quickstart:

Quickstart
==========

This guide will help you get started with the Trustworthiness Detector package.

Basic Usage
-----------

Import and initialize the detector:

.. code-block:: python

    from trustworthiness import TrustworthinessDetector

    # Initialize with default settings
    detector = TrustworthinessDetector()

    # Evaluate a single Q&A pair
    score = detector.get_trustworthiness_score(
        question="What is the capital of France?",
        answer="Paris"
    )
    print(f"Trustworthiness score: {score:.2f}")

Using the Convenience Function
-----------------------------

For simple use cases, you can use the convenience function:

.. code-block:: python

    from trustworthiness import evaluate_trustworthiness

    score = evaluate_trustworthiness(
        question="What is 2 + 2?",
        answer="4"
    )
    print(f"Trustworthiness score: {score:.2f}")

Batch Processing
---------------

Evaluate multiple Q&A pairs at once:

.. code-block:: python

    questions = [
        "What is the capital of France?",
        "What is 2 + 2?",
        "Who painted the Mona Lisa?"
    ]
    
    answers = [
        "Paris",
        "4",
        "Leonardo da Vinci"
    ]
    
    scores = detector.batch_evaluate(questions, answers)
    
    for q, a, s in zip(questions, answers, scores):
        print(f"Q: {q}")
        print(f"A: {a}")
        print(f"Score: {s['score']:.2f}")
        print(f"Confidence: {s['confidence']:.2f}")
        print()

Using the REST API
-----------------

Start the API server:

.. code-block:: bash

    uvicorn trustworthiness.api:app --reload

Then make requests to the API:

.. code-block:: bash

    # Single evaluation
    curl -X POST "http://localhost:8000/api/v1/evaluate" \
         -H "Content-Type: application/json" \
         -d '{"question": "What is the capital of France?", "answer": "Paris"}'

    # Batch evaluation
    curl -X POST "http://localhost:8000/api/v1/batch-evaluate" \
         -H "Content-Type: application/json" \
         -d '{"questions": ["What is 2+2?"], "answers": ["4"]}'

Configuration
-------------

Customize the detector with different models and settings:

.. code-block:: python

    from trustworthiness import TrustworthinessDetector, ModelConfig

    config = ModelConfig(
        model_name="gemini-1.5-pro",
        temperature=0.7,
        max_tokens=1024,
        trust_threshold=0.8,
        warning_threshold=0.6
    )
    
    detector = TrustworthinessDetector(config=config)

Next Steps
----------

- :ref:`configuration` - Learn about advanced configuration options
- :ref:`api_reference` - Explore the full API reference
- :ref:`examples` - See more examples of using the package
