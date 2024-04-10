from datetime import datetime, timedelta
from flask import Flask, request, render_template, redirect, url_for, session, jsonify, make_response, send_file
import pymysql
from functools import wraps
from decouple import config
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import landscape, letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageTemplate, Frame
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from io import BytesIO
from reportlab.lib.enums import TA_RIGHT, TA_LEFT, TA_CENTER
import io
import base64
from datetime import date
import matplotlib.pyplot as plt

app = Flask(__name__)
app.secret_key = config('SECRET_KEY')

def conectar_bd():
    return pymysql.connect(
        host=config('MYSQL_HOST'),
        port=int(config('MYSQL_PORT')),
        user=config('MYSQL_USER'),
        password=config('MYSQL_PASSWORD'),
        database=config('MYSQL_DATABASE'),
        cursorclass=pymysql.cursors.DictCursor
    )

def formatar_data(data):
    if data is None:
        return ''  # Retorna uma string vazia se a data for None
    if isinstance(data, str):
        data = datetime.strptime(data, '%Y-%m-%d').date()  # Convertendo a string para objeto de data
    return data.strftime('%d/%m/%Y')  # Formatando a data conforme necessário

# Função para obter os registros de abastecimento por semana
def obter_registros_por_semana(data_inicial_semana, data_final_semana):
    conn = conectar_bd()
    cur = conn.cursor()
    query = "SELECT * FROM amb_abastecimento WHERE data BETWEEN %s AND %s"
    cur.execute(query, (data_inicial_semana, data_final_semana))
    registros = cur.fetchall()
    cur.close()
    conn.close()
    return registros

# Função para calcular os saldos de combustível
def calcular_saldos(data_final_semana):
    conn = conectar_bd()
    cur = conn.cursor()
    
    # Consulta para obter os volumes de entrada de diesel e arla
    query_volume_entrada = "SELECT tipo_combustivel, SUM(volume_entrada) AS volume_entrada FROM amb_combustivel WHERE data_entrada <= %s GROUP BY tipo_combustivel"
    cur.execute(query_volume_entrada, (data_final_semana,))
    resultados_entrada = cur.fetchall()
    
    # Consulta para obter os volumes de saída de diesel e arla
    query_volume_saida = "SELECT tipo_combustivel, SUM(volume_diesel) AS volume_diesel, SUM(volume_arla) AS volume_arla FROM amb_abastecimento WHERE data <= %s GROUP BY tipo_combustivel"
    cur.execute(query_volume_saida, (data_final_semana,))
    resultados_saida = cur.fetchall()
    
    cur.close()
    conn.close()
    
    # Dicionários para armazenar os volumes de entrada e saída de diesel e arla
    volumes_entrada = {'diesel s10': 0, 'arla': 0}
    volumes_saida = {'diesel s10': 0, 'arla': 0}
    
    # Preencher os dicionários com os resultados das consultas
    for resultado in resultados_entrada:
        volumes_entrada[resultado['tipo_combustivel']] = resultado['volume_entrada']
    
    for resultado in resultados_saida:
        volumes_saida[resultado['tipo_combustivel']] = resultado['volume_diesel'] + resultado['volume_arla']
    
    # Calcular os saldos de diesel e arla
    saldo_diesel = volumes_entrada['diesel s10'] - volumes_saida['diesel s10']
    saldo_arla = volumes_entrada['arla'] - volumes_saida['arla']
    
    return saldo_diesel, saldo_arla

def obter_saldo_combustivel(data_abastecimento, tipo_combustivel):
    conn = conectar_bd()
    cur = conn.cursor()

    query_saldo_entrada = "SELECT COALESCE(SUM(volume_entrada), 0) AS saldo_entrada FROM amb_combustivel WHERE tipo_combustivel = %s AND data_entrada <= %s"
    cur.execute(query_saldo_entrada, (tipo_combustivel, data_abastecimento))
    saldo_entrada = float(cur.fetchone()['saldo_entrada'])

    query_saldo_abastecimento = "SELECT COALESCE(SUM(volume_diesel), 0) AS saldo_abastecimento FROM amb_abastecimento WHERE tipo_combustivel = %s"
    cur.execute(query_saldo_abastecimento, (tipo_combustivel,))
    saldo_abastecimento = float(cur.fetchone()['saldo_abastecimento'])

    cur.close()
    conn.close()

    return saldo_entrada - saldo_abastecimento

def obter_saldo_diesel():
    return obter_saldo_combustivel(datetime.now().date(), 'diesel s10')

def obter_saldo_arla():
    conn = conectar_bd()
    cur = conn.cursor()

    # Consulta para obter o saldo total de entrada de ARLA
    query_saldo_entrada = "SELECT COALESCE(SUM(volume_entrada), 0) AS saldo_entrada FROM amb_combustivel WHERE tipo_combustivel = 'arla' AND data_entrada <= %s"
    cur.execute(query_saldo_entrada, (datetime.now().date(),))
    saldo_entrada = float(cur.fetchone()['saldo_entrada'])

    # Consulta para obter o saldo total de saída de ARLA
    query_saldo_saida = "SELECT COALESCE(SUM(volume_arla), 0) AS saldo_saida FROM amb_abastecimento WHERE data <= %s"
    cur.execute(query_saldo_saida, (datetime.now().date(),))
    saldo_saida = float(cur.fetchone()['saldo_saida'])

    cur.close()
    conn.close()

    # Calcular e retornar o saldo atual de ARLA
    saldo_atual_arla = saldo_entrada - saldo_saida
    return saldo_atual_arla

def obter_saldo_etanol():
    return obter_saldo_combustivel(datetime.now().date(), 'etanol')

def verificar_saldo_combustivel(data_abastecimento, tipo_combustivel, volume_abastecimento):
    conn = conectar_bd()
    cur = conn.cursor()

    query_saldo_entrada = "SELECT COALESCE(SUM(volume_entrada), 0) AS saldo_entrada FROM amb_combustivel WHERE tipo_combustivel = %s AND data_entrada <= %s"
    cur.execute(query_saldo_entrada, (tipo_combustivel, data_abastecimento))
    saldo_entrada = float(cur.fetchone()['saldo_entrada'])

    query_saldo_abastecimento = "SELECT COALESCE(SUM(volume_diesel), 0) AS saldo_abastecimento FROM amb_abastecimento WHERE tipo_combustivel = %s"
    if tipo_combustivel == 'arla':
        query_saldo_abastecimento = "SELECT COALESCE(SUM(volume_arla), 0) AS saldo_abastecimento FROM amb_abastecimento WHERE tipo_combustivel = %s"
    elif tipo_combustivel == 'etanol':
        query_saldo_abastecimento = "SELECT COALESCE(SUM(volume_etanol), 0) AS saldo_abastecimento FROM amb_abastecimento WHERE tipo_combustivel = %s"

    cur.execute(query_saldo_abastecimento, (tipo_combustivel,))
    saldo_abastecimento = float(cur.fetchone()['saldo_abastecimento'])

    cur.close()
    conn.close()

    if tipo_combustivel == 'diesel s10':
        return saldo_entrada - saldo_abastecimento - volume_abastecimento >= 0
    elif tipo_combustivel == 'arla':
        return saldo_entrada >= saldo_abastecimento
    elif tipo_combustivel == 'etanol':
        return saldo_entrada >= saldo_abastecimento

