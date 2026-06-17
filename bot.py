from flask import Flask
import threading
import os
import re
import unicodedata

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
    texto = "" if texto is None else str(texto).lower()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = re.sub(r'[^\w\s]', ' ', texto)
    texto = re.sub(r'\s+', ' ', texto).strip()
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
        "restaurante", "pizza", "hamburguer", "hamburger", "lanche", "lanchonete",
        "padaria", "mercado", "supermercado", "hortifruti", "acougue", "ifood",
        "delivery", "acai", "cafeteria", "cafe", "bebida", "refeicao", "almoco",
        "jantar", "marmita", "sorvete", "burger", "pizzaria", "suco", "energetico",
        "sanduiche", "pastel", "esfiha", "japones", "sushi", "churrasco"
    ],

    "Transporte": [
        "uber", "99", "combustivel", "gasolina", "etanol", "diesel", "posto",
        "estacionamento", "pedagio", "taxi", "onibus", "metro", "passagem",
        "blablacar", "trips", "abastecimento", "moto", "carro", "oficina",
        "lavajato", "borracharia", "ipva", "licenciamento"
    ],

    "Moradia": [
        "aluguel", "condominio", "energia", "luz", "agua", "internet", "wifi",
        "manutencao", "reforma", "material", "tinta", "ferramenta", "casa",
        "apartamento", "gas", "sabesp", "enel", "claro", "vivo", "tim"
    ],

    "Saúde": [
        "farmacia", "remedio", "consulta", "medico", "dentista", "exame",
        "hospital", "clinica", "laboratorio", "vitamina", "plano de saude",
        "psicologo", "terapia", "academia", "suplemento"
    ],

    "Lazer": [
        "cinema", "netflix", "spotify", "bar", "balada", "show", "viagem",
        "hotel", "passeio", "parque", "evento", "sorveteria", "festa",
        "ingresso", "jogo", "steam", "playstation", "xbox"
    ],

    "Compras": [
        "amazon", "mercadolivre", "mercado livre", "shopee", "shoppee", "shein",
        "compra", "loja", "shopping", "roupa", "tenis", "camisa", "presente",
        "roupas", "eletronico", "celular", "moveis", "magalu", "americanas"
    ],

    "Educação": [
        "curso", "livro", "faculdade", "mensalidade", "aula", "treinamento",
        "workshop", "certificacao", "pos", "escola", "material escolar"
    ],

    "Serviços": [
        "assinatura", "icloud", "google", "microsoft", "canva", "chatgpt",
        "openai", "dominio", "hospedagem", "app", "software", "sistema"
    ],

    "Impostos e Taxas": [
        "imposto", "taxa", "tarifa", "multa", "juros", "boleto", "mei", "das",
        "irpf", "inss", "fgts"
    ],

    "Pets": [
        "pet", "racao", "veterinario", "banho", "tosa", "petshop"
    ]

}

def detectar_categoria(texto):

    texto = limpar_texto(texto)
    palavras_texto = texto.split()
    conjunto_palavras = set(palavras_texto)
    melhor_categoria = "Outros"
    melhor_pontuacao = 0

    for categoria, palavras in mapa_categorias.items():
        for palavra in palavras:
            palavra_normalizada = limpar_texto(palavra)
            palavras_chave = palavra_normalizada.split()

            if not palavra_normalizada:
                continue

            if len(palavras_chave) > 1 and palavra_normalizada in texto:
                pontuacao = len(palavras_chave) + 1
            elif palavra_normalizada in conjunto_palavras:
                pontuacao = 2
            elif len(palavra_normalizada) >= 4 and palavra_normalizada in texto:
                pontuacao = 1
            else:
                pontuacao = 0

            if pontuacao > melhor_pontuacao:
                melhor_categoria = categoria
                melhor_pontuacao = pontuacao

    return melhor_categoria


def eh_entrada_por_descricao(descricao):

    texto = limpar_texto(descricao)
    palavras_entrada = [
        "salario", "recebimento", "recebi", "recebeu", "bonus",
        "bonificacao", "comissao", "freela", "freelance", "rendimento",
        "pix recebido", "transferencia recebida", "deposito", "entrada",
        "reembolso", "estorno"
    ]

    for palavra in palavras_entrada:
        if palavra in texto:
            return True

    return False


