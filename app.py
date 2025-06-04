from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from dateutil.relativedelta import relativedelta
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os

# Configuração do caminho do banco de dados
basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, 'db', 'database.db')

# Garantir que a pasta db existe
if not os.path.exists(os.path.join(basedir, 'db')):
    os.makedirs(os.path.join(basedir, 'db'))

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

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
    data_pagamento = db.Column(db.DateTime)
    status = db.Column(db.String(20))  # OK, Pendente, NA

class Presenca(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    convidado_id = db.Column(db.Integer, db.ForeignKey('convidado.id'))
    data = db.Column(db.Date)
    status = db.Column(db.String(20))  # Presente, Faltou

@app.route('/')
def index():
    return redirect(url_for('associados'))

@app.route('/associados')
def associados():
    hoje = datetime.now()
    # Formato YYYY-MM para consistência com o banco
    mes_atual_interno = hoje.strftime('%Y-%m')
    proximo_mes_interno = (hoje.replace(day=1) + relativedelta(months=1)).strftime('%Y-%m')

    # Para exibição, você pode criar uma versão formatada MM/YYYY se preferir
    mes_atual_display = hoje.strftime('%m/%Y')
    proximo_mes_display = (hoje.replace(day=1) + relativedelta(months=1)).strftime('%m/%Y')

    # ...
    return render_template(
        'associados.html',
        associados=associados,
        mes_atual=mes_atual_interno, # Usar o formato interno para lógica
        mes_atual_display=mes_atual_display, # Usar para mostrar na tela
        proximo_mes=proximo_mes_interno, # Usar o formato interno para o form
        proximo_mes_display=proximo_mes_display # Usar para mostrar na tela
    )

@app.route('/convidados')
def convidados():
    convidados = Convidado.query.all()
    proxima_data = "07/06/2025"  # Isso poderia ser dinâmico
    return render_template('convidados.html', convidados=convidados, proxima_data=proxima_data)

@app.route('/adicionar', methods=['GET', 'POST'])
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
def registrar_pagamento(associado_id):
    mes = request.form['mes']
    status = request.form['status']
    
    pagamento = Pagamento.query.filter_by(associado_id=associado_id, mes=mes).first()
    
    if pagamento:
        pagamento.status = status
        if status == 'OK':
            pagamento.data_pagamento = datetime.now()
    else:
        novo_pagamento = Pagamento(
            associado_id=associado_id,
            mes=mes,
            status=status,
            data_pagamento=datetime.now() if status == 'OK' else None
        )
        db.session.add(novo_pagamento)
    
    db.session.commit()
    return redirect(url_for('associados'))

@app.route('/registrar_presenca/<int:convidado_id>', methods=['POST'])
def registrar_presenca(convidado_id):
    data = request.form['data']
    status = request.form['status']
    
    presenca = Presenca(
        convidado_id=convidado_id,
        data=datetime.strptime(data, '%d/%m/%Y'),
        status=status
    )
    db.session.add(presenca)
    db.session.commit()
    
    return redirect(url_for('convidados'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=5000, debug=True)


login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' # Rota para onde usuários não logados são redirecionados
login_manager.login_message = "Você precisa estar logado para acessar esta página."
login_manager.login_message_category = "info" # Categoria para flash messages (opcional)