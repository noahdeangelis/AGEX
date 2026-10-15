# Setting Up a Cloud Model

AGEX supports cloud models through OpenAI-compatible APIs, such as Groq or OpenAI.

> Note: You need to get the API key from your choice of provider (e.g. Groq)

## 1. Get an API Key (From Groq method)

1. Visit https://console.groq.com/
2. Create an account.
3. Generate an API key.

## 2. Configure AGEX

Edit your `.env` file to look as following (for groq):

```env
OPENAI_API_KEY=your-api-key
CLOUD_MODEL_NAME=openai/gpt-oss-120b
CLOUD_BASE_URL=https://api.groq.com/openai/v1
```

Replace `your-api-key` with your actual API key generated

Replace `openai/gpt-oss-120b` for the model you have chosen

Replace `https://api.groq.com/openai/v1` to be correct for your choice of provider

> Note: You will use a different BASE_URL and MODEL_NAME based on your provider