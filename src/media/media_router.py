import pathlib
import uuid
import aiofiles
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse



app = APIRouter(prefix="/media", tags=["Media"])
UPLOAD_DIR = pathlib.Path("videos")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@app.post("/video")
async def upload_video(file:UploadFile = File(...)):
    ext = pathlib.Path(file.filename).suffix.lower()
    if ext not in [".mp4"]:
        raise HTTPException(status_code=400, detail="Only MP4 files are allowed")
    new_name = f"{uuid.uuid4()}{ext}"
    dist = UPLOAD_DIR / new_name
    
    async with aiofiles.open(dist, "wb") as f:
        while chunk := await file.read(1024 * 1024):
            await f.write(chunk)
            if not chunk:
                break
            await f.write(chunk)
    await file.close()
    return {"filename":new_name, "url":dist}



@app.get("/video")
async def get_video(filename:str):
    file = UPLOAD_DIR / filename
    return FileResponse(file, media_type="video/mp4")


@app.delete("/video")
async def get_video(filename:str):
    file = UPLOAD_DIR / filename
    file.unlink
    return True