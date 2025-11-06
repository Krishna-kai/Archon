# 🚀 MLX Models Quick Start Guide

## Pre-Download All Models (Recommended)

Run this **once** before first use to download all models:

```bash
cd ~/Projects/archon/services
./download_all_mlx_models.sh
```

This downloads:
- **DeepSeek-OCR MLX**: ~4-6 GB (5-10 minutes)
- **MinerU MLX**: ~500 MB - 1 GB (2-5 minutes)

**Total**: ~5-7 GB, ~10-15 minutes total

---

## Individual Model Downloads

### Option 1: DeepSeek-OCR MLX Only

```bash
cd ~/Projects/archon/services/deepseek-ocr-mlx
source venv/bin/activate
pip install -r requirements.txt
python download_model.py
```

### Option 2: MinerU MLX Only

```bash
cd ~/Projects/archon/services/mineru-mlx
source venv/bin/activate
pip install -r requirements.txt
python download_models.py
```

---

## Model Details

### DeepSeek-OCR MLX

| Property | Value |
|----------|-------|
| **Model** | `mlx-community/DeepSeek-OCR-8bit` |
| **Type** | Vision-Language Model (VLM) |
| **Source** | Hugging Face Hub |
| **Size** | ~4-6 GB |
| **Cache** | `~/.cache/mlx/` |
| **Uses Ollama?** | ❌ No - Direct from Hugging Face |
| **Framework** | MLX (Apple Silicon optimized) |

### MinerU MLX

| Property | Value |
|----------|-------|
| **Backend** | magic-pdf (MinerU) |
| **Type** | Layout detection + OCR |
| **Source** | Hugging Face Hub |
| **Size** | ~500 MB - 1 GB |
| **Cache** | `~/.cache/huggingface/` |
| **Uses Ollama?** | ❌ No - Uses MinerU's models |
| **Framework** | PyTorch + pypdfium2 |

---

## ❓ What About Ollama?

**Neither MLX service uses Ollama!** They download models directly from Hugging Face.

### Services That Use Ollama (Not MLX)

Only the **legacy DeepSeek OCR service** (port 9001) uses Ollama:

```bash
# .env configuration for LEGACY service (not MLX)
OLLAMA_HOST=http://host.docker.internal:11434
DEEPSEEK_MODEL=deepseek-ocr
DEEPSEEK_SERVICE_MODE=ollama
```

**This is the OLD service** - you don't need this if you're using the new MLX services!

### Comparison

| Service | Port | Uses Ollama? | Model Source |
|---------|------|--------------|--------------|
| **DeepSeek-OCR MLX** (NEW) | 9005 | ❌ No | Hugging Face → MLX cache |
| **MinerU MLX** (NEW) | 9006 | ❌ No | Hugging Face → MinerU cache |
| DeepSeek-OCR Legacy | 9001 | ✅ Yes | Ollama (if configured) |

---

## 🎯 Recommended Setup

For the **best performance on Mac M4**, use the MLX services:

1. **Pre-download models** (one time):
   ```bash
   cd ~/Projects/archon/services
   ./download_all_mlx_models.sh
   ```

2. **Start DeepSeek-OCR MLX** (Terminal 1):
   ```bash
   cd ~/Projects/archon/services/deepseek-ocr-mlx
   ./start_service.sh
   ```

3. **Start MinerU MLX** (Terminal 2):
   ```bash
   cd ~/Projects/archon/services/mineru-mlx
   ./start_service.sh
   ```

4. **Verify both running**:
   ```bash
   curl http://localhost:9005/health  # DeepSeek-OCR MLX
   curl http://localhost:9006/health  # MinerU MLX
   ```

---

## 🔍 Check Model Cache

### DeepSeek-OCR MLX Models

```bash
ls -lh ~/.cache/mlx/
```

Should show `DeepSeek-OCR-8bit` directory with model files.

### MinerU Models

```bash
ls -lh ~/.cache/huggingface/hub/
```

Should show various model files for layout detection.

---

## 💾 Disk Space Requirements

Before downloading, ensure you have:

- **DeepSeek-OCR MLX**: ~6 GB free
- **MinerU MLX**: ~1.5 GB free
- **Total**: ~8 GB free (recommended)

Check available space:
```bash
df -h ~
```

---

## 🚨 Troubleshooting

### Models Not Downloading

**Issue**: Download script fails

**Solution**:
1. Check internet connection
2. Ensure sufficient disk space
3. Models will auto-download on first use anyway!

### Slow Download

**Issue**: Download taking too long

**Solution**:
- Models download from Hugging Face servers
- Speed depends on your internet connection
- Can pause and resume (downloads are resumable)

### Already Cached

**Issue**: Script says models already cached

**Result**: ✅ This is good! You can skip the download.

---

## 📝 Summary

**Do you need Ollama?**
- ❌ **No** - for MLX services (ports 9005, 9006)
- ✅ **Yes** - only for legacy DeepSeek OCR (port 9001)

**Recommended**: Use the new MLX services, skip Ollama entirely!

**Models come from**: Hugging Face Hub, cached locally

**Download time**: 10-15 minutes total (one time only)

**Ready to start?**
```bash
cd ~/Projects/archon/services
./download_all_mlx_models.sh
```
