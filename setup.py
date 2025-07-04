"""
Setup script for the Trustworthiness Detector package.

This script allows the package to be installed with pip.
"""

from setuptools import setup, find_packages

# Read the README for the long description
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# Read requirements from requirements.txt
with open("requirements.txt", "r", encoding="utf-8") as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]

setup(
    name="trustworthiness-detector",
    version="0.2.0",
    author="Ridwan Abdusalam",
    author_email="ridwanabdsal@gmail.com",
    description="A Python package for detecting trustworthiness in LLM outputs with confidence intervals and explainability",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Ridwanabdusalam/cleanlab_takehome",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    package_data={"trustworthiness": ["py.typed"]},
    python_requires=">=3.10",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.4.0,<8.0.0",
            "pytest-cov>=4.1.0,<5.0.0",
            "black>=23.9.0,<24.0.0",
            "isort>=5.12.0,<6.0.0",
            "mypy>=1.5.0,<2.0.0",
            "ruff>=0.0.280,<0.1.0",
            "pre-commit>=3.3.0,<4.0.0",
            "sphinx>=7.1.0,<8.0.0",
            "sphinx-rtd-theme>=1.2.0,<2.0.0",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Framework :: FastAPI",
        "Typing :: Typed",
    ],
    keywords=["llm", "trustworthiness", "ai-safety", "nlp", "machine-learning"],
    project_urls={
        "Homepage": "https://github.com/Ridwanabdusalam/cleanlab_takehome",
        "Documentation": "https://trustworthiness-detector.readthedocs.io/",
        "Source": "https://github.com/Ridwanabdusalam/cleanlab_takehome",
        "Issues": "https://github.com/Ridwanabdusalam/cleanlab_takehome/issues",
    },
)
