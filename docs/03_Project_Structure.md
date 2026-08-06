# Project Structure

## Overview

The project follows a modular architecture where every directory has a single responsibility. This improves maintainability, scalability, readability, and makes future development easier.

The folder structure is designed to support future expansion without requiring major architectural changes.

---

# Root Structure

```
Calling Bot/

├── backend/
├── docker/
├── docs/
├── scripts/
├── tests/
├── .env.example
├── .gitignore
├── pyproject.toml
├── uv.lock
└── README.md
```

---

# Backend Structure

```
backend/

└── app/

    ├── agents/
    ├── api/
    ├── audio/
    ├── config/
    ├── conversation/
    ├── core/
    ├── database/
    ├── llm/
    ├── memory/
    ├── models/
    ├── schemas/
    ├── services/
    ├── stt/
    ├── telephony/
    ├── tools/
    ├── tts/
    ├── utils/
    └── websocket/
```

---

# Folder Responsibilities

## agents/

Contains AI agents responsible for planning, reasoning, orchestration, and autonomous task execution.

---

## api/

Contains REST API endpoints exposed by the backend.

Responsibilities:

- Route definitions
- Request handling
- Response formatting

---

## audio/

Handles raw audio processing.

Responsibilities:

- Audio preprocessing
- Audio streaming
- Voice Activity Detection
- Audio utilities

---

## config/

Stores application configuration.

Responsibilities:

- Environment variables
- Application settings
- Configuration management

---

## conversation/

Responsible for conversation lifecycle.

Responsibilities:

- Session management
- Context tracking
- Dialogue state
- Conversation history

---

## core/

Contains core application services.

Examples:

- Logging
- Startup
- Shared utilities
- Application initialization

---

## database/

Database configuration and initialization.

Responsibilities:

- Database connection
- Session management
- Migrations

---

## llm/

Contains language model integrations.

Examples:

- OpenAI
- Ollama
- Gemini
- Future providers

---

## memory/

Stores conversational memory.

Responsibilities:

- Short-term memory
- Long-term memory
- Semantic memory
- Retrieval

---

## models/

Database models.

Examples:

- Users
- Calls
- Sessions
- Messages

---

## schemas/

Request and response validation.

Responsibilities:

- API schemas
- Validation
- Serialization

---

## services/

Business logic.

The API layer should delegate business operations to this layer.

---

## stt/

Speech-to-Text implementations.

Examples:

- Whisper
- Deepgram
- Azure Speech

---

## telephony/

Telephony integrations.

Examples:

- Twilio
- Exotel
- SIP
- Future providers

---

## tools/

External tools available to the AI.

Examples:

- Calendar
- Email
- Contacts
- Search
- Database

---

## tts/

Text-to-Speech implementations.

Examples:

- ElevenLabs
- OpenAI TTS
- Piper

---

## utils/

Common helper functions.

---

## websocket/

Real-time communication using WebSockets.

Responsibilities:

- Streaming audio
- Live events
- Session communication

---

# Design Principles

The structure follows:

- Single Responsibility Principle
- Separation of Concerns
- Scalability
- Maintainability
- Provider Independence