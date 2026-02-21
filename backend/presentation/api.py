
from fastapi import FastAPI, HTTPException
try:
    from ..application.agent import run_agent
    from ..infrastructure.firebase_service import (
        save_purchase,
        save_chat,
        delete_purchase_order,
        get_purchase_order_by_id,
        get_product_by_id,
        get_product_by_detail,
    )
except ImportError:
    from application.agent import run_agent
    from infrastructure.firebase_service import (
        save_purchase,
        save_chat,
        delete_purchase_order,
        get_purchase_order_by_id,
        get_product_by_id,
        get_product_by_detail,
    )
from datetime import datetime, timezone
import uuid

app = FastAPI(title="HITL Agent Enterprise")


import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("main")

@app.post("/chat")
async def chat(data:dict):
    logger.info(f"[REQUEST] /chat: {data}")
    try:
        messages = data["messages"]
        user_id = data["user_id"]

        save_chat(user_id, messages[-1])

        result = run_agent(messages, user_id=user_id)

        if result["type"] == "UNSAFE":
            response = {
                "status":"APPROVAL_REQUIRED",
                "payload":result["payload"],
                "approval": result.get("approval", {})
            }
            logger.info(f"[RESPONSE] /chat: {response}")
            return response

        response = {"status":"OK","message":result["content"]}
        logger.info(f"[RESPONSE] /chat: {response}")
        return response

    except Exception as e:
        logger.error(f"[ERROR] /chat: {e}")
        raise HTTPException(500,str(e))


@app.post("/execute")
async def execute(data:dict):
    logger.info(f"[REQUEST] /execute: {data}")
    try:
        user_id = data.get("user_id")
        if not user_id:
            raise HTTPException(422, "user_id es obligatorio para ejecutar la compra")

        action = data.get("action", "CREATE_PURCHASE_ORDER")

        if action == "DELETE_PURCHASE_ORDER":
            order_id = data.get("purchase_order_id")
            if not order_id:
                raise HTTPException(422, "purchase_order_id es obligatorio para eliminar")

            existing_order = get_purchase_order_by_id(order_id)
            if not existing_order:
                raise HTTPException(404, f"No existe orden con id {order_id}")
            if existing_order.get("user_id") and existing_order.get("user_id") != user_id:
                raise HTTPException(403, "No puedes eliminar una orden de otro usuario")

            deleted_order = delete_purchase_order(order_id)
            response = {
                "status": "EXECUTED",
                "action": "DELETE_PURCHASE_ORDER",
                "deleted_purchase_order": deleted_order
            }
            logger.info(f"[DB] purchase_orders eliminado: {deleted_order}")
            logger.info(f"[RESPONSE] /execute: {response}")
            return response

        order_data = {
            k: v for k, v in data.items()
            if k not in {"user_id", "action"}
        }
        product_id = order_data.get("product_id")
        detail = order_data.get("detail")
        product = get_product_by_id(product_id) if product_id else None
        if not product and detail:
            product = get_product_by_detail(detail)
        if not product:
            raise HTTPException(
                422,
                "No se pudo resolver el producto. Debe existir y enviarse `detail` válido o `product_id`."
            )

        try:
            quantity = int(order_data.get("quantity"))
        except (TypeError, ValueError):
            raise HTTPException(422, "quantity debe ser un entero válido")
        if quantity <= 0:
            raise HTTPException(422, "quantity debe ser mayor a 0")

        unit_price = float(product.get("price", 0))
        purchase_order = {
            "id": str(uuid.uuid4()),
            "purchase_date": datetime.now(timezone.utc).isoformat(),
            "user_id": user_id,
            **order_data,
            "product_id": product["product_id"],
            "detail": product.get("detail", ""),
            "unit_price": unit_price,
            "quantity": quantity,
            "total_amount": round(quantity * unit_price, 2),
            "status": "EXECUTED"
        }
        saved_order = save_purchase(purchase_order)
        response = {
            "status":"EXECUTED",
            "action": "CREATE_PURCHASE_ORDER",
            "purchase_order": saved_order
        }
        logger.info(f"[DB] purchase_orders registrado: {saved_order}")
        logger.info(f"[RESPONSE] /execute: {response}")
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] /execute: {e}")
        raise HTTPException(500,str(e))
