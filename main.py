from flask import Flask, render_template, flash, request, url_for, redirect, session, send_file, send_from_directory
import fdb
import os
import pygal
from collections import Counter
from flask_bcrypt import Bcrypt

import os
import io
import time
import qrcode
import crcmod
from qrcode.constants import ERROR_CORRECT_H

import smtplib
from email.mime.text import MIMEText


app = Flask(__name__)
bcrypt = Bcrypt(app)



app = Flask(__name__)
app.config['SECRET_KEY'] = 'sua_chave_secreta_aqui'

host = 'localhost'
database = r'C:\Projetos\Biblioteca_Fire_JWT_Bcript_pdf_imagem\Banco\LIVRO.FDB'
user = 'sysdba'
password = 'sysdba'

con = fdb.connect(host=host, database=database, user=user, password=password)

@app.route('/upload/<filename>')
def upload(filename):
    return send_from_directory('upload/capa', filename)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/acervo')
def acervo():

    cursor = con.cursor()
    cursor.execute("SELECT ID_LIVRO, TITULO, AUTOR, ANO_PUBLICACAO FROM livros")
    livros = cursor.fetchall()
    cursor.close()
    return render_template('livros.html', livros=livros)

@app.route('/novo')
def novo():
        if 'usuario_id' not in session:
            flash("Você precisa estar logado para acessar essa página.", "error")
            return redirect(url_for('login'))

        return render_template('novo.html', titulo='Novo Livro')


import os

@app.context_processor
def verificar_imagem():

    def imagem_existe(id_livro):

        caminho = os.path.join(app.root_path,'upload/capa',f'{id_livro}.png')

        return os.path.exists(caminho)

    return dict(imagem_existe=imagem_existe)

@app.route('/criar', methods=['POST'])
def criar():
    if 'usuario_id' not in session:
        flash("Você precisa estar logado para acessar essa página.", "error")
        return redirect(url_for('login'))

    titulo = request.form['titulo']
    autor = request.form['autor']
    ano_publicacao = request.form['ano_publicacao']
    cursor = con.cursor()

    try:
        cursor.execute("SELECT 1 FROM livros WHERE TITULO = ?", (titulo,))
        if cursor.fetchone():
            flash("Erro: Livro já cadastrado.", "error")
            return redirect(url_for('novo'))

        cursor.execute("INSERT INTO livros (TITULO, AUTOR, ANO_PUBLICACAO) VALUES (?, ?, ?) returning id_livro",
                       (titulo, autor, ano_publicacao))
        id_livro = cursor.fetchone()[0]
        con.commit()

        arquivo = request.files['arquivo']
        os.makedirs('upload/capa', exist_ok=True)
        arquivo.save(f'upload/capa/{id_livro}.png')

    finally:
        cursor.close()

    flash("Livro cadastrado com sucesso!", "success")
    return redirect(url_for('index'))
@app.route('/editar/<int:id>', methods=['GET', 'POST'])
def editar(id):

    if 'usuario_id' not in session:
        flash("Você precisa estar logado para acessar essa página.", "error")
        return redirect(url_for('login'))

    cursor = con.cursor()

    cursor.execute("""
        SELECT ID_LIVRO, TITULO, AUTOR, ANO_PUBLICACAO 
        FROM livros 
        WHERE ID_LIVRO = ?
    """, (id,))

    livro = cursor.fetchone()

    if not livro:
        cursor.close()
        flash("Livro não encontrado!", "error")
        return redirect(url_for('index'))

    if request.method == 'POST':

        titulo = request.form['titulo']
        autor = request.form['autor']
        ano_publicacao = request.form['ano_publicacao']

        # Pega a nova imagem enviada
        arquivo = request.files.get('arquivo')

        # Atualiza os dados do livro
        cursor.execute("""
            UPDATE livros 
            SET TITULO = ?, AUTOR = ?, ANO_PUBLICACAO = ? 
            WHERE ID_LIVRO = ?
        """, (titulo, autor, ano_publicacao, id))

        con.commit()

        # Se o usuário escolheu uma nova imagem
        if arquivo and arquivo.filename:

            # Caminho da pasta das capas
            pasta_capa = os.path.join(
                app.root_path,
                'upload',
                'capa'
            )

            # Garante que a pasta exista
            os.makedirs(pasta_capa, exist_ok=True)

            # Caminho da imagem antiga
            caminho_imagem = os.path.join(
                pasta_capa,
                f'{id}.png'
            )

            # Se já existe uma capa, exclui
            if os.path.exists(caminho_imagem):
                os.remove(caminho_imagem)

            # Salva a nova imagem usando o ID do livro
            arquivo.save(caminho_imagem)

        cursor.close()

        flash("Livro atualizado com sucesso!", "success")
        return redirect(url_for('acervo'))

    # Verifica se existe uma imagem para o livro
    caminho_imagem = os.path.join(
        app.root_path,
        'upload',
        'capa',
        f'{id}.png'
    )

    imagem_existe = os.path.exists(caminho_imagem)

    cursor.close()

    return render_template(
        'editar.html',
        livro=livro,
        imagem_existe=imagem_existe,
        titulo='Editar Livro'
    )

