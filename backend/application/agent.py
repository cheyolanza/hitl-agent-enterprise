from openai import OpenAI
import os
from dotenv import load_dotenv
import logging
import json
try:
    from ..infrastructure.firebase_service import (
        list_purchase_orders,
        get_purchase_order_by_id,
        get_product_by_detail,
    )
except ImportError:
    from infrastructure.firebase_service import (
        list_purchase_orders,
        get_purchase_order_by_id,
        get_product_by_detail,
    )


# Cargar variables de entorno desde .env

# Cargar variables de entorno desde .env
load_dotenv()

# Configuración básica de logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("agent")


# Usar la variable de entorno OPENAI_API_KEY definida en .env
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

tools = [
    {
        "type":"function",
        "function":
        {
            "name":"create_purchase_order",
            "description":"Crear orden de compra",
            "parameters":
            {
                "type":"object",
                "properties":
                {
                    "detail":{"type":"string"},
                    "quantity":{"type":"integer"},
                    "justification":{"type":"string"}
                },
                "required":["detail","quantity"]
            }
        }
    },
    {
        "type":"function",
        "function":
        {
            "name":"list_purchase_orders",
            "description":"Listar órdenes de compra registradas",
            "parameters":
            {
                "type":"object",
                "properties":
                {
                    "user_id":{"type":"string"},
                    "date":{"type":"string", "description":"Fecha en formato YYYY-MM-DD"},
                    "status":{"type":"string"},
                    "limit":{"type":"integer"}
                }
            }
        }
    },
    {
        "type":"function",
        "function":
        {
            "name":"delete_purchase_order",
            "description":"Eliminar una orden de compra por ID",
            "parameters":
            {
                "type":"object",
                "properties":
                {
                    "purchase_order_id":{"type":"string"},
                    "reason":{"type":"string"}
                },
                "required":["purchase_order_id"]
            }
        }
    }
]




def run_agent(messages, user_id=None):
    logger.info("Mensajes enviados a OpenAI:")
    for m in messages:
        logger.info(m)
    logger.info(f"OPENAI_API_KEY usado: {os.getenv('OPENAI_API_KEY')}")
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            tools=tools
        )
        logger.info(f"Respuesta OpenAI: {response}")
    except Exception as e:
        logger.error(f"Error al llamar OpenAI: {e}")
        raise

    msg = response.choices[0].message

    if msg.tool_calls:
        tool_call = msg.tool_calls[0].function
        tool_name = tool_call.name
        raw_args = tool_call.arguments
        # OpenAI tool arguments come as a JSON string; parse before returning.
        try:
            payload = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
        except json.JSONDecodeError:
            logger.error(f"Tool arguments no son JSON válido: {raw_args}")
            payload = raw_args

        if tool_name == "create_purchase_order":
            safe_payload = payload if isinstance(payload, dict) else {}
            detail = safe_payload.get("detail")
            quantity = safe_payload.get("quantity")
            if not detail:
                return {
                    "type": "NORMAL",
                    "content": "Para crear la orden necesito `detail` del producto."
                }
            try:
                quantity_value = int(quantity)
            except (TypeError, ValueError):
                return {
                    "type": "NORMAL",
                    "content": "La cantidad debe ser un número entero válido."
                }
            if quantity_value <= 0:
                return {
                    "type": "NORMAL",
                    "content": "La cantidad debe ser mayor a 0."
                }

            product = get_product_by_detail(detail)
            if not product:
                return {
                    "type": "NORMAL",
                    "content": f"No encontré un producto único con detail `{detail}` en la base de datos."
                }

            unit_price = float(product.get("price", 0))
            enriched_payload = {
                "action": "CREATE_PURCHASE_ORDER",
                "product_id": product["product_id"],
                "detail": product.get("detail", ""),
                "unit_price": unit_price,
                "quantity": quantity_value,
                "total_amount": round(quantity_value * unit_price, 2),
                "justification": safe_payload.get("justification", ""),
            }
            return {
                "type": "UNSAFE",
                "payload": enriched_payload,
                "approval": {
                    "action": "CREATE_PURCHASE_ORDER",
                    "impact": "Se creará una nueva orden de compra en la base de datos.",
                    "record": enriched_payload
                }
            }

        if tool_name == "list_purchase_orders":
            safe_payload = payload if isinstance(payload, dict) else {}
            orders = list_purchase_orders(
                user_id=safe_payload.get("user_id") or user_id,
                date=safe_payload.get("date"),
                status=safe_payload.get("status"),
                limit=safe_payload.get("limit", 20),
            )

            if not orders:
                return {
                    "type": "NORMAL",
                    "content": "No se encontraron órdenes de compra con esos filtros."
                }

            return {
                "type": "NORMAL",
                "content": "Órdenes de compra encontradas:\n```json\n"
                + json.dumps(orders, ensure_ascii=False, indent=2)
                + "\n```"
            }

        if tool_name == "delete_purchase_order":
            safe_payload = payload if isinstance(payload, dict) else {}
            order_id = safe_payload.get("purchase_order_id")
            if not order_id:
                return {
                    "type": "NORMAL",
                    "content": "Para eliminar, necesito el `purchase_order_id`."
                }

            target = get_purchase_order_by_id(order_id)
            if not target:
                return {
                    "type": "NORMAL",
                    "content": f"No existe una orden con id `{order_id}`."
                }

            if user_id and target.get("user_id") and target.get("user_id") != user_id:
                return {
                    "type": "NORMAL",
                    "content": "No puedes eliminar una orden que pertenece a otro usuario."
                }

            return {
                "type": "UNSAFE",
                "payload": {
                    "action": "DELETE_PURCHASE_ORDER",
                    "purchase_order_id": order_id,
                    "reason": safe_payload.get("reason", "")
                },
                "approval": {
                    "action": "DELETE_PURCHASE_ORDER",
                    "impact": "Se eliminará permanentemente el registro de la orden de compra.",
                    "record": target
                }
            }

    return {"type":"NORMAL","content":msg.content}