def get_combustivel_abastecido(data_abastecimento, tipo_combustivel):
    conn = conectar_bd()
    cur = conn.cursor()

    query_abastecimento = "SELECT COALESCE(SUM(volume_diesel), 0) AS volume_abastecido FROM amb_abastecimento WHERE data <= %s AND tipo_combustivel = %s"
    cur.execute(query_abastecimento, (data_abastecimento, tipo_combustivel))
    volume_abastecido = float(cur.fetchone()['volume_abastecido'])

    cur.close()
    conn.close()

    return volume_abastecido

def get_combustivel_entrada(data_abastecimento, tipo_combustivel):
    conn = conectar_bd()
    cur = conn.cursor()

    query_entrada = "SELECT COALESCE(SUM(volume_entrada), 0) AS volume_entrada FROM amb_combustivel WHERE data_entrada <= %s AND tipo_combustivel = %s"
    cur.execute(query_entrada, (data_abastecimento, tipo_combustivel))
    volume_entrada = float(cur.fetchone()['volume_entrada'])

    cur.close()
    conn.close()

    return volume_entrada

@app.route('/saldo_combustivel', methods=['GET'])
def saldo_combustivel():
    data_abastecimento = datetime.strptime(request.args.get('data'), '%Y-%m-%d').date()
    tipo_combustivel = request.args.get('tipo_combustivel')

    if verificar_saldo_combustivel(data_abastecimento, tipo_combustivel, 0):
        return jsonify({'saldo_disponivel': True})
    else:
        return jsonify({'saldo_disponivel': False})

# Rota de login
@app.route('/login', methods=['GET', 'POST'])
def mostrar_login(error_message=None):
    if request.method == 'POST':
        # Recebe os dados de login do formulário
        dados_login = request.form
        user_name = dados_login['user_name']
        senha = dados_login['senha']

        # Conecta ao banco de dados
        conn = conectar_bd()
        cur = conn.cursor()

        # Executa a consulta SQL para verificar as credenciais do usuário
        cur.execute("SELECT * FROM amb_usuarios WHERE user_name = %s AND senha = %s", (user_name, senha))

        # Obtém o resultado da consulta
        usuario = cur.fetchone()

        # Fecha o cursor e a conexão
        cur.close()
        conn.close()

        # Verifica se o usuário foi encontrado no banco de dados
        if usuario:
            # Se o usuário foi encontrado, armazena seu ID na sessão para indicar autenticação
            session['usuario_id'] = usuario['id_usuario']
            # Redireciona para a página inicial
            return redirect(url_for('pagina_inicial'))
        else:
            # Se o usuário não foi encontrado, retorna uma resposta de erro
            error_message = "Usuário ou senha incorreto."

    return render_template('login.html', error_message=error_message)

# Rota para a página inicial (requer autenticação)
@app.route('/')
def pagina_inicial():
    # Verifica se o usuário está autenticado
    if 'usuario_id' not in session:
        # Se não estiver autenticado, redireciona para a página de login
        return redirect(url_for('mostrar_login'))
    return render_template('pagina_inicial.html')

@app.route('/cadastrar_abastecimento', methods=['POST'])
def cadastrar_abastecimento():
    data = request.form['data']
    data_abastecimento = datetime.strptime(data, '%Y-%m-%d').date()  # Convertendo para objeto datetime.date
    placa = request.form['placa']
    posto = request.form['posto']
    km = float(request.form['km'])
    tipo_combustivel = request.form['tipo_combustivel']
    horimetro_veiculo = float(request.form['horimetro_veiculo'])
    volume_diesel = float(request.form.get('volume_diesel', 0))
    volume_arla = float(request.form.get('volume_arla', 0))
    volume_etanol = float(request.form.get('volume_etanol', 0))
    preco_litro = float(request.form['preco_unitario'])
    filial = request.form['filial']

    # Verifica se o horímetro e a quilometragem são maiores ou iguais aos últimos registrados para o veículo
    conn = conectar_bd()
    cur = conn.cursor()
    cur.execute("SELECT km, horimetro_veiculo FROM amb_abastecimento WHERE placa = %s ORDER BY id_abastecimento DESC LIMIT 1", (placa,))
    ultimo_registro = cur.fetchone()
    cur.close()
    conn.close()

    if ultimo_registro:
        ultimo_km = ultimo_registro['km']
        ultimo_horimetro_veiculo = ultimo_registro['horimetro_veiculo']

        if km < ultimo_km:
            error_message = "Quilometragem informada é menor que o último registro."
            app.logger.error(f"Quilometragem informada ({km}) é menor que o último registro ({ultimo_km}) para a placa {placa}.")
            return redirect(url_for('gerenciar_combustivel', error_message=error_message))

        if horimetro_veiculo < ultimo_horimetro_veiculo:
            error_message = "Horímetro do veículo informado é menor que o último registro."
            app.logger.error(f"Horímetro do veículo informado ({horimetro_veiculo}) é menor que o último registro ({ultimo_horimetro_veiculo}) para a placa {placa}.")
            return redirect(url_for('gerenciar_combustivel', error_message=error_message))

    # Define o valor do horímetro inicial fixo para o primeiro abastecimento
    horimetro_inicial_fixo = 1000  # Substitua pelo valor fixo desejado

    # Define as variáveis horimetro_inicial_comboio e horimetro_final_comboio
    horimetro_inicial_comboio = request.form.get('horimetro_inicial_comboio', horimetro_inicial_fixo)
    horimetro_final_comboio = request.form.get('horimetro_final_comboio', None)

    # Log dos valores recebidos do formulário
    app.logger.info(f'Horímetro Inicial: {horimetro_inicial_comboio}')
    app.logger.info(f'Horímetro Final: {horimetro_final_comboio}')

    if request.method == 'POST':
        # Convertendo horimetro_inicial_comboio para float
        horimetro_inicial_comboio = float(horimetro_inicial_comboio)

        # Verificando se o horímetro final foi informado e tratando o valor
        if horimetro_final_comboio is not None and horimetro_final_comboio != '':
            horimetro_final_comboio = float(horimetro_final_comboio)
        else:
            horimetro_final_comboio = None

        # Verifica se o horímetro final da bomba é menor que o horímetro inicial
        if horimetro_final_comboio is not None:
            if horimetro_final_comboio < horimetro_inicial_comboio:
                error_message = "Horímetro final da bomba não pode ser menor que o horímetro inicial."
                app.logger.error(error_message)
                return redirect(url_for('gerenciar_combustivel', error_message=error_message))

        # Calcula o volume de diesel com base nos horímetros
        if horimetro_final_comboio is not None:
            volume_diesel = max(horimetro_final_comboio - horimetro_inicial_comboio, 0)  # Garante que o volume não seja negativo
        else:
            volume_diesel = None

        # Verifica saldo de diesel
        if not verificar_saldo_combustivel(data_abastecimento, tipo_combustivel, volume_diesel):
            return redirect(url_for('gerenciar_combustivel', error_message=f"Saldo Insuficiente. Não foi possível registrar o abastecimento"))
        
        # Insere os dados na tabela de abastecimento
        conn = conectar_bd()
        cur = conn.cursor()
        cur.execute("INSERT INTO amb_abastecimento (data, placa, posto, km, tipo_combustivel, horimetro_veiculo, horimetro_inicial_comboio, horimetro_final_comboio, volume_diesel, volume_arla, volume_etanol, preco_litro, filial) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", (data_abastecimento, placa, posto, km, tipo_combustivel, horimetro_veiculo, horimetro_inicial_comboio, horimetro_final_comboio, volume_diesel, volume_arla, volume_etanol, preco_litro, filial))
        conn.commit()
        cur.close()
        conn.close()
        
        success_message = "Abastecimento cadastrado com sucesso."
        app.logger.info(success_message)
        return redirect(url_for('gerenciar_combustivel', success_message=success_message))