FORMAS_PAGAMENTO = {
    "Crédito": [
        "cartao de credito", "cartao credito", "credito", "credit", "cc"
    ],
    "Débito": [
        "cartao de debito", "cartao debito", "debito", "debit", "cd"
    ],
    "Pix": [
        "pix"
    ],
    "Dinheiro": [
        "dinheiro", "cash", "especie"
    ],
    "Boleto": [
        "boleto"
    ],
    "Transferência": [
        "transferencia", "ted", "doc"
    ]
}

PALAVRAS_SAIDA = [
    "paguei", "pago", "pagamento", "gastei", "gasto", "comprei", "compra",
    "despesa", "saida", "debito", "debitar", "pagar"
]

PALAVRAS_IGNORADAS_DESCRICAO = {
    "paguei", "pago", "pagamento", "gastei", "gasto", "comprei", "compra",
    "recebi", "recebido", "recebimento", "entrada", "saida", "despesa",
    "no", "na", "nos", "nas", "em", "de", "do", "da", "dos", "das",
    "com", "via", "por", "para", "pra", "um", "uma", "o", "a"
}


def contem_palavra_ou_frase(texto, opcoes):

    texto = limpar_texto(texto)
    palavras = set(texto.split())

    for opcao in opcoes:
        opcao = limpar_texto(opcao)
        if " " in opcao and opcao in texto:
            return True
        if opcao in palavras:
            return True

    return False


def extrair_valor_da_mensagem(texto):

    padrao = re.compile(
        r"(?P<sinal>[+-])?\s*(?P<moeda>r\$)?\s*"
        r"(?P<valor>\d{1,3}(?:\.\d{3})+(?:,\d{1,2})?|\d+(?:[.,]\d{1,2})?)",
        re.IGNORECASE
    )
    candidatos = list(padrao.finditer(texto))

    if not candidatos:
        return None, texto, None

    escolhido = None

    for candidato in candidatos:
        if candidato.group("sinal") or candidato.group("moeda"):
            escolhido = candidato
            break

    if escolhido is None and candidatos[0].start() == 0:
        escolhido = candidatos[0]

    if escolhido is None:
        escolhido = candidatos[-1]

    valor = parse_valor(escolhido.group(0))
    texto_sem_valor = f"{texto[:escolhido.start()]} {texto[escolhido.end():]}"
    sinal = escolhido.group("sinal")

    return valor, texto_sem_valor, sinal


def detectar_forma_pagamento(descricao):

    descricao_limpa = limpar_texto(descricao)
    forma_detectada = "Outro"

    for forma, aliases in FORMAS_PAGAMENTO.items():
        for alias in aliases:
            alias_limpo = limpar_texto(alias)
            padrao = r"\b" + re.escape(alias_limpo) + r"\b"

            if re.search(padrao, descricao_limpa):
                forma_detectada = forma
                descricao_limpa = re.sub(padrao, " ", descricao_limpa)
                descricao_limpa = re.sub(r"\s+", " ", descricao_limpa).strip()
                return forma_detectada, descricao_limpa

    return forma_detectada, descricao_limpa


def detectar_tipo_mensagem(descricao, sinal):

    if sinal == "+":
        return "Entrada"

    if sinal == "-":
        return "Saída"

    if eh_entrada_por_descricao(descricao):
        return "Entrada"

    if contem_palavra_ou_frase(descricao, PALAVRAS_SAIDA):
        return "Saída"

    return "Saída"


def padronizar_descricao(descricao):

    texto = limpar_texto(descricao)
    palavras = [
        palavra for palavra in texto.split()
        if palavra not in PALAVRAS_IGNORADAS_DESCRICAO
    ]

    if not palavras:
        return "Sem descrição"

    return " ".join(palavras)


def parse_valor(valor_bruto):

    if isinstance(valor_bruto, (int, float)):
        return float(valor_bruto)

    if valor_bruto is None:
        return 0.0

    texto = str(valor_bruto).strip()

    if not texto:
        return 0.0

    texto = texto.replace("R$", "").replace(" ", "")
    texto = re.sub(r"[^0-9,.\-]", "", texto)

    # CASO tenha vírgula → padrão BR
    if "," in texto:
        texto = texto.replace(".", "")   # remove milhar
        texto = texto.replace(",", ".")  # decimal
    elif "." in texto:
        partes = texto.split(".")
        if len(partes[-1]) == 3 and all(len(parte) <= 3 for parte in partes):
            texto = texto.replace(".", "")

    # CASO não tenha vírgula → já está correto (padrão EUA)
    # NÃO mexe no ponto

    try:
        return float(texto)
    except:
        return 0.0


