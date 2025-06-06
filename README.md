# Sistema de Gestão Financeira para Times de Futebol Amador

## 1. Visão Geral

Este projeto é uma aplicação web desenvolvida em Flask (Python) para modernizar e simplificar a gestão financeira e administrativa de um time de futebol amador. O sistema substitui planilhas manuais, oferecendo uma plataforma online centralizada onde membros e administradores podem consultar informações sobre pagamentos, presença e finanças do grupo.

A aplicação conta com duas visões principais:
- **Visão Pública:** Acessível a todos, permite consultar o status de pagamento dos associados para o mês atual e o balanço financeiro do caixa do grupo.
- **Visão Administrativa:** Protegida por login, permite ao administrador gerenciar associados, convidados, registrar pagamentos, presenças e todas as transações financeiras do caixa.

---

## 2. Funcionalidades Implementadas

### 2.1. Visão Pública (Acessível a Todos)

- **Lista de Associados (Mês Atual):**
  - Exibe uma lista de todos os associados do time.
  - Mostra o status de pagamento da mensalidade referente ao mês corrente.
  - O status é destacado visualmente:
    - **Verde (OK):** Pagamento confirmado.
    - **Amarelo (Pendente):** Pagamento ainda não realizado.
    - **Cinza (NA):** Não aplicável ou outro status.

- **Caixa do Grupo (Público):**
  - Apresenta um resumo financeiro simplificado e transparente.
  - Mostra o **Saldo Total** atual do caixa do grupo.
  - Exibe um resumo das **entradas e saídas** totais do mês corrente.
  - Inclui uma seção para pagamento via **PIX**, com a chave do tesoureiro e um botão para copiar a chave facilmente.

### 2.2. Visão Administrativa (Requer Login)

O acesso a todas as funcionalidades de gestão é protegido por um sistema de login.

- **Login de Administrador:**
  - Uma página de login moderna e segura para o administrador acessar as ferramentas de gestão.
  - O usuário e senha do admin são criados na primeira execução da aplicação.

- **Gestão de Associados e Convidados:**
  - **Adicionar:** Permite cadastrar novos associados (com número, nome e apelido) e novos convidados (com nome).
  - **Editar:** Permite corrigir ou atualizar as informações cadastrais de associados e convidados existentes.

- **Gestão de Pagamentos de Associados:**
  - Acessível através da página "Pagamentos Associados", que leva a um histórico detalhado por membro.
  - O administrador pode registrar ou alterar o status de pagamento (`OK`, `Pendente`, `NA`) para qualquer mês (passado, presente ou futuro).
  - Ao registrar um pagamento como "OK", o administrador deve inserir:
    - O **valor pago**.
    - A **data exata** em que o pagamento foi realizado (independente da data do registro no sistema).
  - O registro de um pagamento como "OK" com valor gera automaticamente uma transação de "entrada" no caixa do grupo. Se o status for alterado de "OK" para outro, a transação correspondente é removida do caixa.

- **Gestão de Jogos e Taxas de Convidados:**
  - Permite visualizar um histórico de jogos (sábados passados e futuros) para cada convidado.
  - Para cada jogo, o administrador pode registrar a presença do convidado:
    - **Presente**
    - **Faltou**
    - **Não Registrado**
  - Se a presença for "Presente", o administrador pode registrar o status do pagamento da taxa do jogo (`Pago`, `Pendente`, `Dispensado`).

- **Gestão do Caixa (Admin):**
  - Oferece uma visão completa e detalhada de todas as movimentações financeiras.
  - Exibe o **Saldo Atual** calculado com base em todas as entradas e saídas.
  - Permite ao administrador registrar manualmente:
    - **Saídas (Despesas):** Como aluguel do campo, compra de materiais (bolas, coletes), etc.
    - **Entradas (Outras Receitas):** Doações ou outras fontes de receita.
  - Mostra um histórico completo de todas as transações, indicando data, descrição, tipo (entrada/saída) e valor.

---

## 3. Tecnologias Utilizadas

- **Backend:**
  - **Python 3:** Linguagem de programação principal.
  - **Flask:** Micro-framework web para construir a aplicação.
  - **Flask-SQLAlchemy:** Para interagir com o banco de dados de forma orientada a objetos (ORM).
  - **Flask-Login:** Para gerenciar a autenticação e sessões do administrador.
- **Banco de Dados:**
  - **SQLite:** Banco de dados leve e baseado em arquivo, ideal para aplicações de pequeno e médio porte.
- **Frontend:**
  - **HTML5:** Estrutura das páginas.
  - **CSS3:** Estilização, layout responsivo e design moderno.
  - **JavaScript (Vanilla):** Para interatividade dinâmica no lado do cliente (ex: mostrar/esconder campos de formulário, funcionalidade de copiar PIX).
- **Bibliotecas Externas:**
  - **Font Awesome:** Para os ícones utilizados na interface.
  - **Google Fonts (Roboto):** Para uma tipografia moderna e legível.

---

## 4. Como Configurar e Executar o Projeto

### Pré-requisitos

- Python 3 instalado.
- `pip` (gerenciador de pacotes do Python).

### Instalação

1.  **Clone o repositório ou descompacte os arquivos do projeto em uma pasta local.**

2.  **Crie e ative um ambiente virtual (recomendado):**
    ```bash
    # No Windows
    python -m venv venv
    .\venv\Scripts\activate

    # No macOS/Linux
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Instale as dependências:**
    Crie um arquivo `requirements.txt` com o seguinte conteúdo:
    ```
    Flask
    Flask-SQLAlchemy
    Flask-Login
    python-dateutil
    ```
    E instale-as com o comando:
    ```bash
    pip install -r requirements.txt
    ```

### Execução

1.  **Execute o arquivo principal da aplicação:**
    ```bash
    python app.py
    ```

2.  **Primeira Execução:**
    - Na primeira vez que você rodar o `app.py`, o sistema criará automaticamente a pasta `db/` e o arquivo de banco de dados `database.db`.
    - Um usuário administrador padrão será criado. Verifique o console do Flask para ver o usuário e a senha gerados (por exemplo, usuário `admin`, senha `admin123`).

3.  **Acesse a Aplicação:**
    - Abra seu navegador e acesse a URL exibida no console, geralmente `http://127.0.0.1:5000` ou `http://localhost:5000`.

### Migração de Banco de Dados

- O sistema utiliza `db.create_all()` para criar o banco de dados inicial. Se você modificar os modelos em `app.py` (adicionando uma nova coluna, por exemplo) após o banco já ter sido criado, esta função **não** atualizará a estrutura da tabela.
- Para desenvolvimento, a maneira mais fácil de aplicar as mudanças é deletar o arquivo `db/database.db` e reiniciar a aplicação. **Atenção: isso apagará todos os dados existentes.**
- Para ambientes com dados importantes, o uso de uma ferramenta de migração como **Flask-Migrate** é recomendado.