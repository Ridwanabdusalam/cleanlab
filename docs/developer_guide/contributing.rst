.. _contributing_guide:

Contributing Guide
=================

We welcome contributions to the Trustworthiness Detector! Here's how you can help.

Ways to Contribute
-----------------

- Report bugs
- Suggest new features
- Improve documentation
- Submit bug fixes
- Add test cases
- Improve performance
- Review pull requests

Getting Started
--------------

1. Fork the repository
2. Create a feature branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. Make your changes
4. Run tests and linters:
   ```bash
   pytest
   black .
   isort .
   flake8
   mypy .
   ```
5. Commit your changes with a descriptive message
6. Push to your fork and submit a pull request

Pull Request Guidelines
----------------------

- Keep PRs focused on a single feature or bug fix
- Include tests for new functionality
- Update documentation as needed
- Follow the existing code style
- Make sure all tests pass
- Add yourself to AUTHORS.md

Code Style
----------

- Follow PEP 8
- Use type hints
- Keep functions small and focused
- Write docstrings for all public functions
- Use meaningful variable names
- Keep lines under 88 characters

Commit Message Format
---------------------

Use the following format for commit messages:

```
<type>: <description>

[optional body]

[optional footer]
```

Types:
- feat: New feature
- fix: Bug fix
- docs: Documentation changes
- style: Code style changes
- refactor: Code refactoring
- test: Adding or modifying tests
- chore: Maintenance tasks

Example:
```
feat: add new scoring function

Add a new scoring function that calculates trustworthiness based on sentiment analysis.

Closes #123
```

Reporting Bugs
-------------

1. Check if the bug has already been reported
2. Open a new issue with a clear title and description
3. Include steps to reproduce the bug
4. Add any relevant logs or screenshots
5. Specify your environment (OS, Python version, etc.)

Feature Requests
---------------

1. Check if the feature has already been requested
2. Open a new issue with a clear description
3. Explain why this feature would be useful
4. Provide any relevant examples or use cases

Code Review Process
------------------

1. A maintainer will review your PR
2. You may be asked to make changes
3. Once approved, your PR will be merged
4. Thank you for your contribution!

License
-------

By contributing, you agree that your contributions will be licensed under the project's LICENSE file.
