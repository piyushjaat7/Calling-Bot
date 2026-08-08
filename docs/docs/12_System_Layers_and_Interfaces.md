
12. System Layers and Interfaces

1. Purpose

This document defines the major architectural layers and user-facing interfaces of the Calling Bot / AI Communication Platform.

The system is designed so that the core AI and conversation logic remains independent from the way a user communicates with the platform.

A phone call, web application, mobile application, desktop client, or API client should be able to use the same underlying conversation and AI systems.

2. High-Level Architecture

┌──────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                        │
│                                                              │
│   Web Dashboard     Mobile UI     Admin Panel     Desktop UI │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                 COMMUNICATION / API LAYER                    │
│                                                              │
│       REST API       WebSocket       Telephony       Voice   │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                    CONVERSATION LAYER                        │
│                                                              │
│  Session Manager │ Conversation │ State Machine │ Context   │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                       AI LAYER                               │
│                                                              │
│ LLM Router │ Prompt Engine │ Memory │ Planner │ Reasoning   │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                    TOOL / ACTION LAYER                       │
│                                                              │
│ Search │ Calendar │ Database │ External APIs │ Custom Tools │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                 INFRASTRUCTURE / DATA LAYER                  │
│                                                              │
│ PostgreSQL │ Redis │ Storage │ Logging │ Configuration      │
└──────────────────────────────────────────────────────────────┘

3. Architectural Principle

The most important principle is:

Interfaces should depend on the communication layer, and communication should depend on the conversation/AI core — not the other way around.

The Conversation Engine must not contain phone-specific, browser-specific, or UI-specific business logic.

For example:

Phone User
    │
    ▼
Telephony Adapter
    │
    ▼
Conversation Engine
    │
    ▼
AI System
    │
    ▼
Response
    │
    ▼
Telephony Adapter
    │
    ▼
Phone User

The same engine can be used by a web client:

Web UI
  │
  ▼
REST/WebSocket API
  │
  ▼
Conversation Engine
  │
  ▼
AI System
  │
  ▼
Web UI

This keeps the AI core reusable.

4. System Layers

4.1 Presentation Layer

The Presentation Layer contains interfaces through which humans interact with the platform.

Planned interfaces

Web Dashboard

Web Conversation UI

Admin Panel

Mobile Application

Future Desktop Application

Responsibilities

Display conversations

Display call/session status

Accept user input

Display AI responses

Display system status and analytics

Provide administrative controls

Non-responsibilities

The presentation layer should not:

Directly call the LLM

Implement conversation state transitions

Execute tools directly

Manage database transactions

Contain telephony provider logic

The UI communicates with the backend through defined APIs.

4.2 Communication / API Layer

This layer provides communication interfaces between clients/providers and the backend.

Planned interfaces

REST API
WebSocket
Telephony Adapter
Voice Streaming

REST API

Used for:

Authentication

Session management

Conversation history

Dashboard data

Configuration

Administrative operations

WebSocket

Used for real-time functionality such as:

Streaming AI responses

Live conversation updates

Call/session status

Real-time events

Telephony

The telephony layer connects external calling providers to the platform.

It should translate provider-specific events into internal platform events.

For example:

Twilio/WebRTC/Other Provider
            │
            ▼
     Telephony Adapter
            │
            ▼
     Internal Event Model
            │
            ▼
    Conversation Engine

Provider-specific logic should remain inside the adapter rather than leaking into the conversation engine.

5. Conversation Layer

The Conversation Layer is the core interaction-management layer.

It manages the lifecycle and state of a conversation independently of the interface being used.

Main components

Session Manager
Conversation Manager
State Machine
Context Manager
Message/Event Models

Responsibilities

Create and manage sessions

Track conversations

Store and retrieve messages

Maintain conversation state

Build the current conversation context

Coordinate interaction flow

Handle conversation-level errors and transitions

Example

Incoming Message
       │
       ▼
Session
       │
       ▼
Conversation
       │
       ▼
State Machine
       │
       ▼
Context
       │
       ▼
AI Layer

6. AI Layer

The AI Layer provides intelligence to the Conversation Layer.

