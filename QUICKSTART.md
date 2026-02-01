# Quick Start Guide - Pragya Company Law CompanyGPT

## 🚀 Quick Start (Windows)

### Option 1: Using the Batch Script (Easiest)
1. Double-click `start.bat` in the `app` folder
2. Two command windows will open (Flask backend and Next.js frontend)
3. Wait 10-15 seconds for both servers to start
4. Open your browser to http://localhost:3000

### Option 2: Manual Start

#### Terminal 1 - Flask Backend
```bash
cd companies_act_2013
python app.py
```

#### Terminal 2 - Next.js Frontend
```bash
cd app
npm run dev
```

## 📋 Pre-requisites

### Required Software
- ✅ Node.js 18+ ([Download](https://nodejs.org/))
- ✅ Python 3.8+ ([Download](https://www.python.org/downloads/))

### First Time Setup

#### 1. Install Node.js Dependencies
```bash
cd app
npm install
```

#### 2. Install Python Dependencies
```bash
cd companies_act_2013
pip install -r requirements.txt
```

#### 3. Create Environment File
Create `app/.env.local`:
```env
FLASK_API_URL=http://localhost:5000
```

## 🔍 Verify Installation

### Check Flask Backend
Open browser to: http://localhost:5000/api/health

You should see:
```json
{
  "status": "ok",
  "retriever_ready": true
}
```

### Check Next.js Frontend
Open browser to: http://localhost:3000/api/health

You should see:
```json
{
  "status": "ok",
  "backend": {...},
  "message": "Both frontend and backend are running"
}
```

### Check Full Application
Open browser to: http://localhost:3000

You should see the search interface!

## 🎯 Using the Application

1. **Enter a Query**: Type your question about the Companies Act 2013
2. **Click Search**: Or press Enter
3. **View Results**: 
   - Synthesized AI answer with citations
   - Source documents from the act
   - Supporting materials

### Example Queries
- "What is the process for incorporation of a company?"
- "What are the requirements for registered office?"
- "What forms are required for company registration?"
- "What are the requirements for directors?"

## ❗ Troubleshooting

### Flask Backend Won't Start
**Error**: `ModuleNotFoundError: No module named 'flask'`
**Solution**:
```bash
cd companies_act_2013
pip install -r requirements.txt
```

### Flask Backend - Retriever Not Ready
**Error**: `retriever_ready: false`
**Solution**: Make sure the vector store and embeddings are built:
```bash
cd companies_act_2013
python build_embeddings.py
```

### Next.js Won't Connect to Flask
**Error**: "Failed to connect to backend service"
**Solution**:
1. Verify Flask is running: http://localhost:5000/api/health
2. Check `.env.local` has correct Flask URL
3. Restart Next.js dev server

### Port Already in Use
**Error**: `Port 3000 is already in use`
**Solution**:
```bash
# Kill process on port 3000
npx kill-port 3000

# Or use different port
PORT=3001 npm run dev
```

**Error**: `Port 5000 is already in use`
**Solution**:
```bash
# Find and kill process on port 5000
netstat -ano | findstr :5000
taskkill /PID <PID> /F

# Or modify Flask app.py to use different port
```

## 🛠️ Development

### File Structure
```
app/
├── src/
│   ├── app/
│   │   ├── api/query/route.ts      # Query endpoint
│   │   ├── api/health/route.ts     # Health check
│   │   ├── page.tsx                # Main UI
│   │   └── globals.css             # Styles
│   └── components/
│       ├── SearchBar.tsx           # Search input
│       ├── LoadingSpinner.tsx      # Loading state
│       ├── SynthesizedAnswer.tsx   # AI answer display
│       └── SectionResults.tsx      # Source documents
```

### Making Changes
- **UI Changes**: Edit files in `src/app/` and `src/components/`
- **API Logic**: Edit `src/app/api/query/route.ts`
- **Backend Logic**: Edit `companies_act_2013/app.py` or retrieval files

### Hot Reload
Both servers support hot reload:
- Next.js: Automatically reloads on file changes
- Flask: Reloads when Python files change (debug mode)

## 📚 API Documentation

### POST /api/query
Request:
```json
{
  "query": "What is the process for incorporation?"
}
```

Response:
```json
{
  "success": true,
  "result": {
    "synthesized_answer": "...",
    "answer_citations": ["Section 7", "Section 12"],
    "retrieved_sections": [...]
  }
}
```

### GET /api/health
Response:
```json
{
  "status": "ok",
  "backend": {
    "status": "ok",
    "retriever_ready": true
  }
}
```

## 🚢 Production Deployment

### Build Next.js for Production
```bash
cd app
npm run build
npm start
```

### Run Flask in Production
```bash
cd companies_act_2013
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### Environment Variables
- `FLASK_API_URL`: URL of Flask backend (default: http://localhost:5000)
- `PORT`: Next.js port (default: 3000)

## 📞 Support

If you encounter issues:
1. Check both terminal windows for error messages
2. Verify all prerequisites are installed
3. Ensure ports 3000 and 5000 are available
4. Check the troubleshooting section above
