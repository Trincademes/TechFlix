from flask import Flask, render_template, request, jsonify, session
import sqlite3
import os
import re
import uuid
from groq import Groq
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "techfix-dev-secret")

api_key = os.getenv("GROQ_API_KEY")
client = Groq(api_key=api_key)


# =========================
# CONFIGURAÇÕES BÁSICAS
# =========================

def conectar_db():
    return sqlite3.connect("database.db")


def data_atual():
    return datetime.now().strftime("%d/%m/%Y %H:%M")


# =========================
# BANCO DE DADOS
# =========================

def init_db():
    conn = conectar_db()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS conversas (
        id TEXT PRIMARY KEY,
        nome TEXT DEFAULT '',
        telefone TEXT DEFAULT '',
        necessidade TEXT DEFAULT '',
        intencao TEXT DEFAULT 'Atendimento Geral',
        prioridade TEXT DEFAULT 'Normal',
        status TEXT DEFAULT 'Novo contato',
        criado_em TEXT,
        atualizado_em TEXT,
        etapa TEXT DEFAULT 'coletar_nome',
        detalhe TEXT DEFAULT '',
        resumo TEXT DEFAULT ''
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS mensagens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        conversa_id TEXT,
        remetente TEXT,
        mensagem TEXT,
        data TEXT,
        FOREIGN KEY (conversa_id) REFERENCES conversas(id)
    )
    """)

    novas_colunas = [
        ("etapa", "TEXT DEFAULT 'coletar_nome'"),
        ("detalhe", "TEXT DEFAULT ''"),
        ("resumo", "TEXT DEFAULT ''")
    ]

    for coluna, tipo in novas_colunas:
        try:
            cursor.execute(f"ALTER TABLE conversas ADD COLUMN {coluna} {tipo}")
        except sqlite3.OperationalError:
            pass

    conn.commit()
    conn.close()


def criar_conversa():
    conversa_id = str(uuid.uuid4())
    agora = data_atual()

    conn = conectar_db()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO conversas 
        (id, criado_em, atualizado_em, etapa, status)
        VALUES (?, ?, ?, ?, ?)
    """, (
        conversa_id,
        agora,
        agora,
        "coletar_nome",
        "Novo contato"
    ))

    conn.commit()
    conn.close()

    return conversa_id


def buscar_conversa(conversa_id):
    conn = conectar_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM conversas WHERE id = ?", (conversa_id,))
    conversa = cursor.fetchone()

    conn.close()
    return conversa


def garantir_conversa(conversa_id=None):
    if not conversa_id:
        return criar_conversa()

    conversa = buscar_conversa(conversa_id)

    if conversa is None:
        return criar_conversa()

    return conversa_id


def salvar_mensagem(conversa_id, remetente, mensagem):
    conn = conectar_db()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO mensagens (conversa_id, remetente, mensagem, data)
        VALUES (?, ?, ?, ?)
    """, (
        conversa_id,
        remetente,
        mensagem,
        data_atual()
    ))

    conn.commit()
    conn.close()


def buscar_historico(conversa_id):
    conn = conectar_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT remetente, mensagem
        FROM mensagens
        WHERE conversa_id = ?
        ORDER BY id ASC
        LIMIT 18
    """, (conversa_id,))

    historico = cursor.fetchall()

    conn.close()
    return historico


# =========================
# EXTRAÇÃO DE DADOS
# =========================

def eh_saudacao(texto):
    texto = texto.lower().strip()

    saudacoes = [
        "oi", "olá", "ola", "bom dia", "boa tarde", "boa noite",
        "e aí", "eai", "opa", "salve", "hello", "hi"
    ]

    return texto in saudacoes


def extrair_telefone(texto):
    padrao = r"(\(?\d{2}\)?\s?\d{4,5}-?\d{4})"
    resultado = re.search(padrao, texto)

    if resultado:
        return resultado.group(1)

    apenas_numeros = re.sub(r"\D", "", texto)

    if len(apenas_numeros) in [10, 11]:
        return apenas_numeros

    return ""


