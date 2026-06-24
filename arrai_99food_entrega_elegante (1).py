import streamlit as st
import pandas as pd
from datetime import datetime
import unicodedata
import json
import os
from supabase import create_client, Client

# Configuração de página no padrão visual da 99Food
st.set_page_config(
    page_title="Entrega Elegante 99Food", 
    page_icon="🌽", 
    layout="centered"
)

# --- INICIALIZAÇÃO DE SESSÃO PRIVADA PARA PALPITES ---
if "meus_palpites" not in st.session_state:
    st.session_state.meus_palpites = {}

# --- CONFIGURAÇÃO DO SUPABASE COM FALLBACK SEGURO ---
FICHEIRO_MENSAGENS = "mensagens.json"

def obter_cliente_supabase():
    """Inicializa o cliente do Supabase utilizando as chaves dos Secrets se disponíveis."""
    try:
        if "supabase" in st.secrets:
            url = st.secrets["supabase"]["url"].strip()
            key = st.secrets["supabase"]["key"].strip()
            
            # Limpeza automática para evitar o erro PGRST125 de caminho inválido
            if url.endswith("/rest/v1"):
                url = url[:-8]
            elif url.endswith("/rest/v1/"):
                url = url[:-9]
            url = url.rstrip("/")
            
            return create_client(url, key)
    except Exception:
        pass
    return None

