from fastapi import FastAPI

app = FastAPI()


@app.get("/message")
async def get_static_message():
    # Return static text
    return "not implemented yet"

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
