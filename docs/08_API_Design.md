# API Design

## Overview

The backend exposes REST APIs for application management and WebSockets for real-time communication.

The APIs are organized by functionality and follow RESTful design principles.

---

# REST API

## Health

GET /health

Purpose:

Returns backend health status.

---

## Session

POST /session/start

Starts a new conversation session.

---

POST /session/end

Ends the current session.

---

GET /session/{id}

Returns session details.

---

# Messages

POST /message

Stores a conversation message.

---

GET /messages/{session_id}

Returns conversation history.

---

# Memory

POST /memory

Creates a memory record.

---

GET /memory/{user_id}

Returns stored memories.

---

# Tools

POST /tools/calendar

Calendar integration.

---

POST /tools/search

Search integration.

---

POST /tools/email

Email integration.

---

# Settings

GET /settings

Returns application configuration.

---

PUT /settings

Updates application settings.

---

# Logs

GET /logs

Returns application logs.

---

# WebSocket API

/ws/audio

Used for:

- Live audio streaming
- Real-time speech recognition
- Voice communication

---

/ws/events

Used for:

- Live events
- Notifications
- Conversation updates

---

# Response Format

Successful response:

```json
{
  "success": true,
  "message": "Operation completed successfully.",
  "data": {}
}
```

---

Error response:

```json
{
  "success": false,
  "message": "Error description",
  "error": {}
}
```

---

# API Design Principles

- RESTful
- Versioned
- Stateless
- Secure
- Modular
- Consistent
- Easy to extend