def extrair_nome(texto, etapa_atual):
    texto_original = texto.strip()
    texto_lower = texto_original.lower()

    padroes = [
        r"meu nome é ([a-zA-ZÀ-ÿ\s]+)",
        r"me chamo ([a-zA-ZÀ-ÿ\s]+)",
        r"sou o ([a-zA-ZÀ-ÿ\s]+)",
        r"sou a ([a-zA-ZÀ-ÿ\s]+)",
        r"pode me chamar de ([a-zA-ZÀ-ÿ\s]+)"
    ]

    for padrao in padroes:
        resultado = re.search(padrao, texto_lower)

        if resultado:
            nome = resultado.group(1).strip()

            cortes = [
                " e ", " meu ", " minha ", " telefone ",
                " preciso ", " quero ", " gostaria ", " tenho ",
                " meu telefone", " minha empresa"
            ]

            for corte in cortes:
                if corte in nome:
                    nome = nome.split(corte)[0]

            return nome.title()

    if etapa_atual == "coletar_nome":
        palavras_bloqueadas = [
            "oi", "olá", "ola", "bom dia", "boa tarde", "boa noite",
            "quero orçamento", "preciso de suporte", "suporte", "orçamento",
            "site", "sistema", "automação", "automatização", "preço", "valor",
            "quero um site", "quero criar um site"
        ]

        parece_nome = (
            len(texto_original.split()) <= 3
            and not any(char.isdigit() for char in texto_original)
            and len(texto_original) >= 2
            and texto_lower not in palavras_bloqueadas
            and not eh_saudacao(texto_original)
        )

        if parece_nome:
            return texto_original.title()

    return ""


def detectar_intencao(texto):
    texto = texto.lower()

    if any(p in texto for p in [
        "orçamento", "preço", "valor", "proposta", "quanto custa",
        "contratar", "venda", "site", "landing page", "loja virtual",
        "e-commerce", "ecommerce"
    ]):
        return "Venda / Orçamento"

    if any(p in texto for p in [
        "erro", "problema", "bug", "suporte", "não funciona",
        "falha", "travando", "fora do ar", "sistema caiu"
    ]):
        return "Suporte Técnico"

    if any(p in texto for p in [
        "horário", "funcionamento", "atendimento", "abre", "fecha"
    ]):
        return "Informação"

    if any(p in texto for p in [
        "automação", "automatizar", "processo", "planilha",
        "manual", "repetitivo"
    ]):
        return "Automação"

    return "Atendimento Geral"


def detectar_prioridade(texto):
    texto = texto.lower()

    if any(p in texto for p in [
        "urgente", "parado", "fora do ar", "sistema caiu",
        "não consigo vender", "produção", "cliente reclamando",
        "perdendo venda", "perdendo dinheiro"
    ]):
        return "Alta"

    if any(p in texto for p in [
        "erro", "problema", "falha", "bug", "travando", "lento"
    ]):
        return "Média"

    return "Normal"


def extrair_necessidade(texto):
    texto = texto.lower()

    if any(p in texto for p in ["site institucional", "site para empresa"]):
        return "Site institucional"

    if any(p in texto for p in ["landing page", "página de vendas", "pagina de vendas"]):
        return "Landing page"

    if any(p in texto for p in ["loja virtual", "e-commerce", "ecommerce", "vender online"]):
        return "Loja virtual / E-commerce"

    if any(p in texto for p in ["site", "website", "página", "pagina"]):
        return "Criação de site"

    if any(p in texto for p in ["sistema", "sistema web", "plataforma", "dashboard", "painel"]):
        return "Sistema web"

    if any(p in texto for p in ["automação", "automatizar", "processo manual", "planilha"]):
        return "Automação de processos"

    if any(p in texto for p in ["suporte", "erro", "problema", "bug", "falha", "travando", "fora do ar"]):
        return "Suporte técnico"

    if any(p in texto for p in ["consultoria", "análise", "melhoria"]):
        return "Consultoria técnica"

    return ""


def gerar_resumo(nome, telefone, necessidade, intencao, prioridade, detalhe):
    partes = []

    if nome:
        partes.append(f"Cliente: {nome}")

    if telefone:
        partes.append(f"Telefone: {telefone}")

    if necessidade:
        partes.append(f"Necessidade: {necessidade}")

    if detalhe:
        partes.append(f"Detalhe: {detalhe}")

    partes.append(f"Intenção: {intencao}")
    partes.append(f"Prioridade: {prioridade}")

    return " | ".join(partes)


# =========================
# FLUXO DA CONVERSA
# =========================

def calcular_etapa_status(nome, telefone, necessidade, detalhe, prioridade, intencao):
    if not nome:
        return "coletar_nome", "Novo contato"

    if not telefone:
        return "coletar_telefone", "Coletando contato"

    if not necessidade:
        return "entender_problema", "Entendendo necessidade"

    if not detalhe:
        return "aprofundar_necessidade", "Qualificando lead"

    if prioridade == "Alta":
        return "finalizado", "Prioridade alta"

    if intencao == "Venda / Orçamento":
        return "finalizado", "Encaminhar comercial"

    if intencao == "Suporte Técnico":
        return "finalizado", "Encaminhar suporte"

    return "finalizado", "Lead qualificado"