@app.route('/gerenciar_combustivel')
def gerenciar_combustivel():
    # Verifica se o usuário está autenticado
    if 'usuario_id' not in session:
        # Se não estiver autenticado, redireciona para a página de login
        return redirect(url_for('mostrar_login'))

    conn = conectar_bd()
    cur = conn.cursor()
    cur.execute("SELECT * FROM amb_abastecimento ORDER BY data DESC LIMIT 20")  # Seleciona todos os registros de abastecimento ordenados por data crescente
    abastecimentos = cur.fetchall()  # Recupera todos os registros
    cur.execute("SELECT placa FROM amb_veiculos")
    placas = cur.fetchall()
    cur.execute("SELECT filial FROM amb_filial")
    filiais = cur.fetchall()
    cur.close()
    conn.close()
    success_message = request.args.get('success_message')
    error_message = request.args.get('error_message')
    saldo_diesel = obter_saldo_diesel()
    saldo_arla = obter_saldo_arla()
    saldo_etanol = obter_saldo_etanol()

    return render_template('gerenciar_combustivel.html', abastecimentos=abastecimentos, placas=placas, filiais=filiais, success_message=success_message, error_message=error_message, saldo_diesel=saldo_diesel, saldo_arla=saldo_arla, saldo_etanol=saldo_etanol, formatar_data=formatar_data)


@app.route('/obter_ultimo_horimetro_diesel')
def obter_ultimo_horimetro_diesel():
    conn = conectar_bd()
    cur = conn.cursor()
    cur.execute("SELECT horimetro_final_comboio FROM amb_abastecimento WHERE tipo_combustivel = 'diesel s10' ORDER BY id_abastecimento DESC LIMIT 1")
    ultimo_horimetro = cur.fetchone()
    cur.close()
    conn.close()
    return jsonify(ultimo_horimetro)

@app.route('/cadastrar_entrada_combustivel', methods=['POST'])
def cadastrar_entrada_combustivel():
    data_entrada = request.form['data_entrada_combustivel']
    posto_combustivel = request.form['posto_combustivel']
    local_entrada = request.form['local_entrada']
    tipo_combustivel = request.form['tipo_combustivel_entrada']
    volume_entrada = float(request.form['volume_entrada_combustivel'])
    filial = request.form['filial_entrada_combustivel']
    preco_litro = float(request.form['preco_unitario'])
    conn = conectar_bd()
    cur = conn.cursor()
    cur.execute("INSERT INTO amb_combustivel (data_entrada, posto_combustivel, local_entrada, tipo_combustivel, volume_entrada, filial, preco_litro) VALUES (%s, %s, %s, %s, %s, %s, %s)", (data_entrada, posto_combustivel, local_entrada, tipo_combustivel, volume_entrada, filial, preco_litro))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('gerenciar_combustivel', success_message="Entrada de combustível cadastrada com sucesso!"))

##GERAR PDF ABASTECIMENTO
# Contador global de páginas
global numero_pagina

# Inicialização da variável
numero_pagina = 1

def construir_tabela_registros(registros):
    header = ["Data", "Placa", "Km", "Horímetro do\nVeículo", "Tipo de\nCombustível", "Horímetro\nInicial Comboio", "Horímetro\nFinal Comboio", "Volume\nAbastecido (L)", "Assinatura\nAbastecedor"]
    data = [header]
    for registro in registros:
        volume_total = registro['volume_diesel'] + registro['volume_arla']
        data.append([
            registro['data'].strftime('%d/%m/%Y'), 
            registro['placa'], 
            registro['km'], 
            registro['horimetro_veiculo'], 
            registro['tipo_combustivel'], 
            registro['horimetro_inicial_comboio'], 
            registro['horimetro_final_comboio'], 
            volume_total,
            registro.get('assinatura_abastecedor', '')
        ])
    table = Table(data)
    return table

def adicionar_estilo_tabela(table):
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#E1E9EC')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('INNERGRID', (0, 0), (-1, -1), 1, colors.black),
    ])
    table.setStyle(style)
    return table

def rodape(canvas, doc):
    global numero_pagina
    estilo_rodape = ParagraphStyle(
        name='RodapeEstilo',
        fontSize=8,
        alignment=TA_RIGHT
    )

    estilo_assinatura = ParagraphStyle(
        name='AssinaturaEstilo',
        fontSize=10,
        alignment=TA_LEFT
    )

    largura_pagina, altura_pagina = canvas._pagesize

    data_hora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    texto_rodape = f"Relatório gerado em: {data_hora} - Página {numero_pagina}"
    p_rodape = Paragraph(texto_rodape, estilo_rodape)

    assinatura_gerente = "Assinatura do Gerente/Supervisor: __________________________"
    p_assinatura = Paragraph(assinatura_gerente, estilo_assinatura)

    largura_texto_rodape, _ = p_rodape.wrap(largura_pagina, 0)
    largura_assinatura_gerente, _ = p_assinatura.wrap(largura_pagina, 0)

    p_rodape.drawOn(canvas, largura_pagina - largura_texto_rodape - 30, 20)
    p_assinatura.drawOn(canvas, 30, 20)

    # Incrementar o contador de páginas
    numero_pagina += 1