@app.route('/confirmar_delete/<int:id>')
def confirmar_delete(id):
    if 'usuario_id' not in session:
        flash("Você precisa estar logado para acessar essa página.", "error")
        return redirect(url_for('login'))

    cursor = con.cursor()
    cursor.execute("SELECT ID_LIVRO, TITULO FROM livros WHERE ID_LIVRO = ?", (id,))
    livro = cursor.fetchone()
    cursor.close()

    if not livro:
        flash("Livro não encontrado.", "error")
        return redirect(url_for('index'))

    return render_template('confirmar_delete.html', livro=livro)

@app.route('/deletar/<int:id>', methods=['POST'])
def deletar(id):
    if 'usuario_id' not in session:
        flash("Você precisa estar logado para acessar essa página.", "error")
        return redirect(url_for('login'))

    cursor = con.cursor()
    try:
        cursor.execute('DELETE FROM livros WHERE id_livro = ?', (id,))
        con.commit()
        flash('Livro excluído com sucesso!', 'success')
    except:
        con.rollback()
        flash('Erro ao excluir o livro.', 'error')
    finally:
        cursor.close()

    return redirect(url_for('acervo'))

@app.route('/grafico')
def grafico():
    if 'usuario_id' not in session:
        flash("Você precisa estar logado para acessar essa página.", "error")
        return redirect(url_for('login'))

    cursor = con.cursor()
    cursor.execute("SELECT ANO_PUBLICACAO FROM livros")
    resultado = cursor.fetchall()
    cursor.close()
    anos = []

    for row in resultado:
        ano = row[0]
        anos.append(ano)

    contagem = Counter(anos)

    grafico = pygal.Bar()
    grafico.title = 'Livros por Ano de Publicação'

    for ano in sorted(contagem):
        grafico.add(str(ano), contagem[ano])

    caminho = os.path.join('static', 'graficos')
    os.makedirs(caminho, exist_ok=True)

    caminho_svg = os.path.join(caminho, 'grafico.svg')
    grafico.render_to_file(caminho_svg)

    return render_template('grafico.html',
        svg=url_for('static', filename='graficos/grafico.svg'))


@app.route('/grafico_pizza')
def grafico_pizza():
    if 'usuario_id' not in session:
        flash("Você precisa estar logado para acessar essa página.", "error")
        return redirect(url_for('login'))

    cursor = con.cursor()
    cursor.execute("SELECT ANO_PUBLICACAO FROM livros")
    anos = [row[0] for row in cursor.fetchall()]
    cursor.close()

    contagem = Counter(anos)

    grafico = pygal.Pie()
    grafico.title = 'Distribuição de Livros por Ano de Publicação'

    for ano in sorted(contagem):
        grafico.add(str(ano), contagem[ano])

    caminho = os.path.join('static', 'graficos')
    os.makedirs(caminho, exist_ok=True)

    caminho_svg = os.path.join(caminho, 'grafico_pizza.svg')
    grafico.render_to_file(caminho_svg)

    return render_template('grafico.html',
        svg=url_for('static', filename='graficos/grafico_pizza.svg'))


