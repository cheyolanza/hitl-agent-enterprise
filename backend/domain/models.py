
from pydantic import BaseModel
from typing import List, Optional

class ChatMessage(BaseModel):
    role: str
    content: str

class PurchaseOrder(BaseModel):
    product_id: str
    quantity: int
    justification: str

class ApprovalResponse(BaseModel):
    status: str
    action: str
    payload: dict