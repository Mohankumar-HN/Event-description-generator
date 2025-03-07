import os
import re
import json
from typing import Optional
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
import httpx
from pydantic import BaseModel
from prompt_templates import EVENT_DESCRIPTION_PROMPT

app = FastAPI(title="Event Description Generator")

# Set up templates and static files
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# iVis Labs API Configuration
WEBUI_BASE_URL = "https://chat.ivislabs.in/api"
API_KEY = "sk-3d8414fcf8d44495a9b4967a84cbbdd4"
DEFAULT_MODEL = "deepseek-r1:1.5b"

class EventRequest(BaseModel):
    event_name: str
    date: str
    location: str
    audience: str
    key_attractions: str
    event_type: Optional[str] = "formal"

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/generate", response_class=JSONResponse)
async def generate_event_description(
    event_name: str = Form(...),
    date: str = Form(...),
    location: str = Form(...),
    audience: str = Form(...),
    key_attractions: str = Form(...),
    event_type: str = Form("formal"),
    model: str = Form(DEFAULT_MODEL)
):
    try:
        # Create the prompt using event details
        prompt = EVENT_DESCRIPTION_PROMPT.format(
            event_name=event_name,
            date=date,
            location=location,
            audience=audience,
            key_attractions=key_attractions,
            event_type=event_type
        )
        
        messages = [{"role": "user", "content": prompt}]
        
        request_payload = {
            "model": model,
            "messages": messages
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{WEBUI_BASE_URL}/chat/completions",
                headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
                json=request_payload
            )

        if response.status_code == 200:
            result = response.json()
            ai_response = result.get("choices", [{}])[0].get("message", {}).get("content", "{}")

            # Debug: Print raw AI response
            print("Raw AI Response:", ai_response)

            # Extract only JSON block
            json_match = re.search(r"\{.*\}", ai_response, re.DOTALL)
            if json_match:
                try:
                    generated_data = json.loads(json_match.group())  # Parse JSON
                    
                    # Extract details
                    event_description = generated_data.get("event_description", "No event description available.")
                    social_media_post = generated_data.get("social_media_post", "No social media post available.")

                    return JSONResponse(content={
                        "generated_event_description": [
                            f"📅 <b>Date:</b> {date}",
                            f"📍 <b>Location:</b> {location}",
                            f"🎯 <b>Target Audience:</b> {audience}",
                            f"🌟 <b>Key Attractions:</b> {key_attractions}",
                            f"📝 <b>Event Summary:</b> {event_description}"
                        ],
                        "social_media_post": [
                            f"📢 {social_media_post}",
                            "#JoinUs #TechSummit2025"
                        ]
                    })

                except json.JSONDecodeError:
                    raise HTTPException(status_code=500, detail="AI response contained invalid JSON formatting.")

        raise HTTPException(status_code=500, detail="Failed to generate event description")

    except Exception as e:
        print(f"Error generating event description: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating event description: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