def atualizar_conversa(conversa_id, mensagem):
    conversa_id = garantir_conversa(conversa_id)
    session["conversa_id"] = conversa_id

    conversa = buscar_conversa(conversa_id)

    nome_atual = conversa[1]
    telefone_atual = conversa[2]
    necessidade_atual = conversa[3]
    intencao_atual = conversa[4]
    prioridade_atual = conversa[5]
    etapa_atual = conversa[9] if len(conversa) > 9 else "coletar_nome"
    detalhe_atual = conversa[10] if len(conversa) > 10 else ""

    nome_extraido = extrair_nome(mensagem, etapa_atual)
    telefone_extraido = extrair_telefone(mensagem)
    necessidade_extraida = extrair_necessidade(mensagem)
    intencao_extraida = detectar_intencao(mensagem)
    prioridade_extraida = detectar_prioridade(mensagem)

    nome_final = nome_extraido if nome_extraido else nome_atual
    telefone_final = telefone_extraido if telefone_extraido else telefone_atual
    necessidade_final = necessidade_extraida if necessidade_extraida else necessidade_atual

    detalhe_final = detalhe_atual
    texto_limpo = mensagem.strip()

    mensagem_nao_util_para_detalhe = (
        eh_saudacao(texto_limpo)
        or texto_limpo == nome_extraido
        or texto_limpo == telefone_extraido
        or len(texto_limpo) < 4
    )

    if necessidade_final and not detalhe_atual and not mensagem_nao_util_para_detalhe:
        if etapa_atual in [
            "aprofundar_necessidade",
            "entender_problema",
            "coletar_detalhe",
            "coletar_necessidade"
        ]:
            detalhe_final = texto_limpo

    intencao_final = intencao_extraida

    if intencao_extraida == "Atendimento Geral" and intencao_atual != "Atendimento Geral":
        intencao_final = intencao_atual

    prioridade_final = prioridade_extraida

    if prioridade_atual == "Alta":
        prioridade_final = "Alta"
    elif prioridade_atual == "Média" and prioridade_extraida == "Normal":
        prioridade_final = "Média"

    etapa_final, status_final = calcular_etapa_status(
        nome_final,
        telefone_final,
        necessidade_final,
        detalhe_final,
        prioridade_final,
        intencao_final
    )

    resumo_final = gerar_resumo(
        nome_final,
        telefone_final,
        necessidade_final,
        intencao_final,
        prioridade_final,
        detalhe_final
    )

    conn = conectar_db()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE conversas
        SET nome = ?,
            telefone = ?,
            necessidade = ?,
            intencao = ?,
            prioridade = ?,
            status = ?,
            atualizado_em = ?,
            etapa = ?,
            detalhe = ?,
            resumo = ?
        WHERE id = ?
    """, (
        nome_final,
        telefone_final,
        necessidade_final,
        intencao_final,
        prioridade_final,
        status_final,
        data_atual(),
        etapa_final,
        detalhe_final,
        resumo_final,
        conversa_id
    ))

    conn.commit()
    conn.close()

    return conversa_id


# =========================
# IA CONTROLADA / NATURAL
# =========================

def obter_instrucao_resposta(conversa, ultima_mensagem):
    nome = conversa[1]
    etapa = conversa[9]

    return f"""
A última mensagem do cliente foi:
"{ultima_mensagem}"

Antes de seguir o fluxo, analise se o cliente fez uma pergunta específica.

Se ele fez uma pergunta específica sobre serviços, sites, sistemas, automação, suporte, reunião, orçamento ou funcionamento:
- Responda essa dúvida de forma objetiva.
- Depois continue a etapa atual com naturalidade.
- Não ignore a pergunta do cliente.

Se ele não fez pergunta específica:
- Apenas siga a etapa atual.

Etapa atual do atendimento: {etapa}

COMO AGIR EM CADA ETAPA:

1. coletar_nome:
Se ainda não tiver nome, peça o nome de forma natural.
Exemplo:
"Sim, podemos te ajudar com isso. Para eu registrar seu atendimento, qual é o seu nome?"

2. coletar_telefone:
Se já tiver nome mas não tiver telefone, peça o telefone.
Exemplo:
"Perfeito, {nome}. Para nossa equipe conseguir retornar depois, qual telefone podemos usar?"

