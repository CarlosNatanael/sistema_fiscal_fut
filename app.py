from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask import flash
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import event
from sqlalchemy.engine import Engine
import os

# Configuração do caminho do banco de dados
basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, 'db', 'database.db')

# Garantir que a pasta db existe
if not os.path.exists(os.path.join(basedir, 'db')):
    os.makedirs(os.path.join(basedir, 'db'))

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24) # Ou uma string secreta forte e aleatória
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}' #
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False #

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' # Rota para onde usuários não logados são redirecionados
login_manager.login_message = "Você precisa estar logado para acessar esta página."
login_manager.login_message_category = "info" # Categoria para flash messages (opcional)

@event.listens_for(Engine, "connect")
def set_sqlite_timeout(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA busy_timeout = 5000") # Timeout de 5 segundos (5000 ms)
        cursor.close()
        print("DEBUG: SQLite busy_timeout configurado para 5000ms.")
    except Exception as e:
        print(f"DEBUG: Erro ao configurar SQLite busy_timeout: {e}")

# ========= Classes ====================
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Associado(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.Integer, unique=True)
    nome = db.Column(db.String(100), nullable=False)
    apelido = db.Column(db.String(50))
    pagamentos = db.relationship('Pagamento', backref='associado', lazy=True)

class Convidado(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    presencas = db.relationship('Presenca', backref='convidado', lazy=True)

class Pagamento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    associado_id = db.Column(db.Integer, db.ForeignKey('associado.id'))
    mes = db.Column(db.String(7))  # Formato YYYY-MM
    data_pagamento = db.Column(db.DateTime) # Data em que o pagamento foi feito
    status = db.Column(db.String(20))  # OK, Pendente, NA
    valor = db.Column(db.Float, nullable=True) # VALOR PAGO - importante para o caixa

class Presenca(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    convidado_id = db.Column(db.Integer, db.ForeignKey('convidado.id'))
    data = db.Column(db.Date)
    status = db.Column(db.String(20))
    pagamento_jogo = db.Column(db.String(20), default='Pendente', nullable=True)

class PagamentoJogoConvidado(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    presenca_id = db.Column(db.Integer, db.ForeignKey('presenca.id'), unique=True)
    data_pagamento_jogo = db.Column(db.DateTime, default=datetime.utcnow)
    status_pagamento = db.Column(db.String(20), default='Pago') # Ex: Pago, Pendente

    presenca = db.relationship('Presenca', backref=db.backref('pagamento_info', uselist=False))

class TransacaoCaixa(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.DateTime, nullable=False, default=datetime.utcnow) # Data da transação
    descricao = db.Column(db.String(200), nullable=False)
    tipo = db.Column(db.String(10), nullable=False) 
    valor = db.Column(db.Float, nullable=False) 
    pagamento_id = db.Column(db.Integer, db.ForeignKey('pagamento.id'), nullable=True)
    pagamento = db.relationship('Pagamento', backref=db.backref('transacao_caixa', uselist=False))

    def __repr__(self):
        return f"<TransacaoCaixa {self.id} [{self.tipo}] {self.descricao} - R${self.valor:.2f}>"

# ========== Login ================
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Você foi desconectado.', 'success')
    return redirect(url_for('index'))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            flash('Login realizado com sucesso!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        else:
            flash('Login falhou. Verifique seu nome de usuário e senha.', 'danger')
    return render_template('login.html')

@app.route('/')
def index():
    return redirect(url_for('associados'))

# ================= Caixa grupo ==============
@app.route('/caixa')
def public_caixa():
    hoje = datetime.now()
    mes_atual_para_caixa = hoje.strftime('%Y-%m')

    pagamentos_mes_atual = Pagamento.query.filter(
        Pagamento.mes == mes_atual_para_caixa,
        Pagamento.status == 'OK',
        Pagamento.valor != None
    ).all()

    total_arrecadado_mes_atual_associados = sum(p.valor for p in pagamentos_mes_atual if p.valor is not None) 

    total_geral_mes_atual = total_arrecadado_mes_atual_associados

    todos_pagamentos_ok = Pagamento.query.filter(Pagamento.status == 'OK', Pagamento.valor != None).order_by(Pagamento.mes.desc(), Pagamento.data_pagamento.desc()).all()

    def format_mes_para_display(mes_yyyymm):
        if mes_yyyymm:
            try:
                return datetime.strptime(mes_yyyymm, '%Y-%m').strftime('%m/%Y')
            except ValueError:
                return mes_yyyymm 
        return ''

    return render_template(
        'caixa.html',
        mes_atual_display=hoje.strftime('%m/%Y'),
        total_arrecadado_mes_atual=total_geral_mes_atual,
        pagamentos_recentes=pagamentos_mes_atual,
        todos_pagamentos_historico=todos_pagamentos_ok,
        format_mes_display=format_mes_para_display
    )

@app.route('/admin/caixa', methods=['GET', 'POST'])
@login_required
def admin_caixa():
    if request.method == 'POST':
        descricao = request.form.get('descricao')
        valor_str = request.form.get('valor')
        tipo_transacao = request.form.get('tipo_transacao', 'saida') # 'saida' ou 'entrada'
        data_str = request.form.get('data_transacao') # Formato AAAA-MM-DD

        if not all([descricao, valor_str, data_str]):
            flash('Descrição, valor e data são obrigatórios para a transação.', 'danger')
        else:
            try:
                valor = float(valor_str)
                # A data da transação já vem como AAAA-MM-DD do input type="date"
                data_transacao = datetime.strptime(data_str, '%Y-%m-%d').date() 
                                   # ou .datetime() se quiser guardar hora, mas .date() é suficiente se o input é date

                if valor <= 0: # Valor deve ser positivo, o 'tipo' define a operação
                    flash('O valor da transação deve ser um número positivo.', 'danger')
                else:
                    nova_transacao = TransacaoCaixa(
                        data=datetime.combine(data_transacao, datetime.min.time()), # Converte date para datetime se o campo do modelo for DateTime
                        descricao=descricao,
                        tipo=tipo_transacao,
                        valor=valor
                    )
                    db.session.add(nova_transacao)
                    db.session.commit()
                    flash(f'Transação de "{tipo_transacao}" registrada com sucesso!', 'success')
            except ValueError:
                flash('Valor ou formato de data inválido.', 'danger')
            except Exception as e:
                db.session.rollback()
                flash(f'Erro ao registrar transação: {str(e)}', 'danger')
        return redirect(url_for('admin_caixa'))

    # GET: Exibir histórico e saldo
    transacoes = TransacaoCaixa.query.order_by(TransacaoCaixa.data.desc(), TransacaoCaixa.id.desc()).all()
    
    saldo_atual = 0.0
    for t in transacoes:
        if t.tipo == 'entrada':
            saldo_atual += t.valor
        elif t.tipo == 'saida':
            saldo_atual -= t.valor
            
    return render_template('admin_caixa.html', 
                           transacoes=transacoes, 
                           saldo_atual=saldo_atual,
                           today_date_for_input=date.today().strftime('%Y-%m-%d')) # Para o valor padrão do input de data

def format_mes_para_display_filter(mes_yyyymm):
    if mes_yyyymm:
        try:
            return datetime.strptime(mes_yyyymm, '%Y-%m').strftime('%m/%Y')
        except ValueError:
            return mes_yyyymm 
    return ''
app.jinja_env.filters['format_mes_display'] = format_mes_para_display_filter


# ================= Associados ==============
@app.route('/associados')
def associados():
    hoje = datetime.now()
    mes_atual_interno = hoje.strftime('%Y-%m') # Formato YYYY-MM para lógica
    mes_atual_display = hoje.strftime('%m/%Y') # Formato MM/YYYY para exibição

    todos_associados = Associado.query.order_by(Associado.numero).all()

    return render_template(
        'associados.html',
        associados=todos_associados,
        mes_atual=mes_atual_interno,
        mes_atual_display=mes_atual_display
        # Removido: proximo_mes e proximo_mes_display
    )

@app.route('/historico-pagamentos')
@login_required
def lista_associados_para_historico():
    associados = Associado.query.order_by(Associado.nome).all()
    return render_template('lista_associados_historico.html', associados=associados)

@app.route('/historico-pagamentos/associado/<int:associado_id>', methods=['GET'])
@login_required
def historico_pagamentos_associado(associado_id):
    associado = Associado.query.get_or_404(associado_id)
    
    # ... (lógica para gerar meses_para_exibir) ...
    meses_para_exibir = []
    hoje = datetime.now().replace(day=1) 
    
    for i in range(12, 0, -1): # 12 meses passados
        meses_para_exibir.append((hoje - relativedelta(months=i)).strftime('%Y-%m'))
    for i in range(0, 6): # Mês atual + 5 próximos
        meses_para_exibir.append((hoje + relativedelta(months=i)).strftime('%Y-%m'))
    # Remove duplicatas e ordena se necessário, embora a lógica acima deva gerar sequencialmente
    meses_para_exibir = sorted(list(set(meses_para_exibir)))


    # Busca todos os pagamentos do associado de uma vez para otimizar
    pagamentos_do_associado_dict = {p.mes: p for p in associado.pagamentos}

    historico_display = []
    for mes_yyyymm in meses_para_exibir:
        pagamento = pagamentos_do_associado_dict.get(mes_yyyymm) # Usando o dict para pegar o pagamento
        mes_display = datetime.strptime(mes_yyyymm, '%Y-%m').strftime('%m/%Y')
        
        data_pagamento_para_display = None
        data_pagamento_para_input_value = None
        valor_atual_do_pagamento = None # Para armazenar o valor do pagamento

        if pagamento: # Se existe um objeto pagamento para este mês
            if pagamento.data_pagamento:
                data_pagamento_para_display = pagamento.data_pagamento.strftime('%d/%m/%Y')
                data_pagamento_para_input_value = pagamento.data_pagamento.strftime('%Y-%m-%d')
            if pagamento.valor is not None: # Verifica se o pagamento tem um valor
                valor_atual_do_pagamento = pagamento.valor

        historico_display.append({
            'mes_yyyymm': mes_yyyymm,
            'mes_display': mes_display,
            'status': pagamento.status if pagamento else 'Pendente',
            'data_pagamento_display': data_pagamento_para_display,
            'data_pagamento_input_value': data_pagamento_para_input_value,
            'valor_pago_atual': valor_atual_do_pagamento # ADICIONA O VALOR AQUI
        })
            
    return render_template(
        'historico_pagamentos_associado.html',
        associado=associado,
        historico_display=historico_display
        # Note que pagamentos_dict NÃO está sendo passado para o template aqui
    )

# ================= Convidados ==============
@app.route('/convidados') #
def convidados():
    convidados_query = Convidado.query.all() # Renomeei para evitar conflito com o nome da função, boa prática
    proxima_data = "07/06/2025"  # Isso poderia ser dinâmico

    # Crie a data específica aqui
    data_evento_fixa = date(2025, 5, 31)

    return render_template(
        'convidados.html',
        convidados=convidados_query, # Passando a lista de convidados
        proxima_data=proxima_data,
        data_evento_fixa=data_evento_fixa # Passe a data para o template
    )

@app.route('/convidados/historico')
@login_required
def lista_convidados_para_historico_jogos():
    convidados = Convidado.query.order_by(Convidado.nome).all()
    return render_template('lista_convidados_historico.html', convidados=convidados)

@app.route('/convidados/historico/<int:convidado_id>', methods=['GET'])
@login_required
def historico_jogos_convidado(convidado_id):
    convidado = Convidado.query.get_or_404(convidado_id)
    
    # Determinar o range de datas (Sábados) para exibir
    datas_jogos_display = []
    hoje = date.today()
    
    # Encontrar o sábado desta semana ou o próximo se hoje já passou de sábado
    dia_semana_hoje = hoje.weekday() # Segunda=0, Domingo=6
    if dia_semana_hoje <= 5: # Se hoje é Sábado ou antes
        sabado_desta_semana = hoje + relativedelta(days=(5 - dia_semana_hoje))
    else: # Se hoje é Domingo
        sabado_desta_semana = hoje + relativedelta(days=(5 - dia_semana_hoje + 7))

    # Exibir, por exemplo, os últimos 8 sábados e os próximos 4 sábados
    for i in range(8, 0, -1): # 8 sábados passados
        datas_jogos_display.append(sabado_desta_semana - relativedelta(weeks=i))
    for i in range(0, 5): # Sábado atual/próximo e os 4 seguintes (total de 5)
        datas_jogos_display.append(sabado_desta_semana + relativedelta(weeks=i))
    
    # Ordenar e remover duplicatas (embora a lógica acima deva gerar datas únicas)
    datas_jogos_display = sorted(list(set(datas_jogos_display)), reverse=True)

    # Buscar todas as presenças do convidado de uma vez para otimizar
    presencas_do_convidado_dict = {p.data: p for p in Presenca.query.filter_by(convidado_id=convidado.id).all()}
    
    historico_para_template = []
    for data_jogo in datas_jogos_display:
        presenca_obj = presencas_do_convidado_dict.get(data_jogo)
        
        status_presenca_atual = presenca_obj.status if presenca_obj else 'Não Registrado'
        pagamento_jogo_atual = '-'
        if presenca_obj and presenca_obj.status == 'Presente':
            pagamento_jogo_atual = presenca_obj.pagamento_jogo
        elif not presenca_obj or presenca_obj.status == 'Faltou':
            pagamento_jogo_atual = 'N/A'


        historico_para_template.append({
            'data_obj': data_jogo,
            'data_display': data_jogo.strftime('%d/%m/%Y (%a)'), # Ex: 08/06/2024 (Sáb)
            'data_for_input': data_jogo.strftime('%d/%m/%Y'),   # Formato para o input hidden do formulário
            'status_presenca': status_presenca_atual,
            'pagamento_jogo': pagamento_jogo_atual
        })
            
    return render_template(
        'historico_jogos_convidado.html',
        convidado=convidado,
        historico_jogos=historico_para_template
    )

# ======== Funções adicionais ============
@app.route('/adicionar', methods=['GET', 'POST']) #
@login_required
def adicionar():
    if request.method == 'POST':
        tipo = request.form['tipo']
        if tipo == 'associado':
            novo_associado = Associado(
                numero=request.form['numero'],
                nome=request.form['nome'],
                apelido=request.form.get('apelido', '')
            )
            db.session.add(novo_associado)
        elif tipo == 'convidado':
            novo_convidado = Convidado(nome=request.form['nome'])
            db.session.add(novo_convidado)
        
        db.session.commit()
        return redirect(url_for('index'))
    
    return render_template('adicionar.html')



@app.route('/registrar_pagamento/<int:associado_id>', methods=['POST'])
@login_required
def registrar_pagamento(associado_id):
    # Busca o objeto Associado no início para ter acesso ao nome
    associado_info = Associado.query.get(associado_id)
    if not associado_info:
        flash(f'Associado com ID {associado_id} não encontrado.', 'danger')
        return redirect(url_for('lista_associados_para_historico')) # Ou outra rota apropriada

    mes = request.form['mes']
    status = request.form['status']
    data_pagamento_str = request.form.get('data_pagamento_input')
    valor_pago_str = request.form.get('valor_pago')
    if valor_pago_str is not None:
        valor_pago_str = valor_pago_str.strip()

    print(f"DEBUG: Registrar Pagamento - Associado: {associado_info.nome} (ID: {associado_id}), Mês: {mes}, Status: {status}, Data Pag. Input: {data_pagamento_str}, Valor Pago Input: '{valor_pago_str}'")

    data_pagamento_obj = None
    valor_pago_obj = None

    if status == 'OK':
        # ... (sua lógica de validação para data_pagamento_obj e valor_pago_obj) ...
        # MANTENHA A VALIDAÇÃO QUE VOCÊ TINHA AQUI
        if not data_pagamento_str:
            flash('A data do pagamento é obrigatória quando o status é "OK".', 'danger')
            return redirect(url_for('historico_pagamentos_associado', associado_id=associado_id))
        try:
            data_pagamento_obj = datetime.strptime(data_pagamento_str, '%Y-%m-%d').date()
        except ValueError:
            flash(f'Formato de data de pagamento inválido: "{data_pagamento_str}". Use AAAA-MM-DD.', 'danger')
            return redirect(url_for('historico_pagamentos_associado', associado_id=associado_id))

        if not valor_pago_str:
            flash('O valor pago é obrigatório quando o status é "OK".', 'danger')
            return redirect(url_for('historico_pagamentos_associado', associado_id=associado_id))
        try:
            valor_pago_obj = float(valor_pago_str)
            if valor_pago_obj <= 0:
                flash('O valor pago deve ser positivo para o status "OK".', 'danger')
                return redirect(url_for('historico_pagamentos_associado', associado_id=associado_id))
        except ValueError:
            flash(f'Valor pago inválido: "{valor_pago_str}". Use um número.', 'danger')
            return redirect(url_for('historico_pagamentos_associado', associado_id=associado_id))
    
    pagamento_obj = Pagamento.query.filter_by(associado_id=associado_id, mes=mes).first()
    status_anterior_era_ok = False
    # pagamento_id_para_transacao = None # Removido pois pagamento_obj.id é usado diretamente após o flush

    if not pagamento_obj:
        print(f"DEBUG: Novo pagamento para Mês: {mes}. Criando.")
        pagamento_obj = Pagamento(associado_id=associado_id, mes=mes)
        db.session.add(pagamento_obj)
    else:
        print(f"DEBUG: Pagamento existente para Mês: {mes}. ID: {pagamento_obj.id}. Atualizando.")
        status_anterior_era_ok = pagamento_obj.status == 'OK'
        # pagamento_id_para_transacao = pagamento_obj.id

    pagamento_obj.status = status
    pagamento_obj.data_pagamento = data_pagamento_obj # Este deve ser um objeto datetime, não date, se o modelo for DateTime
                                                     # Se Pagamento.data_pagamento for db.Date, então .date() está ok.
                                                     # Assumindo Pagamento.data_pagamento = db.Column(db.DateTime)
    if data_pagamento_obj: # data_pagamento_obj é um objeto date
        pagamento_obj.data_pagamento = datetime.combine(data_pagamento_obj, datetime.min.time())
    else:
        pagamento_obj.data_pagamento = None

    pagamento_obj.valor = valor_pago_obj

    # Flush para obter o ID do pagamento_obj se for novo, antes de criar TransacaoCaixa
    try:
        db.session.flush()
    except Exception as e_flush:
        db.session.rollback()
        flash(f'Erro ao preparar dados do pagamento: {str(e_flush)}', 'danger')
        print(f"DEBUG: ERRO no flush do pagamento (antes da transação): {str(e_flush)}")
        return redirect(url_for('historico_pagamentos_associado', associado_id=associado_id))

    # Lógica para TransacaoCaixa
    if status == 'OK' and valor_pago_obj is not None:
        if pagamento_obj.id: # Garante que temos um ID para o pagamento
            transacao_existente = TransacaoCaixa.query.filter_by(pagamento_id=pagamento_obj.id).first()
            
            # Usa associado_info.nome que foi buscado no início
            descricao_transacao = f"Mensalidade {pagamento_obj.mes} - {associado_info.nome}"

            if transacao_existente:
                print(f"DEBUG: Atualizando TransacaoCaixa existente ID {transacao_existente.id}")
                if transacao_existente.valor != valor_pago_obj or \
                   (pagamento_obj.data_pagamento and transacao_existente.data != pagamento_obj.data_pagamento):
                    transacao_existente.valor = valor_pago_obj
                    transacao_existente.data = pagamento_obj.data_pagamento # Já é datetime
                    transacao_existente.descricao = f"{descricao_transacao} (Valor/Data Atualizado)"
            else:
                print(f"DEBUG: Criando nova TransacaoCaixa para Pagamento ID {pagamento_obj.id}")
                nova_transacao = TransacaoCaixa(
                    data=pagamento_obj.data_pagamento if pagamento_obj.data_pagamento else datetime.utcnow(),
                    descricao=descricao_transacao,
                    tipo='entrada',
                    valor=valor_pago_obj,
                    pagamento_id=pagamento_obj.id
                )
                db.session.add(nova_transacao)
    elif status_anterior_era_ok and status != 'OK' and pagamento_obj.id:
        transacao_a_remover = TransacaoCaixa.query.filter_by(pagamento_id=pagamento_obj.id, tipo='entrada').first()
        if transacao_a_remover:
            print(f"DEBUG: Removendo TransacaoCaixa ID {transacao_a_remover.id} pois o pagamento não é mais 'OK'.")
            db.session.delete(transacao_a_remover)

    try:
        db.session.commit()
        flash('Pagamento e/ou transação do caixa atualizados com sucesso!', 'success')
        print(f"DEBUG: Pagamento e TransacaoCaixa COMITADOS - Associado ID: {associado_id}, Mês: {mes}, Status: {status}")
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao salvar alterações: {str(e)}', 'danger')
        print(f"DEBUG: ERRO no commit final: {str(e)}")
    
    return redirect(url_for('historico_pagamentos_associado', associado_id=associado_id))

@app.route('/registrar_presenca/<int:convidado_id>', methods=['POST'])
@login_required
def registrar_presenca(convidado_id):
    data_str = request.form['data']  # Espera-se DD/MM/YYYY do formulário
    status_presenca = request.form['status'] # "Presente", "Faltou", "Não Registrado"
    # Pega o status do pagamento do jogo, default para 'Pendente' se não enviado ou se não for relevante
    status_pagamento_jogo = request.form.get('pagamento_jogo_status', 'Pendente')

    print(f"DEBUG: Registrar Presenca - Convidado ID: {convidado_id}, Data: {data_str}, Status Pres.: {status_presenca}, Status Pag. Jogo: {status_pagamento_jogo}")

    try:
        data_obj = datetime.strptime(data_str, '%d/%m/%Y').date()
    except ValueError:
        flash(f'Formato de data inválido: "{data_str}". Use o formato DD/MM/AAAA.', 'danger')
        return redirect(request.referrer or url_for('lista_convidados_para_historico_jogos'))

    presenca_existente = Presenca.query.filter_by(convidado_id=convidado_id, data=data_obj).first()

    if status_presenca == 'Não Registrado':
        if presenca_existente:
            print(f"DEBUG: Deletando registro de presença para Data {data_obj} pois status é 'Não Registrado'")
            db.session.delete(presenca_existente)
            flash('Registro de presença e pagamento do jogo removido.', 'success')
        else:
            flash('Nenhum registro para remover.', 'info') # Ou não faz nada
    elif presenca_existente:
        print(f"DEBUG: Presença existente para Data {data_obj}. Atualizando.")
        presenca_existente.status = status_presenca
        if status_presenca == 'Presente':
            presenca_existente.pagamento_jogo = status_pagamento_jogo
        else:  # Se Faltou
            presenca_existente.pagamento_jogo = 'N/A' # Não aplicável ou pode manter Pendente
        flash('Presença e pagamento do jogo atualizados com sucesso!', 'success')
    else: # Criar novo registro de presença (se não for "Não Registrado")
        print(f"DEBUG: Nova presença para Data {data_obj}. Criando.")
        nova_presenca = Presenca(
            convidado_id=convidado_id,
            data=data_obj,
            status=status_presenca,
            pagamento_jogo=(status_pagamento_jogo if status_presenca == 'Presente' else 'N/A')
        )
        db.session.add(nova_presenca)
        flash('Presença e pagamento do jogo registrados com sucesso!', 'success')
    
    try:
        db.session.commit()
        print(f"DEBUG: Commit da presença/pagamento do jogo bem-sucedido.")
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao salvar presença/pagamento do jogo: {str(e)}', 'danger')
        print(f"DEBUG: ERRO no commit da presença/pagamento do jogo: {str(e)}")
            
    # Redireciona de volta para a página de histórico do convidado específico
    return redirect(url_for('historico_jogos_convidado', convidado_id=convidado_id))

@app.route('/associado/editar/<int:associado_id>', methods=['GET', 'POST'])
@login_required
def editar_associado(associado_id):
    associado = Associado.query.get_or_404(associado_id)
    if request.method == 'POST':
        associado.numero = request.form['numero']
        associado.nome = request.form['nome']
        associado.apelido = request.form.get('apelido', '')
        try:
            db.session.commit()
            flash('Associado atualizado com sucesso!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar associado: {str(e)}', 'danger')
        return redirect(url_for('associados'))
    
    return render_template('editar_associado.html', associado=associado)

@app.route('/convidado/editar/<int:convidado_id>', methods=['GET', 'POST'])
@login_required
def editar_convidado(convidado_id):
    convidado = Convidado.query.get_or_404(convidado_id)
    if request.method == 'POST':
        convidado.nome = request.form['nome']
        try:
            db.session.commit()
            flash('Convidado atualizado com sucesso!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar convidado: {str(e)}', 'danger')
        return redirect(url_for('convidados'))
    
    return render_template('editar_convidado.html', convidado=convidado)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Criar admin se não existir
        if not User.query.filter_by(username='admin').first():
            admin_user = User(username='admin')
            admin_user.set_password('admin123')
            db.session.add(admin_user)
            db.session.commit()
    app.run(host="0.0.0.0", port=5000, debug=True)