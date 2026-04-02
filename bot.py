from flask import Flask
import threading
import os
import re

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
def limpar_texto(texto):
    texto = texto.lower()
    texto = re.sub(r'[^\w\s]', '', texto)
    return texto
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

    "Alimentação": [
    "restaurante","pizza","hamburguer","lanche","lanchonete","padaria","mercado",
    "supermercado","ifood","delivery","açaí","cafeteria","café","bar","bebida",
    "refeição","almoço","jantar","marmita","sorvete","burger","pizzaria","suco",
    "energetico"
],

    "Transporte": [
    "uber","99","combustivel","gasolina","etanol","diesel","posto","estacionamento",
    "pedagio","taxi","onibus","metro","passagem","viagem","blablacar","trips"
],

    "Moradia": [
    "aluguel","condominio","energia","luz","agua","internet","wifi",
    "manutencao","reforma","material","tinta","ferramenta","telefone"
],

    "Saúde": [
    "farmacia","remedio","consulta","medico","dentista","exame",
    "hospital","clinica","laboratorio","vitamina"
],

    "Lazer": [
    "cinema","netflix","spotify","bar","balada","show","viagem",
    "hotel","passeio","parque","evento","sorveteria"
],

    "Compras": [
    "amazon","mercadolivre","shoppee","shein","compra","loja",
    "shopping","roupa","tenis","camisa","presente","roupas"
],

    "Educação": [
    "curso","livro","faculdade","mensalidade","aula","treinamento",
    "workshop","certificacao","pos"
]

}

def detectar_categoria(texto):

    texto = limpar_texto(texto)
    palavras_texto = texto.split()

    for categoria, palavras in mapa_categorias.items():
        for palavra in palavras:
            if palavra in palavras_texto or palavra in texto:
                return categoria

    return "Outros"


def parse_valor(valor_bruto):

    """
    Converte o valor bruto (string, int, float) em float de forma segura.
    Aceita formatos como '39,90', 'R$ 39,90', números já numéricos
    e células vazias. Se não for possível converter, retorna 0.0.
    """

    if isinstance(valor_bruto, (int, float)):
        return float(valor_bruto)

    if valor_bruto is None:
        return 0.0

    texto = str(valor_bruto).strip()

    if not texto:
        return 0.0

    texto = texto.replace("R$", "").replace(" ", "")
    # remove separador de milhar e converte vírgula para ponto
    texto = texto.replace(".", "").replace(",", ".")

    try:
        return float(texto)
    except:
        return 0.0


def mes_ano_anterior():

    agora = datetime.now()
    mes = agora.month - 1
    ano = agora.year

    if mes == 0:
        mes = 12
        ano -= 1

    return f"{mes:02d}/{ano}"


def resumo_mes_por_periodo(registros, periodo_mes_ano):

    entradas = 0.0
    saidas = 0.0

    for r in registros[1:]:

        if len(r) < 4:
            continue

        data = r[0]
        tipo = r[1]
        valor = parse_valor(r[3])

        if periodo_mes_ano in data:
            if tipo == "Entrada":
                entradas += valor
            else:
                saidas += valor

    saldo = entradas - saidas
    return entradas, saidas, saldo

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

    try:

        # transforma em número
        valor = valor.replace(",", ".")
        valor = float(valor)
        valor = round(valor, 2)

    except:
        await update.message.reply_text(
            "Formato inválido.\nExemplo:\n50 mercado\n+120 salario"
        )
        return

    data = datetime.now().strftime("%d/%m/%Y")

    categoria = detectar_categoria(descricao)

    # envia o valor como número (float) para o Sheets
    # isso garante que o dado seja tratado como numérico independentemente da localidade
    sheet.append_row(
        [data, tipo, categoria, float(valor), descricao],
        value_input_option="RAW"
    )

    await update.message.reply_text("Registrado!")

