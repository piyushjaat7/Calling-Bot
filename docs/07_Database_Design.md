# Database Design

## Overview

The application uses PostgreSQL as the primary relational database.

The database stores persistent information such as users, conversations, call sessions, messages, memory, and application settings.

Redis is used for temporary session storage and caching.

---

# Core Entities

The database consists of the following major entities:

- Users
- Call Sessions
- Messages
- Memory
- Contacts
- Tasks
- Settings
- Logs

---

# Users

Stores user information.

Fields:

- id
- name
- email
- phone_number
- created_at
- updated_at

---

# Call Sessions

Represents a single conversation.

Fields:

- id
- session_id
- caller_id
- start_time
- end_time
- duration
- status

---

# Messages

Stores every conversational message.

Fields:

- id
- session_id
- speaker
- message
- timestamp

Speaker values:

- User
- AI

---

# Memory

Stores long-term memory.

Fields:

- id
- user_id
- category
- content
- embedding
- created_at

---

# Contacts

Stores known contacts.

Fields:

- id
- name
- phone
- priority

---

# Tasks

Stores pending actions.

Examples:

- Call back
- Reminder
- Schedule meeting

---

# Settings

Stores application settings.

Examples:

- Preferred language
- Voice model
- AI provider
- TTS provider

---

# Logs

Stores important application events.

Examples:

- Errors
- Warnings
- API events

---

# Relationships

```
Users

↓

Call Sessions

↓

Messages

↓

Memory
```

---

# Future Expansion

Future entities may include:

- Calendar
- Email
- Notifications
- Voice Profiles
- AI Models
- Analytics