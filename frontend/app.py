import streamlit as st
import requests
import json

API="http://localhost:8000"

st.markdown(
    """
    <style>
    button[kind="primary"] {
        background-color: #16a34a !important;
        border-color: #16a34a !important;
        color: #ffffff !important;
    }
    button[kind="primary"]:hover {
        background-color: #15803d !important;
        border-color: #15803d !important;
    }
    button[kind="secondary"] {
        background-color: #dc2626 !important;
        border-color: #dc2626 !important;
        color: #ffffff !important;
    }
    button[kind="secondary"]:hover {
        background-color: #b91c1c !important;
        border-color: #b91c1c !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

if "state" not in st.session_state:
    st.session_state.state="CHAT"
if "payload" not in st.session_state:
    st.session_state.payload = None
if "approval" not in st.session_state:
    st.session_state.approval = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

user=st.text_input("User email")

if st.button("Limpiar chat"):
    st.session_state.chat_history = []
    st.session_state.state = "CHAT"
    st.session_state.payload = None
    st.session_state.approval = None
    st.rerun()

for message in st.session_state.chat_history:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if st.session_state.state=="APPROVAL":
    payload_data = st.session_state.payload or {}
    approval = st.session_state.approval or {}
    action = approval.get("action") or payload_data.get("action", "UNKNOWN")
    impact = approval.get("impact", "Esta acción impactará registros en la base de datos.")
    record = approval.get("record")

    st.warning(f"Acción crítica: {action}")
    st.write("Impacto:")
    st.info(impact)
    st.write("Registro objetivo:")
    if record:
        st.json(record)
    else:
        st.json(payload_data)

    col1, col2 = st.columns(2)
    if col1.button("Sí", use_container_width=True, type="primary"):
        st.session_state.chat_history.append(
            {"role": "user", "content": "Confirmo la ejecución de la acción crítica."}
        )
        payload = payload_data
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except json.JSONDecodeError:
                st.error("El payload de aprobación no es JSON válido.")
                st.stop()

        execute_payload = {"user_id": user, **payload}
        resp = requests.post(f"{API}/execute", json=execute_payload)
        if resp.ok:
            data = resp.json()
            if "purchase_order" in data:
                st.session_state.chat_history.append(
                    {
                        "role": "assistant",
                        "content": "Orden ejecutada y registrada:\n```json\n"
                        + json.dumps(data["purchase_order"], ensure_ascii=False, indent=2)
                        + "\n```",
                    }
                )
            elif "deleted_purchase_order" in data:
                st.session_state.chat_history.append(
                    {
                        "role": "assistant",
                        "content": "Orden eliminada:\n```json\n"
                        + json.dumps(data["deleted_purchase_order"], ensure_ascii=False, indent=2)
                        + "\n```",
                    }
                )
            else:
                st.session_state.chat_history.append(
                    {"role": "assistant", "content": "Orden ejecutada correctamente."}
                )
            st.session_state.state = "CHAT"
            st.session_state.payload = None
            st.session_state.approval = None
            st.rerun()
        else:
            st.error(f"Error al ejecutar: {resp.status_code} - {resp.text}")
    if col2.button("No", use_container_width=True, type="secondary"):
        st.session_state.chat_history.append(
            {"role": "user", "content": "No apruebo esta acción crítica."}
        )
        st.session_state.chat_history.append(
            {"role": "assistant", "content": "Acción cancelada. No se realizó ningún cambio en la base de datos."}
        )
        st.session_state.state = "CHAT"
        st.session_state.payload = None
        st.session_state.approval = None
        st.rerun()

prompt = st.chat_input("Escribe tu mensaje")
if prompt:
    if not user:
        st.error("Ingresa primero el User email.")
        st.stop()

    st.session_state.chat_history.append({"role": "user", "content": prompt})
    messages = [
        {"role": m["role"], "content": m["content"]}
        for m in st.session_state.chat_history
        if m["role"] in {"user", "assistant"}
    ]

    try:
        res = requests.post(
            f"{API}/chat",
            json={"user_id": user, "messages": messages}
        ).json()
    except Exception as e:
        st.error(f"Error llamando al backend: {e}")
        st.stop()

    if res.get("status")=="APPROVAL_REQUIRED":
        st.session_state.payload = res["payload"]
        st.session_state.approval = res.get("approval")
        st.session_state.state = "APPROVAL"
        st.session_state.chat_history.append(
            {
                "role": "assistant",
                "content": "Se requiere aprobación humana para continuar. Revisa impacto y registro objetivo, luego responde Sí o No.",
            }
        )
    elif res.get("status")=="OK":
        st.session_state.state = "CHAT"
        st.session_state.chat_history.append(
            {"role": "assistant", "content": res.get("message", "")}
        )
    else:
        st.session_state.chat_history.append(
            {"role": "assistant", "content": f"Respuesta inesperada: {res}"}
        )

    st.rerun()
