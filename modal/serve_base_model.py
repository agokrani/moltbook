"""
Deploy Qwen3.5-35B-A3B-Base on Modal with SGLang.

Exposes an OpenAI-compatible /v1/completions endpoint that the
content-gen service on Alliance Canada can call.

Usage:
    # Download model weights first (one-time)
    modal run modal/serve_base_model.py::download_model

    # Deploy (stays running until stopped)
    modal deploy modal/serve_base_model.py

    # Test locally first
    modal run modal/serve_base_model.py

    # Get the endpoint URL after deploy:
    #   https://<your-workspace>--qwen35-base-model-v1-completions.modal.run
"""

import modal

MODEL_NAME = "Qwen/Qwen3.5-35B-A3B-Base"
GPU = "H100:2"
DTYPE = "bfloat16"
MAX_MODEL_LEN = 16384

app = modal.App("qwen35-base")

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

model_volume = modal.Volume.from_name("qwen35-base-weights", create_if_missing=True)
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
)
@modal.concurrent(max_inputs=32)
class Model:
    @modal.enter()
    def start_engine(self):
        import os
        os.environ["SGLANG_DISABLE_CUDNN_CHECK"] = "1"
        import sglang as sgl

        self.engine = sgl.Engine(
            model_path=f"{MODEL_DIR}/{MODEL_NAME}",
            dtype=DTYPE,
            mem_fraction_static=0.88,
            tp_size=2,
            trust_remote_code=True,
            context_length=MAX_MODEL_LEN,
        )
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
            "stop": stop or ["\n---\n", "\n### ", "\n## ", "<|endoftext|>"],
        }

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
        """OpenAI-compatible /v1/completions endpoint."""
        prompt = request.get("prompt", "")
        max_tokens = request.get("max_tokens", 16384)
        temperature = request.get("temperature", 0.9)
        top_p = request.get("top_p", 0.95)
        repetition_penalty = request.get("repetition_penalty", 1.1)
        stop = request.get("stop", None)

        result = await self.generate.local(
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            repetition_penalty=repetition_penalty,
            stop=stop,
        )

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
    """Download model then test a completion."""
    download_model.remote()

    model = Model()
    import asyncio
    result = asyncio.get_event_loop().run_until_complete(
        model.generate.remote.aio(
            prompt="The meaning of life is",
            max_tokens=50,
        )
    )
    print(f"Test output: {result['text'][:200]}")
    print(f"Tokens: {result['usage']}")
