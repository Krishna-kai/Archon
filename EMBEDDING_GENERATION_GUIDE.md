# 🚀 EMBEDDING GENERATION GUIDE

**Date**: November 5, 2025
**System**: Mac Studio M4 Max + Archon + Ollama
**Configuration**: 100% Local (nomic-embed-text)

---

## 📊 CURRENT STATUS

```
✅ Ollama configured: nomic-embed-text (embeddings)
✅ Ollama configured: qwen2.5-coder:7b (LLM)
✅ Pages crawled: 138 pages
✅ Sources: 5 knowledge sources
❌ Embeddings: 0 (needs generation)
```

---

## 🎯 STEP-BY-STEP INSTRUCTIONS

### **Step 1: Open Archon UI**

```
Open in browser: http://localhost:9737
```

### **Step 2: Navigate to Knowledge Base**

1. Look for **"Knowledge Base"** or **"Knowledge"** in the sidebar
2. Click on it
3. You should see your 5 sources:
   - Pydantic Documentation
   - Mediversityglobal
   - N8N Documentation
   - Astro Documentation
   - Astro Documentation Guide

### **Step 3: Trigger Embedding Generation**

For **EACH source**, do the following:

1. **Click on the source** (e.g., "Pydantic Documentation")
2. Look for one of these buttons:
   - **"Re-process"**
   - **"Generate Embeddings"**
   - **"Re-crawl"**
   - **"Process Documents"**
3. **Click the button**
4. Confirm if prompted
5. **Repeat for all 5 sources**

### **Step 4: Monitor Progress**

Open a new terminal and run:

```bash
bash /tmp/monitor_embeddings.sh
```

This will show you real-time progress:
```
🔄 EMBEDDING GENERATION MONITOR
==================================
📊 Total: 1500, Embedded: 450, Progress: 30.0%

🕐 Last checked: 14:23:45
⏰ Next update in 10 seconds...
```

Press **Ctrl+C** to stop monitoring.

---

## ⏱️ EXPECTED TIMELINE

### **With Ollama (Local):**

```
Pages: 138 pages
Model: nomic-embed-text
Hardware: Mac Studio M4 Max

Estimated Time: 5-15 minutes total
Speed: ~10-30 pages/minute (CPU-based)
```

**Factors affecting speed:**
- ✅ M4 Max CPU (very fast)
- ✅ 128GB RAM (plenty of headroom)
- ⚠️ CPU-bound (not GPU accelerated)

---

## 📈 MONITORING OPTIONS

### **Option 1: Monitoring Script** (Recommended)
```bash
bash /tmp/monitor_embeddings.sh
```

### **Option 2: Manual SQL Check**
```bash
# In terminal, run:
docker exec archon-server python3 -c "
from src.server.config.database import get_supabase_client
supabase = get_supabase_client()
result = supabase.table('archon_crawled_pages').select('*', count='exact').execute()
total = result.count
result_emb = supabase.table('archon_crawled_pages').select('*', count='exact').not_.is_('embedding', 'null').execute()
embedded = result_emb.count
print(f'Total: {total}, Embedded: {embedded}, Progress: {round(embedded/total*100 if total > 0 else 0, 1)}%')
"
```

### **Option 3: UI Progress Bar**
The Archon UI may show a progress indicator while processing.

---

## ✅ SUCCESS CRITERIA

Embeddings are complete when:

```sql
-- Run this query (all chunks should have embeddings):
SELECT
    COUNT(*) as total_chunks,
    COUNT(embedding) as embedded_chunks,
    COUNT(*) - COUNT(embedding) as missing_embeddings
FROM archon_crawled_pages;

-- Expected result:
-- total_chunks: ~1000-2000 (depends on chunking)
-- embedded_chunks: ~1000-2000 (should match total)
-- missing_embeddings: 0
```

---

## 🔍 WHAT HAPPENS DURING GENERATION

