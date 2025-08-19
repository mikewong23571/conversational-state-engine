# OpenAI-Compatible API Configuration Guide

This project supports various OpenAI-compatible API providers including OpenAI, vLLM, Ollama, DeepSeek, and others.

## Quick Setup

### 1. Choose Your Provider

Edit your `.env` file and set the appropriate configuration:

```bash
# Enable OpenAI-compatible provider
CSE_LLM_PROVIDER=openai
```

### 2. Configure Your Provider

Choose one of the following configurations:

#### OpenAI Official API
```bash
CSE_LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-openai-key-here
# CSE_MODEL=gpt-3.5-turbo  # Optional, defaults to gpt-3.5-turbo
```

#### vLLM Server
```bash
CSE_LLM_PROVIDER=openai
CSE_API_KEY=dummy-key  # vLLM often doesn't require real API key
CSE_BASE_URL=http://localhost:8000/v1
CSE_MODEL=your-model-name  # e.g., microsoft/DialoGPT-medium
```

#### Ollama
```bash
CSE_LLM_PROVIDER=openai
CSE_API_KEY=dummy-key  # Ollama doesn't require API key
CSE_BASE_URL=http://localhost:11434/v1
CSE_MODEL=llama2  # or your preferred model
```

#### DeepSeek API
```bash
CSE_LLM_PROVIDER=openai
CSE_API_KEY=your-deepseek-api-key
CSE_BASE_URL=https://api.deepseek.com/v1
CSE_MODEL=deepseek-chat
```

#### Anthropic Claude (via OpenAI-compatible proxy)
```bash
CSE_LLM_PROVIDER=openai
CSE_API_KEY=your-anthropic-api-key
CSE_BASE_URL=https://your-proxy-url/v1
CSE_MODEL=claude-3-sonnet-20240229
```

#### Local LM Studio
```bash
CSE_LLM_PROVIDER=openai
CSE_API_KEY=lm-studio
CSE_BASE_URL=http://localhost:1234/v1
CSE_MODEL=your-loaded-model
```

### 3. Start the Server

```bash
# Restart the backend server to apply new configuration
pnpm run dev:backend
```

You should see confirmation messages like:
```
Using OpenAI-compatible API at: http://localhost:8000/v1
Model: your-model-name
✅ LLM Analyzer initialized with provider: openai
```

## Testing Your Setup

### 1. Check API Health
```bash
curl http://localhost:8000/health
```

### 2. Test Authentication
```bash
# Register a user
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "test123", "role": "admin"}'

# Login to get token
TOKEN=$(curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "test123"}' \
  | jq -r '.access_token')
```

### 3. Create a Session
```bash
SESSION_ID=$(curl -X POST http://localhost:8000/sessions \
  -H "Authorization: Bearer $TOKEN" \
  | jq -r '.session_id')

echo "Session ID: $SESSION_ID"
```

### 4. Test LLM Analysis
```bash
curl -X POST http://localhost:8000/sessions/$SESSION_ID/analyze \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "Add a new user login story with SSO support"}'
```

Expected response should include:
```json
{
  "message": "Add a new user login story with SSO support",
  "intentions": {
    "items": [...],
    "notes": null
  },
  "analyzer_type": "openai",
  "context_analysis": {...}
}
```

## Provider-Specific Setup Instructions

### vLLM Setup

1. **Install vLLM**:
```bash
pip install vllm
```

2. **Start vLLM server**:
```bash
vllm serve microsoft/DialoGPT-medium \
  --host 0.0.0.0 \
  --port 8000 \
  --api-key dummy-key
```

3. **Configure CSE**:
```bash
CSE_LLM_PROVIDER=openai
CSE_API_KEY=dummy-key
CSE_BASE_URL=http://localhost:8000/v1
CSE_MODEL=microsoft/DialoGPT-medium
```

### Ollama Setup

1. **Install Ollama**:
Visit https://ollama.ai and follow installation instructions

2. **Pull a model**:
```bash
ollama pull llama2
```

3. **Start Ollama with OpenAI compatibility**:
```bash
OLLAMA_ORIGINS=* ollama serve
```

4. **Configure CSE**:
```bash
CSE_LLM_PROVIDER=openai
CSE_API_KEY=dummy-key
CSE_BASE_URL=http://localhost:11434/v1
CSE_MODEL=llama2
```

### DeepSeek Setup

1. **Get API Key**:
Visit https://platform.deepseek.com and create an account

2. **Configure CSE**:
```bash
CSE_LLM_PROVIDER=openai
CSE_API_KEY=your-deepseek-api-key
CSE_BASE_URL=https://api.deepseek.com/v1
CSE_MODEL=deepseek-chat
```

## Environment Variables Reference

| Variable | Description | Example |
|----------|-------------|---------|
| `CSE_LLM_PROVIDER` | LLM provider type | `openai` |
| `OPENAI_API_KEY` | OpenAI official API key | `sk-...` |
| `CSE_API_KEY` | Alternative API key for other providers | `your-key` |
| `CSE_BASE_URL` | Custom API base URL | `http://localhost:8000/v1` |
| `OPENAI_BASE_URL` | Alternative base URL env var | `http://localhost:8000/v1` |
| `CSE_MODEL` | Model name to use | `gpt-3.5-turbo` |

## Troubleshooting

### Common Issues

**1. "No API key provided" error**
```bash
# Make sure you set one of these:
export OPENAI_API_KEY=your-key  # For OpenAI
export CSE_API_KEY=your-key     # For other providers
```

**2. Connection refused**
```bash
# Check if your API server is running
curl http://localhost:8000/v1/models  # for vLLM
curl http://localhost:11434/api/tags  # for Ollama
```

**3. "Model not found" error**
```bash
# Verify your model name matches what's available
# For vLLM: check the model you started the server with
# For Ollama: run 'ollama list' to see available models
```

**4. Authentication errors**
```bash
# Check your API key is correct and has proper permissions
# For local servers, often any dummy key works
```

### Debug Mode

Enable debug logging:
```bash
export DEBUG=1
export PYTHONPATH=.
uv run uvicorn server.app:app --reload --port 8000 --log-level debug
```

### Testing Different Models

You can test different models by changing the `CSE_MODEL` environment variable:

```bash
# Test with different models
export CSE_MODEL=gpt-4
# or
export CSE_MODEL=llama2:13b
# or  
export CSE_MODEL=deepseek-coder
```

Then restart the server to apply changes.

## Performance Tips

1. **Use faster models for development**: `gpt-3.5-turbo` instead of `gpt-4`
2. **Local models**: Consider using Ollama or vLLM for offline development
3. **Caching**: The system includes intelligent context slicing to reduce API costs
4. **Fallback**: Always keeps mock analyzer as fallback if LLM fails

## Security Considerations

1. **API Keys**: Never commit API keys to version control
2. **Local servers**: Ensure proper firewall configuration
3. **Production**: Use environment variable management services
4. **Rate limiting**: Be aware of API rate limits from your provider

Your Conversational State Engine is now ready to work with any OpenAI-compatible API provider!