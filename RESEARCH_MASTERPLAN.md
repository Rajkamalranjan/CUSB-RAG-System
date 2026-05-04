# CUSB AI Assistant - Research & Production Masterplan

## 🎯 Project Vision
Research-grade, production-ready RAG system for Indian Higher Education - specifically Central University of South Bihar (CUSB).

---

## 📊 Current State
- **Chunks:** 1,599
- **Vectors:** 1,599 (384-dim)
- **Max Chunk Size:** 7,582 chars (no giant chunks)
- **Knowledge Base:** 4.8M+ characters
- **Coverage:** Courses, Fees, Faculty, Admissions, Hostel, Syllabus

---

## 🔬 Phase 1: Research Excellence (Weeks 1-4)

### 1.1 Evaluation Framework ✅
**Status:** Implemented in `src/evaluation_framework.py`

**Metrics:**
- Context Precision: % relevant chunks retrieved
- Context Recall: % of relevant info found
- Answer Relevance: Query-answer alignment
- Faithfulness: Answer supported by context
- RAGAS Score: Combined metric

**Test Cases:** 10 domain-specific queries
- Fee-related queries
- Faculty queries
- Admission queries
- Course queries

**Deliverable:** Research paper dataset + production quality metrics

### 1.2 Benchmark Dataset Creation
**Goal:** CUSB-QA Dataset (10K+ questions)

**Categories:**
- Admissions (20%)
- Fees & Financial (20%)
- Courses & Syllabus (20%)
- Faculty & Research (15%)
- Campus Life (15%)
- General (10%)

**Data Collection:**
- Synthetic generation from chunks
- Human annotation
- Crowd-sourced from students

### 1.3 Baseline Comparisons
Compare against:
- Naive RAG (no re-ranking)
- BM25 only
- Dense only
- Hybrid (our approach)
- Agentic RAG (advanced)

**Metrics for comparison:**
- Accuracy
- Latency
- Token efficiency
- Cost per query

---

## 🚀 Phase 2: Production Deployment (Weeks 2-5)

### 2.1 API Server ✅
**Status:** Implemented in `src/api_server.py`

**Features:**
- RESTful API (FastAPI)
- Auto-generated docs (/docs)
- Request validation (Pydantic)
- Error handling
- CORS for web/mobile
- GZip compression
- Query history & analytics

**Endpoints:**
```
GET  /              - API info
GET  /api/health    - Health check
POST /api/query     - Ask questions
GET  /api/stats     - System statistics
GET  /api/history   - Query history
GET  /docs          - Swagger UI
```

### 2.2 Database Integration
**PostgreSQL Schema:**
```sql
-- Queries table
CREATE TABLE queries (
    id UUID PRIMARY KEY,
    question TEXT,
    answer TEXT,
    confidence FLOAT,
    processing_time FLOAT,
    tokens_used INT,
    timestamp TIMESTAMP
);

-- Feedback table
CREATE TABLE feedback (
    query_id UUID,
    rating INT,  -- 1-5
    comment TEXT,
    timestamp TIMESTAMP
);

-- Analytics table
CREATE TABLE daily_stats (
    date DATE PRIMARY KEY,
    total_queries INT,
    avg_confidence FLOAT,
    avg_latency FLOAT
);
```

**Redis for:**
- Caching frequent queries
- Rate limiting
- Session management

### 2.3 Web Application
**Tech Stack:**
- Frontend: React/Vue.js + Tailwind
- Backend: FastAPI (already done)
- Deployment: Docker + Kubernetes

**Features:**
- Chat interface
- Voice input
- Source citations
- Feedback buttons
- Mobile responsive

### 2.4 Mobile App
**Framework:** Flutter or React Native

**Features:**
- Offline mode (cache FAQs)
- Push notifications (admission deadlines)
- Voice search
- Campus map integration

---

## 🤖 Phase 3: Advanced AI (Weeks 3-6)

### 3.1 Multi-Modal RAG ✅
**Status:** Implemented in `src/advanced_ai.py`

**Components:**
- PDF image extraction (PyMuPDF)
- Table extraction (HTML/PDF)
- Image indexing
- OCR for scanned documents

