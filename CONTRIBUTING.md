# Contributing to CNC Bridge

Thanks for your interest in contributing! CNC Bridge is an open-source project connecting Autodesk Fusion 360 to Anilam Crusader M/II CNC controllers.

## How to Contribute

### Reporting Bugs

Open a [GitHub Issue](https://github.com/Apocscode/CNC-Bridge/issues) with:
- What happened vs. what you expected
- Steps to reproduce
- Your OS, Python version, COM port adapter
- Controller model (Crusader M or II)
- Serial traffic log from `logs/serial/` (if applicable)

### Suggesting Features

Open an issue with the `enhancement` label. Describe the use case and how it would help your workflow.

### Submitting Code

1. **Fork** the repository
2. **Create a branch** for your feature: `git checkout -b feature/my-feature`
3. **Make your changes** following the coding guidelines below
4. **Test your changes** — run `pytest tests/` and launch the app
5. **Commit** with clear messages: `git commit -m "Add XYZ feature"`
6. **Push** and open a **Pull Request** against `master`

## Coding Guidelines

### Python (bridge-app)
- Python 3.10+ required
- Follow PEP 8 style
- Use type hints for function signatures
- Docstrings on all public classes and methods
- Use `logging` instead of `print` for diagnostics
- PyQt6 for all GUI code
- Thread-safe GUI updates via `QTimer.singleShot(0, ...)`

### Post Processor (.cps)
- Autodesk CAM post processor JavaScript format
- Test output against Anilam RS-274-D specification
- Include comments explaining any Anilam-specific behavior
- Test with both Crusader M and Crusader II profiles

### ESP32 Firmware (C++)
- PlatformIO build system
- Arduino framework for ESP32-S3
- Keep state machines clean with `BridgeState` enum
- All serial timing values are configurable in `config.h`

## Adding Reference Library Entries

Edit `bridge-app/src/core/reference_library.py`:

```python
LibraryEntry(
    code="CATEGORY CODE",
    title="Short Title",
    category=EntryCategory.YOUR_CATEGORY,
    description="Detailed explanation...",
    syntax="G-code syntax example",
    example="N100 G1 X1.0 Y2.0 F10",
    when_to_use="When you need to...",
    related_codes=["G0", "G2"],
    warning="Safety notes if applicable",
    source="Anilam manual reference",
    tags=["keyword1", "keyword2"],
),
```

Run the test script to validate: `python test_library.py`

## Adding Tools to the Tool Library

The tool library is managed through the UI (Tool Library tab) and stored in `config/tool_library.json`. No code changes needed.

## Project Structure

```
CNC Bridge/
├── bridge-app/          # Python desktop application
│   ├── src/
│   │   ├── core/        # Serial, DNC, parser, settings, logger, backup
│   │   └── ui/          # PyQt6 widgets and panels
│   ├── tests/           # pytest unit tests
│   └── requirements.txt
├── post-processor/      # Fusion 360 post processor (.cps)
├── firmware/            # ESP32-S3 PlatformIO project
├── docs/                # Documentation
└── installer/           # Windows installer (Inno Setup)
```

## Testing

```bash
cd bridge-app
pip install pytest
pytest tests/ -v
```

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
