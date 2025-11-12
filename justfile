# List all available just commands
list:
    just -l

# Check for lint and format violations
lint: 
    uv run ruff format --check .
    uv run ruff check .

# Fix lint and format violations
qa:
    uv run ruff format .
    uv run ruff check . --fix

# Run the tests
test:
    uv run pytest tests/

# Run the interactive demo
run:
    uv run fastapi dev tests/demo.py

# Build the package
build:
    uv build

# Install the package locally for development
install:
    uv pip install -e .

# Tag and release on GitHub and PyPI
tag VERSION:
    echo "Tagging version v{{VERSION}}"
    git tag -a v{{VERSION}} -m "Creating version v{{VERSION}}"
    git push origin v{{VERSION}}