3. entender_problema:
Se já tiver nome e telefone, entenda o que o cliente quer resolver.
Exemplo:
"Certo, {nome}. Me conta um pouco melhor o que você quer desenvolver ou resolver."

4. aprofundar_necessidade:
Se já tiver uma necessidade identificada, faça uma pergunta mais específica sobre ela.
- Para site: pergunte se o objetivo é apresentar a empresa, captar clientes ou vender online.
- Para sistema: pergunte qual processo o sistema precisa organizar.
- Para automação: pergunte qual tarefa hoje é manual ou repetitiva.
- Para suporte: pergunte qual problema está acontecendo e se afeta o uso do sistema.

5. finalizado:
Faça um resumo organizado do atendimento e diga que a equipe da TechFix entrará em contato para alinhar detalhes e, se fizer sentido, marcar uma reunião.

REGRAS:
- Seja natural, como um atendente humano.
- Não seja seco.
- Não escreva textão.
- Responda dúvidas específicas sem fugir do tema.
- Depois de responder a dúvida, volte suavemente para a coleta do lead.
- Faça no máximo uma pergunta no final.
- Não invente preço.
- Não prometa prazo.
- Não diga que é IA.
"""


def montar_prompt_sistema(conversa, instrucao):
    nome = conversa[1] if conversa[1] else "não informado"
    telefone = conversa[2] if conversa[2] else "não informado"
    necessidade = conversa[3] if conversa[3] else "não informada"
    intencao = conversa[4]
    prioridade = conversa[5]
    status = conversa[6]
    etapa = conversa[9]
    detalhe = conversa[10] if conversa[10] else "não informado"

    return f"""
Você é o TechFix AI Assistant, atendente virtual da TechFix Soluções Digitais.

A TechFix é uma empresa fictícia de tecnologia que atende pequenos negócios com:
- Criação de sites institucionais
- Landing pages
- Lojas virtuais
- Sistemas web
- Dashboards
- Automação de processos
- Suporte técnico

Seu objetivo é fazer um pré-atendimento natural:
1. Entender o que o cliente precisa.
2. Responder dúvidas relacionadas aos serviços.
3. Coletar nome, telefone e necessidade.
4. Organizar as informações.
5. Encaminhar para a equipe humana.

DADOS ATUAIS DO ATENDIMENTO:
- Nome: {nome}
- Telefone: {telefone}
- Necessidade: {necessidade}
- Detalhe: {detalhe}
- Intenção: {intencao}
- Prioridade: {prioridade}
- Status: {status}
- Etapa atual: {etapa}

INSTRUÇÃO PARA ESTA RESPOSTA:
{instrucao}

COMO VOCÊ DEVE RESPONDER:
- Converse como um atendente humano de uma empresa de tecnologia.
- Seja consultivo, simpático e direto.
- Se o cliente perguntar algo específico, responda primeiro.
- Depois conduza para o próximo passo do atendimento.
- Use o nome do cliente quando ele já estiver disponível.
- Faça apenas uma pergunta por mensagem.
- Não repita perguntas já respondidas.
- Não force o cliente.
- Não diga "como posso ajudar?" repetidamente.
- Não invente preços, prazos, garantias ou funcionalidades que não foram citadas.
- Não fale que é uma IA.
- Não explique regras internas.
- Não use respostas genéricas demais.

EXEMPLOS DE BOAS RESPOSTAS:

Cliente: "Vocês fazem loja virtual?"
Resposta:
"Sim, fazemos loja virtual para empresas que querem vender online, com estrutura para produtos, pedidos e gestão básica. Para eu registrar seu atendimento, qual é o seu nome?"

Cliente: "Quanto custa um site?"
Resposta:
"O valor depende do tipo de site, quantidade de páginas e funcionalidades. A equipe consegue avaliar melhor depois de entender sua necessidade. Para começar, qual é o seu nome?"

Cliente: "Preciso automatizar uma planilha"
Resposta:
"Entendi. A TechFix pode ajudar a transformar processos manuais em fluxos mais automatizados. Qual tarefa dessa planilha você quer reduzir ou automatizar?"

Cliente: "Meu sistema caiu"
Resposta:
"Entendi, isso parece um caso de suporte com prioridade maior. Para registrar corretamente, qual é o seu nome?"

Cliente: "Pedro"
Resposta:
"Perfeito, Pedro. Qual telefone nossa equipe pode usar para retornar?"

