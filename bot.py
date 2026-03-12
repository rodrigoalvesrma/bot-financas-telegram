from flask import Flask
import threading
import os

app = Flask(__name__)

@app.route("/")
def home():
    return "Bot rodando"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=run_web).start()

import matplotlib.pyplot as plt
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes
from datetime import datetime
USUARIO_AUTORIZADO = 1550267050

# ----------------------------
# CONEXÃO COM GOOGLE SHEETS
# ----------------------------

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

import os
import json
from oauth2client.service_account import ServiceAccountCredentials

credenciais_json = os.getenv("GOOGLE_CREDENTIALS")
credenciais_dict = json.loads(credenciais_json)

creds = ServiceAccountCredentials.from_json_keyfile_dict(credenciais_dict, scope)
client = gspread.authorize(creds)

sheet = client.open("Controle Financeiro").sheet1

# ----------------------------
# CATEGORIAS AUTOMÁTICAS
# ----------------------------

mapa_categorias = {
    "almoço": "Alimentação",
    "jantar": "Alimentação",
    "lanche": "Alimentação",
    "restaurante": "Alimentação",

    "gasolina": "Transporte",
    "uber": "Transporte",
    "combustivel": "Transporte",

    "mercado": "Casa",
    "supermercado": "Casa",

    "farmacia": "Saúde",
    "remedio": "Saúde",

    "cinema": "Lazer",
    "bar": "Lazer",
}

def detectar_categoria(texto):

    texto = texto.lower()

    for palavra, categoria in mapa_categorias.items():
        if palavra in texto:
            return categoria

    return "Outros"


# ----------------------------
# FUNÇÃO PRINCIPAL
# ----------------------------