@app.route('/cadastro_usuario', methods=['GET', 'POST'])
def cadastro_usuario():
    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        senha = request.form['senha']

        cursor = con.cursor()
        cursor.execute('SELECT 1 FROM usuarios WHERE EMAIL = ?', (email,))
        usuario = cursor.fetchone()
        cursor.close()

        if not usuario is None:
            flash("Email já está sendo usado por outro usuário", "error")
            return redirect(url_for('cadastro_usuario'))


        # Verifica se a senha é forte
        if len(senha) < 8 or senha.isdigit() or senha.isalpha():
            flash("Senha fraca: use letras, números e mínimo 8 caracteres", "error")
            return redirect(url_for('cadastro_usuario'))

        # Criptografa a senha
        senha_cripto = bcrypt.generate_password_hash(senha).decode('utf-8')

        cursor = con.cursor()
        cursor.execute("INSERT INTO usuarios (nome, email, senha, tentativas, ativo) VALUES (?, ?, ?, ?, ?)",
                       (nome, email, senha_cripto, 0, 1))
        con.commit()
        cursor.close()
        flash("Usuário cadastrado com sucesso!", "success")
        return render_template('cadastro_usuario.html')

    return render_template('cadastro_usuario.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']

        cursor = con.cursor()
        cursor.execute("SELECT id_usuario, senha, coalesce(tentativas,0), ativo FROM usuarios WHERE email = ?", (email,))
        usuario = cursor.fetchone()

        if not usuario:
            flash("Usuário não encontrado", "error")
            return redirect(url_for('login'))

        id_usuario, senha_hash, tentativas, ativo = usuario

        if not ativo:
            flash("Conta bloqueada por tentativas inválidas", "error")
            return redirect(url_for('login'))

        if bcrypt.check_password_hash(senha_hash, senha):
            # Login OK: zera tentativas
            cursor.execute("UPDATE usuarios SET tentativas = 0 WHERE id_usuario = ?", (id_usuario,))
            con.commit()
            session['usuario_id'] = id_usuario  # <-- salvando login na sessão
            flash("Login bem-sucedido", "success")
            return redirect(url_for('acervo'))
        else:
            tentativas += 1
            if tentativas >= 3:
                cursor.execute("UPDATE usuarios SET tentativas = ?, ativo = 0 WHERE id_usuario = ?", (tentativas, id_usuario))
                flash("Conta bloqueada por 3 tentativas erradas", "error")
            else:
                cursor.execute("UPDATE usuarios SET tentativas = ? WHERE id_usuario = ?", (tentativas, id_usuario))
                flash(f"Tentativa inválida ({tentativas}/3)", "error")
            con.commit()
            cursor.close()
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/editar_usuario/<int:id>', methods=['GET', 'POST'])
def editar_usuario(id):
    cursor = con.cursor()
    cursor.execute("SELECT nome, email FROM usuarios WHERE id_usuario = ?", (id,))
    usuario = cursor.fetchone()

    if not usuario:
        flash("Usuário não encontrado", "error")
        return redirect(url_for('index'))

    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        nova_senha = request.form.get('senha')

        if nova_senha:
            if len(nova_senha) < 8 or nova_senha.isdigit() or nova_senha.isalpha():
                flash("Senha fraca: use letras, números e 8+ caracteres", "error")
                return redirect(url_for('editar_usuario', id=id))
            senha_cripto = bcrypt.hashpw(nova_senha.encode('utf-8'), bcrypt.gensalt())
            cursor.execute("UPDATE usuarios SET nome = ?, email = ?, senha = ? WHERE id_usuario = ?",
                           (nome, email, senha_cripto, id))
        else:
            cursor.execute("UPDATE usuarios SET nome = ?, email = ? WHERE id_usuario = ?",
                           (nome, email, id))
        con.commit()
        cursor.close()
        flash("Usuário atualizado", "success")
        return redirect(url_for('index'))

    return render_template('editar_usuario.html', usuario=usuario, id=id)

@app.route('/logout')
def logout():
    session.pop('usuario_id', None)
    flash("Sessão encerrada com sucesso.", "success")
    return redirect(url_for('login'))


@app.route('/enviar_email/<int:id_usuario>')
def enviar_email(id_usuario):
    if 'usuario_id' not in session:
        flash("Precisa estar logado.", "error")
        return redirect(url_for('login'))

    cursor = con.cursor()
    cursor.execute("SELECT email, nome FROM usuarios WHERE id_usuario = ?", (id_usuario,))
    usuario = cursor.fetchone()
    cursor.close()

    if not usuario:
        flash("Usuário não encontrado.", "error")
        return redirect(url_for('index'))

    email_destino, nome = usuario

    try:
        # Configurações do servidor SMTP (exemplo com Gmail)
        smtp_server = 'smtp.gmail.com'
        smtp_port = 587
        remetente = 'lslaissinnatra@gmail.com'         # <-- troca pelo seu e-mail
        senha = 'hdyt xvhp bpra wcgj'                # <-- usa senha de app, se for Gmail

        msg = MIMEText(f"Olá {nome}, isso é um e-mail de teste enviado pela aplicação Flask.")
        msg['Subject'] = 'Teste de E-mail'
        msg['From'] = remetente
        msg['To'] = email_destino

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(remetente, senha)
            server.send_message(msg)

        flash("E-mail enviado com sucesso!", "success")
    except Exception as e:
        flash(f"Erro ao enviar e-mail: {str(e)}", "error")

    return redirect(url_for('index'))


