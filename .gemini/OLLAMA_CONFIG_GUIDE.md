# Ollama Response Token Configuration Guide

## Current Settings:

### 1. Answer Generation (User Queries)
**File**: `retrieval_service_faiss.py` (line 223)
```python
'num_predict': 2048  # Maximum tokens in response
```
- **Purpose**: Generate detailed answers to user questions
- **Current Limit**: 2048 tokens (~1500-2000 words)
- **Recommended**: 1024-4096 depending on answer length needed

### 2. Summary Generation (Document Ingestion)
**File**: `unified_ingest_full.py` (line 113)
```python
'num_predict': 200  # Limit output length
```
- **Purpose**: Generate concise summaries of document chunks
- **Current Limit**: 200 tokens (~150 words)
- **Recommended**: Keep at 200-300 for concise summaries

### 3. Keyword Extraction (Document Ingestion)
**File**: `unified_ingest_full.py` (similar section)
```python
'num_predict': 200  # Limit output length
```
- **Purpose**: Extract keywords from text
- **Current Limit**: 200 tokens
- **Recommended**: Keep at 100-200 for keyword lists

---

## How to Adjust Token Limits:

### For Longer Answers:
Increase `num_predict` in `retrieval_service_faiss.py`:
```python
'num_predict': 4096  # For very detailed answers
```

### For Shorter Answers:
Decrease `num_predict`:
```python
'num_predict': 1024  # For concise answers
```

### Token-to-Word Conversion:
- **100 tokens** ≈ 75 words
- **500 tokens** ≈ 375 words
- **1000 tokens** ≈ 750 words
- **2048 tokens** ≈ 1500 words
- **4096 tokens** ≈ 3000 words

---

## Other Ollama Parameters:

### Temperature (Creativity)
```python
'temperature': 0.5  # Current setting
```
- **0.0-0.3**: Very focused, deterministic (good for factual answers)
- **0.4-0.7**: Balanced creativity and accuracy
- **0.8-1.0**: More creative, less predictable

### Top P (Nucleus Sampling)
```python
'top_p': 0.9  # Current setting
```
- **0.5-0.7**: More focused responses
- **0.8-0.95**: Balanced (recommended)
- **0.95-1.0**: More diverse responses

### Top K (Token Selection)
```python
'top_k': 40  # Optional, not currently set
```
- Limits token selection to top K most likely tokens
- **20-40**: More focused
- **40-100**: More diverse

---

## Example Configurations:

### For Legal/Factual Answers (Current):
```python
'options': {
    'temperature': 0.5,
    'top_p': 0.9,
    'num_predict': 2048
}
```

### For Very Detailed Explanations:
```python
'options': {
    'temperature': 0.4,
    'top_p': 0.85,
    'num_predict': 4096
}
```

### For Quick, Concise Answers:
```python
'options': {
    'temperature': 0.3,
    'top_p': 0.8,
    'num_predict': 512
}
```

---

## Testing Changes:

After modifying parameters:
1. **No restart needed** - changes take effect immediately
2. **Test with a query** through the user UI
3. **Monitor response length** and quality
4. **Adjust as needed**

---

## Current Status:

✅ **Answer Generation**: 2048 tokens (detailed responses)
✅ **Summary Generation**: 200 tokens (concise summaries)
✅ **Temperature**: 0.5 (balanced)
✅ **Top P**: 0.9 (diverse but focused)

**System is configured for detailed, accurate legal answers!**
