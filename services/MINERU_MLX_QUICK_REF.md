# MinerU MLX - Quick Reference Card

## 🚀 Start Service
```bash
cd ~/Projects/archon/services/mineru-mlx
./start_service.sh
```

## 🔍 Check Status
```bash
curl http://localhost:9006/health
```

## 📊 Service Info
- **Port**: 9006
- **URL**: http://localhost:9006
- **Docs**: http://localhost:9006/docs
- **Backend**: MinerU + Apple Metal GPU
- **Version**: 2.0.0

## ✨ Features
✅ Text extraction (58K+ chars/doc)
✅ Formula detection (88 formulas/doc)
✅ Table recognition (6 tables/doc)
✅ Image extraction (15+ regions/doc)
✅ Multi-column layout support
✅ OCR auto-enabled
✅ Apple M4 GPU accelerated

## 🎯 Use Cases
- 📄 Scientific papers
- 📊 Technical reports
- 📋 Forms with tables
- 🧮 Documents with formulas
- 🖼️ Image-heavy PDFs

## 📦 Test It
```bash
curl -X POST http://localhost:9006/process \
  -F 'file=@document.pdf' \
  -F 'device=mps' \
  -F 'lang=en' \
  | jq '.metadata'
```

## 📁 Key Files
```
services/
├── mineru-mlx/
│   ├── app.py (FastAPI service)
│   ├── start_service.sh
│   ├── requirements.txt
│   └── venv/
├── MINERU_MLX_INTEGRATION.md (full guide)
├── MINERU_MLX_QUICK_REF.md (this file)
└── check_mlx_status.sh
```

## 🔗 Integration
```python
# Python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://localhost:9006/process",
        files={'file': open('doc.pdf', 'rb')},
        data={'device': 'mps', 'lang': 'en'}
    )
    result = response.json()
```

```typescript
// TypeScript
const formData = new FormData();
formData.append('file', file);
formData.append('device', 'mps');

const response = await fetch('http://localhost:9006/process', {
  method: 'POST',
  body: formData
});
const result = await response.json();
```

## 📈 Performance
- **34 MB PDF**: 2 minutes
- **13 pages**: ~10 seconds/page
- **Memory**: ~2 GB peak
- **GPU**: MPS accelerated

## 🛠️ Commands
```bash
# Start
./start_service.sh

# Status
curl localhost:9006/health

# Logs
tail -f logs/mineru.log

# Process
ps aux | grep "uvicorn.*9006"

# Stop
kill $(lsof -t -i:9006)
```

## 🔄 Next Steps
1. ✅ Service running on port 9006
2. ✅ Image extraction implemented
3. ✅ Documentation complete
4. ⏳ Integrate with Archon backend
5. ⏳ Add frontend UI option
6. ⏳ Consider MLX-engine upgrade

## 💡 Tips
- Use MPS device for M4 GPU
- Pre-download models first
- Allow 2 min for large PDFs
- Check logs for details
- Use DeepSeek-OCR for simple text

## 📚 Full Docs
- **Integration**: `services/MINERU_MLX_INTEGRATION.md`
- **Summary**: `services/mineru-mlx/IMPLEMENTATION_SUMMARY.md`
- **Port Map**: `PORT_MAPPING.md`
- **Models**: `services/MLX_MODELS_QUICK_START.md`
