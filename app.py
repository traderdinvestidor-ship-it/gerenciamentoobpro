import streamlit as st
import pandas as pd
import json
import os
import plotly.graph_objects as go
from strategies.soros_gale_session import SorosGaleSession

# --- CONFIGURAÇÃO DA PÁGINA ---
# Deve ser OBRIGATORIAMENTE o primeiro comando Streamlit
st.set_page_config(page_title="Gerenciamento OB Poseidon Pro", page_icon="💎", layout="wide")

# --- SISTEMA DE LOGIN E PAGAMENTO (MERCADO PAGO) ---
from datetime import datetime, timedelta
import os
import json
import base64
from utils.payment import create_pix_payment, check_payment_status

USERS_DB_FILE = "users_db.json"

def load_users_db():
    if not os.path.exists(USERS_DB_FILE):
        return {}
    try:
        with open(USERS_DB_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_users_db(db):
    try:
        with open(USERS_DB_FILE, "w") as f:
            json.dump(db, f, indent=4)
    except Exception as e:
        st.error(f"Erro ao salvar banco de usuários: {e}")

def check_access():
    """
    Verifica se o usuário está logado e se o status é pago.
    """
    if "user_email" not in st.session_state:
        return False

    email = st.session_state.user_email
    db = load_users_db()
    
    if email not in db:
        return False
        
    user_data = db[email]
    
    # Acesso libertado APENAS se estiver 'paid'
    if user_data.get("status") == "paid":
        return True
    
    # Qualquer outro status (trial, pending, expired) cai no Paywall
    return "blocked"

# --- INTERFACE DE LOGIN / ADMIN ---
if "user_email" not in st.session_state and "admin_logged" not in st.session_state:
    st.markdown("""
    <style>
    .login-container { margin: 100px auto; padding: 40px; text-align: center; }
    </style>
    """, unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        st.markdown("<h1 style='text-align: center; color: #38bdf8;'>💎 POSEIDON PRO</h1>", unsafe_allow_html=True)
        
        tab_user, tab_admin = st.tabs(["👤 Sou Cliente", "🔒 Sou Administrador"])
        
        with tab_user:
            st.info("👋 Digite seu e-mail para acessar.")
            email_input = st.text_input("E-mail", placeholder="seu@email.com").strip().lower()
            
            if st.button("🚀 ENTRAR COMO CLIENTE", type="primary", width="stretch"):
                if email_input and "@" in email_input:
                    db = load_users_db()
                    today_str = datetime.now().strftime("%Y-%m-%d")
                    
                    if email_input not in db:
                        db[email_input] = {
                            "start_date": today_str,
                            "status": "pending",
                            "plan": "premium"
                        }
                        save_users_db(db)
                    
                    st.session_state.user_email = email_input
                    st.rerun()
                else:
                    st.error("E-mail inválido.")
        
        with tab_admin:
            st.warning("Área Restrita para Gestão.")
            admin_user = st.text_input("Usuário Admin")
            admin_pass = st.text_input("Senha", type="password")
            
            if st.button("🔑 ACESSAR PAINEL", width="stretch"):
                try:
                    sec_user = st.secrets["admin"]["user"]
                    sec_pass = st.secrets["admin"]["password"]
                    
                    if admin_user == sec_user and admin_pass == sec_pass:
                        st.session_state.admin_logged = True
                        st.success("Login Admin realizado!")
                        st.rerun()
                    else:
                        st.error("Credenciais Inválidas")
                except:
                    st.error("Erro na configuração de segredos.")

    st.stop()

# --- PAINEL DO ADMINISTRADOR ---
if st.session_state.get("admin_logged"):
    # st.set_option('deprecation.showPyplotGlobalUse', False) # REMOVED: Deprecated
    st.title("🛡️ Painel Administrativo Poseidon")
    
    if st.button("Sair do Admin", type="secondary"):
        del st.session_state["admin_logged"]
        st.rerun()
        
    st.divider()
    
    # Carregar DB
    db = load_users_db()
    
    # Métricas
    total_users = len(db)
    paid_users = len([u for u in db.values() if u.get("status") == "paid"])
    pending_users = total_users - paid_users
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Total de Usuários", total_users)
    m2.metric("Usuários Ativos (Pagos)", paid_users)
    m3.metric("Pendentes", pending_users)
    
    st.markdown("### 📋 Gestão de Usuários")
    
    # Converter para DataFrame para facilitar visualização
    if db:
        data_list = []
        for email, info in db.items():
            data_list.append({
                "Email": email,
                "Status": info.get("status", "pending"),
                "Desde": info.get("start_date", "-"),
                "Plano": info.get("plan", "premium")
            })
        
        df_users = pd.DataFrame(data_list)
        
        # Edição
        edited_df = st.data_editor(
            df_users, 
            column_config={
                "Status": st.column_config.SelectboxColumn(
                    "Status",
                    help="Selecione o status do usuário",
                    width="medium",
                    options=[
                        "pending",
                        "paid",
                        "blocked"
                    ],
                    required=True,
                )
            },
            hide_index=True,
            width="stretch",
            key="user_editor"
        )
        
        # Botão Salvar
        if st.button("💾 SALVAR ALTERAÇÕES NO BANCO DE DADOS", type="primary"):
            # Atualizar DB com os dados editados
            updated_db = db.copy()
            for index, row in edited_df.iterrows():
                email = row["Email"]
                new_status = row["Status"]
                
                if email in updated_db:
                    updated_db[email]["status"] = new_status
            
            save_users_db(updated_db)
            st.success("Banco de dados atualizado com sucesso!")
            st.rerun()
            
    else:
        st.info("Nenhum usuário cadastrado ainda.")
        
    st.stop() # Fim do script para Admin


# --- VERIFICAÇÃO DE ACESSO ---
access_status = check_access()

if access_status == "blocked":
    st.markdown("<h1 style='text-align: center; color: #ef4444;'>🔒 Acesso Bloqueado</h1>", unsafe_allow_html=True)
    
    c1, c2 = st.columns(2)
    with c1:
        st.metric("Acesso Vitalício", "R$ 19,99")
    with c2:
        st.info("Liberação Imediata (Automática)")
    
    st.divider()
    
    # Lógica de Pagamento
    email = st.session_state.user_email
    
    if "payment_info" not in st.session_state:
        st.warning("Clique abaixo para gerar seu código PIX.")
        if st.button("💠 GERAR PIX DE R$ 19,99", type="primary"):
            with st.spinner("Gerando PIX..."):
                pay_data = create_pix_payment(email, 19.99)
                if pay_data:
                    st.session_state.payment_info = pay_data
                    st.rerun()
                else:
                    st.error("Erro ao gerar PIX. Tente novamente.")
    else:
        # Exibir PIX Gerado
        pay_data = st.session_state.payment_info
        
        # decodificar imagem base64
        qr_bytes = base64.b64decode(pay_data["qr_code_base64"])
        
        col_pix1, col_pix2 = st.columns(2)
        with col_pix1:
            st.image(qr_bytes, caption="Escaneie com seu App de Banco", width=250)
        with col_pix2:
            st.markdown("### Copia e Cola")
            st.code(pay_data["qr_code"], language="text")
            st.caption("👆 Copie o código acima e pague no seu banco.")
            
        st.divider()
        
        # Botão de Verificar
        if st.button("🔄 JÁ PAGUEI (VERIFICAR AGORA)", type="primary", width="stretch"):
            status = check_payment_status(pay_data["id"])
            if status == "approved":
                st.balloons()
                st.success("✅ Pagamento Aprovado! Liberando acesso...")
                
                # Atualizar DB
                db = load_users_db()
                if email in db:
                    db[email]["status"] = "paid"
                    save_users_db(db)
                
                # Limpar estado de pagamento
                del st.session_state["payment_info"]
                st.rerun()
            elif status == "pending":
                st.warning("⏳ Pagamento ainda pendente. Aguarde alguns segundos e tente novamente.")
            else:
                st.error(f"Status do pagamento: {status}")
                
        if st.button("Cancelar / Gerar Novo"):
            del st.session_state["payment_info"]
            st.rerun()

    
    if st.button("Sair / Trocar E-mail", type="secondary"):
        del st.session_state["user_email"]
        if "payment_info" in st.session_state:
            del st.session_state["payment_info"]
        st.rerun()
        
    st.stop()

# ... (CSS Block remains same) ...

# Arquivo de Salvamento
SESSION_FILE = "session_state.json"
CAREER_FILE = "career_state.json"

# --- UTILITÁRIOS DE PERSISTÊNCIA ---
def save_session(session):
    with open(SESSION_FILE, "w") as f:
        json.dump(session.to_dict(), f)

def load_session():
    if os.path.exists(SESSION_FILE):
        try:
            with open(SESSION_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return SorosGaleSession.from_dict(data)
        except Exception as e:
            st.warning(f"Erro ao carregar sessão anterior: {e}")
            return None
    return None

def clear_session():
    if os.path.exists(SESSION_FILE):
        os.remove(SESSION_FILE)
    st.session_state.sg_session = None

def save_career_state(state):
    with open(CAREER_FILE, "w") as f:
        json.dump(state, f)

def load_career_state():
    if os.path.exists(CAREER_FILE):
        with open(CAREER_FILE, "r") as f:
            return json.load(f)
    return None

def reset_career():
    if os.path.exists(CAREER_FILE):
        os.remove(CAREER_FILE)

# --- INICIALIZAÇÃO DE ESTADO ---
if 'sg_session' not in st.session_state or st.session_state.sg_session is None:
    loaded = load_session()
    if loaded:
        st.session_state.sg_session = loaded
        # Não precisa do rerun aqui se for a primeira carga do script
        # mas mantemos por segurança caso o estado mude no meio

# --- ESTILO PREMIUM (CSS) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&family=Orbitron:wght@400;700&display=swap');

    :root {
        --bg-deep: #0a0f1e;
        --card-bg: rgba(15, 23, 42, 0.65);
        --primary-glow: hsla(199, 89%, 48%, 0.5);
        --cyan-vibrant: hsl(199, 89%, 48%);
        --emerald-vibrant: hsl(158, 64%, 52%);
        --rose-vibrant: hsl(346, 84%, 61%);
        --violet-vibrant: hsl(262, 83%, 58%);
        --glass-border: rgba(255, 255, 255, 0.08);
        --text-main: #f8fafc;
        --text-dim: #94a3b8;
    }

    /* Fundo Escuro Futurista */
    .stApp {
        background: radial-gradient(circle at top left, #1e293b 0%, #0f172a 40%, #020617 100%);
        color: var(--text-main);
        font-family: 'Inter', sans-serif;
    }
    
    /* Configurações de Layout */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 2rem !important;
        max-width: 1400px;
    }

    /* Ocultar elementos padrão do Streamlit */
    #MainMenu, footer, header { visibility: hidden; }

    /* Estilização Geral de Títulos */
    h1, h2, h3 {
        font-family: 'Orbitron', sans-serif !important;
        text-transform: uppercase;
        letter-spacing: 2px !important;
        background: linear-gradient(90deg, #fff 0%, var(--cyan-vibrant) 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-shadow: 2px 2px 10px rgba(0,0,0,0.5);
    }

    /* Cards Glassmorphism 2.0 */
    .css-1r6slb0, .css-12w0qpk, .stMetric, div[data-testid="stExpander"], div[data-testid="stForm"] {
        background: var(--card-bg) !important;
        backdrop-filter: blur(20px) saturate(180%) !important;
        border: 1px solid var(--glass-border) !important;
        border-radius: 20px !important;
        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.4), inset 0 0 0 1px rgba(255,255,255,0.05);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        margin-bottom: 1.5rem;
    }
    
    .stMetric:hover {
        border-color: var(--primary-glow) !important;
        box-shadow: 0 10px 50px rgba(56, 189, 248, 0.15);
        transform: translateY(-2px);
    }

    /* Estilização de Métricas */
    div[data-testid="stMetric"] {
        padding: 15px !important;
        text-align: center;
    }
    div[data-testid="stMetric"] label {
        color: var(--text-dim) !important;
        font-size: 0.75rem !important;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        font-weight: 600;
    }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        color: white !important;
        font-family: 'Orbitron', sans-serif;
        font-size: 2.2rem !important;
        font-weight: 700;
        text-shadow: 0 0 20px rgba(56, 189, 248, 0.3);
    }

    /* Botões Premium */
    .stButton button {
        border-radius: 14px !important;
        padding: 0.8rem 2rem !important;
        background: rgba(255, 255, 255, 0.03) !important;
        border: 1px solid var(--glass-border) !important;
        color: white !important;
        font-weight: 700 !important;
        letter-spacing: 1px;
        transition: all 0.3s ease !important;
    }
    .stButton button:hover {
        background: rgba(255, 255, 255, 0.08) !important;
        border-color: var(--text-main) !important;
        box-shadow: 0 0 25px rgba(255,255,255,0.1);
        transform: scale(1.02);
    }

    /* Botões WIN e LOSS Personalizados */
    div.stButton > button:first-child[aria-label="✅ WIN"] {
        background: linear-gradient(135deg, hsla(158, 64%, 52%, 0.1) 0%, hsla(158, 64%, 52%, 0.2) 100%) !important;
        border: 1px solid var(--emerald-vibrant) !important;
        box-shadow: 0 0 20px hsla(158, 64%, 52%, 0.2);
    }
    div.stButton > button:first-child[aria-label="❌ LOSS"] {
        background: linear-gradient(135deg, hsla(346, 84%, 61%, 0.1) 0%, hsla(346, 84%, 61%, 0.2) 100%) !important;
        border: 1px solid var(--rose-vibrant) !important;
        box-shadow: 0 0 20px hsla(346, 84%, 61%, 0.2);
    }

    /* Inputs Modernos */
    .stNumberInput input, .stSelectbox div[data-baseweb="select"] > div {
        background-color: rgba(2, 6, 23, 0.4) !important;
        border: 1px solid var(--glass-border) !important;
        border-radius: 12px !important;
        color: white !important;
    }
    
    /* Indicador de Passos 4x */
    .step-container {
        display: flex;
        gap: 12px;
        margin-bottom: 25px;
        justify-content: center;
    }
    .step-box {
        flex: 1;
        padding: 12px;
        text-align: center;
        border-radius: 12px;
        font-family: 'Orbitron', sans-serif;
        font-size: 0.7rem;
        font-weight: 700;
        color: var(--text-dim);
        opacity: 0.3;
        transition: all 0.4s ease;
        border: 1px solid var(--glass-border);
        background: rgba(255,255,255,0.02);
    }
    .step-active {
        opacity: 1 !important;
        transform: scale(1.08);
        box-shadow: 0 0 25px var(--primary-glow);
        border: 2px solid white !important;
        color: white !important;
    }
    .step-red { background: var(--rose-vibrant) !important; }
    .step-blue { background: var(--cyan-vibrant) !important; }
    .step-green { background: var(--emerald-vibrant) !important; }

    /* Alerta Subsolo Futurista */
    .subsolo-alert {
        background: linear-gradient(90deg, #f59e0b 0%, #ea580c 100%);
        padding: 20px;
        border-radius: 15px;
        color: white;
        font-family: 'Orbitron', sans-serif;
        font-weight: 800;
        text-align: center;
        box-shadow: 0 0 30px rgba(234, 88, 12, 0.4);
        margin-bottom: 25px;
        animation: glow 2s ease-in-out infinite;
    }
    @keyframes glow {
        0% { filter: brightness(1) drop-shadow(0 0 5px orange); }
        50% { filter: brightness(1.2) drop-shadow(0 0 15px orange); }
        100% { filter: brightness(1) drop-shadow(0 0 5px orange); }
    }

    /* Tabela Premium */
    .stDataFrame {
        border: 1px solid var(--glass-border) !important;
        border-radius: 15px !important;
        overflow: hidden !important;
    }
</style>
""", unsafe_allow_html=True)



# Carregar Modo Carreira
career = load_career_state()

# --- ESTRUTURA DE ABAS ---
tab_ops, tab_plan = st.tabs(["🎮 Operações", "📈 Planejamento (Juros Compostos)"])

with tab_plan:
    st.markdown("## 🎯 Plano de Carreira - Juros Compostos")
    st.caption("Projete o crescimento da sua banca a longo prazo.")
    
    col_p1, col_p2, col_p3 = st.columns(3)
    with col_p1:
        cap_inicial = st.number_input("Investimento Inicial (R$)", value=1000.0, step=100.0)
    with col_p2:
        perc_diario = st.number_input("Retorno Diário (%)", value=3.0, step=0.5)
    with col_p3:
        dias_plan = st.number_input("Período (Dias)", value=30, min_value=1, max_value=365)
    
    # Gerar Tabela
    rows = []
    cap_prev = cap_inicial
    for d in range(1, dias_plan + 1):
        lucro_d = cap_prev * (perc_diario / 100)
        acumulado = cap_prev + lucro_d
        rows.append({
            "Dia": d,
            "Investimento (R$)": f"{cap_prev:.2f}",
            "Retorno Dia %": f"{perc_diario:.2f}%",
            "Lucro do Dia (R$)": f"{lucro_d:.2f}",
            "Acumulado (R$)": f"{acumulado:.2f}"
        })
        cap_prev = acumulado
    
    df_plan = pd.DataFrame(rows)
    
    # Resumo visual
    c_res1, c_res2 = st.columns(2)
    with c_res1:
        st.success(f"**Resultado após {dias_plan} dias:** R$ {cap_prev:.2f}")
    with c_res2:
        growth = ((cap_prev - cap_inicial) / cap_inicial) * 100
        st.info(f"**Crescimento Total:** {growth:.1f}%")

    st.dataframe(df_plan, width="stretch", hide_index=True)
    st.caption("💡 Dica: Use o Lucro do Dia como seu Stop Win na aba de Operações.")

    if st.button("🚀 ATIVAR MODO CARREIRA COM ESTE PLANO", type="primary"):
        new_career = {
            "cap_inicial": cap_inicial,
            "perc_diario": perc_diario,
            "dias_plan": dias_plan,
            "current_day": 1,
            "is_active": True
        }
        save_career_state(new_career)
        st.success("✅ Modo Carreira Ativado! Vá para a aba Operações.")
        st.rerun()

with tab_ops:
    # Lógica Principal
    if not st.session_state.get('sg_session'):
        # --- MODO CARREIRA BANNER ---
        banca_val = 100.0
        meta_val = 0.0
        
        if career and career.get("is_active"):
            d = career["current_day"]
            cap_i = career["cap_inicial"]
            perc = career["perc_diario"]
            
            # Cálculo do Dia Atual (Compostos)
            cap_atual = cap_i * ((1 + (perc/100)) ** (d-1))
            lucro_dia = cap_atual * (perc/100)
            
            banca_val = float(cap_atual)
            meta_val = float(lucro_dia)
            
            st.markdown(f"""
            <div style="background: rgba(16, 185, 129, 0.1); border: 1px solid #10b981; padding: 15px; border-radius: 12px; margin-bottom: 20px;">
                <h4 style="margin:0; color: #10b981;">🚀 MODO CARREIRA ATIVO - DIA {d}</h4>
                <p style="margin:5px 0 0 0; font-size: 0.9rem; color: #94a3b8;">
                    Objetivo: <b>R$ {meta_val:.2f}</b> de lucro sobre banca de <b>R$ {banca_val:.2f}</b>
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("🚩 Desativar Modo Carreira", type="secondary"):
                reset_career()
                st.rerun()

        st.markdown("<h1 style='text-align: center; color: #38bdf8;'>💎 Gerenciamento OB Poseidon Pro</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #94a3b8;'>O sistema definitivo de SorosGale.</p>", unsafe_allow_html=True)
        st.write("---")
        
        c1, c2 = st.columns(2)
        with c1:
            banca = st.number_input("Banca Inicial (R$)", value=banca_val, step=10.0)
            tipo_entrada = st.radio("Tipo de Entrada (George Soros)", ["Fixo (R$)", "Composto (%)"], horizontal=True)
            if tipo_entrada == "Fixo (R$)":
                entrada = st.number_input("Entrada Base (R$)", value=5.0, step=1.0)
                is_perc = False
            else:
                entrada = st.number_input("Entrada Base (%)", value=1.0, step=0.1)
                is_perc = True
        with c2:
            payout = st.number_input("Payout (%)", value=87, min_value=50, max_value=99)
            nivel = st.number_input("Nível Soros", value=2, min_value=1)
        
        st.write("")
        c_extra1, c_extra2, c_extra3 = st.columns(3)
        with c_extra1:
                fator = st.number_input("Fator Recup. Final", value=1.0, step=0.1, help="Gale Final: 1.0 = Recupera 0x0. 1.2 = Lucro.")
        with c_extra2:
                base_strats = ["SorosGale (Vídeo)", "4x (Senhor Trader)", "SACAC (Escalonável)"]
                estrategia_base = st.selectbox("Estratégia", base_strats, index=0)
                
                final_strat = estrategia_base
                if estrategia_base == "SACAC (Escalonável)":
                    escala = st.selectbox("Escala SACAC", ["Dezena (50)", "Centena (100)", "Milhar (1000)", "Personalizado"])
                    final_strat = f"SACAC - {escala}"

        with c_extra3:
                meta_lucro = st.number_input("Meta de Lucro (R$)", value=meta_val, step=5.0)

        st.write("")
        if st.button("▶️ INICIAR SESSÃO PREMIUM", width="stretch", type="primary"):
            reiniciar = True 
            strat_map = {
                "SorosGale (Vídeo)": "SorosGale (Recuperação 2x)",
                "4x (Senhor Trader)": "4x (Senhor Trader)",
                "SACAC - Dezena (50)": "SACAC - Dezena",
                "SACAC - Centena (100)": "SACAC - Centena",
                "SACAC - Milhar (1000)": "SACAC - Milhar",
                "SACAC - Personalizado": "SACAC - Custom"
            }
            strat_internal = strat_map.get(final_strat, "SorosGale (Recuperação 2x)")
            session = SorosGaleSession(banca, payout, entrada, nivel, fator, 100.0, reiniciar, strat_internal, meta_lucro=meta_lucro)
            st.session_state.sg_session = session
            save_session(session)
            st.rerun()

    else:
        # --- DASHBOARD PREMIUM ---
        session = st.session_state.sg_session
        status = session.get_status()
        
        # 1. Top Bar (Header & Reset)
        col_head1, col_head2 = st.columns([3, 1])
        with col_head1:
            # Melhoria visual da Fase
            fase_label = status['Fase']
            if session.estrategia_gale == "4x (Senhor Trader)":
                if session.subsolo_step > 0:
                    fase_label = f"🔥 SUBSOLO G{session.subsolo_step}"
                else:
                    fase_label = f"💠 PASSO {session.step_4x}/4"
            
            st.markdown(f"### 🛡️ Operando: {fase_label}")
        with col_head2:
            if st.button("Sair / Reiniciar", type="secondary"):
                clear_session() # Limpa o save
                st.rerun()
                
        # 2. Big Metrics Row
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Banca Atual", f"R$ {(session.banca + session.saldo_sessao):.2f}")
        m2.metric("Lucro Sessão", f"R$ {session.saldo_sessao:.2f}")
        m3.metric("Próxima Entrada", f"R$ {status['Entrada Sugerida']:.2f}")
        m4.metric("Status", "🟢 Ativo" if not session.sessao_encerrada else "🛑 Parado")
        
        # 2.2 Row Extra para SACAC
        if session.sacac_mode:
            st.write("")
            s_col1, s_col2, s_col3 = st.columns(3)
            with s_col1:
                st.markdown(f"📉 **Piso de Proteção:** R$ {session.sacac_piso:.2f}")
            with s_col2:
                st.markdown(f"🏁 **Base Secured:** R$ {session.sacac_base:.2f}")
            with s_col3:
                st.markdown(f"🎯 **Próximo Alvo:** R$ {session.sacac_alvo:.2f}")
        
        st.divider()

        # 3. Main Action Area & Chart
        c_left, c_right = st.columns([1, 2])
        
        with c_left:
            # Se 4x, mostra indicadores de passos
            if session.estrategia_gale == "4x (Senhor Trader)":
                if session.subsolo_step > 0:
                    st.markdown(f"""
                    <div class="subsolo-alert">
                        ⚠️ MODO SUBSOLO ATIVO: G{session.subsolo_step}/2
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    s1 = "step-active" if session.step_4x == 1 else ""
                    s2 = "step-active" if session.step_4x == 2 else ""
                    s3 = "step-active" if session.step_4x == 3 else ""
                    s4 = "step-active" if session.step_4x == 4 else ""
                    
                    st.markdown(f"""
                    <div class="step-container">
                        <div class="step-box step-red {s1}">1º ORDEM</div>
                        <div class="step-box step-red {s2}">2º SOROS</div>
                        <div class="step-box step-blue {s3}">INVERSO 1</div>
                        <div class="step-box step-green {s4}">INVERSO 2</div>
                    </div>
                    """, unsafe_allow_html=True)

            st.markdown("#### 🎮 Painel de Controle")
            st.info(f"📝 **Instrução:** {status['Mensagem']}")
            
            st.write("")
            
            # Botões de Ação / Encerramento
            if session.sessao_encerrada:
                # Verifica se foi Win ou Loss
                if session.saldo_sessao > 0:
                    st.success("🏆 **PARABÉNS! META BATIDA!**")
                    st.balloons()
                else:
                    st.error("🚫 **STOP LOSS ATINGIDO!** (2 Losses Seguidos)")
                
                if st.button("🔄 Iniciar Nova Sessão", type="primary", width="stretch"):
                     clear_session()
                     st.rerun()
                
                # Botão Avançar Modo Carreira
                if career and career.get("is_active") and session.saldo_sessao >= session.meta_lucro:
                    st.write("---")
                    if st.button(f"✅ CONCLUIR DIA {career['current_day']} E AVANÇAR", type="primary", width="stretch"):
                        career["current_day"] += 1
                        save_career_state(career)
                        clear_session()
                        st.rerun()
            else:
                # Botões Normais de Operação
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("✅ WIN", type="primary", width="stretch"):
                        session.registrar_win()
                        save_session(session) # Auto-save
                        st.rerun()
                        
                with c2:
                    if st.button("❌ LOSS", type="secondary", width="stretch"):
                        session.registrar_loss()
                        save_session(session) # Auto-save
                        st.rerun()
                    
        with c_right:
            st.markdown("#### 📈 Performance (Equity)")
            # Gerar Gráfico Plotly
            if len(session.historico) > 0:
                df = pd.DataFrame(session.historico)
                # Criar saldo acumulado trade a trade
                df['Saldo_Acumulado'] = df['Saldo Sessão']
                
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    y=df['Saldo_Acumulado'],
                    mode='lines+markers',
                    name='Lucro',
                    line=dict(color='#10b981', width=3),
                    fill='tozeroy',
                    fillcolor='rgba(16, 185, 129, 0.1)'
                ))
                fig.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    margin=dict(l=10, r=10, t=10, b=10),
                    height=300,
                    xaxis=dict(showgrid=False, title='Trades'),
                    yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)'),
                    font=dict(color='#e2e8f0')
                )
                st.plotly_chart(fig)
            else:
                st.caption("O gráfico aparecerá após o primeiro trade.")

        # Histórico
        if session.historico:
            with st.expander("📜 Histórico Detalhado", expanded=True):
                df = pd.DataFrame(session.historico)
                # Fix para ArrowError (Tipos mistos na coluna)
                df['Nível Soros'] = df['Nível Soros'].astype(str)
                
                st.dataframe(
                    df[['Nível Soros', 'Gale', 'Entrada', 'Resultado', 'Saldo Sessão']]
                    .iloc[::-1]
                    .style.map(lambda v: 'color: #10B981; font-weight: bold;' if v == 'WIN' else ('color: #EF4444; font-weight: bold;' if v == 'LOSS' else ''), subset=['Resultado']),
                    width="stretch"
                )
        else:
            st.info("Nenhum trade registrado ainda.")