def normalizar_texto_calculo(texto):

    texto = "" if texto is None else str(texto).strip().lower()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = re.sub(r"[^a-z0-9]", "", texto)

    return texto


def tipo_lancamento(tipo_bruto):

    tipo = normalizar_texto_calculo(tipo_bruto)

    if tipo in ("entrada", "receita"):
        return "Entrada"

    if tipo in ("saida", "sada", "saada", "despesa", "gasto"):
        return "Saida"

    return None


def forma_e_credito(forma_bruta):

    forma = normalizar_texto_calculo(forma_bruta)

    return forma in ("credito", "crdito", "credit", "cc") or "credito" in forma


def valor_lancamento(valor_bruto):

    return abs(parse_valor(valor_bruto))


def campo_registro(registro, nome, indice):

    if isinstance(registro, dict):
        return registro.get(nome, "")

    if len(registro) > indice:
        return registro[indice]

    return ""


def data_no_periodo(data_bruta, periodo_mes_ano):

    data = str(data_bruta).strip()

    if not periodo_mes_ano:
        return True

    try:
        return datetime.strptime(data, "%d/%m/%Y").strftime("%m/%Y") == periodo_mes_ano
    except ValueError:
        return data.endswith(periodo_mes_ano)


def calcular_entradas_saidas(registros, periodo_mes_ano=None):

    entradas = 0.0
    saidas = 0.0

    for registro in registros:

        data = campo_registro(registro, "Data", 0)

        if not data_no_periodo(data, periodo_mes_ano):
            continue

        tipo = tipo_lancamento(campo_registro(registro, "Tipo", 1))
        valor = valor_lancamento(campo_registro(registro, "Valor", 3))

        if tipo == "Entrada":
            entradas += valor
        elif tipo == "Saida":
            saidas += valor

    saldo = entradas - saidas

    return entradas, saidas, saldo


def mes_ano_anterior():

    agora = datetime.now()
    mes = agora.month - 1
    ano = agora.year

    if mes == 0:
        mes = 12
        ano -= 1

    return f"{mes:02d}/{ano}"


def resumo_mes_por_periodo(registros, periodo_mes_ano):
    return calcular_entradas_saidas(registros[1:], periodo_mes_ano)


def gastos_por_descricao_no_periodo(registros, periodo_mes_ano):

    gastos = {}

    for r in registros[1:]:

        if len(r) < 5:
            continue

        data = r[0]
        tipo = r[1]
        valor = parse_valor(r[3])
        descricao = r[4].strip() if r[4] else "Sem descrição"

        if periodo_mes_ano in data and tipo == "Saída":
            if descricao not in gastos:
                gastos[descricao] = 0.0
            gastos[descricao] += valor

    # ordena do maior gasto para o menor
    return dict(sorted(gastos.items(), key=lambda item: item[1], reverse=True))

# ----------------------------
# FUNÇÃO PRINCIPAL
# ----------------------------