Planned components

LLM Router
Prompt Engine
Memory
Planner
Reasoning
Response Generation

LLM Router

Responsible for selecting the appropriate model/provider.

Potential providers include:

OpenAI

Gemini

Ollama

Future providers

The Conversation Layer should not need to know provider-specific implementation details.

Conversation Engine
        │
        ▼
    LLM Router
     /   |   \
 OpenAI Gemini Ollama

Prompt Engine

Responsible for constructing model inputs from:

System instructions

Conversation context

Memory

User message

Tool results

Runtime information

Memory

Responsible for providing relevant historical information to the AI.

Planner

Responsible for deciding when a request requires:

Direct response

Clarification

Tool execution

Multi-step reasoning/workflow

7. Tool / Action Layer

The Tool Layer allows the AI system to interact with external systems.

Examples:

Search
Calendar
Database
Email
External APIs
Custom Business APIs

The AI should not execute arbitrary tools directly.

Instead:

AI / Planner
     │
     ▼
Tool Registry
     │
     ▼
Tool Validation
     │
     ▼
Tool Execution
     │
     ▼
Tool Result
     │
     ▼
Conversation Engine

This provides a controlled boundary for tool execution.

8. Infrastructure / Data Layer

This layer provides persistence and shared infrastructure.

Planned components

PostgreSQL
Redis
Object/File Storage
Logging
Configuration

PostgreSQL

Primary persistent database for structured application data.

Potential data includes:

Users

Sessions

Conversations

Messages

Tool executions

Call records

Configuration

Audit records

Redis

Potential uses:

Session/cache data

Temporary state

Rate limiting

Real-time coordination

Background task support

Logging

The existing logging system belongs to this infrastructure layer.

It provides:

Application logs

Error logs

AI logs

Telephony logs

Conversation logs

Performance logs

9. Developer / Terminal Interface

The terminal is not the primary end-user interface.

It is a developer and operations interface.

Examples:

uv run uvicorn backend.main:app --reload
uv run pytest
uv run ruff check .
uv run mypy backend

The terminal may also eventually provide developer/admin commands such as:

calling-bot health
calling-bot sessions
calling-bot logs
calling-bot test

These commands are operational tools and should not be confused with the main product UI.

10. User Interface Strategy

The first major user-facing interface should be a Web UI.

A future web application can provide:

Dashboard
├── Overview
├── Active Calls
├── Conversations
├── Call History
├── AI Activity
├── Analytics
└── Settings

A conversation screen could provide:

┌──────────────────────────────────────────┐
│ Conversation                             │
├──────────────────────────────────────────┤
│ User                                     │
│ Can you schedule an appointment?         │
│                                          │
│ AI                                       │
│ Sure. What time would you prefer?        │
│                                          │
│ User                                     │
│ Tomorrow at 4 PM.                        │
│                                          │
│ AI                                       │
│ Done. I've scheduled it for 4 PM.        │
├──────────────────────────────────────────┤
│ [ Type a message... ]          [ Send ]  │
└──────────────────────────────────────────┘

Voice functionality can later be added to the same interface.

11. Phone / Voice Interface

The phone interface is a communication channel rather than the AI brain.

The expected flow is:

Incoming Call
     │
     ▼
Telephony Provider
     │
     ▼
Telephony Adapter
     │
     ▼
Audio / STT
     │
     ▼
Conversation Engine
     │
     ▼
AI Layer
     │
     ▼
Response
     │
     ▼
TTS
     │
     ▼
Telephony Adapter
     │
     ▼
Caller

This separation allows the telephony implementation to change without rewriting the Conversation Engine.

12. Interface Independence

The same conversation should be usable through multiple interfaces.

                         ┌── Web UI
                         │
                         ├── Mobile
                         │
                         ├── Phone
User ──► Interface ──────┼── Desktop
                         │
                         └── API Client
                                │
                                ▼
                       Communication Layer
                                │
                                ▼
                       Conversation Engine
                                │
                                ▼
                            AI Layer

The core conversation and AI logic remain shared.

13. Request / Response Abstraction

Interfaces should convert their external representation into internal platform models.