Cliente: "15999999999"
Resposta:
"Obrigado, Pedro. Agora me conta um pouco melhor: o que você quer desenvolver ou resolver?"

Cliente: "Quero um site para captar clientes"
Resposta:
"Entendi, Pedro. Então o objetivo é criar um site focado em apresentar sua empresa e gerar contatos. Esse site seria mais institucional ou uma página de vendas?"

Cliente: "Institucional"
Resposta:
"Perfeito, Pedro. Registrei as informações do seu atendimento:
- Nome: Pedro
- Telefone: 15999999999
- Necessidade: Criação de site
- Objetivo: site institucional para captar clientes

Vou encaminhar essas informações para a equipe da TechFix. Eles poderão entrar em contato pelo telefone informado para alinhar os detalhes e, se fizer sentido, marcar uma reunião."

FORMATO:
Responda apenas a mensagem que será enviada ao cliente.
"""


def gerar_resposta_ia(conversa_id):
    conversa = buscar_conversa(conversa_id)
    historico = buscar_historico(conversa_id)

    ultima_mensagem = historico[-1][1] if historico else ""
    instrucao = obter_instrucao_resposta(conversa, ultima_mensagem)

    mensagens_groq = [
        {
            "role": "system",
            "content": montar_prompt_sistema(conversa, instrucao)
        }
    ]

    for remetente, mensagem in historico:
        role = "user" if remetente == "cliente" else "assistant"

        mensagens_groq.append({
            "role": role,
            "content": mensagem
        })

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=mensagens_groq,
            temperature=0.55,
            max_tokens=320
        )

        return response.choices[0].message.content

    except Exception as e:
        print("ERRO REAL:", e)
        return "Desculpe, tive um problema ao responder agora. Pode tentar novamente?"


# =========================
# ROTAS
# =========================

init_db()


@app.route("/")
def index():
    conversa_id = session.get("conversa_id")
    conversa_id = garantir_conversa(conversa_id)
    session["conversa_id"] = conversa_id

    return render_template("index.html")


@app.route("/nova-conversa")
def nova_conversa():
    session["conversa_id"] = criar_conversa()
    return jsonify({"status": "nova conversa criada"})


@app.route("/chat", methods=["POST"])
def chat():
    conversa_id = session.get("conversa_id")
    conversa_id = garantir_conversa(conversa_id)
    session["conversa_id"] = conversa_id

    user_message = request.json["message"]

    conversa_id = atualizar_conversa(conversa_id, user_message)

    salvar_mensagem(conversa_id, "cliente", user_message)

    bot_reply = gerar_resposta_ia(conversa_id)

    salvar_mensagem(conversa_id, "assistente", bot_reply)

    return jsonify({"reply": bot_reply})


@app.route("/admin")
def admin():
    conn = conectar_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            c.id,
            c.nome,
            c.telefone,
            c.necessidade,
            c.intencao,
            c.prioridade,
            c.status,
            c.criado_em,
            c.atualizado_em,
            COUNT(m.id) as total_mensagens
        FROM conversas c
        LEFT JOIN mensagens m ON c.id = m.conversa_id
        GROUP BY c.id
        ORDER BY c.atualizado_em DESC
    """)

    conversas = cursor.fetchall()

    cursor.execute("SELECT COUNT(*) FROM conversas")
    total_conversas = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*) FROM conversas
        WHERE nome != '' OR telefone != ''
    """)
    total_leads = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*) FROM conversas
        WHERE prioridade = 'Alta'
    """)
    alta_prioridade = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*) FROM conversas
        WHERE intencao = 'Venda / Orçamento'
    """)
    oportunidades = cursor.fetchone()[0]

    conn.close()

    return render_template(
        "admin.html",
        conversas=conversas,
        total_conversas=total_conversas,
        total_leads=total_leads,
        alta_prioridade=alta_prioridade,
        oportunidades=oportunidades
    )


@app.route("/admin/conversa/<conversa_id>")
def detalhes_conversa(conversa_id):
    conn = conectar_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM conversas WHERE id = ?", (conversa_id,))
    conversa = cursor.fetchone()

    cursor.execute("""
        SELECT remetente, mensagem, data
        FROM mensagens
        WHERE conversa_id = ?
        ORDER BY id ASC
    """, (conversa_id,))

    mensagens = cursor.fetchall()

    conn.close()

    if conversa is None:
        return "Conversa não encontrada", 404

    return render_template(
        "detalhes.html",
        conversa=conversa,
        mensagens=mensagens
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)