@app.route('/gerar_relatorio_pdf', methods=['GET', 'POST'])
def gerar_relatorio_pdf():
    if request.method == 'POST':
        data_string = request.form['data']
        data_atual = datetime.strptime(data_string, '%Y-%m-%d')
    else:
        data_atual = datetime.now()
    data_inicial_semana = (data_atual - timedelta(days=data_atual.weekday())).date()
    data_final_semana = data_inicial_semana + timedelta(days=6)
    registros_semana = obter_registros_por_semana(data_inicial_semana, data_final_semana)
    saldo_diesel, saldo_arla = calcular_saldos(data_final_semana.strftime('%Y-%m-%d'))
    consumo_diesel = sum(registro.get('volume_diesel', 0) or 0 for registro in registros_semana)
    consumo_arla = sum(registro.get('volume_arla', 0) or 0 for registro in registros_semana)
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter), leftMargin=30, rightMargin=30, topMargin=20, bottomMargin=50)  # Adjusted margins
    elements = []
    
    estilo_texto = ParagraphStyle(
        name='estilo_texto',
        fontName='Helvetica',
        fontSize=12,
        textColor=colors.black
    )

    estilo_titulo = ParagraphStyle(
        name='estilo_titulo',
        fontName='Helvetica-Bold',
        fontSize=16,
        alignment=TA_LEFT
    )

    titulo = Paragraph(f"<b>Relatório Semanal de Abastecimento</b><br/>({data_inicial_semana.strftime('%d/%m/%Y')} - {data_final_semana.strftime('%d/%m/%Y')})", estilo_titulo)
    elements.append(titulo)

    elements.append(Spacer(1, 20))

    table_data = [["Data", "Placa", "Km", "Horímetro do\nVeículo", "Tipo de\nCombustível", "Horímetro\nInicial Comboio", "Horímetro\nFinal Comboio", "Volume\nAbastecido (L)", "Assinatura\nAbastecedor"]]

    col_widths = [doc.width / len(table_data[0])] * len(table_data[0])
    row_height = 25  # Adjusted row height

    for registro in registros_semana:
        volume_diesel = registro.get('volume_diesel', 0) or 0
        volume_arla = registro.get('volume_arla', 0) or 0
        table_data.append([
            registro['data'].strftime('%d/%m/%Y'), 
            registro['placa'], 
            registro['km'], 
            registro['horimetro_veiculo'], 
            registro['tipo_combustivel'], 
            registro['horimetro_inicial_comboio'], 
            registro['horimetro_final_comboio'], 
            volume_diesel + volume_arla, 
            registro.get('assinatura_abastecedor', '')
        ])
    
    table = Table(table_data, colWidths=col_widths, rowHeights=row_height)
    table.setStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#CCCCCC')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
    ])
    elements.append(table)

    elements.append(Spacer(1, 20))

    estilo_caixa_destaque = ParagraphStyle(
        name='estilo_caixa_destaque',
        fontSize=15,
        textColor=colors.black,
        borderWidth=2,
        borderColor=colors.blue,
        borderPadding=8,
        borderRadius=8,
        backgroundColor=colors.lightgrey,
        shadowColor=colors.grey,
        shadowOffsetX=5,
        shadowOffsetY=5,
        width=80,
        height=100,
        alignment=TA_LEFT,
    )

    cor_texto_diesel = colors.red if saldo_diesel < 200 else colors.green
    cor_texto_arla = colors.red if saldo_arla < 10 else colors.green

    elements.append(Spacer(1, 50))
    elements.append(Paragraph(f"<b>Saldo Diesel:</b> <font color='{cor_texto_diesel}'>{saldo_diesel}</font> L", estilo_caixa_destaque))
    elements.append(Spacer(2, 20))
    elements.append(Paragraph(f"<b>Saldo Arla:</b> <font color='{cor_texto_arla}'>{saldo_arla}</font> L", estilo_caixa_destaque))
    elements.append(Spacer(1, 10))
    
    elements.append(Paragraph(f"<b>Consumo Diesel na Semana:</b> {consumo_diesel} L | <b>Consumo Arla na Semana:</b> {consumo_arla} L", estilo_texto))

    frame1 = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height - 50, id='normal')
    template = PageTemplate(id='all_pages', frames=[frame1], onPage=rodape)
    doc.addPageTemplates([template])

    doc.build(elements)

    buffer.seek(0)
    return send_file(buffer, as_attachment=True, mimetype='application/pdf', download_name='relatorio_abastecimento_semanal.pdf')

##REVISÃO
# Função para calcular a média de horímetro por dia com base nos últimos cinco abastecimentos
def calcular_media_horimetro_por_dia(abastecimentos):
    # Verificar se existem pelo menos cinco abastecimentos
    if len(abastecimentos) < 5:
        return None
    
    # Filtrar os abastecimentos para garantir datas distintas
    datas = set()
    abastecimentos_distintos = []
    for abastecimento in reversed(abastecimentos):
        if abastecimento['data'] not in datas:
            abastecimentos_distintos.append(abastecimento)
            datas.add(abastecimento['data'])
        if len(abastecimentos_distintos) == 5:
            break
    
    # Verificar se há pelo menos cinco abastecimentos com datas distintas
    if len(abastecimentos_distintos) < 5:
        return None
    
    # Calcular o horímetro gasto entre o último e o terceiro abastecimento
    horimetro_gasto = abastecimentos_distintos[0]['horimetro_veiculo'] - abastecimentos_distintos[-1]['horimetro_veiculo']
    
    # Calcular o total de dias entre o último e o terceiro abastecimento
    total_dias = (abastecimentos_distintos[0]['data'] - abastecimentos_distintos[-1]['data']).days
    
    # Verificar se total_dias é maior que zero para evitar a divisão por zero
    if total_dias > 0:
        # Calcular a média de horímetro por dia
        media_dia = horimetro_gasto / total_dias
        return media_dia
    else:
        return None
# Função para calcular a previsão da próxima revisão com base nos últimos três abastecimentos
def calcular_previsao_proxima_revisao(abastecimentos, horimetro_atual, horimetro_prox_rev):
    # Calcular a média de horímetro por dia
    media_horimetro_dia = calcular_media_horimetro_por_dia(abastecimentos)
    
    # Verificar se foi possível calcular a média de horímetro por dia
    if media_horimetro_dia is None or media_horimetro_dia == 0:
        return None, None
    
    # Calcular o horímetro restante até a próxima revisão
    horimetro_restante = horimetro_prox_rev - horimetro_atual
    
    # Calcular os dias restantes até a próxima revisão
    dias_prox_rev = horimetro_restante / media_horimetro_dia
    
    # Calcular a previsão da próxima revisão
    previsao = abastecimentos[-1]['data'] + timedelta(days=int(dias_prox_rev))
    
    # Calcular o status
    if horimetro_atual > horimetro_prox_rev:
        status = 'Vencido'
    else:
        status = 'Em dia'
    
    return previsao, status

