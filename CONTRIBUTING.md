# Contributing to Pharmacy AI Automation System

First off, thank you for considering contributing! 🎉

## 🚀 Quick Start

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR_USERNAME/Pharmacy-AI-automation-system.git`
3. Create a branch: `git checkout -b feature/amazing-feature`
4. Make your changes
5. Commit: `git commit -m "feat: add amazing feature"`
6. Push: `git push origin feature/amazing-feature`
7. Open a Pull Request

## 📋 Development Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment variables
cp .env.example .env
# Edit .env with your API keys

# Run the server
python -m uvicorn app.main:app --reload
```

## 🎯 Commit Convention

We use [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation only
- `style:` Formatting, no code change
- `refactor:` Code change that neither fixes a bug nor adds a feature
- `test:` Adding tests
- `chore:` Updating build tasks, etc.

## 🧪 Testing

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=app tests/
```

## 📝 Code Style

- Follow PEP 8
- Use type hints
- Write docstrings for public functions
- Keep functions small and focused

## ⚠️ HIPAA Compliance

When contributing:
- Never commit real patient data
- Use mock data for testing
- Ensure PHI is properly encrypted
- Review security implications of changes

## 🙏 Thank You!

Your contributions make this project better for everyone!
