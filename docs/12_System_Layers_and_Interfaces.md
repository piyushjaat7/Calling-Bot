
Konsa kya select kru?

Ye le bhai


Bhai sab final h jo folders h wo inke andar create hogye h

Abhi mujhe ye bta kya commands chalau m?

prr yaha toh mera account dikh rha h

Konsi?


Pasted text(20260806-130442).txt
Document
Bhai ye aaya h dekh le

What next it stopped here



b1856bee-e394-4cba-b646-880dcf23ecec.png
1b660117-2c12-4af7-8225-91d1a011fe02.png
I have only one branch and my team member is nikki she is helping me in this project

Bhai, ab hume random files banana start nahi karna hai. Tum dono ko ek proper sequence follow karna chahiye. Tumhara foundation already ready hai, so now we move from infrastructure → product/core logic.

🚀 Where We Start
Current project:

Sprint 0  → Setup                    ✅
Sprint 1  → Architecture/Docs        ✅
Sprint 2  → Backend Foundation       ✅
----------------------------------------
Sprint 3  → Conversation System      ← START HERE
The first mistake we should avoid is:

"Piyush coding Conversation Engine, Nikki coding Session Manager" before deciding what a conversation/session actually means.

So today's first goal is to create the contract between both of you.

Phase 1 — Both of you understand the existing project
Before writing code, both Piyush and Nikki should pull the latest develop.

You
git checkout develop
git pull origin develop
Nikki
git checkout develop
git pull origin develop
Then both should inspect:

backend/
docs/
pyproject.toml
README.md
Especially these docs:

docs/01_Project_Overview.md
docs/02_System_Architecture.md
docs/03_Project_Structure.md
docs/04_Tech_Stack.md
docs/05_Request_Flow.md
docs/06_AI_Pipeline.md
docs/07_Database_Design.md
docs/08_API_Design.md
docs/09_Coding_Standards.md
docs/10_Development_Roadmap.md
docs/11_Feature_Roadmap.md
The purpose isn't to reread everything deeply. You both need the same mental model of the project.

Phase 2 — Create the Conversation Architecture
This is the first actual work.

Create:

docs/12_Conversation_Architecture.md
This document should answer:

What is a Session?
For example:

Session
 ├── session_id
 ├── user/caller
 ├── status
 ├── created_at
 ├── last_activity_at
 └── metadata
What is a Conversation?
Conversation
 ├── conversation_id
 ├── session_id
 ├── messages
 └── metadata
What is a Message?
Message
 ├── message_id
 ├── role
 ├── content
 ├── timestamp
 └── metadata
What are the states?
Something along the lines of:

CREATED
   ↓
LISTENING
   ↓
THINKING
   ↓
RESPONDING
   ↓
LISTENING
with possible branches:

THINKING
   ├── CLARIFICATION
   ├── TOOL_EXECUTION
   └── RESPONDING
Don't blindly use these states. They're starting points. You and Nikki should decide the final state model based on the project requirements.

Phase 3 — Agree on the contracts
This is where you two work together.

Before coding, agree on:

Message contract
Session contract
Conversation contract
State contract
Event contract
For example, both should agree whether the application uses:

UUID
or some other identifier.

Whether a message is:

user
assistant
system
tool
Whether session state is:

Enum
etc.

Why?
Because if you build:

Session
one way and Nikki builds:

Conversation
assuming something completely different, you'll spend tomorrow resolving Git conflicts instead of developing.

Phase 4 — Commit the architecture
Once both of you agree:

You create branch
git checkout develop
git pull origin develop
git checkout -b feature/conversation-architecture
Create:

docs/12_Conversation_Architecture.md
Then:

git add docs/12_Conversation_Architecture.md
git commit -m "docs(conversation): define conversation architecture"
git push -u origin feature/conversation-architecture
Create a PR:

feature/conversation-architecture
              ↓
           develop
Review it together and merge it.

Phase 5 — NOW divide the coding
This is where you and Nikki work side by side.

👨‍💻 Piyush — Conversation Core
Create:

git checkout develop
git pull origin develop
git checkout -b feature/conversation-core
Your responsibility:

Conversation domain
      ↓
Message models
      ↓
Conversation state machine
      ↓
Conversation context
      ↓
Conversation engine
Your primary area will be something like:

backend/app/conversation/
The exact files should be determined from the architecture document.

👩‍💻 Nikki — Session System
Nikki creates:

git checkout develop
git pull origin develop
git checkout -b feature/session-manager
Her responsibility:

Session creation
      ↓
Session lookup
      ↓
Session lifecycle
      ↓
Session expiration
      ↓
Session tests
She should work primarily in the session/service/persistence area defined by the architecture.

🔥 This is the important part
You aren't working like this:

Piyush → writes everything
Nikki → waits
You're working like this:

                    develop
                       │
              Architecture Contract
                       │
             ┌─────────┴─────────┐
             │                   │
             ▼                   ▼
          PIYUSH               NIKKI
             │                   │
    Conversation Core      Session Manager
             │                   │
             │                   │
             └─────────┬─────────┘
                       │
                    PRs
                       ↓
                    develop
                       ↓
                 Integration
                       ↓
                     main
