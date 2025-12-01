# DocuExtract System Diagrams

> **Last Updated:** November 30, 2025

---

## Table of Contents

1. [Activity Diagrams](#activity-diagrams)
   - [Document Upload Activity](#1-document-upload-activity-diagram)
   - [Duplicate Override Activity](#2-duplicate-override-activity-diagram)
   - [Query/Search Activity](#3-querysearch-activity-diagram)
   - [SFXBot Chat Activity](#4-sfxbot-chat-activity-diagram)
   - [SFXBot Thread Management Activity](#5-sfxbot-thread-management-activity-diagram)
2. [System Sequence Diagrams (SSD)](#system-sequence-diagrams)
   - [Document Upload SSD](#1-document-upload-sequence)
   - [Duplicate Override SSD](#2-duplicate-override-sequence)
   - [Version History SSD](#3-version-history-retrieval-sequence)
   - [Document Search SSD](#4-document-search-sequence)
   - [SFXBot Message Flow SSD](#5-sfxbot-message-flow-sequence)
   - [SFXBot Thread Operations SSD](#6-sfxbot-thread-operations-sequence)

---

## Activity Diagrams

### 1. Document Upload Activity Diagram

```
                                    ┌─────────────────┐
                                    │     START       │
                                    └────────┬────────┘
                                             │
                                             ▼
                                    ┌─────────────────┐
                                    │  User selects   │
                                    │   PDF file      │
                                    └────────┬────────┘
                                             │
                                             ▼
                                    ┌─────────────────┐
                                    │ Send file to    │
                                    │ /pdf/parse-pdf  │
                                    └────────┬────────┘
                                             │
                                             ▼
                                    ┌─────────────────┐
                                    │ Calculate       │
                                    │ content hash    │
                                    └────────┬────────┘
                                             │
                                             ▼
                              ┌──────────────────────────────┐
                              │    Check for duplicates      │
                              │  (filename & content_hash)   │
                              └──────────────┬───────────────┘
                                             │
                                             ▼
                                    ◇─────────────────◇
                                   ╱                   ╲
                                  ╱   Is duplicate?     ╲
                                 ╱                       ╲
                                ◇─────────────────────────◇
                               │                           │
                          [YES]│                           │[NO]
                               ▼                           ▼
                      ┌─────────────────┐        ┌─────────────────┐
                      │ Return 409      │        │ Parse PDF       │
                      │ Conflict with   │        │ Extract text    │
                      │ existing doc    │        │ & tables        │
                      └────────┬────────┘        └────────┬────────┘
                               │                          │
                               ▼                          ▼
                      ┌─────────────────┐        ┌─────────────────┐
                      │ Show Duplicate  │        │ Create chunks   │
                      │ Modal to user   │        │ with metadata   │
                      └────────┬────────┘        └────────┬────────┘
                               │                          │
                               ▼                          ▼
                      ◇─────────────────◇        ┌─────────────────┐
                     ╱                   ╲       │ Return chunks   │
                    ╱  User chooses       ╲      │ to frontend     │
                   ╱   action?             ╲     └────────┬────────┘
                  ◇─────────────────────────◇            │
                 │              │            │            ▼
           [Cancel]       [Override]    [View History]    │
                 │              │            │            │
                 ▼              ▼            ▼            │
         ┌───────────┐  ┌───────────┐  ┌───────────┐     │
         │   Close   │  │  Show     │  │  Fetch &  │     │
         │   modal   │  │ Confirm   │  │  show     │     │
         │           │  │  Modal    │  │ versions  │     │
         └─────┬─────┘  └─────┬─────┘  └─────┬─────┘     │
               │              │              │            │
               │              ▼              │            │
               │      ◇───────────────◇      │            │
               │     ╱                 ╲     │            │
               │    ╱  User confirms?   ╲    │            │
               │   ◇─────────────────────◇   │            │
               │   │                     │   │            │
               │ [NO]                 [YES]  │            │
               │   │                     │   │            │
               │   ▼                     ▼   │            ▼
               │ ┌───────┐      ┌─────────────────┐  ┌─────────────────┐
               │ │ Close │      │ Go to Override  │  │ User reviews    │
               │ │ modal │      │ Flow (see next) │  │ chunks in UI    │
               │ └───┬───┘      └────────┬────────┘  └────────┬────────┘
               │     │                   │                    │
               │     │                   │                    ▼
               │     │                   │           ┌─────────────────┐
               │     │                   │           │ User clicks     │
               │     │                   │           │ "Upload to KB"  │
               │     │                   │           └────────┬────────┘
               │     │                   │                    │
               │     │                   │                    ▼
               │     │                   │           ┌─────────────────┐
               │     │                   │           │ POST /kb/       │
               │     │                   │           │ upload-to-kb    │
               │     │                   │           └────────┬────────┘
               │     │                   │                    │
               │     │                   │                    ▼
               │     │                   │           ┌─────────────────┐
               │     │                   │           │ Insert to       │
               │     │                   │           │ Weaviate        │
               │     │                   │           └────────┬────────┘
               │     │                   │                    │
               │     │                   │                    ▼
               │     │                   │           ┌─────────────────┐
               │     │                   │           │ Save to SQLite  │
               │     │                   │           │ documents table │
               │     │                   │           └────────┬────────┘
               │     │                   │                    │
               │     │                   │                    ▼
               │     │                   │           ┌─────────────────┐
               │     │                   │           │ Show Success    │
               │     │                   │           │ Modal           │
               └─────┴───────────────────┴───────────┴────────┬────────┘
                                                              │
                                                              ▼
                                                     ┌─────────────────┐
                                                     │      END        │
                                                     └─────────────────┘
```

---

### 2. Duplicate Override Activity Diagram (Updated)

> **Key Change:** Override now re-parses the PDF before uploading.

```
                                    ┌─────────────────┐
                                    │     START       │
                                    │ (from Duplicate │
                                    │   Detection)    │
                                    └────────┬────────┘
                                             │
                                             ▼
                                    ┌─────────────────┐
                                    │ User clicks     │
                                    │ "Override"      │
                                    └────────┬────────┘
                                             │
                                             ▼
                                    ┌─────────────────┐
                                    │ Show Override   │
                                    │ Confirmation    │
                                    │ Modal           │
                                    └────────┬────────┘
                                             │
                                             ▼
                                    ◇─────────────────◇
                                   ╱                   ╲
                                  ╱  User confirms?     ╲
                                 ╱                       ╲
                                ◇─────────────────────────◇
                               │                           │
                          [NO] │                           │ [YES]
                               ▼                           ▼
                      ┌─────────────────┐        ┌─────────────────┐
                      │ Close modal     │        │ Close both      │
                      │ Return to       │        │ modals          │
                      │ duplicate modal │        └────────┬────────┘
                      └────────┬────────┘                 │
                               │                          ▼
                               │                 ┌─────────────────┐
                               │                 │ Set state:      │
                               │                 │ forceReplaceMode│
                               │                 │ = true          │
                               │                 └────────┬────────┘
                               │                          │
                               │                          ▼
                               │                 ┌─────────────────┐
                               │                 │ RE-PARSE PDF:   │
                               │                 │ POST /pdf/      │
                               │                 │ parse-pdf with  │
                               │                 │ force_reparse   │
                               │                 │ = "true"        │
                               │                 └────────┬────────┘
                               │                          │
                               │                          ▼
                               │                 ┌─────────────────┐
                               │                 │ Backend skips   │
                               │                 │ duplicate check │
                               │                 │ Parses PDF      │
                               │                 └────────┬────────┘
                               │                          │
                               │                          ▼
                               │                 ┌─────────────────┐
                               │                 │ Display chunks  │
                               │                 │ for review      │
                               │                 │ Save to         │
                               │                 │ localStorage    │
                               │                 └────────┬────────┘
                               │                          │
                               │                          ▼
                               │                 ┌─────────────────┐
                               │                 │ User clicks     │
                               │                 │ "Upload to KB"  │
                               │                 └────────┬────────┘
                               │                          │
                               │                          ▼
                               │                 ┌─────────────────┐
                               │                 │ POST /kb/       │
                               │                 │ upload-to-kb    │
                               │                 │ force_replace   │
                               │                 │ = true          │
                               │                 └────────┬────────┘
                               │                          │
                               │                          ▼
                               │                 ┌─────────────────┐
                               │                 │ BACKEND:        │
                               │                 │ Archive version │
                               │                 │ Delete old from │
                               │                 │ SQLite+Weaviate │
                               │                 └────────┬────────┘
                               │                          │
                               │                          ▼
                               │                 ┌─────────────────┐
                               │                 │ Calculate next  │
                               │                 │ version number  │
                               │                 └────────┬────────┘
                               │                          │
                               │                          ▼
                               │                 ┌─────────────────┐
                               │                 │ Delete old doc  │
                               │                 │ from SQLite &   │
                               │                 │ Weaviate        │
                               │                 └────────┬────────┘
                               │                          │
                               │                          ▼
                               │                 ┌─────────────────┐
                               │                 │ Insert new doc  │
                               │                 │ to Weaviate     │
                               │                 │ (with new       │
                               │                 │ embeddings)     │
                               │                 └────────┬────────┘
                               │                          │
                               │                          ▼
                               │                 ┌─────────────────┐
                               │                 │ Save new doc    │
                               │                 │ to SQLite with  │
                               │                 │ new version #   │
                               │                 └────────┬────────┘
                               │                          │
                               │                          ▼
                               │                 ┌─────────────────┐
                               │                 │ Return response │
                               │                 │ with version    │
                               │                 │ info            │
                               │                 └────────┬────────┘
                               │                          │
                               │                          ▼
                               │                 ┌─────────────────┐
                               │                 │ Show Success    │
                               │                 │ Modal with      │
                               │                 │ version details │
                               │                 └────────┬────────┘
                               │                          │
                               └──────────────────────────┤
                                                          │
                                                          ▼
                                                 ┌─────────────────┐
                                                 │      END        │
                                                 └─────────────────┘
```

---

### 3. Query/Search Activity Diagram

```
                                    ┌─────────────────┐
                                    │     START       │
                                    └────────┬────────┘
                                             │
                                             ▼
                                    ┌─────────────────┐
                                    │ User enters     │
                                    │ search query    │
                                    └────────┬────────┘
                                             │
                                             ▼
                                    ┌─────────────────┐
                                    │ POST /chat/send │
                                    └────────┬────────┘
                                             │
                                             ▼
                                    ┌─────────────────┐
                                    │ Generate query  │
                                    │ embedding via   │
                                    │ OpenAI API      │
                                    └────────┬────────┘
                                             │
                                             ▼
                                    ┌─────────────────┐
                                    │ Vector search   │
                                    │ in Weaviate     │
                                    │ (cosine sim.)   │
                                    └────────┬────────┘
                                             │
                                             ▼
                                    ┌─────────────────┐
                                    │ Retrieve top-k  │
                                    │ similar chunks  │
                                    └────────┬────────┘
                                             │
                                             ▼
                                    ┌─────────────────┐
                                    │ Rank & filter   │
                                    │ chunks by       │
                                    │ relevance       │
                                    └────────┬────────┘
                                             │
                                             ▼
                                    ┌─────────────────┐
                                    │ Build context   │
                                    │ from chunks     │
                                    └────────┬────────┘
                                             │
                                             ▼
                                    ┌─────────────────┐
                                    │ Send context +  │
                                    │ query to GPT    │
                                    └────────┬────────┘
                                             │
                                             ▼
                                    ┌─────────────────┐
                                    │ Generate AI     │
                                    │ response        │
                                    └────────┬────────┘
                                             │
                                             ▼
                                    ┌─────────────────┐
                                    │ Return response │
                                    │ to frontend     │
                                    └────────┬────────┘
                                             │
                                             ▼
                                    ┌─────────────────┐
                                    │ Display in      │
                                    │ chat interface  │
                                    └────────┬────────┘
                                             │
                                             ▼
                                    ┌─────────────────┐
                                    │      END        │
                                    └─────────────────┘
```

---

### 4. SFXBot Chat Activity Diagram

```
                                    ┌─────────────────┐
                                    │     START       │
                                    └────────┬────────┘
                                             │
                                             ▼
                                    ┌─────────────────┐
                                    │ User opens      │
                                    │ SFXBot page     │
                                    └────────┬────────┘
                                             │
                                             ▼
                                    ┌─────────────────┐
                                    │ Fetch user      │
                                    │ sessions/threads│
                                    └────────┬────────┘
                                             │
                                             ▼
                                    ◇─────────────────◇
                                   ╱                   ╲
                                  ╱  Active thread?     ╲
                                 ╱                       ╲
                                ◇─────────────────────────◇
                               │                           │
                          [NO] │                           │ [YES]
                               ▼                           ▼
                      ┌─────────────────┐        ┌─────────────────┐
                      │ Show welcome    │        │ Load thread     │
                      │ screen with     │        │ history         │
                      │ suggestions     │        └────────┬────────┘
                      └────────┬────────┘                 │
                               │                          ▼
                               │                 ┌─────────────────┐
                               │                 │ Display messages│
                               │                 │ in chat         │
                               │                 └────────┬────────┘
                               │                          │
                               │                          ▼
                               │                 ┌─────────────────┐
                               │                 │ Load token usage│
                               │                 │ (session & total)│
                               │                 └────────┬────────┘
                               │                          │
                               └──────────────────────────┤
                                                          │
                                                          ▼
                                                 ┌─────────────────┐
                                                 │ User enters     │
                                                 │ message         │
                                                 └────────┬────────┘
                                                          │
                                                          ▼
                                                 ◇─────────────────◇
                                                ╱                   ╲
                                               ╱  Has active thread? ╲
                                              ╱                       ╲
                                             ◇─────────────────────────◇
                                            │                           │
                                       [NO] │                           │ [YES]
                                            ▼                           ▼
                                   ┌─────────────────┐        ┌─────────────────┐
                                   │ POST /chat/     │        │ Add user message│
                                   │ session/new     │        │ to UI           │
                                   └────────┬────────┘        └────────┬────────┘
                                            │                          │
                                            ▼                          ▼
                                   ┌─────────────────┐        ┌─────────────────┐
                                   │ Create new      │        │ Add placeholder │
                                   │ session with    │        │ for assistant   │
                                   │ auto-title      │        │ message         │
                                   └────────┬────────┘        └────────┬────────┘
                                            │                          │
                                            ▼                          ▼
                                   ┌─────────────────┐        ┌─────────────────┐
                                   │ Update threads  │        │ POST /chat/     │
                                   │ list            │        │ message         │
                                   └────────┬────────┘        └────────┬────────┘
                                            │                          │
                                            └──────────────┬───────────┘
                                                           │
                                                           ▼
                                                  ┌─────────────────┐
                                                  │ Backend sends   │
                                                  │ to OpenAI       │
                                                  └────────┬────────┘
                                                           │
                                                           ▼
                                                  ┌─────────────────┐
                                                  │ Backend builds  │
                                                  │ context from KB │
                                                  └────────┬────────┘
                                                           │
                                                           ▼
                                                  ┌─────────────────┐
                                                  │ Generate AI     │
                                                  │ response        │
                                                  └────────┬────────┘
                                                           │
                                                           ▼
                                                  ┌─────────────────┐
                                                  │ Update assistant│
                                                  │ message in UI   │
                                                  └────────┬────────┘
                                                           │
                                                           ▼
                                                  ┌─────────────────┐
                                                  │ Refresh token   │
                                                  │ usage stats     │
                                                  └────────┬────────┘
                                                           │
                                                           ▼
                                                  ┌─────────────────┐
                                                  │ Scroll to bottom│
                                                  └────────┬────────┘
                                                           │
                                                           ▼
                                                  ◇─────────────────◇
                                                 ╱                   ╲
                                                ╱  User continues     ╲
                                               ╱   chatting?           ╲
                                              ◇─────────────────────────◇
                                             │                           │
                                        [YES]│                           │[NO]
                                             │                           │
                                             │                           ▼
                                             │                  ┌─────────────────┐
                                             └─────────────────>│      END        │
                                                                └─────────────────┘
```

---

### 5. SFXBot Thread Management Activity Diagram

```
                                    ┌─────────────────┐
                                    │     START       │
                                    │  (Thread Mgmt)  │
                                    └────────┬────────┘
                                             │
                                             ▼
                                    ◇─────────────────◇
                                   ╱                   ╲
                                  ╱   User action?      ╲
                                 ╱                       ╲
                                ◇─────────────────────────◇
                               ╱            │              ╲
                [Create New] ╱              │               ╲ [Switch Thread]
                           ╱                │                ╲
                          ▼                 │                 ▼
                 ┌─────────────────┐        │        ┌─────────────────┐
                 │ Click "New Chat"│        │        │ Click thread    │
                 │ button          │        │        │ from sidebar    │
                 └────────┬────────┘        │        └────────┬────────┘
                          │                 │                 │
                          ▼                 │                 ▼
                 ┌─────────────────┐        │        ┌─────────────────┐
                 │ POST /chat/     │        │        │ GET /chat/      │
                 │ session/new     │        │        │ session/{id}/   │
                 └────────┬────────┘        │        │ history         │
                          │                 │        └────────┬────────┘
                          ▼                 │                 │
                 ┌─────────────────┐        │                 ▼
                 │ Create session  │        │        ┌─────────────────┐
                 │ without title   │        │        │ Load message    │
                 │ (auto-gen later)│        │        │ history         │
                 └────────┬────────┘        │        └────────┬────────┘
                          │                 │                 │
                          ▼                 │                 ▼
                 ┌─────────────────┐        │        ┌─────────────────┐
                 │ Set as active   │        │        │ Set as active   │
                 │ thread          │        │        │ thread          │
                 └────────┬────────┘        │        └────────┬────────┘
                          │                 │                 │
                          ▼                 │                 ▼
                 ┌─────────────────┐        │        ┌─────────────────┐
                 │ Clear messages  │        │        │ Display messages│
                 └────────┬────────┘        │        └────────┬────────┘
                          │                 │                 │
                          └─────────────────┼─────────────────┘
                                            │
                                            │ [Edit Title]
                                            │
                                            ▼
                                   ┌─────────────────┐
                                   │ Click edit icon │
                                   │ on thread       │
                                   └────────┬────────┘
                                            │
                                            ▼
                                   ┌─────────────────┐
                                   │ Show inline     │
                                   │ edit input      │
                                   └────────┬────────┘
                                            │
                                            ▼
                                   ┌─────────────────┐
                                   │ User edits title│
                                   └────────┬────────┘
                                            │
                                            ▼
                                   ◇─────────────────◇
                                  ╱                   ╲
                                 ╱   Save or cancel?   ╲
                                ╱                       ╲
                               ◇─────────────────────────◇
                              │                           │
                        [Save]│                           │[Cancel]
                              ▼                           ▼
                     ┌─────────────────┐        ┌─────────────────┐
                     │ PATCH /chat/    │        │ Revert to       │
                     │ session/{id}/   │        │ original title  │
                     │ title           │        └────────┬────────┘
                     └────────┬────────┘                 │
                              │                          │
                              ▼                          │
                     ┌─────────────────┐                 │
                     │ Update title    │                 │
                     │ in backend      │                 │
                     └────────┬────────┘                 │
                              │                          │
                              ▼                          │
                     ┌─────────────────┐                 │
                     │ Update thread   │                 │
                     │ in local state  │                 │
                     └────────┬────────┘                 │
                              │                          │
                              └──────────────────────────┤
                                                         │
                                                         │
                                            [Delete Thread]
                                                         │
                                                         ▼
                                                ┌─────────────────┐
                                                │ Click delete    │
                                                │ icon (X)        │
                                                └────────┬────────┘
                                                         │
                                                         ▼
                                                ┌─────────────────┐
                                                │ Show Delete     │
                                                │ Confirmation    │
                                                │ Modal           │
                                                └────────┬────────┘
                                                         │
                                                         ▼
                                                ◇─────────────────◇
                                               ╱                   ╲
                                              ╱  User confirms      ╲
                                             ╱   deletion?           ╲
                                            ◇─────────────────────────◇
                                           │                           │
                                      [YES]│                           │[NO]
                                           ▼                           ▼
                                  ┌─────────────────┐        ┌─────────────────┐
                                  │ DELETE /chat/   │        │ Close modal     │
                                  │ session/{id}    │        │ No changes      │
                                  └────────┬────────┘        └────────┬────────┘
                                           │                          │
                                           ▼                          │
                                  ┌─────────────────┐                 │
                                  │ Remove thread   │                 │
                                  │ from backend    │                 │
                                  └────────┬────────┘                 │
                                           │                          │
                                           ▼                          │
                                  ┌─────────────────┐                 │
                                  │ Remove from     │                 │
                                  │ threads list    │                 │
                                  └────────┬────────┘                 │
                                           │                          │
                                           ▼                          │
                                  ◇─────────────────◇                 │
                                 ╱                   ╲                │
                                ╱  Was active thread? ╲               │
                               ╱                       ╲              │
                              ◇─────────────────────────◇             │
                             │                           │            │
                        [YES]│                           │[NO]        │
                             ▼                           ▼            │
                    ┌─────────────────┐        ┌─────────────────┐   │
                    │ Clear active    │        │ Keep current    │   │
                    │ thread ID       │        │ view            │   │
                    └────────┬────────┘        └────────┬────────┘   │
                             │                          │            │
                             ▼                          │            │
                    ┌─────────────────┐                 │            │
                    │ Clear messages  │                 │            │
                    │ Show welcome    │                 │            │
                    └────────┬────────┘                 │            │
                             │                          │            │
                             └──────────────────────────┴────────────┘
                                                        │
                                                        ▼
                                               ┌─────────────────┐
                                               │      END        │
                                               └─────────────────┘
```

---

## System Sequence Diagrams

### 1. Document Upload Sequence

```
┌──────────┐          ┌──────────┐          ┌──────────┐          ┌──────────┐          ┌──────────┐
│  User    │          │ Frontend │          │ Backend  │          │  SQLite  │          │ Weaviate │
│          │          │ (React)  │          │ (FastAPI)│          │          │          │          │
└────┬─────┘          └────┬─────┘          └────┬─────┘          └────┬─────┘          └────┬─────┘
     │                     │                     │                     │                     │
     │ 1. Select PDF       │                     │                     │                     │
     │────────────────────>│                     │                     │                     │
     │                     │                     │                     │                     │
     │                     │ 2. POST /pdf/parse-pdf                    │                     │
     │                     │     (multipart/form-data)                 │                     │
     │                     │────────────────────>│                     │                     │
     │                     │                     │                     │                     │
     │                     │                     │ 3. Calculate SHA256 │                     │
     │                     │                     │    content_hash     │                     │
     │                     │                     │─────────┐           │                     │
     │                     │                     │         │           │                     │
     │                     │                     │<────────┘           │                     │
     │                     │                     │                     │                     │
     │                     │                     │ 4. SELECT by filename & hash             │
     │                     │                     │────────────────────>│                     │
     │                     │                     │                     │                     │
     │                     │                     │ 5. Return: no duplicate                  │
     │                     │                     │<────────────────────│                     │
     │                     │                     │                     │                     │
     │                     │                     │ 6. Parse PDF        │                     │
     │                     │                     │    Extract & chunk  │                     │
     │                     │                     │─────────┐           │                     │
     │                     │                     │         │           │                     │
     │                     │                     │<────────┘           │                     │
     │                     │                     │                     │                     │
     │                     │ 7. Return: {chunks, document_metadata,    │                     │
     │                     │     content_hash, file_size_bytes}        │                     │
     │                     │<────────────────────│                     │                     │
     │                     │                     │                     │                     │
     │ 8. Display chunks   │                     │                     │                     │
     │    preview          │                     │                     │                     │
     │<────────────────────│                     │                     │                     │
     │                     │                     │                     │                     │
     │ 9. Click "Upload    │                     │                     │                     │
     │    to KB"           │                     │                     │                     │
     │────────────────────>│                     │                     │                     │
     │                     │                     │                     │                     │
     │                     │ 10. POST /kb/upload-to-kb                 │                     │
     │                     │     {chunks, metadata, filename,          │                     │
     │                     │      content_hash, file_size_bytes}       │                     │
     │                     │────────────────────>│                     │                     │
     │                     │                     │                     │                     │
     │                     │                     │ 11. Insert Document & DocumentChunks     │
     │                     │                     │────────────────────────────────────────────>
     │                     │                     │                     │                     │
     │                     │                     │ 12. Return: weaviate_doc_id              │
     │                     │                     │<────────────────────────────────────────────
     │                     │                     │                     │                     │
     │                     │                     │ 13. INSERT INTO documents                │
     │                     │                     │────────────────────>│                     │
     │                     │                     │                     │                     │
     │                     │                     │ 14. Return: success │                     │
     │                     │                     │<────────────────────│                     │
     │                     │                     │                     │                     │
     │                     │ 15. Return: {success, doc_id,             │                     │
     │                     │      weaviate_doc_id, action, version}    │                     │
     │                     │<────────────────────│                     │                     │
     │                     │                     │                     │                     │
     │ 16. Show Success    │                     │                     │                     │
     │     Modal           │                     │                     │                     │
     │<────────────────────│                     │                     │                     │
     │                     │                     │                     │                     │
```

---

### 2. Duplicate Override Sequence (Updated)

> **Key Change:** Override now re-parses the PDF before uploading.

```
┌──────────┐          ┌──────────┐          ┌──────────┐          ┌──────────┐          ┌──────────┐
│  User    │          │ Frontend │          │ Backend  │          │  SQLite  │          │ Weaviate │
│          │          │ (React)  │          │ (FastAPI)│          │          │          │          │
└────┬─────┘          └────┬─────┘          └────┬─────┘          └────┬─────┘          └────┬─────┘
     │                     │                     │                     │                     │
     │ [Duplicate Modal    │                     │                     │                     │
     │  is showing]        │                     │                     │                     │
     │                     │                     │                     │                     │
     │ 1. Click "Override" │                     │                     │                     │
     │────────────────────>│                     │                     │                     │
     │                     │                     │                     │                     │
     │ 2. Show Confirm     │                     │                     │                     │
     │    Modal            │                     │                     │                     │
     │<────────────────────│                     │                     │                     │
     │                     │                     │                     │                     │
     │ 3. Click "Yes,      │                     │                     │                     │
     │    Override"        │                     │                     │                     │
     │────────────────────>│                     │                     │                     │
     │                     │                     │                     │                     │
     │                     │ 4. Close modals, set forceReplaceMode=true                      │
     │                     │─────────┐           │                     │                     │
     │                     │         │           │                     │                     │
     │                     │<────────┘           │                     │                     │
     │                     │                     │                     │                     │
     │                     │ 5. POST /pdf/parse-pdf                    │                     │
     │                     │    {file, force_reparse: "true"}          │                     │
     │                     │────────────────────>│                     │                     │
     │                     │                     │                     │                     │
     │                     │                     │ 6. Skip duplicate check (force_reparse)  │
     │                     │                     │    Parse PDF, create chunks               │
     │                     │                     │─────────┐           │                     │
     │                     │                     │         │           │                     │
     │                     │                     │<────────┘           │                     │
     │                     │                     │                     │                     │
     │                     │ 7. Return: {chunks, document_metadata,    │                     │
     │                     │     content_hash, file_size_bytes}        │                     │
     │                     │<────────────────────│                     │                     │
     │                     │                     │                     │                     │
     │                     │ 8. Save to localStorage                   │                     │
     │                     │    Display chunks for review              │                     │
     │                     │─────────┐           │                     │                     │
     │                     │<────────┘           │                     │                     │
     │                     │                     │                     │                     │
     │ 9. Review/edit      │                     │                     │                     │
     │    chunks           │                     │                     │                     │
     │<────────────────────│                     │                     │                     │
     │                     │                     │                     │                     │
     │ 10. Click "Upload   │                     │                     │                     │
     │     to KB"          │                     │                     │                     │
     │────────────────────>│                     │                     │                     │
     │                     │                     │                     │                     │
     │                     │ 11. POST /kb/upload-to-kb                 │                     │
     │                     │    {chunks, ..., force_replace: true}     │                     │
     │                     │────────────────────>│                     │                     │
     │                     │                     │                     │                     │
     │                     │                     │ 12. SELECT existing doc by filename      │
     │                     │                     │────────────────────>│                     │
     │                     │                     │                     │                     │
     │                     │                     │ 13. Return existing doc (with weaviate_doc_id)
     │                     │                     │<────────────────────│                     │
     │                     │                     │                     │                     │
     │                     │                     │ 14. INSERT INTO document_versions        │
     │                     │                     │    (archive current version)             │
     │                     │                     │────────────────────>│                     │
     │                     │                     │                     │                     │
     │                     │                     │ 15. DELETE FROM documents (old doc)      │
     │                     │                     │────────────────────>│                     │
     │                     │                     │                     │                     │
     │                     │                     │ 16. DELETE Document & Chunks using       │
     │                     │                     │     weaviate_doc_id (NOT doc_id)         │
     │                     │                     │────────────────────────────────────────────>
     │                     │                     │                     │                     │
     │                     │                     │ 17. INSERT new Document & Chunks         │
     │                     │                     │────────────────────────────────────────────>
     │                     │                     │                     │                     │
     │                     │                     │ 18. Return: new weaviate_doc_id          │
     │                     │                     │<────────────────────────────────────────────
     │                     │                     │                     │                     │
     │                     │                     │ 19. INSERT INTO documents                │
     │                     │                     │     (new doc with new version)           │
     │                     │                     │────────────────────>│                     │
     │                     │                     │                     │                     │
     │                     │ 20. Return: {success, doc_id, action:"replaced",               │
     │                     │     version: 2, version_info: {previous_version: {...}}}       │
     │                     │<────────────────────│                     │                     │
     │                     │                     │                     │                     │
     │                     │ 21. Clear localStorage                    │                     │
     │                     │─────────┐           │                     │                     │
     │                     │<────────┘           │                     │                     │
     │                     │                     │                     │                     │
     │ 22. Show Success    │                     │                     │                     │
     │     Modal with      │                     │                     │                     │
     │     version info    │                     │                     │                     │
     │<────────────────────│                     │                     │                     │
     │                     │                     │                     │                     │
```

---

### 3. Version History Retrieval Sequence

```
┌──────────┐          ┌──────────┐          ┌──────────┐          ┌──────────┐
│  User    │          │ Frontend │          │ Backend  │          │  SQLite  │
│          │          │ (React)  │          │ (FastAPI)│          │          │
└────┬─────┘          └────┬─────┘          └────┬─────┘          └────┬─────┘
     │                     │                     │                     │
     │ 1. Click "View      │                     │                     │
     │    Version History" │                     │                     │
     │────────────────────>│                     │                     │
     │                     │                     │                     │
     │                     │ 2. GET /kb/document-versions/{file_name}  │
     │                     │────────────────────>│                     │
     │                     │                     │                     │
     │                     │                     │ 3. SELECT FROM documents                 │
     │                     │                     │    WHERE file_name = ?                   │
     │                     │                     │────────────────────>│
     │                     │                     │                     │
     │                     │                     │ 4. Return current_doc                    │
     │                     │                     │<────────────────────│
     │                     │                     │                     │
     │                     │                     │ 5. SELECT FROM document_versions         │
     │                     │                     │    WHERE file_name = ?                   │
     │                     │                     │    ORDER BY version_number DESC          │
     │                     │                     │────────────────────>│
     │                     │                     │                     │
     │                     │                     │ 6. Return versions []                    │
     │                     │                     │<────────────────────│
     │                     │                     │                     │
     │                     │ 7. Return: {success, file_name,           │
     │                     │     current_version: {...},               │
     │                     │     version_history: [...],               │
     │                     │     total_versions: N}                    │
     │                     │<────────────────────│                     │
     │                     │                     │                     │
     │ 8. Show Version     │                     │                     │
     │    History Modal    │                     │                     │
     │<────────────────────│                     │                     │
     │                     │                     │                     │
```

---

### 4. Document Search Sequence

```
┌──────────┐          ┌──────────┐          ┌──────────┐          ┌──────────┐          ┌──────────┐
│  User    │          │ Frontend │          │ Backend  │          │  OpenAI  │          │ Weaviate │
│          │          │ (React)  │          │ (FastAPI)│          │   API    │          │          │
└────┬─────┘          └────┬─────┘          └────┬─────┘          └────┬─────┘          └────┬─────┘
     │                     │                     │                     │                     │
     │ 1. Enter search     │                     │                     │                     │
     │    query            │                     │                     │                     │
     │────────────────────>│                     │                     │                     │
     │                     │                     │                     │                     │
     │                     │ 2. POST /chat/send  │                     │                     │
     │                     │    {query: "..."}   │                     │                     │
     │                     │────────────────────>│                     │                     │
     │                     │                     │                     │                     │
     │                     │                     │ 3. POST /v1/embeddings                   │
     │                     │                     │    {model: "text-embedding-3-small",     │
     │                     │                     │     input: "user query"}                 │
     │                     │                     │────────────────────>│                     │
     │                     │                     │                     │                     │
     │                     │                     │ 4. Return: embedding                     │
     │                     │                     │    [1536 floats]    │                     │
     │                     │                     │<────────────────────│                     │
     │                     │                     │                     │                     │
     │                     │                     │ 5. nearVector search in                  │
     │                     │                     │    DocumentChunk collection              │
     │                     │                     │────────────────────────────────────────────>
     │                     │                     │                     │                     │
     │                     │                     │ 6. Return: top-k chunks                  │
     │                     │                     │    with similarity scores                │
     │                     │                     │<────────────────────────────────────────────
     │                     │                     │                     │                     │
     │                     │                     │ 7. Build context from chunks             │
     │                     │                     │─────────┐           │                     │
     │                     │                     │         │           │                     │
     │                     │                     │<────────┘           │                     │
     │                     │                     │                     │                     │
     │                     │                     │ 8. POST /v1/chat/completions             │
     │                     │                     │    {messages: [system, context, query]}  │
     │                     │                     │────────────────────>│                     │
     │                     │                     │                     │                     │
     │                     │                     │ 9. Return: AI response                   │
     │                     │                     │<────────────────────│                     │
     │                     │                     │                     │                     │
     │                     │ 10. Return: {response, chunks_used}       │                     │
     │                     │<────────────────────│                     │                     │
     │                     │                     │                     │                     │
     │ 11. Display AI      │                     │                     │                     │
     │     response in chat│                     │                     │                     │
     │<────────────────────│                     │                     │                     │
     │                     │                     │                     │                     │
```

---

### 5. SFXBot Message Flow Sequence

```
┌──────────┐          ┌──────────┐          ┌──────────┐          ┌──────────┐          ┌──────────┐
│  User    │          │ Frontend │          │ Backend  │          │  OpenAI  │          │ Database │
│          │          │ (React)  │          │ (FastAPI)│          │   API    │          │ (SQLite) │
└────┬─────┘          └────┬─────┘          └────┬─────┘          └────┬─────┘          └────┬─────┘
     │                     │                     │                     │                     │
     │ 1. Type message     │                     │                     │                     │
     │    and press Enter  │                     │                     │                     │
     │────────────────────>│                     │                     │                     │
     │                     │                     │                     │                     │
     │                     │ 2. Check activeThreadId                   │                     │
     │                     │─────────┐           │                     │                     │
     │                     │         │           │                     │                     │
     │                     │<────────┘           │                     │                     │
     │                     │                     │                     │                     │
     │                     │ 3. If no thread: POST /chat/session/new   │                     │
     │                     │────────────────────>│                     │                     │
     │                     │                     │                     │                     │
     │                     │                     │ 4. INSERT INTO chat_sessions              │
     │                     │                     │────────────────────────────────────────────>
     │                     │                     │                     │                     │
     │                     │                     │ 5. Return: session_id                     │
     │                     │                     │<────────────────────────────────────────────
     │                     │                     │                     │                     │
     │                     │ 6. Return: {success, session_id}          │                     │
     │                     │<────────────────────│                     │                     │
     │                     │                     │                     │                     │
     │                     │ 7. Set activeThreadId                     │                     │
     │                     │    Update threads list                    │                     │
     │                     │─────────┐           │                     │                     │
     │                     │<────────┘           │                     │                     │
     │                     │                     │                     │                     │
     │                     │ 8. Add user message to UI                 │                     │
     │                     │─────────┐           │                     │                     │
     │                     │<────────┘           │                     │                     │
     │                     │                     │                     │                     │
     │ 9. Display user msg │                     │                     │                     │
     │<────────────────────│                     │                     │                     │
     │                     │                     │                     │                     │
     │                     │ 10. Add assistant placeholder             │                     │
     │                     │─────────┐           │                     │                     │
     │                     │<────────┘           │                     │                     │
     │                     │                     │                     │                     │
     │                     │ 11. POST /chat/message                    │                     │
     │                     │     {session_id, message,                 │                     │
     │                     │      options: {include_context: true}}    │                     │
     │                     │────────────────────>│                     │                     │
     │                     │                     │                     │                     │
     │                     │                     │ 12. GET session context                   │
     │                     │                     │────────────────────────────────────────────>
     │                     │                     │                     │                     │
     │                     │                     │ 13. Return: conversation history          │
     │                     │                     │<────────────────────────────────────────────
     │                     │                     │                     │                     │
     │                     │                     │ 14. Search knowledge base (if enabled)    │
     │                     │                     │─────────┐           │                     │
     │                     │                     │         │           │                     │
     │                     │                     │<────────┘           │                     │
     │                     │                     │                     │                     │
     │                     │                     │ 15. POST /v1/chat/completions             │
     │                     │                     │     {messages: [...context, user_msg]}    │
     │                     │                     │────────────────────>│                     │
     │                     │                     │                     │                     │
     │                     │                     │ 16. Return: AI response                   │
     │                     │                     │<────────────────────│                     │
     │                     │                     │                     │                     │
     │                     │                     │ 17. Save user & assistant messages        │
     │                     │                     │────────────────────────────────────────────>
     │                     │                     │                     │                     │
     │                     │                     │ 18. Update token usage                    │
     │                     │                     │────────────────────────────────────────────>
     │                     │                     │                     │                     │
     │                     │                     │ 19. Auto-generate title (if first msg)    │
     │                     │                     │─────────┐           │                     │
     │                     │                     │         │           │                     │
     │                     │                     │<────────┘           │                     │
     │                     │                     │                     │                     │
     │                     │ 20. Return: {success, content,            │                     │
     │                     │     sources, metadata}                    │                     │
     │                     │<────────────────────│                     │                     │
     │                     │                     │                     │                     │
     │                     │ 21. Update assistant message              │                     │
     │                     │─────────┐           │                     │                     │
     │                     │<────────┘           │                     │                     │
     │                     │                     │                     │                     │
     │ 22. Display AI      │                     │                     │                     │
     │     response        │                     │                     │                     │
     │<────────────────────│                     │                     │                     │
     │                     │                     │                     │                     │
     │                     │ 23. Fetch token usage stats               │                     │
     │                     │────────────────────>│                     │                     │
     │                     │                     │                     │                     │
     │                     │                     │ 24. GET session tokens                    │
     │                     │                     │────────────────────────────────────────────>
     │                     │                     │                     │                     │
     │                     │                     │ 25. GET user total tokens                 │
     │                     │                     │────────────────────────────────────────────>
     │                     │                     │                     │                     │
     │                     │                     │ 26. Return: token usage                   │
     │                     │                     │<────────────────────────────────────────────
     │                     │                     │                     │                     │
     │                     │ 27. Return: {session_tokens,              │                     │
     │                     │     total_tokens, costs}                  │                     │
     │                     │<────────────────────│                     │                     │
     │                     │                     │                     │                     │
     │                     │ 28. Update token display                  │                     │
     │                     │─────────┐           │                     │                     │
     │                     │<────────┘           │                     │                     │
     │                     │                     │                     │                     │
     │ 29. View updated    │                     │                     │                     │
     │     token stats     │                     │                     │                     │
     │<────────────────────│                     │                     │                     │
     │                     │                     │                     │                     │
```

---

### 6. SFXBot Thread Operations Sequence

```
┌──────────┐          ┌──────────┐          ┌──────────┐          ┌──────────┐
│  User    │          │ Frontend │          │ Backend  │          │ Database │
│          │          │ (React)  │          │ (FastAPI)│          │ (SQLite) │
└────┬─────┘          └────┬─────┘          └────┬─────┘          └────┬─────┘
     │                     │                     │                     │
     │ === CREATE NEW THREAD ===                 │                     │
     │                     │                     │                     │
     │ 1. Click "New Chat" │                     │                     │
     │────────────────────>│                     │                     │
     │                     │                     │                     │
     │                     │ 2. POST /chat/session/new                 │
     │                     │────────────────────>│                     │
     │                     │                     │                     │
     │                     │                     │ 3. INSERT INTO chat_sessions             │
     │                     │                     │     (no title - auto-gen later)          │
     │                     │                     │────────────────────>│
     │                     │                     │                     │
     │                     │                     │ 4. Return: new row  │
     │                     │                     │<────────────────────│
     │                     │                     │                     │
     │                     │ 5. Return: {success, session_id, session} │
     │                     │<────────────────────│                     │
     │                     │                     │                     │
     │                     │ 6. Add to threads list                    │
     │                     │    Set as active thread                   │
     │                     │    Clear messages                         │
     │                     │─────────┐           │                     │
     │                     │<────────┘           │                     │
     │                     │                     │                     │
     │ 7. Show empty chat  │                     │                     │
     │<────────────────────│                     │                     │
     │                     │                     │                     │
     │                     │                     │                     │
     │ === SWITCH THREAD ===                     │                     │
     │                     │                     │                     │
     │ 8. Click thread     │                     │                     │
     │    from sidebar     │                     │                     │
     │────────────────────>│                     │                     │
     │                     │                     │                     │
     │                     │ 9. GET /chat/session/{id}/history         │
     │                     │────────────────────>│                     │
     │                     │                     │                     │
     │                     │                     │ 10. SELECT messages │
     │                     │                     │     FROM chat_messages                   │
     │                     │                     │     WHERE session_id = ?                 │
     │                     │                     │     ORDER BY timestamp                   │
     │                     │                     │────────────────────>│
     │                     │                     │                     │
     │                     │                     │ 11. Return: messages│
     │                     │                     │<────────────────────│
     │                     │                     │                     │
     │                     │ 12. Return: {success, messages: [...]}    │
     │                     │<────────────────────│                     │
     │                     │                     │                     │
     │                     │ 13. Set activeThreadId                    │
     │                     │     Update messages state                 │
     │                     │─────────┐           │                     │
     │                     │<────────┘           │                     │
     │                     │                     │                     │
     │ 14. Display chat    │                     │                     │
     │     history         │                     │                     │
     │<────────────────────│                     │                     │
     │                     │                     │                     │
     │                     │                     │                     │
     │ === EDIT THREAD TITLE ===                 │                     │
     │                     │                     │                     │
     │ 15. Click edit icon │                     │                     │
     │────────────────────>│                     │                     │
     │                     │                     │                     │
     │                     │ 16. Show inline edit input                │
     │                     │─────────┐           │                     │
     │                     │<────────┘           │                     │
     │                     │                     │                     │
     │ 17. Edit & save     │                     │                     │
     │────────────────────>│                     │                     │
     │                     │                     │                     │
     │                     │ 18. PATCH /chat/session/{id}/title        │
     │                     │     {title: "new title"}                  │
     │                     │────────────────────>│                     │
     │                     │                     │                     │
     │                     │                     │ 19. UPDATE chat_sessions                 │
     │                     │                     │     SET title = ?   │
     │                     │                     │     WHERE session_id = ?                 │
     │                     │                     │────────────────────>│
     │                     │                     │                     │
     │                     │                     │ 20. Return: success │
     │                     │                     │<────────────────────│
     │                     │                     │                     │
     │                     │ 21. Return: {success, title}              │
     │                     │<────────────────────│                     │
     │                     │                     │                     │
     │                     │ 22. Update thread in local state          │
     │                     │─────────┐           │                     │
     │                     │<────────┘           │                     │
     │                     │                     │                     │
     │ 23. Show updated    │                     │                     │
     │     title           │                     │                     │
     │<────────────────────│                     │                     │
     │                     │                     │                     │
     │                     │                     │                     │
     │ === DELETE THREAD ===                     │                     │
     │                     │                     │                     │
     │ 24. Click delete (X)│                     │                     │
     │────────────────────>│                     │                     │
     │                     │                     │                     │
     │                     │ 25. Show confirmation modal               │
     │                     │─────────┐           │                     │
     │                     │<────────┘           │                     │
     │                     │                     │                     │
     │ 26. Confirm delete  │                     │                     │
     │<────────────────────│                     │                     │
     │────────────────────>│                     │                     │
     │                     │                     │                     │
     │                     │ 27. DELETE /chat/session/{id}             │
     │                     │────────────────────>│                     │
     │                     │                     │                     │
     │                     │                     │ 28. DELETE FROM chat_messages            │
     │                     │                     │     WHERE session_id = ?                 │
     │                     │                     │────────────────────>│
     │                     │                     │                     │
     │                     │                     │ 29. DELETE FROM chat_sessions            │
     │                     │                     │     WHERE session_id = ?                 │
     │                     │                     │────────────────────>│
     │                     │                     │                     │
     │                     │                     │ 30. Return: success │
     │                     │                     │<────────────────────│
     │                     │                     │                     │
     │                     │ 31. Return: {success}                     │
     │                     │<────────────────────│                     │
     │                     │                     │                     │
     │                     │ 32. Remove from threads list              │
     │                     │     Clear active if was active            │
     │                     │─────────┐           │                     │
     │                     │<────────┘           │                     │
     │                     │                     │                     │
     │ 33. Update UI       │                     │                     │
     │<────────────────────│                     │                     │
     │                     │                     │                     │
```

---

## Legend

### Activity Diagram Symbols

| Symbol | Meaning |
|--------|---------|
| `┌────┐` / `└────┘` | Activity/Action node |
| `◇────◇` | Decision diamond |
| `[YES]` / `[NO]` | Decision branch labels |
| `────>` | Flow direction |
| `START` / `END` | Start/End nodes |

### Sequence Diagram Symbols

| Symbol | Meaning |
|--------|---------|
| `│` | Lifeline |
| `────>` | Synchronous message |
| `<────` | Return message |
| `─────┐` `│` `<────┘` | Self-call (internal processing) |

---

*See [DOCUEXTRACT_ARCHITECTURE.md](./DOCUEXTRACT_ARCHITECTURE.md) for detailed architecture documentation.*