**Use Cases:**
- "Show me the fee structure table"
- "What does the campus map show?"
- "Explain this diagram from the syllabus"

### 3.2 Agentic RAG ✅
**Status:** Implemented in `src/advanced_ai.py`

**Agent Capabilities:**
- Tool usage (fee lookup, contact finder)
- Multi-hop reasoning
- Planning & execution
- Self-correction

**Tools:**
1. fee_lookup - Course fee information
2. contact_lookup - Department contacts
3. comparison - Compare courses
4. calendar - Admission deadlines
5. form_filler - Help with applications

### 3.3 Query Expansion & Re-ranking ✅
**Status:** Implemented in `src/advanced_ai.py`

**Techniques:**
- Synonym expansion (fee → cost, charges, tuition)
- HyDE (Hypothetical Document Embedding)
- Cross-encoder re-ranking
- Query reformulation

### 3.4 Fine-Tuning Support ✅
**Status:** Implemented in `src/advanced_ai.py`

**Approach:**
- QLoRA (4-bit quantization)
- LoRA adapters (r=16, alpha=32)
- Base: Llama-2-7b or Mistral-7B
- Domain-specific training on CUSB data

**Training Data:**
- Generated from RAG pipeline
- Human-curated Q&A pairs
- 5K-10K examples

**Deployment:**
- Local GPU (RTX 4090/3090)
- Cloud (AWS SageMaker)
- Edge (quantized INT8)

---

## 📚 Phase 4: Research Contributions (Ongoing)

### 4.1 Paper 1: "EduRAG: Domain-Adapted RAG for Indian Higher Education"

**Venue:** AAAI / EAAI / LAK 2025

**Contributions:**
1. First comprehensive RAG evaluation for Indian universities
2. CUSB-QA benchmark dataset (public release)
3. Comparison of RAG architectures for educational domain
4. Best practices for low-resource language support

**Experiments:**
- Baseline vs Advanced RAG
- Multilingual evaluation (Hindi, English, Hinglish)
- Ablation studies (retrieval, generation, ranking)

### 4.2 Paper 2: "Code-Mixed Retrieval for Educational Question Answering"

**Venue:** ACL / EMNLP 2025

**Contributions:**
1. Hinglish query handling
2. Cross-lingual embedding alignment
3. Cultural/language-specific adaptations
4. User study with 100+ students

### 4.3 Paper 3: "Lightweight RAG for Resource-Constrained Institutions"

**Venue:** CoDS-COMAD / ACM India

**Contributions:**
1. Optimized for low-compute environments
2. Cost-effective deployment strategies
3. Tier-2/3 college deployment case study
4. Open-source toolkit release

---

## 🛠️ Technical Stack

### Current
- **Embeddings:** sentence-transformers (384-dim)
- **Vector DB:** FAISS (local)
- **LLM:** Groq API (llama-3.1-8b)
- **Chunking:** Custom markdown splitter

### Production Upgrade
- **Embeddings:** BGE-M3 (multilingual, 1024-dim)
- **Vector DB:** Pinecone/Weaviate (cloud)
- **LLM:** Fine-tuned Llama-3-8B (self-hosted)
- **Reranking:** Cross-encoder (ms-marco)

### Research Additions
- **Evaluation:** RAGAS, DeepEval, custom metrics
- **Training:** PEFT (LoRA, QLoRA), Unsloth
- **Deployment:** Docker, Kubernetes, AWS/GCP
- **Monitoring:** LangSmith, Weights & Biases

---

## 📅 30-Day Sprint Plan

### Week 1: Foundation
- [x] Evaluation framework
- [x] API server
- [x] Advanced AI components
- [ ] Create 100-query test set
- [ ] Run baseline evaluation
- [ ] Fix any issues

### Week 2: Production
- [ ] Database integration (PostgreSQL + Redis)
- [ ] Web frontend (React)
- [ ] Docker containerization
- [ ] CI/CD pipeline (GitHub Actions)
- [ ] Cloud deployment setup

