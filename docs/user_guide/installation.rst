.. _installation:

Installation
============

This guide will help you install the Trustworthiness Detector package and its dependencies.

Prerequisites
------------

- Python 3.10 or higher
- pip (Python package manager)
- (Optional) Docker and Docker Compose for containerized deployment

Installation Methods
-------------------

Using pip
~~~~~~~~

The recommended way to install the package is using pip:

.. code-block:: bash

    # Install the latest stable version from PyPI
    pip install trustworthiness-detector

    # Install with optional dependencies
    pip install "trustworthiness-detector[all]"

    # For development, install in editable mode with all dependencies
    git clone https://github.com/yourusername/trustworthiness-detector.git
    cd trustworthiness-detector
    pip install -e ".[dev]"

Using Docker
~~~~~~~~~~~

You can also run the application using Docker:

.. code-block:: bash

    # Build the Docker image
    docker build -t trustworthiness-detector .
    
    # Run the container
    docker run -p 8000:8000 --env-file .env trustworthiness-detector

Using Docker Compose (Recommended)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For a complete setup with monitoring:

.. code-block:: bash

    # Copy the example environment file
    cp .env.example .env
    
    # Update the .env file with your configuration
    
    # Start all services
    docker-compose up -d

Verifying the Installation
-------------------------

After installation, you can verify that the package is installed correctly:

.. code-block:: python

    import trustworthiness
    print(trustworthiness.__version__)

Or test the API:

.. code-block:: bash

    # Start the development server
    uvicorn trustworthiness.api:app --reload
    
    # In another terminal, test the API
    curl http://localhost:8000/health

Common Installation Issues
-------------------------

1. **Missing Dependencies**
   - Ensure you have Python development headers installed
   - On Ubuntu/Debian: ``sudo apt-get install python3-dev``
   - On macOS: ``xcode-select --install``

2. **Permission Errors**
   - Use a virtual environment: ``python -m venv venv && source venv/bin/activate``
   - Or use ``--user`` flag: ``pip install --user trustworthiness-detector``

3. **Dependency Conflicts**
   - Create a fresh virtual environment
   - Or use ``pip install --upgrade-strategy eager trustworthiness-detector``

Next Steps
----------

- :ref:`quickstart` - Get started with basic usage
- :ref:`configuration` - Learn how to configure the application
- :ref:`api_reference` - Explore the API reference