@app.route('/revisao')
def revisao():
    # Verifica se o usuário está autenticado
    if 'usuario_id' not in session:
        # Se não estiver autenticado, redireciona para a página de login
        return redirect(url_for('mostrar_login'))
    # Conectar ao banco de dados
    conn = conectar_bd()
    cur = conn.cursor()

    # Consulta para buscar as placas de veículos disponíveis na tabela amb_veiculos
    cur.execute("SELECT placa FROM amb_veiculos")

    # Buscar todas as placas
    placas_result = cur.fetchall()
    placas = [row['placa'] for row in placas_result]

    # Consulta para buscar os abastecimentos do banco de dados
    cur.execute("SELECT * FROM amb_abastecimento")
    abastecimentos_result = cur.fetchall()

    # Transformar os resultados em uma lista de dicionários
    abastecimentos = []
    for row in abastecimentos_result:
        abastecimentos.append({
            'data': row['data'],
            'placa': row['placa'],
            'horimetro_veiculo': row['horimetro_veiculo']
            # Adicione mais campos se necessário
        })

    # Query para buscar as informações necessárias da tabela amb_veiculos
    cur.execute("""SELECT 
                            v.placa, 
                            v.frota, 
                            v.tipo_veiculo, 
                            v.status_atual,
                            COALESCE(a.data, 'Nulo') AS data_atualizacao,  -- Adicionando a coluna de data de atualização
                            COALESCE(a.horimetro_veiculo, 0) AS horimetro_atual, 
                            COALESCE(r.horimetro_rev, 0) AS horimetro_ultima_rev,
                            COALESCE(r.horimetro_prox_rev, 0) AS horimetro_prox_rev,
                            (COALESCE(r.horimetro_prox_rev, 0) - COALESCE(a.horimetro_veiculo, 0)) AS horimetro_restante,
                            (COALESCE(r.horimetro_prox_rev, 0) - COALESCE(a.horimetro_veiculo, 0)) - COALESCE(r.horimetro_prox_rev, 0) AS diferenca_horimetros
                            FROM amb_veiculos AS v
                            LEFT JOIN (
                                SELECT placa, MAX(data) AS data, MAX(horimetro_veiculo) AS horimetro_veiculo
                                FROM amb_abastecimento
                                GROUP BY placa
                            ) AS a ON v.placa = a.placa
                            LEFT JOIN (
                                SELECT placa, MAX(id_revisao) AS ultimo_id_revisao
                                FROM amb_revisao
                                GROUP BY placa
                            ) AS ultima_revisao ON v.placa = ultima_revisao.placa
                            LEFT JOIN amb_revisao AS r ON ultima_revisao.ultimo_id_revisao = r.id_revisao
                            WHERE v.status_atual = 'ATIVO'
                            ORDER BY v.placa ASC;""")

    # Fetch all rows
    revisoes = cur.fetchall()

    # Calcular o status e a previsão da próxima revisão para cada revisão
    for revisao in revisoes:
        if revisao['status_atual'] == 'ATIVO':
            # Filtrar os abastecimentos para o veículo correspondente à revisão
            abastecimentos_veiculo = [abastecimento for abastecimento in abastecimentos if abastecimento['placa'] == revisao['placa']]

            # Calcular a média de horímetro por dia
            media_horimetro_dia = calcular_media_horimetro_por_dia(abastecimentos_veiculo)
            
            # Verificar se a média foi calculada com sucesso
            if media_horimetro_dia is not None:
                # Ordenar os abastecimentos por data
                abastecimentos_veiculo.sort(key=lambda x: x['data'])
                
                # Calcular a previsão da próxima revisão com base nos últimos três abastecimentos
                previsao_proxima_revisao, status = calcular_previsao_proxima_revisao(abastecimentos_veiculo, revisao['horimetro_atual'], revisao['horimetro_prox_rev'])
                
                # Verificar se a previsão é None
                if previsao_proxima_revisao is None:
                    previsao_proxima_revisao = 'Nulo'  # Ou qualquer outro valor que você queira usar para representar "Nulo"
                    status = 'Nulo'  # Define também o status como "Nulo" neste caso
                
                # Definir a previsão da próxima revisão, o status e a média de horímetro por dia no dicionário da revisão
                revisao['previsao_proxima_revisao'] = previsao_proxima_revisao
                revisao['status'] = status
                revisao['media_horimetro_dia'] = media_horimetro_dia
            else:
                # Se a média não pôde ser calculada, defina um valor padrão
                revisao['media_horimetro_dia'] = 'N/A'  # Ou qualquer outro valor que você queira usar para indicar que a média não está disponível

    # Fechar cursor e conexão
    cur.close()
    conn.close()

    return render_template('revisao.html', revisoes=revisoes, placas=placas, formatar_data=formatar_data)

# Rota para obter informações do veículo com base na placa selecionada
@app.route('/obter_informacoes_veiculo', methods=['POST'])
def obter_informacoes_veiculo():
    placa = request.form['placa']
    conn = conectar_bd()
    cur = conn.cursor()
    cur.execute("SELECT * FROM amb_veiculos WHERE placa = %s", (placa,))
    veiculo = cur.fetchone()
    cur.close()
    conn.close()
    return jsonify(veiculo)

# Rota para lançar a revisão
@app.route('/cadastrar_revisao', methods=['POST'])
def lancar_revisao():
    # Limpar a mensagem da sessão, se existir
    session.pop('mensagem', None)
    # Obter os dados do formulário
    id_veiculo = request.form['id_veiculo']
    placa = request.form['placa']
    frota = request.form['frota']
    tipo_veiculo = request.form['tipo_veiculo']
    marca_modelo = request.form['marca_modelo']
    data_rev = request.form['data_rev']
    horimetro_rev = request.form['horimetro_rev']
    horimetro_prox_rev = request.form['horimetro_prox_rev']
    
    # Conectar ao banco de dados
    conn = conectar_bd()
    cur = conn.cursor()

    # Inserir os dados na tabela amb_revisao
    try:
        print("Dados do formulário:")
        print("Veículo ID:", id_veiculo)
        print("Placa:", placa)
        print("Frota:", frota)
        print("Tipo de Veículo:", tipo_veiculo)
        print("Marca e Modelo:", marca_modelo)
        print("Data da Revisão:", data_rev)
        print("Horímetro da Revisão:", horimetro_rev)
        print("Horímetro Próxima Revisão:", horimetro_prox_rev)

        cur.execute("INSERT INTO amb_revisao (id_veiculo, placa, frota, tipo_veiculo, marca_modelo, data_rev, horimetro_rev, horimetro_prox_rev) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)", (id_veiculo, placa, frota, tipo_veiculo, marca_modelo, data_rev, horimetro_rev, horimetro_prox_rev))
        conn.commit()
        session['mensagem'] = 'Lançado com Sucesso!'
    except Exception as e:
        conn.rollback()
        session['mensagem'] = f'Erro ao lançar revisão: {str(e)}'
    finally:
        cur.close()
        conn.close()

    # Redirecionar de volta para a página de revisão
    return redirect(url_for('revisao'))