🧪 Every developer follows the same definition of DONE
Neither of you should say:

"Code complete."

until:

Code
 ↓
Ruff
 ↓
MyPy
 ↓
Pytest
 ↓
Review
 ↓
PR
For example:

uv run ruff check .
uv run mypy backend
uv run pytest
Phase 6 — Integration
After both pieces are ready:

Piyush
feature/conversation-core
        ↓
       PR
        ↓
     develop


Nikki
feature/session-manager
        ↓
       PR
        ↓
     develop
Then we test the combined system.

Only after that:

develop
   ↓
PR
   ↓
main
🧠 What comes after Conversation + Session?
Don't start LLM, Twilio, STT or TTS yet.

Our sequence should be:

                    CORE
                     │
        ┌────────────┴────────────┐
        │                         │
 Conversation                  Session
        │                         │
        └────────────┬────────────┘
                     ↓
               Context Manager
                     ↓
                  Memory
                     ↓
                LLM Router
                     ↓
                  Planner
                     ↓
               Tool System
                     ↓
              Response Engine
                     ↓
        ┌────────────┼────────────┐
        ↓            ↓            ↓
       STT          TTS        Telephony
This is important.

If we integrate Twilio now, we'll end up building the communication layer around an unfinished brain.

Instead:

Build the brain first, then attach communication channels to it.

🎯 So, TODAY's exact starting point
Don't create conversation/ yet.

Don't create session/ yet.

Don't integrate OpenAI.

Don't integrate Twilio.

Don't integrate STT/TTS.

Do this:
1. Both update develop

git checkout develop
git pull origin develop
2. Both review the existing 11 docs.

3. Create and finalize:

docs/12_Conversation_Architecture.md
4. Agree on:

Session
Conversation
Message
Event
State
Context
5. Merge that architecture into develop.

6. Then I will divide the actual implementation into two non-overlapping work packages:

Piyush → Conversation Core
Nikki  → Session System
with exact files, branch names, dependencies, tests, and commit messages.

That's the correct place to start. Once the architecture contract is locked, both of you can genuinely code in parallel without stepping on each other's work.


acha mujhein ek chhez btao har ek project mei kuch layers hoti hai.. tohh iss project mei kya humara sara interface jo work krega vo terminal ke through krega yaa kisi ui based interface ke sath integrate krke

Haan bhai — bahut important question hai, aur iska answer hai:

Nahi, humara final Calling Bot terminal-based interface nahi hoga.
Terminal abhi sirf development/testing interface hai. Final system ko proper UI + communication interfaces ke saath integrate karna chahiye.

Tum jo "layers" ki baat kar rahe ho, exactly wahi architecture me hume ab define karna chahiye.

🏗️ Calling Bot ki complete architecture
Main ise roughly 6 layers me divide karunga:

┌───────────────────────────────────────────────┐
│              USER INTERFACES                  │
│                                               │
│  Web UI     Mobile UI     Phone     Desktop   │
└───────────────────────┬───────────────────────┘
                        │
                        ▼
┌───────────────────────────────────────────────┐
│          COMMUNICATION / API LAYER            │
│                                               │
│ REST API │ WebSocket │ Telephony │ Voice      │
└───────────────────────┬───────────────────────┘
                        │
                        ▼
┌───────────────────────────────────────────────┐
│             CONVERSATION LAYER                │
│                                               │
│ Session │ Conversation │ Context │ State      │
└───────────────────────┬───────────────────────┘
                        │
                        ▼
┌───────────────────────────────────────────────┐
│                AI LAYER                       │
│                                               │
│ LLM Router │ Planner │ Memory │ Prompt Engine │
└───────────────────────┬───────────────────────┘
                        │
                        ▼
┌───────────────────────────────────────────────┐
│             TOOL / ACTION LAYER               │
│                                               │
│ Search │ APIs │ Database │ External Tools     │
└───────────────────────┬───────────────────────┘
                        │
                        ▼
┌───────────────────────────────────────────────┐
│          INFRASTRUCTURE / DATA                │
│                                               │
│ PostgreSQL │ Redis │ Logs │ Config │ Storage  │
└───────────────────────────────────────────────┘
And terminal is not one of the actual user-facing layers.

🖥️ Then terminal ka kya role hai?
Terminal रहेगा:

Developer Interface
For example:

uv run uvicorn backend.main:app --reload
or:

uv run pytest
or later maybe:

calling-bot chat
This is for developers/admin/debugging.

End user ko terminal nahi dikhna chahiye.

🌐 What should our actual UI be?
I recommend we eventually build a Web Dashboard.

Something like:

                 CALLING BOT
        ┌───────────────────────────┐
        │ Dashboard                 │
        │                           │
        │ Active Calls      12      │
        │ Conversations    148      │
        │ AI Calls         1,240    │
        │                           │
        │ ───────────────────────   │
        │                           │
        │ Recent Conversations      │
        │                           │
        │ 👤 Rahul                  │
        │    "Book appointment..."  │
        │                           │
        │ 👤 Ankit                  │
        │    "What's my balance?"  │
        └───────────────────────────┘
