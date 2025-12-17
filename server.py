#!/usr/bin/env python3
"""
Image Tools Server (Perspective Crop + Inpaint)
FastAPI + Jinja2 Templates
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Form
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request
import uvicorn
import numpy as np
from PIL import Image
import base64
import io

BASE_DIR = Path(__file__).parent

# LaMA model (singleton)
_lama_model = None


def get_lama():
    global _lama_model
    if _lama_model is None:
        from simple_lama_inpainting import SimpleLama
        print("Loading LaMA model...")
        _lama_model = SimpleLama(device='mps')  # pyright: ignore[reportArgumentType]
        print("LaMA model loaded")
    return _lama_model


@asynccontextmanager
async def lifespan(app: FastAPI):
    get_lama()
    yield


app = FastAPI(title="Image Tools", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


@app.get("/")
async def home_page(request: Request):
    return templates.TemplateResponse("home.html", {
        "request": request,
        "title": "Image Tools",
        "page": "home"
    })


@app.get("/perspective")
async def perspective_page(request: Request):
    return templates.TemplateResponse("perspective.html", {
        "request": request,
        "title": "Perspective Crop",
        "page": "perspective"
    })


@app.get("/inpaint")
async def inpaint_page(request: Request):
    return templates.TemplateResponse("inpaint.html", {
        "request": request,
        "title": "Inpaint",
        "page": "inpaint"
    })


@app.get("/convert")
async def convert_page(request: Request):
    return templates.TemplateResponse("convert.html", {
        "request": request,
        "title": "Image Converter",
        "page": "convert"
    })


@app.post("/api/inpaint")
async def inpaint(
    image: str = Form(...),
    mask: str = Form(...)
):
    try:
        img_data = base64.b64decode(image.split(",")[1])
        mask_data = base64.b64decode(mask.split(",")[1])

        from PIL import ImageOps
        img_pil = Image.open(io.BytesIO(img_data))
        img_pil = ImageOps.exif_transpose(img_pil)
        img_pil = img_pil.convert("RGB")
        mask_pil = Image.open(io.BytesIO(mask_data)).convert("L")

        original_size = img_pil.size

        MAX_SIZE = 1024
        scale = 1.0
        if max(img_pil.size) > MAX_SIZE:
            scale = MAX_SIZE / max(img_pil.size)
            new_w = int(img_pil.width * scale)
            new_h = int(img_pil.height * scale)
            img_pil = img_pil.resize((new_w, new_h), Image.LANCZOS)

        if mask_pil.size != img_pil.size:
            mask_pil = mask_pil.resize(img_pil.size, Image.NEAREST)

        mask_np = np.array(mask_pil)
        mask_binary = (mask_np > 128).astype(np.uint8) * 255

        if np.sum(mask_binary) == 0:
            return JSONResponse({"error": "Please draw a mask area."}, status_code=400)

        lama = get_lama()
        result = lama(img_pil, Image.fromarray(mask_binary))

        if result.size != img_pil.size:
            result = result.crop((0, 0, img_pil.width, img_pil.height))

        if scale < 1.0:
            result = result.resize(original_size, Image.LANCZOS)

        buf = io.BytesIO()
        result.save(buf, format="PNG")
        result_b64 = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()

        return {"result": result_b64}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


if __name__ == "__main__":
    print("Server started: http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
