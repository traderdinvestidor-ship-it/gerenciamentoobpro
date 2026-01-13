import mercadopago
import streamlit as st

def get_mp_sdk():
    try:
        token = st.secrets["mercadopago"]["access_token"]
        return mercadopago.SDK(token)
    except Exception as e:
        print(f"Erro ao carregar credenciais MP: {e}")
        return None

def create_pix_payment(email, amount, description="Acesso Vitalício Poseidon Pro"):
    sdk = get_mp_sdk()
    if not sdk:
        return None
    
    payment_data = {
        "transaction_amount": float(amount),
        "description": description,
        "payment_method_id": "pix",
        "payer": {
            "email": email,
            "first_name": email.split("@")[0]
        }
    }
    
    try:
        payment_response = sdk.payment().create(payment_data)
        response = payment_response["response"]
        
        return {
            "id": response["id"],
            "status": response["status"],
            "qr_code": response["point_of_interaction"]["transaction_data"]["qr_code"],
            "qr_code_base64": response["point_of_interaction"]["transaction_data"]["qr_code_base64"],
            "ticket_url": response["point_of_interaction"]["transaction_data"]["ticket_url"]
        }
    except Exception as e:
        print(f"Erro ao criar pagamento: {e}")
        return None

def check_payment_status(payment_id):
    sdk = get_mp_sdk()
    if not sdk:
        return None

    try:
        payment_response = sdk.payment().get(payment_id)
        response = payment_response["response"]
        return response["status"] # approved, pending, rejected
    except Exception as e:
        print(f"Erro ao checar status: {e}")
        return None
