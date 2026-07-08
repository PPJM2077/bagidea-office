---
name: Archive Search
description: Search the office's past memory, meetings and notes before answering — recall, don't guess.
---

Before answering from memory or assuming, search what the office already knows:
1. Run: curl -s 'http://127.0.0.1:8787/recall?q=<url-encoded keywords>&k=8'
2. The JSON 'hits' are the most relevant past facts/notes/meeting snippets, each
   tagged with a tier (mem/proj/user/arch) and a relevance score.
3. Use them as grounding; if a hit points to a file, Read it for the full text.
4. Recall first, then reason — never invent facts the office may already hold.