async def registrar(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not autorizado(update):
        return

    texto = update.message.text.strip()

    valor, descricao_bruta, sinal = extrair_valor_da_mensagem(texto)

    if valor is None or valor <= 0:
        await update.message.reply_text(
            "Formato inválido.\nExemplos:\n50 mercado debito\nmercado 50 no crédito\n+100 salario\nrecebi R$ 800 pix"
        )
        return

    forma, descricao_sem_forma = detectar_forma_pagamento(descricao_bruta)
    tipo = detectar_tipo_mensagem(descricao_sem_forma, sinal)
    descricao = padronizar_descricao(descricao_sem_forma)
    valor = round(abs(valor), 2)

    data = datetime.now().strftime("%d/%m/%Y")

    categoria = "Receitas" if tipo == "Entrada" else detectar_categoria(descricao)

    sheet.append_row(
        [data, tipo, categoria, float(valor), descricao, forma],
        value_input_option="USER_ENTERED"
    )

    await update.message.reply_text(
        f"Registrado!\n\n"
        f"Tipo: {tipo}\n"
        f"Categoria: {categoria}\n"
        f"Descrição: {descricao}\n"
        f"Forma: {forma}\n"
        f"Valor: R$ {valor:.2f}"
    )

async def saldo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not autorizado(update):
        return

    registros = sheet.get_all_values()

    entradas, saidas, saldo_total = calcular_entradas_saidas(registros[1:])

    await update.message.reply_text(
        f"Saldo atual:\n\n"
        f"Entradas: R$ {entradas:.2f}\n"
        f"Saídas: R$ {saidas:.2f}\n"
        f"Saldo: R$ {saldo_total:.2f}"
    )

from datetime import datetime

async def mes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not autorizado(update):
        return

    registros = sheet.get_all_values()
    mes_atual = datetime.now().strftime("%m/%Y")

    entradas, saidas, saldo_mes = calcular_entradas_saidas(registros[1:], mes_atual)

    await update.message.reply_text(
        f"Resumo do mês:\n\n"
        f"Entradas: R$ {entradas:.2f}\n"
        f"Saídas: R$ {saidas:.2f}\n"
        f"Saldo: R$ {saldo_mes:.2f}"
    )

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


async def subcategorias(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not autorizado(update):
        return

    registros = sheet.get_all_values()
    periodo = datetime.now().strftime("%m/%Y")
    gastos = gastos_por_descricao_no_periodo(registros, periodo)

    if not gastos:
        await update.message.reply_text(f"Nenhum gasto por subcategoria encontrado em {periodo}.")
        return

    mensagem = f"Gastos por subcategoria ({periodo})\n\n"

    for descricao, valor in gastos.items():
        mensagem += f"{descricao}: R$ {valor:.2f}\n"

    await update.message.reply_text(mensagem)


async def subcategoriasanterior(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not autorizado(update):
        return

    registros = sheet.get_all_values()
    periodo = mes_ano_anterior()
    gastos = gastos_por_descricao_no_periodo(registros, periodo)

    if not gastos:
        await update.message.reply_text(f"Nenhum gasto por subcategoria encontrado em {periodo}.")
        return

    mensagem = f"Gastos por subcategoria ({periodo})\n\n"

    for descricao, valor in gastos.items():
        mensagem += f"{descricao}: R$ {valor:.2f}\n"

    await update.message.reply_text(mensagem)

async def categorias(update: Update, context: ContextTypes.DEFAULT_TYPE):

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

async def mesanterior(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not autorizado(update):
        return

    registros = sheet.get_all_values()

    periodo = mes_ano_anterior()

    entradas, saidas, saldo = resumo_mes_por_periodo(registros, periodo)

    await update.message.reply_text(
        f"Resumo do mês anterior ({periodo}):\n\n"
        f"Entradas: R$ {entradas:.2f}\n"
        f"Saídas: R$ {saidas:.2f}\n"
        f"Saldo: R$ {saldo:.2f}"
    )

async def cartao(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not autorizado(update):
        return

    registros = sheet.get_all_values()

    agora = datetime.now()
    mes_atual = agora.strftime("%m/%Y")

    total_credito = 0.0
    quantidade = 0

    for r in registros[1:]:

        if len(r) < 6:
            continue

        data = r[0]
        tipo = tipo_lancamento(r[1])
        valor = valor_lancamento(r[3])

        if data_no_periodo(data, mes_atual) and tipo == "Saida" and forma_e_credito(r[5]):
            total_credito += valor
            quantidade += 1

    await update.message.reply_text(
        f"Gastos no crédito ({mes_atual}):\n\n"
        f"Total: R$ {total_credito:.2f}\n"
        f"Lançamentos: {quantidade}"
    )

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
app.add_handler(CommandHandler("subcategorias", subcategorias))
app.add_handler(CommandHandler("subcategoriasanterior", subcategoriasanterior))
app.add_handler(CommandHandler("hoje", hoje))
app.add_handler(CommandHandler("grafico", grafico))
app.add_handler(CommandHandler("mesgrafico", mesgrafico))
app.add_handler(CommandHandler("ultimos", ultimos))
app.add_handler(CommandHandler("cartao", cartao))
app.add_handler(CommandHandler("apagar", apagar))

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, registrar))

print("Bot rodando...")

app.run_polling()
