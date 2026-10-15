# Setting Up a Local Model

AGEX supports local models through a llama.cpp server.

## 1. Download a Model

Download a GGUF model from [Hugging Face](https://huggingface.co/models?library=gguf).

## 2. Start the Server

Install llama.cpp, then start the server:

```bash
llama-server -m /path/to/model.gguf --port 8080 --jinja
```

Replace `/path/to/model.gguf` with your model's file path.

## 3. Configure AGEX

Add the following to your `.env` file:

```env
LOCAL_MODEL_URL=http://localhost:8080/v1
LOCAL_MODEL_NAME=local-model-name
```

Replace `local-model-name` with your model's name.

## 4. Run AGEX

Keep the llama.cpp server running and start AGEX.

**Note:** Local models run on your own hardware and don't require a cloud API key.