async def saldo(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not autorizado(update):
        return

    registros = sheet.get_all_values()

    entradas = 0
    saidas = 0

    # primeira linha é o cabeçalho
    for r in registros[1:]:

        if len(r) < 4:
            continue

        tipo = r[1]
        valor = parse_valor(r[3])

        if tipo == "Entrada":
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

    registros = sheet.get_all_values()

    mes_atual = datetime.now().strftime("%m/%Y")
    entradas, saidas, saldo = resumo_mes_por_periodo(registros, mes_atual)

    mensagem = f"""
Resumo do mês

Entradas: R$ {entradas:.2f}
Saídas: R$ {saidas:.2f}
Saldo: R$ {saldo:.2f}
"""

    await update.message.reply_text(mensagem)


async def mesanterior(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not autorizado(update):
        return

    registros = sheet.get_all_values()

    periodo = mes_ano_anterior()
    entradas, saidas, saldo = resumo_mes_por_periodo(registros, periodo)

    mensagem = f"""
Resumo do mês anterior ({periodo})

Entradas: R$ {entradas:.2f}
Saídas: R$ {saidas:.2f}
Saldo: R$ {saldo:.2f}
"""

    await update.message.reply_text(mensagem)


async def saldoanterior(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not autorizado(update):
        return

    registros = sheet.get_all_values()

    periodo = mes_ano_anterior()
    _, _, saldo = resumo_mes_por_periodo(registros, periodo)

    await update.message.reply_text(f"Saldo do mês anterior ({periodo}): R$ {saldo:.2f}")


async def compararmes(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not autorizado(update):
        return

    registros = sheet.get_all_values()

    periodo_atual = datetime.now().strftime("%m/%Y")
    periodo_anterior = mes_ano_anterior()

    ent_atual, sai_atual, sal_atual = resumo_mes_por_periodo(registros, periodo_atual)
    ent_ant, sai_ant, sal_ant = resumo_mes_por_periodo(registros, periodo_anterior)

    variacao = sal_atual - sal_ant

    mensagem = f"""
Comparativo de meses

Mês atual ({periodo_atual})
Entradas: R$ {ent_atual:.2f}
Saídas: R$ {sai_atual:.2f}
Saldo: R$ {sal_atual:.2f}

Mês anterior ({periodo_anterior})
Entradas: R$ {ent_ant:.2f}
Saídas: R$ {sai_ant:.2f}
Saldo: R$ {sal_ant:.2f}

Variação de saldo (atual - anterior): R$ {variacao:.2f}
"""

    await update.message.reply_text(mensagem)

async def categorias(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not autorizado(update):
        return

    registros = sheet.get_all_values()

    categorias_total = {}

    for r in registros[1:]:

        if len(r) < 4:
            continue

        tipo = r[1]

        if tipo == "Saída":

            categoria = r[2]
            valor = parse_valor(r[3])

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

    registros = sheet.get_all_values()

    hoje = datetime.now().strftime("%d/%m/%Y")

    total = 0
    mensagem = "Gastos de hoje\n\n"

    for r in registros[1:]:

        if len(r) < 5:
            continue

        data = r[0]
        tipo = r[1]

        if data == hoje and tipo == "Saída":

            valor = parse_valor(r[3])
            descricao = r[4]

            total += valor

            mensagem += f"{descricao}: R$ {valor:.2f}\n"

    mensagem += f"\nTotal: R$ {total:.2f}"

    await update.message.reply_text(mensagem)

async def grafico(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not autorizado(update):
        return

    registros = sheet.get_all_values()

    categorias_total = {}

    for r in registros[1:]:

        if len(r) < 4:
            continue

        tipo = r[1]

        if tipo == "Saída":

            categoria = r[2]
            valor = parse_valor(r[3])

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

    registros = sheet.get_all_values()

    mes_atual = datetime.now().strftime("%m/%Y")

    categorias_total = {}

    for r in registros[1:]:

        if len(r) < 4:
            continue

        data = r[0]
        tipo = r[1]

        if mes_atual in data and tipo == "Saída":

            categoria = r[2]
            valor = parse_valor(r[3])

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
app.add_handler(CommandHandler("mesanterior", mesanterior))
app.add_handler(CommandHandler("saldoanterior", saldoanterior))
app.add_handler(CommandHandler("compararmes", compararmes))
app.add_handler(CommandHandler("categorias", categorias))
app.add_handler(CommandHandler("hoje", hoje))
app.add_handler(CommandHandler("grafico", grafico))
app.add_handler(CommandHandler("mesgrafico", mesgrafico))
app.add_handler(CommandHandler("ultimos", ultimos))
app.add_handler(CommandHandler("apagar", apagar))

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, registrar))

print("Bot rodando...")

app.run_polling()

while True:
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Erro detectado: {e}")
        print("Reiniciando bot em 5 segundos...")
        import time
        time.sleep(5)