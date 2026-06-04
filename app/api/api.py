import os

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.services.pdf_export import export_pdf
from app.graph.graph import graph

app = FastAPI(
    title="AI Travel Planner",
    version="1.0"
)

# Allow Streamlit (port 8501) to call FastAPI (port 8000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "http://127.0.0.1:8501"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

LATEST_PDF = None


class TravelRequest(BaseModel):
    session_id: str = "default"
    query: str
    trip_type: str = "budget"
    modify: bool = False
    modification_request: str = ""


@app.post("/plan")
def generate_plan(request: TravelRequest):

    global LATEST_PDF

    print("\n===== API REQUEST =====")
    print("Session ID:", request.session_id)
    print("Query:", request.query)
    print("Trip Type:", request.trip_type)
    print("Modify:", request.modify)
    print(
        "Modification Request:",
        request.modification_request
    )

    state = {
        "user_query": request.query,

        "destination": None,
        "budget": None,
        "days": None,

        "weather": None,

        "trip_type": request.trip_type,

        "modify": request.modify,

        "modification_request":
            request.modification_request,

        "itinerary": "",

        "estimated_cost": 0,

        "recommendations": [],

        "missing_information": [],

        "previous_destination": None,

        "final_response": {}
    }

    result = graph.invoke(
        state,
        config={
            "configurable": {
                "thread_id":
                    request.session_id
            }
        }
    )

    response = result["final_response"]

    response["weather"] = result.get(
        "weather"
    )

    pdf_path = export_pdf(
        response
    )

    LATEST_PDF = pdf_path

    return {
        "message":
            "Travel plan generated successfully",

        "session_id":
            request.session_id,

        "pdf_file":
            pdf_path,

        "plan":
            response
    }


@app.get("/plan/latest-pdf")
def download_latest_pdf():

    global LATEST_PDF

    if (
        not LATEST_PDF
        or
        not os.path.exists(LATEST_PDF)
    ):
        raise HTTPException(
            status_code=404,
            detail="No generated PDF found."
        )

    return FileResponse(
        path=LATEST_PDF,
        media_type="application/pdf",
        filename=os.path.basename(
            LATEST_PDF
        )
    )


@app.get("/")
def health():
    return {
        "status": "running",
        "message": "AI Travel Planner API"
    }