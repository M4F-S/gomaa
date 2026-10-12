# Contributing to Gomaa

Thank you for your interest in contributing!

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR_USERNAME/gomaa`
3. Install dependencies: `make install`
4. Run tests: `make test`

## Development Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install in development mode
pip install -e ".[dev]"

# Run tests
make test

# Run all checks
make check
```

## Submitting Changes

1. Create a branch from `develop`: `git checkout -b feature/your-feature`
2. Make your changes
3. Add tests for new functionality
4. Ensure all tests pass: `make check`
5. Commit with descriptive message
6. Push to your fork
7. Create a Pull Request to `develop`

## Code Style

- Follow PEP 8
- Use type hints
- Add docstrings to all public functions
- Run `make format` before committing

## Reporting Bugs

Please use the GitHub issue tracker with the bug report template.

## Feature Requests

Please use the GitHub issue tracker with the feature request template.