And another screen:

Conversation
────────────────────────────────

User
"Can you schedule a meeting?"

AI
"Sure. What time would you prefer?"

User
"Tomorrow at 4 PM."

AI
"Done. I've scheduled it for 4 PM."

────────────────────────────────
🎤  [Talk]       [End Call]
That would be the human-facing interface.

📞 But the actual Calling Bot has another interface
Since this is a Calling Bot, the phone itself is an interface.

For example:

Phone Call
    │
    ▼
Telephony Provider
    │
    ▼
STT
    │
    ▼
Conversation Engine
    │
    ▼
LLM
    │
    ▼
TTS
    │
    ▼
Phone
So the phone user doesn't need the web UI at all.

🔥 This is why our architecture matters
The Conversation Engine should not know whether the user came from:

Phone
Web
Mobile
Desktop
API
It should simply receive something like:

User Message
and produce:

Assistant Response
For example:

Phone
   │
   ▼
"What's my appointment time?"
   │
   ▼
Conversation Engine
   │
   ▼
"Your appointment is tomorrow at 4 PM."
   │
   ▼
TTS
   │
   ▼
Phone
But:

Web UI
   │
   ▼
"What's my appointment time?"
   │
   ▼
Conversation Engine
   │
   ▼
"Your appointment is tomorrow at 4 PM."
   │
   ▼
Web UI
Same brain. Different interface.

That's exactly what we want.

🧠 And this changes how we should divide today's work
This question actually came at the perfect time.

Before we create:

Conversation
Session
Message
Engine
we should define the overall system layers properly.

Because otherwise later we'll realize:

"Oh, we need WebSocket support."

or

"Oh, the UI needs streaming responses."

or

"Oh, telephony needs a different event format."

and then we'll have to restructure the core.

📐 I recommend this final architecture
Layer 1 — Presentation
Web Dashboard
Mobile App
Admin Panel
Layer 2 — Communication
REST API
WebSocket
Telephony
Voice
Layer 3 — Conversation
Session Manager
Conversation Manager
State Machine
Context Manager
Layer 4 — Intelligence
LLM Router
Prompt Engine
Memory
Planner
Reasoning
Layer 5 — Tools
Tool Registry
Search
Calendar
Database
External APIs
Actions
Layer 6 — Infrastructure
PostgreSQL
Redis
Object Storage
Logging
Configuration
👥 And now Piyush + Nikki can divide work much better
Instead of simply:

Piyush → Conversation
Nikki → Session
we can eventually divide the entire project into parallel streams.

You — Core/AI
Conversation Engine
State Machine
Context
LLM
Planner
Memory
Nikki — Interface/Platform
API
WebSocket
Dashboard
Session APIs
Integration
But I wouldn't lock this exact division yet. We need to see the architecture document and dependencies first.

🚀 What I would do now
Stop coding for a moment.

Today's first deliverable should actually be:

docs/12_System_Layers_and_Interfaces.md
Define:

1. Presentation Layer
2. Communication Layer
3. Conversation Layer
4. AI Layer
5. Tool Layer
6. Infrastructure Layer
And explicitly document:

Terminal
   ↓
Developer/Debug Interface

Web UI
   ↓
Human Interface

Phone
   ↓
Voice Interface

API
   ↓
Programmatic Interface
Then:

                    Interfaces
                        │
        ┌───────────────┼────────────────┐
        │               │                │
       Web            Phone            API
        │               │                │
        └───────────────┼────────────────┘
                        ↓
                Communication Layer
                        ↓
                Conversation Engine
                        ↓
                    AI Brain
                        ↓
                     Tools
                        ↓
                  Infrastructure
Once this is locked, we'll know exactly what we're building and where every future piece belongs.

And yes — final product should absolutely have a proper UI, not just terminal. The terminal is our developer console; the Web UI/phone/API are the actual product interfaces.


docs/12_System_Layers_and_Interfaces.md create tgis

Done bhai. ✅

Maine complete 12_System_Layers_and_Interfaces.md create kar diya hai.


Isme cover hai:

🖥️ Presentation Layer

🌐 REST/WebSocket/API Layer

📞 Telephony/Voice Layer

🧠 Conversation Layer

🤖 AI Layer

🛠️ Tool/Action Layer

🗄️ Infrastructure/Data Layer

💻 Terminal ka actual role

Web UI strategy

Phone-call flow

Interface independence

Security boundaries

Observability

Complete implementation order

Long-term target architecture

Piyush + Nikki ke development workflow ke liye boundaries

Important: Is document ke according terminal sirf developer/operations interface hai. Final product ka actual user interface Web UI + Phone/Voice + future Mobile/Desktop interfaces hoga.

Ab next step is file ko tumhare project ke docs/ folder me rakhna, review karna, aur phir develop ke through merge karna. 



Library
/
12_System_Layers_and_Interfaces.md


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

Library
/
12_System_Layers_and_Interfaces.md


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