```
1. CHUNKING
   ├─ Reads 138 pages from archon_page_metadata
   ├─ Splits into smaller chunks (~500-1000 words each)
   └─ Creates 1000-2000 chunks total

2. EMBEDDING GENERATION (Local via Ollama)
   ├─ Sends each chunk to Ollama API
   ├─ Ollama runs nomic-embed-text model
   ├─ Returns 768-dimensional vector
   └─ Stores in archon_crawled_pages table

3. STORAGE
   ├─ Chunk text + embedding vector
   ├─ Metadata (source_id, page_id, etc.)
   └─ Ready for vector search!
```

---

## 🚨 TROUBLESHOOTING

### **If embedding generation fails:**

**1. Check Ollama is running:**
```bash
curl http://localhost:11434/api/tags
```
Should return list of models including `nomic-embed-text`.

**2. Check Archon server logs:**
```bash
docker compose logs archon-server | tail -50
```
Look for errors related to embeddings or Ollama.

**3. Verify Ollama config:**
```sql
SELECT key, value FROM archon_settings
WHERE key IN ('EMBEDDING_PROVIDER', 'EMBEDDING_MODEL', 'OLLAMA_EMBEDDING_URL');
```
Should show:
- EMBEDDING_PROVIDER: ollama
- EMBEDDING_MODEL: nomic-embed-text
- OLLAMA_EMBEDDING_URL: http://host.docker.internal:11434/v1

**4. Restart services:**
```bash
docker compose restart archon-server
```

### **If progress seems stuck:**

Check active operations:
```bash
curl -s http://localhost:9181/api/progress/active | python3 -m json.tool
```

---

## 🎯 AFTER EMBEDDINGS COMPLETE

Once embeddings are generated, you can:

### **1. Test RAG Search**
```
Via UI:
- Go to Knowledge Base
- Use the search box
- Try: "How to use PydanticAI with async?"
- Should return relevant chunks with sources
```

### **2. Test via MCP** (If connected)
```
Use Archon MCP tools from Claude Code:
- archon:rag_search_knowledge_base
- archon:rag_search_code_examples
```

### **3. Verify Data Quality**
```sql
-- Check embedding dimensions (should be 768)
SELECT
    source_id,
    COUNT(*) as chunks,
    COUNT(embedding) as embedded,
    array_length(embedding, 1) as dimensions
FROM archon_crawled_pages
GROUP BY source_id, array_length(embedding, 1);
```

---

## 📚 YOUR KNOWLEDGE BASE

Once complete, you'll have searchable:

```
1. Pydantic Documentation (629k words)
   → AI framework, validation, models

2. Mediversityglobal (14k words)
   → Medical education content

3. N8N Documentation (3.8M words!)
   → Workflow automation, integrations

4. Astro Documentation (567k words)
   → Static site generator

5. Astro Documentation Guide (871k words)
   → Advanced Astro concepts

TOTAL: ~6 million words of searchable knowledge!
```

---

## 🎉 NEXT STEPS AFTER COMPLETION

1. ✅ **Test RAG search** (search your docs!)
2. ✅ **Try hybrid search** (vector + keyword)
3. ✅ **Test code search** (741 code examples)
4. ✅ **Use for development** (ask questions about frameworks)
5. ✅ **Create projects for mentees** (organized learning paths)

---

## 💡 OPTIMIZATION TIPS

After initial generation:

### **Use Contextual Embeddings** (Already enabled!)
```
Your config already has:
USE_CONTEXTUAL_EMBEDDINGS = true
```
This improves search quality by adding context to each chunk.

### **Use Hybrid Search** (Already enabled!)
```
Your config already has:
USE_HYBRID_SEARCH = true
```
Combines vector search + keyword matching for better results.

### **Use Reranking** (Already enabled!)
```
Your config already has:
USE_RERANKING = true
```
Intelligently ranks search results for relevance.

---

**You're all set! Start the embedding generation and watch your RAG system come to life!** 🚀