### Week 3: Advanced Features
- [ ] Multi-modal processing (PDF images)
- [ ] Agent fine-tuning
- [ ] Query expansion optimization
- [ ] Re-ranking implementation
- [ ] Fine-tuning data generation

### Week 4: Research & Polish
- [ ] Benchmark dataset curation
- [ ] Human evaluation study
- [ ] Ablation studies
- [ ] Paper draft (introduction, methodology)
- [ ] Documentation & tutorials

### Week 5-6: Deployment & Testing
- [ ] Load testing (k6/Artillery)
- [ ] Security audit
- [ ] Beta testing with students
- [ ] Feedback collection
- [ ] Iterate & improve

---

## 💰 Funding Opportunities

| Grant | Amount | Deadline | Fit |
|-------|--------|----------|-----|
| **AWS Research Credits** | $5K-20K | Rolling | ⭐⭐⭐ |
| **Google Cloud Research** | $5K-20K | Rolling | ⭐⭐⭐ |
| **Microsoft Azure** | Academic | Rolling | ⭐⭐ |
| **MeitY IndiaAI** | ₹10-50L | Quarterly | ⭐⭐⭐⭐ |
| **UGC Research Grant** | ₹5-20L | Annual | ⭐⭐⭐⭐ |
| **SERB CRG** | ₹20-50L | Bi-annual | ⭐⭐⭐ |
| **NVIDIA Academic** | Hardware | Rolling | ⭐⭐⭐ |

---

## 📊 Success Metrics

### Research Metrics
- [ ] 1+ paper accepted at top-tier venue (ACL/AAAI/EAAI)
- [ ] 100+ citations in 2 years
- [ ] CUSB-QA dataset used by 10+ research groups
- [ ] Open-source toolkit with 500+ GitHub stars

### Production Metrics
- [ ] 1,000+ daily active users
- [ ] <2s average response time
- [ ] >85% user satisfaction
- [ ] Deployed in 5+ universities
- [ ] 99.9% uptime

### Technical Metrics
- [ ] Faithfulness >0.85
- [ ] Answer Relevance >0.80
- [ ] Context Precision >0.75
- [ ] Latency <1.5s (p95)

---

## 🎯 Immediate Next Steps

### Today (Priority 1)
```bash
# 1. Install additional dependencies
pip install ragas deepeval fastapi uvicorn

# 2. Run evaluation
python src/evaluation_framework.py

# 3. Start API server
python src/api_server.py

# 4. Test advanced AI
python src/advanced_ai.py
```

### This Week
1. Create 100-query test set
2. Run full evaluation
3. Identify improvement areas
4. Start API development
5. Plan fine-tuning strategy

---

## 🏆 Long-Term Vision

**2024:** Research paper + Production deployment at CUSB
**2025:** Expand to 10 Indian universities
**2026:** Multi-lingual support (Hindi, Tamil, Telugu)
**2027:** National-level educational AI assistant

---

## 🤝 Collaboration Opportunities

- **CUSB Faculty:** Domain expertise, student testing
- **IIT/NIT:** Technical collaboration, paper co-authorship
- **Industry:** AWS, Google, Microsoft (cloud credits)
- **Government:** MeitY, UGC (funding)
- **International:** CMU, Stanford (research exchange)

---

## 📚 Key Resources

**Papers to Read:**
1. "Retrieval-Augmented Generation for Knowledge-Intensive NLP" (Lewis et al., 2020)
2. "Precise Zero-Shot Dense Retrieval without Relevance Labels" (HyDE)
3. "RAGAS: Automated Evaluation of RAG"
4. "Self-RAG: Learning to Retrieve, Generate, and Critique"

**Tools to Explore:**
1. LangChain / LlamaIndex
2. LangSmith (observability)
3. Weights & Biases (experiment tracking)
4. Hugging Face Transformers / PEFT

---

**Ready to start? Choose your first task:**
1. 🔬 Run evaluation framework
2. 🚀 Start API server
3. 🤖 Test advanced AI components
4. 📊 Create benchmark dataset

**Recommendation:** Start with **Evaluation Framework** - it establishes baselines for both research and production.
