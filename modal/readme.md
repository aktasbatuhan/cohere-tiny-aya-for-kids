# Tiny Aya on Modal

## 1) Upload model files to Modal Volume

Run this once (or whenever you need to refresh model files):

```bash
modal run upload.py
```

This downloads `CohereLabs/tiny-aya-global` into the configured Modal volume.

## 2) Deploy inference API

Deploy the API service:

```bash
modal deploy inference.py
```

After deploy, Modal prints the web endpoint URL (for `fastapi_app`), for example:

`https://<workspace>--tiny-aya-global-web.modal.run`

## 3) Call the endpoint with curl

Replace `<YOUR_ENDPOINT_URL>` with the URL shown by `modal deploy`:

```bash
curl -X POST "<YOUR_ENDPOINT_URL>/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Explain the Transformer architecture in simple terms."}
    ],
    "max_new_tokens": 512,
    "temperature": 0.1,
    "top_p": 0.95,
    "do_sample": true
  }'
```