async def registrar(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not autorizado(update):
        return

    texto = update.message.text

    partes = texto.split(" ", 1)

    valor = partes[0]
    descricao = partes[1] if len(partes) > 1 else ""

    tipo = "Saída"

    if valor.startswith("+"):
        tipo = "Entrada"
        valor = valor.replace("+", "")

    data = datetime.now().strftime("%d/%m/%Y")

    categoria = detectar_categoria(descricao)

    sheet.append_row([data, tipo, categoria, valor, descricao])

    await update.message.reply_text("Registrado!")

async def saldo(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not autorizado(update):
        return

    registros = sheet.get_all_records()

    entradas = 0
    saidas = 0

    for r in registros:

        valor = float(r["Valor"])

        if r["Tipo"] == "Entrada":
            entradas += valor
        else:
            saidas += valor

    saldo = entradas - saidas

    mensagem = f"""
Resumo financeiro

Entradas: R$ {entradas:.2f}
Saídas: R$ {saidas:.2f}
Saldo: R$ {saldo:.2f}
"""

    await update.message.reply_text(mensagem)

async def mes(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not autorizado(update):
        return

    registros = sheet.get_all_records()

    mes_atual = datetime.now().strftime("%m/%Y")

    entradas = 0
    saidas = 0

    for r in registros:

        data = r["Data"]

        if mes_atual in data:

            valor = float(r["Valor"])

            if r["Tipo"] == "Entrada":
                entradas += valor
            else:
                saidas += valor

    saldo = entradas - saidas

    mensagem = f"""
Resumo do mês

Entradas: R$ {entradas:.2f}
Saídas: R$ {saidas:.2f}
Saldo: R$ {saldo:.2f}
"""

    await update.message.reply_text(mensagem)

async def categorias(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not autorizado(update):
        return

    registros = sheet.get_all_records()

    categorias_total = {}

    for r in registros:

        if r["Tipo"] == "Saída":

            categoria = r["Categoria"]
            valor = float(r["Valor"])

            if categoria not in categorias_total:
                categorias_total[categoria] = 0

            categorias_total[categoria] += valor

    mensagem = "Gastos por categoria\n\n"

    for cat, valor in categorias_total.items():
        mensagem += f"{cat}: R$ {valor:.2f}\n"

    await update.message.reply_text(mensagem)

async def hoje(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not autorizado(update):
        return

    registros = sheet.get_all_records()

    hoje = datetime.now().strftime("%d/%m/%Y")

    total = 0
    mensagem = "Gastos de hoje\n\n"

    for r in registros:

        if r["Data"] == hoje and r["Tipo"] == "Saída":

            valor = float(r["Valor"])
            descricao = r["Descrição"]

            total += valor

            mensagem += f"{descricao}: R$ {valor:.2f}\n"

    mensagem += f"\nTotal: R$ {total:.2f}"

    await update.message.reply_text(mensagem)

async def grafico(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not autorizado(update):
        return

    registros = sheet.get_all_records()

    categorias_total = {}

    for r in registros:

        if r["Tipo"] == "Saída":

            categoria = r["Categoria"]
            valor = float(r["Valor"])

            if categoria not in categorias_total:
                categorias_total[categoria] = 0

            categorias_total[categoria] += valor

    labels = list(categorias_total.keys())
    valores = list(categorias_total.values())

    plt.figure()

    plt.pie(valores, labels=labels, autopct='%1.1f%%')

    plt.title("Gastos por Categoria")

    caminho = "grafico.png"

    plt.savefig(caminho)

    plt.close()

    with open(caminho, "rb") as foto:
        await update.message.reply_photo(foto)

async def mesgrafico(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not autorizado(update):
        return

    registros = sheet.get_all_records()

    mes_atual = datetime.now().strftime("%m/%Y")

    categorias_total = {}

    for r in registros:

        data = r["Data"]

        if mes_atual in data and r["Tipo"] == "Saída":

            categoria = r["Categoria"]
            valor = float(r["Valor"])

            if categoria not in categorias_total:
                categorias_total[categoria] = 0

            categorias_total[categoria] += valor

    if not categorias_total:
        await update.message.reply_text("Nenhum gasto registrado neste mês.")
        return

    labels = list(categorias_total.keys())
    valores = list(categorias_total.values())

    plt.figure()

    plt.pie(valores, labels=labels, autopct='%1.1f%%')

    plt.title("Gastos do mês por categoria")

    caminho = "grafico_mes.png"

    plt.savefig(caminho)

    plt.close()

    with open(caminho, "rb") as foto:
        await update.message.reply_photo(foto)

async def ultimos(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not autorizado(update):
        return

    registros = sheet.get_all_values()

    ultimos = registros[-5:]

    mensagem = "Ultimos registros\n\n"

    for i, r in enumerate(ultimos, start=1):

        data = r[0]
        descricao = r[4]
        valor = r[3]

        mensagem += f"{i} - {data} | {descricao} | R$ {valor}\n"

    await update.message.reply_text(mensagem)

async def apagar(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not context.args:
        await update.message.reply_text("Use /apagar numero")
        return

    numero = int(context.args[0])

    registros = sheet.get_all_values()

    linha = len(registros) - (5 - numero)

    sheet.delete_rows(linha)

    await update.message.reply_text("Registro apagado com sucesso")

def autorizado(update):

    user_id = update.effective_user.id

    if user_id != USUARIO_AUTORIZADO:
        return False

    return True

# ----------------------------
# INICIAR BOT
# ----------------------------

TOKEN = "8571302338:AAELRp-vYSTjXMrem22xZqIn9Xfo5X9o9Pk"

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("saldo", saldo))
app.add_handler(CommandHandler("mes", mes))
app.add_handler(CommandHandler("categorias", categorias))
app.add_handler(CommandHandler("hoje", hoje))
app.add_handler(CommandHandler("grafico", grafico))
app.add_handler(CommandHandler("mesgrafico", mesgrafico))
app.add_handler(CommandHandler("ultimos", ultimos))
app.add_handler(CommandHandler("apagar", apagar))

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, registrar))

print("Bot rodando...")

app.run_polling()