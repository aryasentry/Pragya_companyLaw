# Pragya - Company Law CompanyGPT

A Next.js web application for querying the Companies Act 2013 with RAG (Retrieval Augmented Generation).

## Architecture

This application consists of two parts:
1. **Frontend**: Next.js app (this directory)
2. **Backend**: Flask API server (in `../companies_act_2013/`)

## Prerequisites

- Node.js 18+ (for Next.js frontend)
- Python 3.8+ (for Flask backend)

## Setup

### 1. Install Frontend Dependencies

```bash
npm install
```

### 2. Configure Environment

Create a `.env.local` file in the root of this directory:

```env
FLASK_API_URL=http://localhost:5000
```

### 3. Start the Flask Backend

In a separate terminal, navigate to the Flask backend directory and start the server:

```bash
cd ../companies_act_2013
python app.py
```

The Flask server will run on `http://localhost:5000`

### 4. Start the Next.js Development Server

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the application.

## Usage

1. Open your browser and navigate to `http://localhost:3000`
2. Enter a question about the Companies Act 2013 in the search bar
3. Click "Search" or press Enter
4. View the synthesized answer and source documents

## Features

- 🔍 Intelligent search across the Companies Act 2013
- 💡 AI-generated synthesized answers with citations
- 📚 Source document references with primary and supporting chunks
- 🎨 Modern, responsive UI built with Next.js and Tailwind CSS
- ⚡ Fast API communication between Next.js and Flask

## Tech Stack

- **Frontend**: Next.js 15, React 19, TypeScript, Tailwind CSS
- **Backend**: Flask, Python
- **API Communication**: Next.js API Routes proxying to Flask

## Project Structure

```
app/
├── src/
│   ├── app/
│   │   ├── api/
│   │   │   └── query/
│   │   │       └── route.ts       # API route for Flask communication
│   │   ├── page.tsx               # Main search page
│   │   ├── layout.tsx             # Root layout
│   │   └── globals.css            # Global styles
│   └── components/
│       ├── SearchBar.tsx          # Search input with example queries
│       ├── LoadingSpinner.tsx     # Loading state component
│       ├── SynthesizedAnswer.tsx  # AI answer display with markdown
│       └── SectionResults.tsx     # Legal document sections display
├── .env.local                     # Environment configuration
├── next.config.ts                 # Next.js configuration
├── tailwind.config.ts             # Tailwind CSS configuration
└── package.json                   # Dependencies
```

## Development

- Frontend runs on port 3000
- Backend (Flask) must run on port 5000 (configurable via FLASK_API_URL)
- Hot reload is enabled for both frontend and backend during development

