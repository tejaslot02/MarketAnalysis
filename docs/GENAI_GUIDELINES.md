# Enterprise Generative AI & RAG Engineering Guidelines

## 1. Architectural Philosophy
The Remote 150K+ DS/AI/ML Job Search Platform enforces a **Clean / Hexagonal Architecture** separating AI-agnostic business logic from Generative AI provider technologies.

```
+-------------------------------------------------------------+
|                        API / Serving                        |
|        (FastAPI, Async SQLAlchemy, Hybrid Search Router)    |
+-------------------------------------------------------------+
                               |
                               v
+-------------------------------------------------------------+
|                         Core Domain                         |
|   (Job, Company, Skill, Salary, Title Canonicalizer)        |
+-------------------------------------------------------------+
                               |
            +------------------+------------------+
            | (Defines Ports)                     | (Defines Ports)
            v                                     v
+-----------------------+             +-----------------------+
|     LLM Provider      |             |   Vector Store Port   |
|   (OpenAI, Claude)    |             |  (pgvector, Elastic)  |
+-----------------------+             +-----------------------+
```

### Key Tenets
1. **AI-Agnostic Core Domain (`core/`):**
   - Core domain models and business rules (`core/domain/`, `core/services/`) never depend on third-party AI libraries (LangChain, OpenAI, Anthropic).
   - Domain operations interface with AI providers exclusively through protocol interfaces defined in `core/ports/` (`LLMProvider`, `EmbeddingProvider`, `VectorStore`, `Reranker`, `Cache`).
2. **Pluggable Adapters (`ai/adapters/`):**
   - Concrete implementations of ports reside in `ai/adapters/`.
   - Adapters handle client timeouts, rate-limiting, retries, and offline mock fallbacks.
3. **Decoupled Prompt Management (`prompts/`):**
   - Prompts are first-class versioned code artifacts written in Jinja2 (`.jinja`), registered in `prompts/registry.yaml`.
   - Never hardcode system or user prompts within Python string literals.

---

## 2. Prompt Engineering & Versioning Standards
- **Template Engine:** Jinja2 with strict variable injection.
- **Defensive Boundary Delimiters:** Unstructured input text (such as raw job descriptions) must always be wrapped in triple quotes (`"""`) or markdown blocks to prevent delimiter hijacking.
- **Structured Outputs:** Generation tasks (skill extraction, title canonicalization, responsibility summarization) must enforce deterministic JSON output schemas with temperature $\le 0.2$.
- **Immutability:** Existing prompt templates (`_v1`) must never be modified in place once released. Create new iterations (`_v2`) and update `prompts/registry.yaml`.

---

## 3. RAG & Semantic Retrieval Layer
### 3.1 Document Chunking
- Handled by `ai/rag/chunking/job_description_chunker.py`.
- Logical section chunking isolates *Requirements*, *Responsibilities*, *Compensation*, and *Tech Stack*.
- Fallback sliding-window chunker uses 800-character windows with 150-character overlap.

### 3.2 Vector Embeddings
- Standard model: `text-embedding-3-small` (1536 dimensions) or `sentence-transformers/all-MiniLM-L6-v2` (384 dimensions).
- Storage: PostgreSQL `jobs(embedding)` column using `pgvector` with HNSW cosine distance index (`embedding vector_cosine_ops`, $m=16, ef\_construction=64$).

### 3.3 Hybrid Search & Reciprocal Rank Fusion (RRF)
- The search endpoint (`/search`) combines dense vector retrieval and BM25 full-text lexical ranking.
- Scoring uses Reciprocal Rank Fusion with standard constant $k=60$:
  $$RRF(d) = \sum_{m \in \{dense, bm25\}} \frac{1}{60 + rank_m(d)}$$

---

## 4. Guardrails & Safety Architecture
Before LLM processing and after generation, all text passes through defensive filters:
1. **Input Guard (`ai/guardrails/input_guard.py`):**
   - Scans for prompt injection attacks (jailbreaks, instruction overrides, system prompt exfiltration).
   - Automatically redacts PII (emails, phone numbers, SSNs, credit card numbers).
2. **Output Guard (`ai/guardrails/output_guard.py`):**
   - Filters toxic, hostile, or disallowed vocabulary.
   - Validates factual grounding / hallucination rates by checking extracted entities against source text.

---

## 5. Evaluation Harnesses & Quality Gates
- **Golden Datasets (`evals/golden_datasets/`):** Curated ground-truth test cases for skill extraction, title normalization, and retrieval ranking.
- **RAGAS Suite (`evals/ragas_suite.py`):** Measures Context Precision, Context Recall, Faithfulness, and Answer Relevance.
- **Prompt Regression (`evals/prompt_regression.py`):** Enforces minimum F1 $\ge 0.70$ and title accuracy $\ge 0.60$.
- **Automated CI Quality Gate (`.github/workflows/eval-gate.yml`):** Rejects pull requests that degrade accuracy below baseline thresholds.

---

## 6. Progressive Rollout & Feature Flags
All GenAI capabilities are safely gated behind configuration flags in `config/feature_flags.yaml` and environment variables:
- `USE_LLM_SKILL_EXTRACTION`: `false` (default: fast dictionary NLP matching).
- `USE_VECTOR_SEARCH`: `false` (default: SQL ILIKE search; activate once embeddings are backfilled).
- `ENABLE_GUARDRAILS`: `false` (development: permissive; production: enforced).
