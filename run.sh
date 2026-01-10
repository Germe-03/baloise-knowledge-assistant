#!/bin/bash
# S&P Knowledge Assistant - Start Script
# Steinmann & Partner GmbH

echo "🚀 Starte S&P Knowledge Assistant..."

# Prüfe ob Ollama läuft
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "✅ Ollama ist erreichbar"
else
    echo "⚠️  Ollama nicht gefunden. Starte mit: ollama serve"
fi

# Prüfe erforderliche Modelle
echo "📥 Prüfe LLM-Modelle..."
if ollama list 2>/dev/null | grep -q "mistral"; then
    echo "✅ Mistral Modell gefunden"
else
    echo "⚠️  Mistral nicht gefunden. Installiere mit: ollama pull mistral:7b-instruct-v0.3"
fi

if ollama list 2>/dev/null | grep -q "nomic-embed-text"; then
    echo "✅ Embedding Modell gefunden"
else
    echo "⚠️  Embedding-Modell nicht gefunden. Installiere mit: ollama pull nomic-embed-text"
fi

echo ""
echo "🌐 Starte Streamlit auf http://localhost:8501"
echo ""

# Streamlit starten
streamlit run app/main.py