def carregar_mensagens_locais():
    """Carrega as mensagens locais em formato JSON caso o Supabase não esteja ativo."""
    if os.path.exists(FICHEIRO_MENSAGENS):
        try:
            with open(FICHEIRO_MENSAGENS, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return [
        {
            "id": 1,
            "remetente_dchat": "Carlos_99",
            "remetente_nome": "",
            "remetente_sobrenome": "",
            "remetente_email": "",
            "destinatario": "Mariana_99",
            "mensagem": "Você não é um cupom de 10%OFF do 99Food, mas quero te dizer/lembrar que... você salvou o meu dia quando me ajudou com aquela planilha de Key Accounts!",
            "data": "15/06/2026 09:30",
            "quem_palpitou": "",
            "palpite": "",
            "palpite_feito": False,
            "acertou": False
        }
    ]

def guardar_mensagens_locais(mensagens):
    """Escreve as mensagens locais no disco do servidor como redundância."""
    try:
        with open(FICHEIRO_MENSAGENS, "w", encoding="utf-8") as f:
            json.dump(mensagens, f, ensure_ascii=False, indent=4)
    except Exception:
        pass

# --- API DE DADOS CENTRALIZADA ---
@st.cache_resource
def iniciar_banco_compartilhado():
    """Cache em memória compartilhada no servidor para sincronização ultra rápida."""
    return {"mensagens": []}

banco_dados = iniciar_banco_compartilhado()

def carregar_mensagens_globais():
    """Lê todas as mensagens, priorizando a tabela do Supabase em tempo real."""
    client = obter_cliente_supabase()
    if client is not None:
        try:
            # Busca todas as linhas ordenadas por ID de forma ascendente
            response = client.table("mensagens").select("*").order("id", desc=False).execute()
            mensagens = response.data
            banco_dados["mensagens"] = mensagens
            return mensagens
        except Exception as e:
            st.error(f"Erro ao conectar com o Supabase: {e}")
            
    # Caso as credenciais não estejam salvas, executa localmente
    banco_dados["mensagens"] = carregar_mensagens_locais()
    return banco_dados["mensagens"]

def salvar_nova_mensagem_global(nova_msg):
    """Salva a nova mensagem de forma persistente e instantânea."""
    client = obter_cliente_supabase()
    if client is not None:
        try:
            # Envia os dados para a tabela do Supabase
            dados_insercao = {
                "remetente_dchat": nova_msg["remetente_dchat"],
                "remetente_nome": nova_msg["remetente_nome"],
                "remetente_sobrenome": nova_msg["remetente_sobrenome"],
                "remetente_email": nova_msg["remetente_email"],
                "destinatario": nova_msg["destinatario"],
                "mensagem": nova_msg["mensagem"],
                "data": nova_msg["data"],
                "quem_palpitou": nova_msg["quem_palpitou"],
                "palpite": nova_msg["palpite"],
                "palpite_feito": nova_msg["palpite_feito"],
                "acertou": nova_msg["acertou"]
            }
            client.table("mensagens").insert(dados_insercao).execute()
            return True
        except Exception as e:
            st.error(f"Erro ao salvar mensagem no Supabase: {e}")
            return False
            
    # Fallback local em JSON
    mensagens = carregar_mensagens_locais()
    nova_msg["id"] = len(mensagens) + 1
    mensagens.append(nova_msg)
    guardar_mensagens_locais(mensagens)
    return True

def salvar_palpite_global(msg_id, quem_palpitou, palpite, acertou):
    """Atualiza de forma irreversível e persistente o palpite feito no banco de dados."""
    client = obter_cliente_supabase()
    if client is not None:
        try:
            client.table("mensagens").update({
                "quem_palpitou": quem_palpitou,
                "palpite": palpite,
                "palpite_feito": True,
                "acertou": acertou
            }).eq("id", msg_id).execute()
            return True
        except Exception as e:
            st.error(f"Erro ao registrar o palpite no Supabase: {e}")
            return False
            
    # Fallback local em JSON
    mensagens = carregar_mensagens_locais()
    for m in mensagens:
        if m["id"] == msg_id:
            m["quem_palpitou"] = quem_palpitou
            m["palpite"] = palpite
            m["palpite_feito"] = True
            m["acertou"] = acertou
    guardar_mensagens_locais(mensagens)
    return True

# --- CARREGA AS MENSAGENS EM SEGUNDO PLANO ---
mensagens_mural = carregar_mensagens_globais()

# --- FUNÇÃO AUXILIAR PARA NORMALIZAR NOMES ---
def normalizar_nome(texto):
    if not texto:
        return ""
    texto = str(texto).lower().strip()
    texto = ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
    return texto

# --- ESTILIZAÇÃO E DIRETRIZES DO BRAND BOOK 99FOOD ---
# Amarelo Prioritário (#FFDD00), Laranja de Apoio (#FF8F00), Cinza Escuro de Contraste (#212121)
st.markdown("""
    <style>
    /* Fundo Amarelo Oficial 99 (Sem gradientes para respeitar ID visual da marca) */
    .stApp {
        background-color: #FFDD00 !important;
        font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    }
    
    /* Leitura de textos em Cinza Escuro */
    .stApp label, .stApp p, .stApp span, .stApp li {
        color: #212121 !important;
    }
    
    /* Inputs brancos limpos de alto contraste */
    input, textarea {
        background-color: #FFFFFF !important;
        color: #212121 !important;
        border: 2px solid #212121 !important;
        border-radius: 8px !important;
    }
    input::placeholder, textarea::placeholder {
        color: #777777 !important;
    }
    
    /* Ocultar legenda/ajuda padrão do Streamlit de 'Press Enter to apply' */
    div[data-testid="InputInstructions"] {
        display: none !important;
    }
    
    /* --- CABEÇALHO PRETO LIMPO --- */
    .header-box {
        background-color: #212121 !important;
        border: none !important;
        border-radius: 16px;
        padding: 35px 20px;
        text-align: center;
        margin-bottom: 30px;
        position: relative;
        overflow: hidden;
    }
    
    /* Scooter caipira correndo da direita para a esquerda de forma física natural */
    @keyframes drive-scooter {
        0% { right: -100px; }
        100% { right: 110%; }
    }
    .scooter-decor {
        position: absolute;
        bottom: 5px;
        font-size: 1.4rem;
        animation: drive-scooter 16s linear infinite;
    }
    
    .header-title {
        color: #FFDD00 !important;
        font-weight: 900 !important;
        font-size: 2.4rem !important;
        margin-top: 15px !important;
        margin-bottom: 10px !important;
        letter-spacing: -0.5px;
    }
    
    .header-divisor {
        font-size: 1.4rem;
        letter-spacing: 6px;
        color: #FFFFFF !important;
        margin-top: 5px;
    }
    
    /* --- SEPARADORES (ABAS) --- */
    .stTabs [data-baseweb="tab-list"] {
        display: flex !important;
        justify-content: center !important;
        gap: 12px !important;
        background-color: #212121 !important;
        padding: 8px !important;
        border-radius: 12px !important;
    }
    .stTabs [data-baseweb="tab"] {
        height: 48px !important;
        padding-left: 20px !important;
        padding-right: 20px !important;
        border-radius: 8px !important;
    }
    .stTabs [data-baseweb="tab"] p {
        font-size: 1rem !important;
        font-weight: bold !important;
        color: #FFFFFF !important;
    }
    .stTabs [aria-selected="true"] {
        background-color: #FFDD00 !important;
    }
    .stTabs [aria-selected="true"] p {
        color: #212121 !important;
    }

    /* --- BOTÕES DE AÇÃO (MÁXIMO 18 CARACTERES NAS CTAS) --- */
    div[data-testid="stFormSubmitButton"] {
        text-align: center !important;
        display: flex;
        justify-content: center;
        margin-top: 15px;
    }
    button[data-testid="stBaseButton-secondaryFormSubmit"], 
    button[data-testid="stBaseButton-secondary"],
    .stButton > button {
        background-color: #212121 !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 12px 50px !important;
        min-width: 240px !important;
        width: auto !important;
        transition: all 0.2s ease !important;
    }
    button[data-testid="stBaseButton-secondaryFormSubmit"] p,
    .stButton > button p {
        color: #FFDD00 !important;
        font-weight: 800 !important;
        font-size: 1.05rem !important;
    }
    button[data-testid="stBaseButton-secondaryFormSubmit"]:hover,
    .stButton > button:hover {
        opacity: 0.95;
        transform: translateY(-1px);
    }
    
    /* Caixa de Instruções */
    .enunciado-container {
        background-color: #FFFFFF !important;
        border: 2px dashed #212121 !important;
        border-radius: 12px;
        padding: 22px;
        margin-bottom: 30px;
    }
    
    /* --- DESIGN DE RECIBO DE ENTREGA 99FOOD (LARANJA E BRANCO FLAT) --- */
    .receipt-card {
        background-color: #FFFFFF !important;
        border-top: 8px solid #FF8F00 !important; /* Laranja Oficial de Apoio */
        border-radius: 12px 12px 0 0;
        padding: 22px;
        margin-top: 20px !important;
        position: relative;
    }
    
    /* Serrilhado Flat de Talão de Compra */
    .receipt-sawtooth {
        height: 10px;
        background: linear-gradient(-45deg, #FFFFFF 5px, transparent 0), linear-gradient(45deg, #FFFFFF 5px, transparent 0);
        background-size: 10px 10px;
        background-position: left top;
        margin-bottom: 25px !important;
    }
    
    .receipt-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 0.8rem;
        color: #777777 !important;
        font-family: monospace;
        border-bottom: 1px dashed #E0E0E0;
        padding-bottom: 6px;
        margin-bottom: 12px;
    }
    .receipt-recipient {
        font-size: 1.25rem;
        font-weight: 800;
        color: #212121 !important;
        margin-bottom: 8px;
    }
    .receipt-message-box {
        background-color: #F1F1F1 !important; /* Cinza Claro de Apoio */
        border-left: 4px solid #FFDD00;
        padding: 12px;
        border-radius: 6px;
        font-style: italic;
        color: #212121 !important;
        font-size: 0.95rem;
        line-height: 1.4;
    }
    
    /* Código de Barras */
    .receipt-barcode {
        display: flex;
        justify-content: center;
        gap: 2px;
        height: 24px;
        margin-top: 15px;
        opacity: 0.7;
    }
    .barcode-line {
        background-color: #212121;
        height: 100%;
    }
    
    /* Retângulo de Resultado de Palpite */
    .resultado-palpite-box {
        background-color: #FFFFFF !important;
        border: 2px solid #212121 !important;
        border-radius: 12px;
        padding: 16px;
        margin-top: 15px !important;
        margin-bottom: 25px !important;
    }
    .resultado-palpite-box p {
        color: #212121 !important;
        margin: 0 !important;
        font-size: 1rem !important;
    }
    
    .centered-title {
        text-align: center !important;
        color: #212121 !important;
        font-weight: 800 !important;
        margin-bottom: 25px !important;
        font-size: 1.3rem !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- CABEÇALHO UNIFICADO DO ARRAIÁ ---
st.markdown("""
<div class="header-box">
    <div class="scooter-decor">🛵💨</div>
    <img src="https://99app.com/_next/image/?url=https%3A%2F%2Fimages.ctfassets.net%2Fx9sul3ikm35w%2F2kYcs2M15uM3cYchuoDRvG%2Ffd6069a06d44476d143559243510a929%2Fimage.png&w=384&q=75" width="95" style="display: block; margin: 0 auto;">
    <div class="header-title">🔥 ARRAIÁ 99Food</div>
    <div class="header-divisor">🎏🍿🌽🔥🌽🍿🎏</div>
</div>
""", unsafe_allow_html=True)

# --- QUADRO DE INSTRUÇÕES DE ACORDO COM O ENUNCIADO DOS ORANGERS ---
st.markdown("""
<div class="enunciado-container">
    <div style="font-weight:bold; font-size:1.2rem; color: #212121; margin-bottom: 12px;">🍿 🎏 Olha a Entrega Elegante! É verdade!</div>
    <p style="margin-bottom: 8px;">O São João chegou na 99Food! Para celebrar, misturamos a tradição do Correio Elegante Junino com o reconhecimento do nosso time em um mural interativo. Veja como participar:</p>
    <ul style="margin-top: 0; padding-left: 20px; color: #212121;">
        <li style="margin-bottom: 6px;"><strong>📌 Fizemos um mural de entregas para todo o time!</strong> Todos os orangers podem acessar e visualizar os recados de carinho e gratidão a qualquer momento.</li>
        <li style="margin-bottom: 6px;">⚠️ <strong>Aviso Importante de Segurança</strong><br>Como o mural é público e visível para todos os colaboradores, lembre-se de manter o bom senso. Não envie mensagens com teor confidencial, informações sensíveis do negócio ou qualquer conteúdo que possa causar constrangimento. O foco aqui é celebrar nossas parcerias!</li>
        <li style="margin-bottom: 6px;"><strong>💌 Enviar um Recadinho</strong><br>Vá até a aba "Enviar Mensagem", insira seus dados (que ficarão totalmente ocultos) e mande aquele agradecimento especial para quem "salvou o seu dia" recentemente na empresa.</li>
        <li style="margin-bottom: 6px;"><strong>🕵️ Adivinhe Quem Enviou</strong><br>Se você recebeu um recado, digite seu nome e tente adivinhar quem é o remetente digitando o nome dele exatamente como aparece no D-Chat. Atenção: você só tem uma única tentativa para tentar descobrir!</li>
    </ul>
</div>
""", unsafe_allow_html=True)

# Configuração das duas abas do aplicativo (Mural 100% aberto!)
aba_enviar, aba_mural = st.tabs(["💌 Enviar Mensagem", "📌 Mural de Entregas"])

# --- ABA 1: ENVIAR MENSAGEM ---
with aba_enviar:
    st.markdown('<div class="centered-title">Prepare seu pedido de agradecimento! 💌</div>', unsafe_allow_html=True)
    
    with st.form(key="form_correio", clear_on_submit=True):
        # Mapeamento do novo padrão simplificado de campos para o D-Chat
        remetente_dchat = st.text_input("Seu nome do D-Chat").strip()
        destinatario = st.text_input("Para quem é a mensagem? (Nome do D-Chat)").strip()
        
        st.markdown("<p style='font-weight: bold; margin-bottom: 2px; color:#212121 !important;'>Complete a frase com uma lembrança:</p>", unsafe_allow_html=True)
        texto_base = "Você não é um cupom do 99Food, mas quero te dizer/lembrar que..."
        
        exemplo_emotivo = "Ex: você me deu a maior força quando aquele projeto deu errado e não me deixou desistir. Obrigado por ser essa liderança/parceira incrível, você salva meu dia sempre!"
        lembranca = st.text_area(texto_base, placeholder=exemplo_emotivo)
        
        # CTA Otimizada para 15 caracteres (Dentro do limite de 18 do Brand Book)
        botao_enviar = st.form_submit_button("Enviar Recado 🚀")
        
        if botao_enviar:
            # Sistema de notificações e validações obrigatórias
            if not remetente_dchat:
                st.error("⚠️ O preenchimento do campo 'Seu nome do D-Chat' é obrigatório!")
            elif not destinatario:
                st.error("⚠️ O preenchimento do campo 'Para quem é a mensagem? (Nome do D-Chat)' é obrigatório!")
            elif not lembranca.strip():
                st.error("⚠️ O preenchimento do campo com o recado/mensagem é obrigatório!")
            else:
                mensagem_completa = f"{texto_base} {lembranca}"
                
                # Monta a estrutura da nova mensagem passando valores em branco para os campos de identificação física descartados
                nova_msg = {
                    "id": len(mensagens_mural) + 1,
                    "remetente_dchat": remetente_dchat,
                    "remetente_nome": "",
                    "remetente_sobrenome": "",
                    "remetente_email": "",
                    "destinatario": destinatario,
                    "mensagem": mensagem_completa,
                    "data": datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "quem_palpitou": "",
                    "palpite": "",
                    "palpite_feito": False,
                    "acertou": False
                }
                
                # Salva o novo registro de forma persistente (Supabase com fallback local)
                if salvar_nova_mensagem_global(nova_msg):
                    st.success("Mensagem enviada com sucesso para a cozinha! Agradecemos a participação. 🛵💨")
                    st.rerun()

# --- ABA 2: MURAL DE ENTREGAS ---
with aba_mural:
    st.markdown('<div class="centered-title">👀 Quem recebeu uma entrega hoje?</div>', unsafe_allow_html=True)
    
    # O Mural é 100% aberto e visível para todos de forma irrestrita
    if len(mensagens_mural) == 0:
        st.info("Ainda não foram feitas entregas. Seja o primeiro a espalhar carinho!")
    else:
        # Exibe os recibos ordenados pelos mais recentes
        for msg in reversed(mensagens_mural):
            orig_id = msg["id"]
            
            # Renderizador visual do recibo térmico de nota fiscal 99Food (Sem indentação para não quebrar markdown)
            st.markdown(f"""
<div class="receipt-card">
<div class="receipt-header">
<span>PEDIDO: #99F-{orig_id:04d}</span>
<span>{msg['data']}</span>
</div>
<div class="receipt-recipient">💛 PARA: {msg['destinatario']}</div>
<div class="receipt-message-box">"{msg['mensagem']}"</div>
<div class="receipt-barcode">
<div class="barcode-line" style="width: 3px;"></div>
<div class="barcode-line" style="width: 1px;"></div>
<div class="barcode-line" style="width: 4px;"></div>
<div class="barcode-line" style="width: 2px;"></div>
<div class="barcode-line" style="width: 1px;"></div>
<div class="barcode-line" style="width: 3px;"></div>
<div class="barcode-line" style="width: 5px;"></div>
<div class="barcode-line" style="width: 1px;"></div>
<div class="barcode-line" style="width: 2px;"></div>
<div class="barcode-line" style="width: 4px;"></div>
</div>
</div>
<div class="receipt-sawtooth"></div>
""", unsafe_allow_html=True)
            
            # --- LÓGICA DE PRIVACIDADE DO PALPITE (SESSÃO INDIVIDUAL) ---
            session_palpite = st.session_state.meus_palpites.get(orig_id, {})
            palpite_feito_na_sessao = session_palpite.get("palpite_feito", False)
            
            # Se o palpite NÃO foi feito por ESTE utilizador no navegador dele, exibe o formulário
            if not palpite_feito_na_sessao:
                with st.form(key=f"form_palpite_{orig_id}"):
                    st.markdown("<p style='font-weight: bold; color: #212121 !important;'>🕵️ Adivinhe quem te enviou esta mensagem:</p>", unsafe_allow_html=True)
                    # Alterado conforme solicitado para melhor clareza na identificação do nome no cartão
                    identificacao = st.text_input("Seu nome (Nome como está no recado):", key=f"id_{orig_id}", placeholder="Digite seu nome para validar...").strip()
                    chute = st.text_input("Quem você acha que enviou? (Nome como está no D-Chat)", key=f"chute_{orig_id}", placeholder="D-Chat do colega...").strip()
                    
                    # CTA Otimizada para 12 caracteres (Dentro do limite de 18 do Brand Book)
                    botao_palpite = st.form_submit_button("Palpitar Já 🔒")
                    
                    if botao_palpite:
                        if identificacao and chute:
                            # Garante que apenas o destinatário correto possa arriscar o palpite
                            if normalizar_nome(identificacao) in normalizar_nome(msg["destinatario"]):
                                # Registra palpite definitivo (Tentativa única)
                                acertou = normalizar_nome(chute) == normalizar_nome(msg["remetente_dchat"])
                                
                                # Grava na sessão local (Garante privacidade visual!)
                                st.session_state.meus_palpites[orig_id] = {
                                    "palpite_feito": True,
                                    "quem_palpitou": identificacao,
                                    "palpite": chute,
                                    "acertou": acertou
                                }
                                
                                # Salva globalmente no Supabase/JSON para auditoria silenciosa do admin
                                salvar_palpite_global(orig_id, identificacao, chute, acertou)
                                st.rerun()
                            else:
                                st.markdown(f"""
                                <div class="resultado-palpite-box" style="border-left: 6px solid #FF8F00 !important;">
                                    <p>✋ <b>Atenção!</b> Esta mensagem foi enviada para o(a) {msg['destinatario']}. Mas não tem problema, alguém pode ter te enviado um recado especial! 😊</p>
                                </div>
                                """, unsafe_allow_html=True)
                        else:
                            st.warning("Preencha o seu nome E o seu palpite antes de confirmar.")
            
            # SE O PALPITE JÁ FOI REALIZADO POR ESTE UTILIZADOR (Visualização estritamente individual)
            else:
                acertou = session_palpite.get("acertou", False)
                quem_palpitou = session_palpite.get("quem_palpitou", "")
                palpite = session_palpite.get("palpite", "")
                
                if acertou:
                    st.markdown(f"""
                    <div class="resultado-palpite-box" style="border-left: 6px solid #28a745 !important;">
                        <p>🎉 <b>{quem_palpitou}, você acertou em cheio!</b> Quem mandou esse recadinho foi o(a) <b>{msg['remetente_dchat']}</b>! 💛</p>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div class="resultado-palpite-box" style="border-left: 6px solid #dc3545 !important;">
                        <p>❌ <b>Poxa, não foi dessa vez, {quem_palpitou}!</b> O seu palpite foi '{palpite}', mas o mistério continua 100% no ar... Quem será que mandou esse recadinho? 🕵️</p>
                    </div>
                    """, unsafe_allow_html=True)

# --- ÁREA DE ADMINISTRAÇÃO SECRETA ---
if st.query_params.get("adm") == "true":
    st.markdown("---")
    if st.text_input("Senha Master:", type="password") == "99food2026":
        df_mural = pd.DataFrame(mensagens_mural)
        st.dataframe(df_mural)
        
        # Exibição unificada dos botões lado a lado para o administrador
        col_down, col_clear = st.columns(2)
        with col_down:
            if not df_mural.empty:
                # Converte dataframe para arquivo CSV decodificado com BOM (perfeito para abrir no Excel em português)
                csv = df_mural.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    label="Baixar Relatório (CSV) 📊",
                    data=csv,
                    file_name=f"relatorio_arraia_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
        with col_clear:
            if st.button("Limpar Dados 🧹"):
                # Limpa tabela se conectada ao Supabase
                client = obter_cliente_supabase()
                if client is not None:
                    try:
                        # Deleta todas as linhas da tabela
                        client.table("mensagens").delete().neq("id", -1).execute()
                    except Exception:
                        pass
                guardar_mensagens_locais([])
                st.rerun()