#RH
# Rota para a página de RH
@app.route('/rh')
def rh():
    # Verifica se o usuário está autenticado
    if 'usuario_id' not in session:
        # Se não estiver autenticado, redireciona para a página de login
        return redirect(url_for('mostrar_login'))
    # Consulta SQL para obter o número de funcionários para cada cargo
    conn = conectar_bd()
    cur = conn.cursor()
    cur.execute("SELECT cargo, COUNT(*) AS quantidade FROM amb_funcionarios WHERE dt_desligamento IS NULL GROUP BY cargo")
    dados_cargos = cur.fetchall()

    # Consulta SQL para obter o número de funcionários por segmento
    cur.execute("SELECT segmento, COUNT(*) AS quantidade FROM amb_funcionarios WHERE dt_desligamento IS NULL GROUP BY segmento")
    dados_segmentos = cur.fetchall()

    # Ordenar os dados pelo número de funcionários em ordem crescente
    dados_cargos = sorted(dados_cargos, key=lambda x: x['quantidade'])

    # Dentro da função rh()
    # Obter o mês selecionado pelo usuário
    mes_selecionado = request.args.get('mes')  # Você precisa adicionar a importação adequada do request no topo do seu arquivo
    if not mes_selecionado:
        mes_selecionado = date.today().month

    # Consultar aniversariantes do mês selecionado
    cur.execute("SELECT nome_funcionario, dt_nascimento FROM amb_funcionarios WHERE MONTH(dt_nascimento) = %s", (mes_selecionado,))
    aniversariantes_mes = cur.fetchall()

    # Consulta SQL para obter todos os colaboradores
    cur.execute("SELECT * FROM amb_funcionarios WHERE dt_desligamento IS NULL")
    colaboradores = cur.fetchall()

    # Consulta SQL para calcular o número total de funcionários CONTRATADOS NO ANO DE 2024
    cur.execute("SELECT COUNT(*) AS quantidade FROM amb_funcionarios WHERE YEAR(dt_admissao) = 2024")
    total_funcionarios_contratados = cur.fetchone()['quantidade']
    
    # Consulta SQL para calcular o número total de funcionários DESLIGADOS NO ANO DE 2024
    cur.execute("SELECT COUNT(*) AS quantidade FROM amb_funcionarios WHERE YEAR(dt_desligamento) = 2024")
    total_funcionarios_desligados = cur.fetchone()['quantidade']

    # Consultas SQL para calcular o número de funcionários por faixa etária
    cur.execute("SELECT COUNT(*) AS quantidade FROM amb_funcionarios WHERE dt_desligamento IS NULL AND TIMESTAMPDIFF(YEAR, dt_nascimento, CURDATE()) BETWEEN 18 AND 28")
    result = cur.fetchone()
    print("Resultado da consulta:", result)  # Debug
    if result:
        funcionarios_18_28 = result['quantidade']
    else:
        funcionarios_18_28 = 0  # Ou qualquer outro valor padrão que você preferir
    
    # Consultas SQL para calcular o número de funcionários por faixa etária
    cur.execute("SELECT COUNT(*) AS quantidade FROM amb_funcionarios WHERE dt_desligamento IS NULL AND TIMESTAMPDIFF(YEAR, dt_nascimento, CURDATE()) BETWEEN 29 AND 39")
    result = cur.fetchone()
    print("Resultado da consulta:", result)  # Debug
    if result:
        funcionarios_29_39 = result['quantidade']
    else:
        funcionarios_29_39 = 0  # Ou qualquer outro valor padrão que você preferir

    # Consultas SQL para calcular o número de funcionários por faixa etária
    cur.execute("SELECT COUNT(*) AS quantidade FROM amb_funcionarios WHERE dt_desligamento IS NULL AND TIMESTAMPDIFF(YEAR, dt_nascimento, CURDATE()) BETWEEN 40 AND 50")
    result = cur.fetchone()
    print("Resultado da consulta:", result)  # Debug
    if result:
        funcionarios_40_50 = result['quantidade']
    else:
        funcionarios_40_50 = 0  # Ou qualquer outro valor padrão que você preferir

    # Consultas SQL para calcular o número de funcionários por faixa etária
    cur.execute("SELECT COUNT(*) AS quantidade FROM amb_funcionarios WHERE dt_desligamento IS NULL AND TIMESTAMPDIFF(YEAR, dt_nascimento, CURDATE()) BETWEEN 51 AND 150")
    result = cur.fetchone()
    print("Resultado da consulta:", result)  # Debug
    if result:
        funcionarios_51_a_cima = result['quantidade']
    else:
        funcionarios_51_a_cima = 0  # Ou qualquer outro valor padrão que você preferir

    # Calcula o número total de funcionários
    total_funcionarios = sum([funcionarios_18_28, funcionarios_29_39, funcionarios_40_50, funcionarios_51_a_cima])  # Adicione as outras faixas etárias conforme necessário

    # Calcular o Turnover
    if total_funcionarios > 0:
        turnover = (((total_funcionarios_desligados + total_funcionarios_contratados) / 2) / total_funcionarios) * 100
    else:
        turnover = 0

    # Calcula o máximo entre as faixas etárias
    max_funcionarios = max(funcionarios_18_28, funcionarios_29_39, funcionarios_40_50, funcionarios_51_a_cima)

    # Calcula as proporções das faixas etárias
    total = funcionarios_18_28 + funcionarios_29_39 + funcionarios_40_50 + funcionarios_51_a_cima
    if total > 0:
        prop_18_28 = (funcionarios_18_28 / total) * 100
        prop_29_39 = (funcionarios_29_39 / total) * 100
        prop_40_50 = (funcionarios_40_50 / total) * 100
        prop_51_a_cima = (funcionarios_51_a_cima / total) * 100
        
    else:
        prop_18_28 = prop_29_39 = prop_40_50 = prop_51_a_cima = 0  # Caso não haja funcionários

    return render_template('rh.html', dados_cargos=dados_cargos, dados_segmentos=dados_segmentos, colaboradores=colaboradores, max_funcionarios=max_funcionarios, total_funcionarios=total_funcionarios, formatar_data=formatar_data, funcionarios_18_28=funcionarios_18_28, funcionarios_29_39=funcionarios_29_39, funcionarios_40_50=funcionarios_40_50, funcionarios_51_a_cima=funcionarios_51_a_cima , prop_18_28=prop_18_28, prop_29_39=prop_29_39, prop_40_50=prop_40_50, prop_51_a_cima=prop_51_a_cima, aniversariantes_mes=aniversariantes_mes, total_funcionarios_desligados=total_funcionarios_desligados, total_funcionarios_contratados=total_funcionarios_contratados, turnover=turnover)

