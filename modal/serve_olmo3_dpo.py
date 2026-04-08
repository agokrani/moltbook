"""
Deploy OLMo-3.1-32B-Instruct (full RL pipeline: SFT+DPO+RLVR) on Modal with SGLang.

Supports both completions and chat formats on the /v1_completions endpoint.
Chat requests are automatically formatted using the model's chat template.

Usage:
    modal run modal/serve_olmo3_instruct.py::download_model
    modal deploy modal/serve_olmo3_instruct.py
"""

import modal

MODEL_NAME = "allenai/Olmo-3.1-32B-Instruct-DPO"
GPU = "H100:2"
DTYPE = "bfloat16"
MAX_MODEL_LEN = 32768

app = modal.App("olmo3-dpo")

sglang_image = (
    modal.Image.from_registry("nvidia/cuda:12.6.3-devel-ubuntu22.04", add_python="3.11")
    .env({
        "HF_HUB_ENABLE_HF_TRANSFER": "1",
        "CUDA_HOME": "/usr/local/cuda",
        "SGLANG_DISABLE_CUDNN_CHECK": "1",
    })
    .apt_install("libnuma-dev")
    .pip_install("nvidia-cudnn-cu12==9.16.0.29")
    .pip_install(
        "sglang[all]>=0.4",
        "sgl-kernel",
        "huggingface_hub[hf_xet]",
        "hf_transfer",
        "flashinfer-python",
    )
)

model_volume = modal.Volume.from_name("olmo3-dpo-weights", create_if_missing=True)
MODEL_DIR = "/models"


@app.function(
    image=sglang_image,
    volumes={MODEL_DIR: model_volume},
    timeout=1800,
)
def download_model():
    """Download model weights to the volume (run once)."""
    from huggingface_hub import snapshot_download

    snapshot_download(
        MODEL_NAME,
        local_dir=f"{MODEL_DIR}/{MODEL_NAME}",
    )
    model_volume.commit()
    print(f"Model downloaded to {MODEL_DIR}/{MODEL_NAME}")


@app.cls(
    image=sglang_image,
    gpu=GPU,
    volumes={MODEL_DIR: model_volume},
    scaledown_window=3600,
    timeout=3600,
    max_containers=1,
)
@modal.concurrent(max_inputs=32)
class Model:
    @modal.enter()
    def start_engine(self):
        import os
        os.environ["SGLANG_DISABLE_CUDNN_CHECK"] = "1"
        import sglang as sgl
        from transformers import AutoTokenizer

        self.engine = sgl.Engine(
            model_path=f"{MODEL_DIR}/{MODEL_NAME}",
            dtype=DTYPE,
            mem_fraction_static=0.88,
            tp_size=2,
            context_length=MAX_MODEL_LEN,
        )
        self.tokenizer = AutoTokenizer.from_pretrained(f"{MODEL_DIR}/{MODEL_NAME}")
        print(f"SGLang engine ready: {MODEL_NAME} (ctx={MAX_MODEL_LEN})")

    @modal.exit()
    def stop_engine(self):
        if hasattr(self, "engine"):
            self.engine.shutdown()

    @modal.method()
    async def generate(self, prompt: str, max_tokens: int = 16384, temperature: float = 0.9,
                 top_p: float = 0.95, repetition_penalty: float = 1.1,
                 stop: list[str] | None = None):

        sampling_params = {
            "max_new_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "repetition_penalty": repetition_penalty,
        }

        if stop:
            sampling_params["stop"] = stop

        output = await self.engine.async_generate(prompt, sampling_params)
        text = output["text"]

        return {
            "text": text,
            "model": MODEL_NAME,
            "usage": {
                "prompt_tokens": output.get("meta_info", {}).get("prompt_tokens", 0),
                "completion_tokens": output.get("meta_info", {}).get("completion_tokens", 0),
            },
        }

    @modal.fastapi_endpoint(method="POST", docs=True)
    async def v1_completions(self, request: dict):
        """OpenAI-compatible endpoint supporting both completions and chat formats."""
        messages = request.get("messages")
        max_tokens = request.get("max_tokens", 16384)
        temperature = request.get("temperature", 0.9)
        top_p = request.get("top_p", 0.95)
        repetition_penalty = request.get("repetition_penalty", 1.1)
        stop = request.get("stop", None)

        if messages:
            prompt = self.tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
        else:
            prompt = request.get("prompt", "")

        result = await self.generate.local(
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            repetition_penalty=repetition_penalty,
            stop=stop,
        )

        if messages:
            return {
                "id": "cmpl-modal",
                "object": "chat.completion",
                "model": result["model"],
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": result["text"]},
                        "finish_reason": "stop",
                    }
                ],
                "usage": result["usage"],
            }

        return {
            "id": "cmpl-modal",
            "object": "text_completion",
            "model": result["model"],
            "choices": [
                {
                    "index": 0,
                    "text": result["text"],
                    "finish_reason": "stop",
                }
            ],
            "usage": result["usage"],
        }

    @modal.fastapi_endpoint(method="GET")
    def health(self):
        return {"status": "ok", "model": MODEL_NAME, "max_model_len": MAX_MODEL_LEN, "engine": "sglang"}


@app.local_entrypoint()
def main():
    download_model.remote()

    model = Model()
    import asyncio
    result = asyncio.get_event_loop().run_until_complete(
        model.generate.remote.aio(
            prompt="The meaning of life is",
            max_tokens=50,
        )
    )
    print(f"Test output: {result['text']}")
    print(f"Tokens: {result['usage']}")
