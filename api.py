from fastapi import FastAPI
from pydantic import BaseModel
import base64
from PIL import Image
import io
from datetime import datetime
import os

app = FastAPI()

class ImageRequest(BaseModel):
    image: str

@app.post(f"/upload")
async def upload_image(request: ImageRequest):
    decoded = base64.b64decode(request.image)
    image = Image.open(io.BytesIO(decoded))

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}.png"

    os.makedirs(f"uploads/", exist_ok=True)
    image.save(f"uploads/{filename}")
    print(f"Image saved as {filename}")

    return {"ok": True}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
