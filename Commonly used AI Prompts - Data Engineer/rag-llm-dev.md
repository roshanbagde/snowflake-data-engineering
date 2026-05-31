# RAG / LLM App Development Prompts

## Design a RAG system
```
Help me design a RAG pipeline for [use case, e.g. "Q&A over internal docs"]. Cover:
ingestion, chunking strategy, embedding model choice, vector store, retrieval (top-k,
hybrid, reranking), and the prompt that combines context + question. Note trade-offs and
where it commonly fails.
```

## Chunking strategy
```
What's the best chunking strategy for [document type, e.g. "PDFs with tables", "code",
"chat logs"]? Compare fixed-size vs semantic vs structural chunking, recommend chunk size
and overlap, and explain the impact on retrieval quality.
```

## Embeddings
```
Explain how to use embeddings for [semantic search / dedup / clustering / classification].
Recommend a model, how to store vectors, similarity metric, and a minimal code example
([Python]).
```

## Build the prompt for an LLM feature
```
Write a system + user prompt for an LLM feature that [does X]. Inputs: [describe]. Output:
[format]. Include guardrails (refuse off-topic, cite sources, stay in format) and handle
the "I don't know" case. Use prompt caching for the static system part if applicable.
```

## Evals
```
Design an evaluation for my LLM feature [describe]. Define: test cases, metrics (accuracy /
faithfulness / relevance / latency / cost), how to score (LLM-as-judge vs exact vs human),
and how to catch regressions. Give a simple eval harness in [Python].
```

## Reduce hallucination
```
My RAG app [hallucinates / ignores context / cites wrong sources]. Diagnose likely causes
(retrieval quality, chunking, prompt, context window) and give concrete fixes ordered by
impact.
```

## Cost / latency optimization
```
Help me reduce cost and latency for my LLM app: [describe model, volume, prompt size].
Cover prompt caching, model choice (Opus/Sonnet/Haiku), batching, streaming, shorter
context, and caching retrieved results. Estimate the savings of each.
```

## Tool use / agents
```
Design a tool-using agent for [task]. Define the tools (name, input schema, what it does),
the system prompt, the control loop, and how to handle errors/retries and stopping
conditions. Keep it minimal and reliable.
```
