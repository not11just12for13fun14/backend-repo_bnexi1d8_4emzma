import os
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, EmailStr

from database import db, create_document, get_documents

app = FastAPI(title="Nutritionist API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------
# Schemas (Pydantic)
# ---------------------
class User(BaseModel):
    name: str
    email: EmailStr
    role: str = Field("patient", description="patient | admin")
    avatar_url: Optional[str] = None


class Appointment(BaseModel):
    patient_email: EmailStr
    patient_name: str
    date: str = Field(..., description="ISO date, e.g., 2025-11-20")
    time: str = Field(..., description="HH:mm in 24h format")
    reason: Optional[str] = None
    status: str = Field("pending", description="pending | confirmed | canceled")


class Message(BaseModel):
    room: str = Field("general")
    sender: str
    sender_email: Optional[EmailStr] = None
    content: str


class QuestionnaireResponse(BaseModel):
    patient_email: EmailStr
    goals: Optional[str] = None
    allergies: Optional[str] = None
    dietary_preferences: Optional[str] = None
    notes: Optional[str] = None


class Prescription(BaseModel):
    patient_email: EmailStr
    patient_name: Optional[str] = None
    items: List[str] = Field(default_factory=list, description="List of supplement or diet items")
    instructions: Optional[str] = None


class InvoiceItem(BaseModel):
    name: str
    price: float
    quantity: int = 1


class Invoice(BaseModel):
    patient_email: EmailStr
    patient_name: Optional[str] = None
    items: List[InvoiceItem] = Field(default_factory=list)
    subtotal: float
    tax: float = 0.0
    total: float


# ---------------------
# Helpers
# ---------------------

def _collection(name: str):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available. Set DATABASE_URL and DATABASE_NAME.")
    return db[name]


# ---------------------
# Health & Meta
# ---------------------
@app.get("/")
def root():
    return {"message": "Nutritionist Backend Running"}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": "❌ Not Set",
        "database_name": "❌ Not Set",
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set"
            response["database_name"] = getattr(db, "name", "✅ Connected")
            response["connection_status"] = "Connected"
            try:
                response["collections"] = db.list_collection_names()[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️ Connected but Error: {str(e)[:80]}"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:80]}"
    return response


# ---------------------
# Auth (Google - placeholder)
# ---------------------
@app.get("/auth/google/start")
def google_auth_start():
    return {"status": "placeholder", "message": "Google OAuth flow not enabled in this demo."}


# ---------------------
# Appointments
# ---------------------
@app.post("/api/appointments")
def create_appointment(payload: Appointment):
    appt_id = create_document("appointment", payload)
    return {"id": appt_id, "status": "created"}


@app.get("/api/appointments")
def list_appointments(patient_email: Optional[str] = None, limit: int = 50):
    filt = {"patient_email": patient_email} if patient_email else {}
    items = get_documents("appointment", filt, limit)
    return {"items": [
        {**{k: (v.isoformat() if hasattr(v, 'isoformat') else v) for k, v in d.items()}, "id": str(d.get("_id"))}
        for d in items
    ]}


# ---------------------
# Messages (Simple Live Chat)
# ---------------------
@app.post("/api/messages")
def post_message(payload: Message):
    msg_id = create_document("message", payload)
    return {"id": msg_id, "status": "created"}


@app.get("/api/messages")
def get_messages(room: str = "general", limit: int = 50):
    items = get_documents("message", {"room": room}, limit)
    return {"items": [
        {**{k: (v.isoformat() if hasattr(v, 'isoformat') else v) for k, v in d.items()}, "id": str(d.get("_id"))}
        for d in items
    ]}


# ---------------------
# Questionnaire
# ---------------------
@app.post("/api/questionnaires")
def submit_questionnaire(payload: QuestionnaireResponse):
    q_id = create_document("questionnaireresponse", payload)
    return {"id": q_id, "status": "submitted"}


# ---------------------
# Prescriptions
# ---------------------
@app.post("/api/prescriptions")
def create_prescription(payload: Prescription):
    p_id = create_document("prescription", payload)
    return {"id": p_id, "status": "created"}


@app.get("/api/prescriptions")
def list_prescriptions(patient_email: Optional[str] = None, limit: int = 50):
    filt = {"patient_email": patient_email} if patient_email else {}
    items = get_documents("prescription", filt, limit)
    return {"items": [
        {**{k: (v.isoformat() if hasattr(v, 'isoformat') else v) for k, v in d.items()}, "id": str(d.get("_id"))}
        for d in items
    ]}


# ---------------------
# Invoices
# ---------------------
@app.post("/api/invoices")
def create_invoice(payload: Invoice):
    inv_id = create_document("invoice", payload)
    return {"id": inv_id, "status": "created"}


@app.get("/api/invoices")
def list_invoices(patient_email: Optional[str] = None, limit: int = 50):
    filt = {"patient_email": patient_email} if patient_email else {}
    items = get_documents("invoice", filt, limit)
    return {"items": [
        {**{k: (v.isoformat() if hasattr(v, 'isoformat') else v) for k, v in d.items()}, "id": str(d.get("_id"))}
        for d in items
    ]}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
