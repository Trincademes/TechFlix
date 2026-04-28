from flask import Flask, render_template, request, jsonify
import sqlite3
import os
import re
from groq import Groq
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

app = Flask(__name__)

api_key = os.getenv("GROQ_API_KEY")
client = Groq(api_key=api_key)


def init_db():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS mensagens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        mensagem TEXT,
        resposta TEXT,
        data TEXT,
        intencao TEXT DEFAULT 'Não classificado',
        prioridade TEXT DEFAULT 'Normal',
        nome TEXT DEFAULT '',
        telefone TEXT DEFAULT ''
    )
    """)

    # Caso sua tabela antiga já exista, adiciona colunas novas sem quebrar
    novas_colunas = [
        ("intencao", "TEXT DEFAULT 'Não classificado'"),
        ("prioridade", "TEXT DEFAULT 'Normal'"),
        ("nome", "TEXT DEFAULT ''"),
        ("telefone", "TEXT DEFAULT ''")
    ]

    for coluna, tipo in novas_colunas:
        try:
            cursor.execute(f"ALTER TABLE mensagens ADD COLUMN {coluna} {tipo}")
        except sqlite3.OperationalError:
            pass

    conn.commit()
    conn.close()


def detectar_intencao(texto):
    texto = texto.lower()

    if any(palavra in texto for palavra in ["orçamento", "preço", "valor", "site", "proposta", "quanto custa"]):
        return "Venda / Orçamento"

    if any(palavra in texto for palavra in ["erro", "problema", "bug", "suporte", "não funciona", "falha", "travando"]):
        return "Suporte Técnico"

    if any(palavra in texto for palavra in ["horário", "funcionamento", "atendimento", "abre", "fecha"]):
        return "Informação"

    return "Atendimento Geral"


def detectar_prioridade(texto):
    texto = texto.lower()

    if any(palavra in texto for palavra in ["urgente", "parado", "não consigo vender", "sistema caiu", "em produção", "cliente reclamando"]):
        return "Alta"

    if any(palavra in texto for palavra in ["erro", "problema", "falha", "bug"]):
        return "Média"

    return "Normal"


def extrair_telefone(texto):
    padrao = r"(\(?\d{2}\)?\s?\d{4,5}-?\d{4})"
    resultado = re.search(padrao, texto)

    if resultado:
        return resultado.group(1)

    return ""


def extrair_nome(texto):
    texto_lower = texto.lower()

    padroes = [
        r"meu nome é ([a-zA-ZÀ-ÿ\s]+)",
        r"me chamo ([a-zA-ZÀ-ÿ\s]+)",
        r"sou o ([a-zA-ZÀ-ÿ\s]+)",
        r"sou a ([a-zA-ZÀ-ÿ\s]+)"
    ]

    for padrao in padroes:
        resultado = re.search(padrao, texto_lower)
        if resultado:
            nome = resultado.group(1).strip().title()
            return nome

    return ""


init_db()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/admin")
def admin():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM mensagens ORDER BY id DESC")
    dados = cursor.fetchall()

    cursor.execute("SELECT COUNT(*) FROM mensagens")
    total_mensagens = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM mensagens WHERE telefone != '' OR nome != ''")
    total_leads = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM mensagens WHERE prioridade = 'Alta'")
    alta_prioridade = cursor.fetchone()[0]

    conn.close()

    return render_template(
        "admin.html",
        dados=dados,
        total_mensagens=total_mensagens,
        total_leads=total_leads,
        alta_prioridade=alta_prioridade
    )


@app.route("/chat", methods=["POST"])
def chat():
    user_message = request.json["message"]

    intencao = detectar_intencao(user_message)
    prioridade = detectar_prioridade(user_message)
    telefone = extrair_telefone(user_message)
    nome = extrair_nome(user_message)

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "system",
                    "content": """
                    Você é o assistente virtual da empresa fictícia TechFix Soluções Digitais.

                    A TechFix oferece:
                    - Criação de sites profissionais
                    - Suporte técnico
                    - Automação de processos
                    - Desenvolvimento de sistemas web

                    Seu papel:
                    - Atender clientes de forma profissional
                    - Identificar se o cliente quer orçamento, suporte ou informação
                    - Fazer perguntas úteis para entender a necessidade
                    - Quando fizer sentido, pedir nome e telefone para contato
                    - Ser educado, claro e objetivo

                    Se o cliente pedir orçamento, pergunte:
                    - Tipo de serviço desejado
                    - Nome
                    - Telefone

                    Se o cliente pedir suporte, pergunte:
                    - Qual problema está acontecendo
                    - Se é urgente
                    - Nome e telefone para retorno

                    Não diga que você é apenas uma IA. Aja como assistente virtual da TechFix.
                    """
                },
                {
                    "role": "user",
                    "content": user_message
                }
            ]
        )

        bot_reply = response.choices[0].message.content

    except Exception as e:
        print("ERRO REAL:", e)
        bot_reply = "Desculpe, tive um problema ao responder agora. Tente novamente em instantes."

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO mensagens 
        (mensagem, resposta, data, intencao, prioridade, nome, telefone) 
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        user_message,
        bot_reply,
        datetime.now().strftime("%d/%m/%Y %H:%M"),
        intencao,
        prioridade,
        nome,
        telefone
    ))

    conn.commit()
    conn.close()

    return jsonify({"reply": bot_reply})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)