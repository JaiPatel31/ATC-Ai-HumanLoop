from fastapi import FastAPI, UploadFile
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"status": "ATC backend running"}

@app.post("/stt")
async def stt(file: UploadFile):
    # placeholder
    return {"transcript": "N123AB ready for takeoff runway two seven"}