# Rota para cadastrar um novo colaborador
@app.route('/cadastrar_colaborador', methods=['POST'])
def cadastrar_colaborador():
    conn = conectar_bd()
    cur = conn.cursor()
    if request.method == 'POST':
        matricula = request.form['matricula']
        nome = request.form['nome'].upper()
        cpf = request.form['cpf']
        cargo = request.form['cargo'].upper()
        filial = request.form['filial'].upper()
        segmento = request.form['segmento'].upper()
        dt_nascimento = request.form['dt_nascimento']
        dt_admissao = request.form['dt_admissao']
        dt_desligamento = request.form.get('dt_desligamento')  # Obter a data de desligamento, se preenchida
        venc_aso = request.form['venc_aso']
        cidade_residencia = request.form['cidade_residencia'].upper()
        estado = request.form['estado'].upper()

        # Se o campo de data de desligamento não estiver preenchido, definir como Null
        if not dt_desligamento:
            dt_desligamento = None

        # Determinar quais campos de vencimento são obrigatórios com base no cargo
        campos_obrigatorios = ['venc_aso', 'venc_nr20', 'venc_nr35', 'venc_pri_socorros', 'venc_com_incendios']
        if cargo.startswith("MOTORISTA"):
            campos_obrigatorios.extend(['venc_dir_defensiva', 'venc_mop'])
        elif cargo.startswith("AJUDANTE"):
            campos_obrigatorios.extend(['venc_man_prod_quimicos', 'venc_rigger'])

        # Verificar se o cargo é 'AJUDANTE' para definir o valor de venc_cnh
        if not cargo.startswith("AJUDANTE"):
            venc_cnh = request.form['venc_cnh']
        else:
            venc_cnh = None

        # Inserir os dados na tabela do banco de dados
        sql = "INSERT INTO amb_funcionarios (matricula, nome_funcionario, cpf, cargo, filial, segmento, dt_nascimento, dt_admissao, dt_desligamento, venc_cnh, cidade_residencia, estado"
        sql += ", " + ", ".join(campos_obrigatorios)  # Adicionar campos obrigatórios à consulta SQL
        sql += ") VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s"
        sql += ", %s" * len(campos_obrigatorios)  # Adicionar marcadores de posição para os valores
        sql += ")"

        # Definir os valores para a consulta SQL
        val = [matricula, nome, cpf, cargo, filial, segmento, dt_nascimento, dt_admissao, dt_desligamento, venc_cnh, cidade_residencia, estado]
        for campo in campos_obrigatorios:
            val.append(request.form[campo])

        cur.execute(sql, val)
        conn.commit()

        return redirect(url_for('rh'))
    

# Rota para atualizar o cadastro de funcionários
@app.route('/atualizar_cadastro', methods=['POST'])
def atualizar_cadastro():
    conn = conectar_bd()
    cur = conn.cursor()
    
    if request.method == 'POST':
        # Obter os dados do formulário
        colaboradores_selecionados = request.form.getlist('colaboradores')
        data_vencimento = request.form['data_vencimento']
        campo_atualizacao = request.form['campo_atualizacao']
        
        # Mapeamento entre o campo de atualização e o campo correspondente no banco de dados
        campos_documento = {
            'CNH': 'venc_cnh', 'ASO': 'venc_aso', 'MOP': 'venc_mop', 'Direção Defensiva': 'venc_dir_defensiva', 'NR20': 'venc_nr20', 'NR35': 'venc_nr35',
            'Primeiro Socorros': 'venc_pri_socorros', 'Combate Incêndios': 'venc_com_incendios', 'Manuseio Produtos Químicos': 'venc_man_prod_quimicos',
            'Rigger': 'venc_rigger',
            # Adicione outros tipos de documento aqui conforme necessário
        }
        
        # Verificar se o campo de atualização corresponde a um tipo de documento
        if campo_atualizacao in campos_documento:
            campo_bd = campos_documento[campo_atualizacao]
            # Atualizar os campos para os colaboradores selecionados
            for colaborador in colaboradores_selecionados:
                sql = f"UPDATE amb_funcionarios SET {campo_bd} = %s WHERE nome_funcionario = %s"
                cur.execute(sql, (data_vencimento, colaborador))
        else:
            # Se o campo de atualização não for um tipo de documento, atualize diretamente
            for colaborador in colaboradores_selecionados:
                sql = f"UPDATE amb_funcionarios SET {campo_atualizacao} = %s WHERE nome_funcionario = %s"
                cur.execute(sql, (data_vencimento, colaborador))

        conn.commit()
        conn.close()

        return redirect(url_for('rh'))
    

#FATURAMENTO
# Função para obter a lista de competências
def obter_competencias():
    try:
        # Conectar ao banco de dados
        conn = conectar_bd()
        cur = conn.cursor()

        # Consultar as competências distintas na tabela amb_faturamento
        cur.execute("SELECT DISTINCT DATE_FORMAT(competencia, '%b/%Y') AS competencia_formatada FROM amb_faturamento ORDER BY competencia_formatada DESC")
        competencias = cur.fetchall()

        # Extrair apenas as competências da lista de tuplas
        competencias = [competencia['competencia_formatada'] for competencia in competencias]

        cur.close()
        conn.close()

        return competencias
    except Exception as e:
        print(f"Erro ao obter as competências: {str(e)}")
        return []


