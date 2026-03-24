import logging
import os
import sys
from typing import Any, Optional

import modal

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

app = modal.App("tiny-aya-global-api")

MODEL_PATH = "/models"
MODEL_ID = "CohereLabs/tiny-aya-global"
LOCAL_MODEL_DIR = f"{MODEL_PATH}/tiny-aya-global"
volume = modal.Volume.from_name("tiny-aya-global-assets", create_if_missing=False)

model_image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "torch",
        "transformers",
        "accelerate",
        "safetensors",
    )
)

@app.cls(
    image=model_image,
    gpu="A10G",
    timeout=1800,
    volumes={MODEL_PATH: volume},
    secrets=[modal.Secret.from_name("huggingface-secret")],
    scaledown_window=120,
)
@modal.concurrent(max_inputs=8, target_inputs=4)
class TinyAyaModel:
    @modal.enter()
    def load(self):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        model_source = LOCAL_MODEL_DIR if os.path.exists(LOCAL_MODEL_DIR) else MODEL_ID
        if model_source == MODEL_ID:
            log.warning("Local model path missing at %s; falling back to remote repo %s", LOCAL_MODEL_DIR, MODEL_ID)
        else:
            log.info("Loading model from local path: %s", model_source)

        hf_token = os.environ.get("HF_TOKEN")
        self.tokenizer = AutoTokenizer.from_pretrained(model_source, token=hf_token)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_source,
            token=hf_token,
            torch_dtype="auto",
            device_map="auto",
        )

    @modal.method()
    def generate(
        self,
        messages: list[dict[str, str]],
        max_new_tokens: int = 4096,
        temperature: float = 0.1,
        top_p: float = 0.95,
        do_sample: bool = True,
    ) -> str:
        import torch

        model_inputs = self.tokenizer.apply_chat_template(
            messages,
            tokenize=True,
            add_generation_prompt=True,
            return_dict=True,
            return_tensors="pt",
        )
        model_inputs = {k: v.to(self.model.device) for k, v in model_inputs.items()}

        use_sampling = do_sample and temperature > 0.0
        with torch.inference_mode():
            output_ids = self.model.generate(
                **model_inputs,
                max_new_tokens=max_new_tokens,
                do_sample=use_sampling,
                temperature=temperature if use_sampling else None,
                top_p=top_p if use_sampling else None,
            )

        prompt_len = model_inputs["input_ids"].shape[-1]
        generated_ids = output_ids[0][prompt_len:]
        return self.tokenizer.decode(generated_ids, skip_special_tokens=True).strip()


web_image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "fastapi==0.104.1",
        "uvicorn[standard]==0.24.0",
        "pydantic==2.5.0",
    )
)


@app.function(image=web_image, timeout=2400)
@modal.asgi_app(label="tiny-aya-global-web")
def fastapi_app():
    from fastapi import FastAPI
    from pydantic import BaseModel, Field

    class ChatMessage(BaseModel):
        role: str
        content: str

    class ChatRequest(BaseModel):
        messages: list[ChatMessage]
        max_new_tokens: int = Field(default=4096, ge=1, le=4096)
        temperature: float = Field(default=0.1, ge=0.0, le=2.0)
        top_p: float = Field(default=0.95, ge=0.0, le=1.0)
        do_sample: bool = True

    web_app = FastAPI(title="Tiny Aya Global API", version="1.0.0")

    @web_app.post("/v1/chat/completions")
    async def chat_completions(payload: ChatRequest) -> dict[str, Any]:
        response_text = TinyAyaModel().generate.remote(
            [m.model_dump() for m in payload.messages],
            max_new_tokens=payload.max_new_tokens,
            temperature=payload.temperature,
            top_p=payload.top_p,
            do_sample=payload.do_sample,
        )
        return {
            "model": MODEL_ID,
            "output_text": response_text,
        }

    @web_app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "healthy", "service": "tiny-aya-global"}

    return web_app


@app.local_entrypoint()
def main(prompt: Optional[str] = None):
    user_prompt = prompt or "Explain the Transformer architecture in simple terms."
    messages = [{"role": "user", "content": user_prompt}]
    output_text = TinyAyaModel().generate.remote(messages)
    print(output_text)
