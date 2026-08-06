# Coding Standards

## Overview

This document defines the coding standards that every contributor must follow throughout the project. These standards ensure consistency, maintainability, readability, and scalability.

---

# General Principles

The project follows:

- Clean Architecture
- SOLID Principles
- DRY (Don't Repeat Yourself)
- KISS (Keep It Simple)
- Separation of Concerns

---

# Naming Conventions

## Files

Use snake_case.

Examples:

```
conversation_manager.py
memory_service.py
speech_engine.py
```

---

## Classes

Use PascalCase.

Examples:

```
ConversationManager
SpeechRecognizer
MemoryService
```

---

## Functions

Use snake_case.

Examples:

```
process_audio()
generate_response()
retrieve_memory()
```

---

## Variables

Use meaningful snake_case names.

Good:

```
caller_name
conversation_history
response_text
```

Bad:

```
a
b
temp1
```

---

# Project Structure Rules

Each folder must have a single responsibility.

Business logic must never be placed inside API routes.

Routes call Services.

Services call Agents.

Agents interact with Memory and Tools.

---

# Documentation

Every public class and function should include docstrings.

Example:

```python
def process_audio(audio: bytes):
    """
    Process incoming audio and return transcription.
    """
```

---

# Logging

Use structured logging.

Never use:

```
print()
```

Always use the project logger.

---

# Error Handling

Every external operation should use exception handling.

Errors should never crash the application.

---

# Configuration

Never hardcode:

- API Keys
- URLs
- Database credentials
- Model names

Everything should come from configuration.

---

# Code Formatting

Use:

- Black
- Ruff
- isort
- MyPy

before every commit.

---

# Git Workflow

Every feature should have its own branch.

Example:

```
feature/stt

feature/tts

feature/memory

feature/api

feature/database
```

---

# Testing

Every major module should have unit tests.

Future:

- Integration Tests
- Performance Tests
- Load Tests

---

# Goal

The objective of these standards is to ensure that the codebase remains readable, scalable, and maintainable as the project grows.