def calcula_crc16(payload: str) -> str:
    """
    Calcula CRC16‐CCITT (polinômio 0x1021, init 0xFFFF) de uma string
    e retorna 4 dígitos hex (MAIÚSCULO).
    """
    crc16_fn = crcmod.mkCrcFun(0x11021, initCrc=0xFFFF, rev=False)
    crc = crc16_fn(payload.encode("utf-8"))
    return f"{crc:04X}"

def format_tlv(id_tag: str, value: str) -> str:
    """
    Monta um TLV (Tag‐Length‐Value). Exemplo:
      format_tlv("00", "br.gov.bcb.pix") -> "00014br.gov.bcb.pix"
    """
    return f"{id_tag}{len(value):02d}{value}"

@app.route('/gerar_pix')
def gerar_pix():
    try:
        # --- 1) Valor fixo para teste ---
        valor = f"{29.4:.2f}"  # "29.40"


        # --- 2) Busca dados do banco ---
        cursor = con.cursor()
        cursor.execute("SELECT NOME, CHAVEPIX, CIDADE FROM usuarios")
        resultado = cursor.fetchone()
        cursor.close()

        if not resultado:
            flash("Chave PIX não encontrada.", "error")
            return redirect(url_for('index'))

        nome_bd, chave_pix_bd, cidade_bd = resultado

        # Remove espaços, converte para maiúsculas (nome/cidade) e faz trim
        nome_pix   = (nome_bd.strip().upper()[:25])   if nome_bd   else "RECEBEDOR PIX"
        cidade_pix = (cidade_bd.strip().upper()[:15]) if cidade_bd else "CIDADE"
        chave_pix  = chave_pix_bd.strip()



        # --- 3) Monta Merchant Account Info (campo 26) COM GUI em minúsculas ---
        gui       = "br.gov.bcb.pix"       # minúsculas OK
        campo00   = format_tlv("00", gui)  # ex.: "00014br.gov.bcb.pix"
        campo01   = format_tlv("01", chave_pix)
        merchant_info = campo00 + campo01
        campo_26  = format_tlv("26", merchant_info)


        # --- 4) Monta Additional Data Field (campo 62) sem “_” no TXID ---
        txid_raw = f"USR{int(time.time())}"   # ex.: "USR1748873335"
        txid     = txid_raw.strip()[:35]
        sub_tlv_62 = format_tlv("05", txid)
        campo_62   = format_tlv("62", sub_tlv_62)


        # --- 5) Monta o payload SEM o CRC (QR estático “01 11”) ---
        prefix = "000201010211"  # tag00="01", tag01="11" (QR estático)

        tag_52 = "52040000"      # Merchant Category Code = "0000"
        tag_53 = "5303986"       # Currency = "986" (BRL)
        tlv_54 = format_tlv("54", valor)


        tag_58 = "5802BR"
        tlv_59 = format_tlv("59", nome_pix)

        tlv_60 = format_tlv("60", cidade_pix)

        crc_placeholder = "6304"

        payload_sem_crc = (
            prefix
            + campo_26
            + tag_52
            + tag_53
            + tlv_54
            + tag_58
            + tlv_59
            + tlv_60
            + campo_62
            + crc_placeholder
        )

        # --- 6) Calcula e anexa o CRC16-CCITT ---
        crc = calcula_crc16(payload_sem_crc)
        payload_completo = payload_sem_crc + crc


        # --- 7) Gera o QR Code (PNG) ---
        qr = qrcode.QRCode(
            version=None,
            error_correction=ERROR_CORRECT_H,
            box_size=10,
            border=4
        )
        qr.add_data(payload_completo)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white")

        # --- 8) Salva o QR Code em disco ---
        pasta_qrcodes = os.path.join(os.getcwd(), "upload", "qrcodes")
        os.makedirs(pasta_qrcodes, exist_ok=True)

        arquivos_existentes = [
            f for f in os.listdir(pasta_qrcodes)
            if f.startswith("pix_") and f.endswith(".png")
        ]
        numeros_usados = []
        for nome_arq in arquivos_existentes:
            try:
                num = int(nome_arq.replace("pix_", "").replace(".png", ""))
                numeros_usados.append(num)
            except ValueError:
                continue
        proximo_numero = max(numeros_usados, default=0) + 1

        nome_arquivo = f"pix_{proximo_numero}.png"
        caminho_arquivo = os.path.join(pasta_qrcodes, nome_arquivo)
        qr_img.save(caminho_arquivo)

        # --- 9) Retorna o PNG para download ---
        return send_file(
            caminho_arquivo,
            mimetype='image/png',
            as_attachment=True,
            download_name=nome_arquivo
        )

    except Exception as e:
        flash(f"Ocorreu um erro interno: {e}", "error")
        return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
