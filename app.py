from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask import flash
from werkzeug.security import generate_password_hash, check_password_hash
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
    mes = db.Column(db.String(7))
    data_pagamento = db.Column(db.DateTime)
    status = db.Column(db.String(20))

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
    
    # Gera uma lista de meses para exibição (ex: últimos 12 meses + próximos 6)
    # Você pode ajustar este range conforme necessário
    meses_para_exibir = []
    hoje = datetime.now().replace(day=1) # Começa do primeiro dia do mês atual
    
    # Meses passados (ex: 12 meses)
    for i in range(12, 0, -1):
        meses_para_exibir.append((hoje - relativedelta(months=i)).strftime('%Y-%m'))
    
    # Mês atual e próximos meses (ex: mês atual + 5 próximos = 6 meses)
    for i in range(0, 6):
        meses_para_exibir.append((hoje + relativedelta(months=i)).strftime('%Y-%m'))

    # Busca todos os pagamentos do associado para otimizar
    pagamentos_dict = {p.mes: p for p in associado.pagamentos}

    # Prepara dados para o template
    historico_display = []
    for mes_yyyymm in meses_para_exibir:
        pagamento = pagamentos_dict.get(mes_yyyymm)
        mes_display = datetime.strptime(mes_yyyymm, '%Y-%m').strftime('%m/%Y')
        
        data_pagamento_para_display = None
        data_pagamento_para_input_value = None # Para o value="" do input date

        if pagamento and pagamento.data_pagamento:
            data_pagamento_para_display = pagamento.data_pagamento.strftime('%d/%m/%Y')
            # O input type="date" espera o formato AAAA-MM-DD
            data_pagamento_para_input_value = pagamento.data_pagamento.strftime('%Y-%m-%d')

        historico_display.append({
            'mes_yyyymm': mes_yyyymm,
            'mes_display': mes_display,
            'status': pagamento.status if pagamento else 'Pendente',
            'data_pagamento_display': data_pagamento_para_display,
            'data_pagamento_input_value': data_pagamento_para_input_value # Passa o valor formatado
        })
            
    return render_template(
        'historico_pagamentos_associado.html',
        associado=associado,
        historico_display=historico_display
    )

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
    mes = request.form['mes']
    status = request.form['status']
    data_pagamento_str = request.form.get('data_pagamento_input') # Campo para data manual

    print(f"DEBUG: Tentando registrar pagamento para Associado ID: {associado_id}, Mês: {mes}, Status: {status}, Data Pagamento Input: {data_pagamento_str}")

    data_pagamento_obj = None
    if status == 'OK':
        if data_pagamento_str:
            try:
                data_pagamento_obj = datetime.strptime(data_pagamento_str, '%Y-%m-%d').date()
            except ValueError:
                flash(f'Formato de data de pagamento inválido: "{data_pagamento_str}". Use o formato AAAA-MM-DD.', 'danger')
                return redirect(url_for('historico_pagamentos_associado', associado_id=associado_id))
        else:
            flash('A data do pagamento é obrigatória quando o status é "OK".', 'danger')
            return redirect(url_for('historico_pagamentos_associado', associado_id=associado_id))

    pagamento = Pagamento.query.filter_by(associado_id=associado_id, mes=mes).first()

    if pagamento:
        print(f"DEBUG: Pagamento existente para Mês: {mes}. Atualizando.")
        pagamento.status = status
        pagamento.data_pagamento = data_pagamento_obj 
    else:
        print(f"DEBUG: Novo pagamento para Mês: {mes}. Criando.")
        pagamento = Pagamento(
            associado_id=associado_id,
            mes=mes,
            status=status,
            data_pagamento=data_pagamento_obj
        )
        db.session.add(pagamento)
    
    try:
        db.session.commit()
        flash('Pagamento atualizado com sucesso!', 'success')
        print(f"DEBUG: Pagamento COMITADO - Mês: {mes}, Status: {status}, Data Obj: {data_pagamento_obj}")
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao atualizar pagamento: {str(e)}', 'danger')
        print(f"DEBUG: ERRO no commit do pagamento: {str(e)}")
    
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
            print("Usuário admin criado com senha 'admin123'.")
    app.run(host="0.0.0.0", port=5000, debug=True)