@app.route('/faturamento')
def faturamento():
    try:
        # Recuperar o filtro (suponha que esteja sendo passado como um parâmetro na URL)
        filtro = request.args.get('filtro')

        # Obter a lista de competências
        competencias = obter_competencias()

        # Conectar ao banco de dados
        conn = conectar_bd()
        cur = conn.cursor()

        # Consultar o faturamento por contrato com base no filtro
        if filtro:
            cur.execute("""
                SELECT DATE_FORMAT(competencia, '%b/%Y') AS competencia_formatada, segmento, contrato, SUM(valor_faturamento) AS total_faturamento, status
                FROM amb_faturamento
                WHERE seu_campo_de_filtro = %s
                GROUP BY competencia, segmento, contrato
            """, (filtro,))
        else:
            cur.execute("""
                SELECT DATE_FORMAT(competencia, '%b/%Y') AS competencia_formatada, segmento, contrato, SUM(valor_faturamento) AS total_faturamento, status
                FROM amb_faturamento
                GROUP BY competencia, segmento, contrato
            """)
        faturamento_por_contrato = cur.fetchall()

        # Calcular a soma do valor de todas as linhas
        soma_valor_faturamento = sum(faturamento['total_faturamento'] for faturamento in faturamento_por_contrato)
        
        # Consultar os contratos no banco de dados
        cur.execute("SELECT id_contrato, contrato, segmento, cliente, cnpj_cliente, id_filial FROM amb_contratos")
        contratos = cur.fetchall()
        
        # Lista de opções de status
        opcoes_status = ['Medição pendente', 'Pendente aprovação', 'Aprovado', 'Enviado p/ faturamento']

        # Definir uma cor de destaque para a linha de valor total
        cor_destaque = 'highlight-background'

        cur.close()
        conn.close()

        # Renderizar a página de faturamento e passar os dados para o template
        return render_template('faturamento.html', faturamento_por_contrato=faturamento_por_contrato, contratos=contratos, opcoes_status=opcoes_status, soma_valor_faturamento=soma_valor_faturamento, cor_destaque=cor_destaque, competencias=competencias)
    except Exception as e:
        return jsonify({'error': str(e)})


# Rota para cadastrar faturamento
@app.route('/cadastrar_faturamento', methods=['POST'])
def cadastrar_faturamento():
    try:
        # Receber os dados do formulário
        contrato = request.form.get('contrato')
        segmento = request.form.get('segmento')
        cliente = request.form.get('cliente')
        cnpj_cliente = request.form.get('cnpj_cliente').replace('.', '').replace('/', '').replace('-', '')  # Remover caracteres especiais do CNPJ
        competencia = request.form.get('competencia')
        
        # Obter o valor de faturamento sem o símbolo de R$ e com duas casas decimais à esquerda
        valor_faturamento = request.form.get('valor_faturamento').replace('R$ ', '').replace('.', '').replace(',', '')
        valor_faturamento = f"{valor_faturamento[:-2]}.{valor_faturamento[-2:]}"  # Adicionar o ponto para separar as casas decimais
        
        # Converter para float
        valor_faturamento = float(valor_faturamento)

        status = request.form.get('status')
        observacao = request.form.get('observacao')
        id_filial = request.form.get('id_filial')

        # Log dos dados do formulário
        print(f'contrato: {contrato}')
        print(f'segmento: {segmento}')
        print(f'cliente: {cliente}')
        print(f'cnpj_cliente: {cnpj_cliente}')
        print(f'competencia: {competencia}')
        print(f'valor_faturamento: {valor_faturamento}')
        print(f'status: {status}')
        print(f'observacao: {observacao}')
        print(f'id_filial: {id_filial}')

        # Validar os dados do formulário
        if not all([contrato, segmento, cliente, cnpj_cliente, competencia, valor_faturamento, status, id_filial]):
            return jsonify({'success': False, 'message': 'Todos os campos são obrigatórios.'})

        # Conectar ao banco de dados
        conn = conectar_bd()
        cur = conn.cursor()

        # Inserir os dados na tabela amb_faturamento
        try:
            cur.execute("INSERT INTO amb_faturamento (contrato, segmento, cliente, cnpj_cliente, competencia, valor_faturamento, status, observacao, id_filial) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                        (contrato, segmento, cliente, cnpj_cliente, competencia, valor_faturamento, status, observacao, id_filial))
            conn.commit()
            return jsonify({'success': True, 'message': 'Faturamento cadastrado com sucesso!'})
        except Exception as e:
            conn.rollback()
            print(f'Dados do formulário: {request.form.to_dict()}')  # Log dos dados do formulário
            return jsonify({'success': False, 'message': f'Erro ao cadastrar faturamento: {str(e)}'})
        finally:
            cur.close()
            conn.close()
        
    except Exception as e:
        print(f'Erro ao processar a solicitação: {str(e)}')  # Log do erro
        return jsonify({'success': False, 'message': str(e)})

# Função para obter os dados do faturamento por segmento e competência
@app.route('/dados_faturamento_segmento_competencia')
def dados_faturamento_segmento_competencia():
    try:
        # Conectar ao banco de dados
        conn = conectar_bd()
        cur = conn.cursor()

        # Consultar o faturamento por segmento e competência
        cur.execute("""
            SELECT segmento, DATE_FORMAT(competencia, '%b/%Y') AS competencia_formatada, SUM(valor_faturamento) AS total_faturamento
            FROM amb_faturamento
            GROUP BY segmento, competencia
            ORDER BY segmento, competencia
        """)
        dados_faturamento = cur.fetchall()

        # Calcular o faturamento total por competência
        faturamento_total_por_competencia = {}
        for item in dados_faturamento:
            competencia = item['competencia_formatada']
            total_faturamento = item['total_faturamento']
            if competencia not in faturamento_total_por_competencia:
                faturamento_total_por_competencia[competencia] = 0
            faturamento_total_por_competencia[competencia] += total_faturamento

        # Adicionar uma linha para representar o faturamento total por competência
        for competencia, total_faturamento in faturamento_total_por_competencia.items():
            dados_faturamento.append({
                'segmento': 'Faturamento Total',
                'competencia_formatada': competencia,
                'total_faturamento': total_faturamento
            })

        cur.close()
        conn.close()

        return jsonify(dados_faturamento)
    except Exception as e:
        return jsonify({'error': str(e)})

# Função para obter os dados do faturamento por segmento
@app.route('/dados_faturamento_segmento')
def dados_faturamento_segmento():
    try:
        # Recuperar o filtro por competência (suponha que seja passado como um parâmetro na URL)
        competencia = request.args.get('competencia')

        # Conectar ao banco de dados
        conn = conectar_bd()
        cur = conn.cursor()

        # Consultar o faturamento por segmento, filtrando por competência, se fornecido
        if competencia:
            cur.execute("""
                SELECT segmento, SUM(valor_faturamento) AS total_faturamento
                FROM amb_faturamento
                WHERE DATE_FORMAT(competencia, '%b/%Y') = %s
                GROUP BY segmento
            """, (competencia,))
        else:
            cur.execute("""
                SELECT segmento, SUM(valor_faturamento) AS total_faturamento
                FROM amb_faturamento
                GROUP BY segmento
            """)
        dados_faturamento = cur.fetchall()

        cur.close()
        conn.close()

        return jsonify(dados_faturamento)
    except Exception as e:
        return jsonify({'error': str(e)})



if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0',port=80)