For example:

Web Request
     │
     ▼
Internal Message

and:

Phone Audio
     │
     ▼
Speech-to-Text
     │
     ▼
Internal Message

Both eventually reach the same conversation system:

Internal Message
       │
       ▼
Conversation Engine

Likewise, the engine produces an internal response:

Internal Response
       │
       ├──► Web Response
       │
       ├──► WebSocket Event
       │
       └──► TTS / Phone Audio

14. Security Boundary

Each layer should have a clear security responsibility.

Presentation
    ↓
Authentication / Authorization
    ↓
API Validation
    ↓
Conversation Authorization
    ↓
Tool Permission Checks
    ↓
Infrastructure Access

Sensitive provider credentials must remain in configuration/environment management and must never be exposed to frontend clients.

15. Observability

Every major layer should produce structured logs and measurable events.

Examples:

API Request
Conversation Started
Message Received
LLM Request
LLM Response
Tool Started
Tool Completed
Call Started
Call Ended
Session Created
Session Expired

These events should carry correlation information such as:

session_id
request_id
caller_id
provider
module

This allows a complete request/conversation flow to be traced across layers.

16. Initial Implementation Order

The layers will not all be implemented simultaneously.

Recommended order:

1. Infrastructure Foundation          ✅
       │
2. System Layers & Interfaces         ← Current design
       │
3. Conversation Models
       │
4. Session Manager
       │
5. Conversation State Machine
       │
6. Conversation Context
       │
7. Conversation Engine
       │
8. Memory
       │
9. LLM Router
       │
10. Tool System
       │
11. Web/API Interface
       │
12. STT / TTS
       │
13. Telephony
       │
14. Production Web Dashboard

The exact ordering may be adjusted when implementation dependencies are finalized.

17. Design Rules

The following rules should be maintained throughout development.

Rule 1 — Core independence

The Conversation Engine must not depend directly on:

React/UI code

Twilio-specific code

OpenAI-specific code

Browser-specific code

Rule 2 — Adapter boundaries

External providers must be accessed through adapters/interfaces.

Rule 3 — Shared internal models

Different interfaces should translate into common internal message/session/event models.

Rule 4 — No business logic in UI

The UI displays and collects information; business decisions belong in the backend.

Rule 5 — No provider logic in the Conversation Engine

Provider-specific behavior belongs in its adapter/router.

Rule 6 — Test layers independently

Each layer should have unit tests, while cross-layer behavior should have integration tests.

18. Target Architecture

The long-term target is:

                         USERS
                           │
          ┌────────────────┼────────────────┐
          │                │                │
        WEB              PHONE            MOBILE
          │                │                │
          └────────────────┼────────────────┘
                           │
                           ▼
                 COMMUNICATION LAYER
                           │
                           ▼
                 CONVERSATION ENGINE
                           │
              ┌────────────┼────────────┐
              │            │            │
           Session       Context       State
              │            │            │
              └────────────┼────────────┘
                           │
                           ▼
                       AI LAYER
                           │
              ┌────────────┼────────────┐
              │            │            │
             LLM         Memory       Planner
              │            │            │
              └────────────┼────────────┘
                           │
                           ▼
                     TOOL SYSTEM
                           │
                           ▼
                  INFRASTRUCTURE
                           │
              ┌────────────┼────────────┐
              │            │            │
          PostgreSQL     Redis        Storage

19. Current Status

Completed

Project setup

Repository and team workflow

Project documentation

Backend foundation

Configuration

Logging

Lifespan

Application factory

Health API

Swagger/OpenAPI

main / develop branch workflow

Current Work

System Layers and Interfaces

Next

Conversation Architecture and Conversation Engine

20. Key Architectural Goal

The final system should not be a terminal application with AI features attached to it.

It should be an AI Communication Platform with a reusable conversation and intelligence core.

                    ONE AI BRAIN
                         │
        ┌────────────────┼────────────────┐
        │                │                │
       Web              Phone           Mobile
        │                │                │
     Browser           Voice          Application

The interface can change.

The communication channel can change.

The AI provider can change.

The core conversation system should remain stable.
