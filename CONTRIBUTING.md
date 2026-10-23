# Contributing to WirePulse

Thank you for your interest in contributing to WirePulse! We welcome bug reports, documentation enhancements, feature proposals, and pull requests.

---

## Development Setup

WirePulse is intentionally engineered with **zero external runtime dependencies**. You only need Python 3.9+ installed.

1. Clone the repository:
   ```bash
   git clone https://github.com/seanzhangsean/wirepulse.git
   cd wirepulse
   ```

2. Run the test suite:
   ```bash
   python -m unittest discover -s tests -p "test_*.py" -v
   ```

3. Test CLI locally without installing:
   ```bash
   PYTHONPATH=. python -m wirepulse.cli --help
   ```

---

## Pull Request Guidelines

- Ensure all existing and new unit tests pass (`python -m unittest discover`).
- Keep code clean, type-hinted, and adhering to PEP 8 standards.
- Maintain the zero-runtime-dependency invariant for core features so embedded devices can run WirePulse smoothly.
- Update documentation or OpenWrt instructions when altering configuration schemas or metrics names.
