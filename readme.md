# DespeZap - Controle Financeiro via WhatsApp

DespeZap é um sistema de controle financeiro que permite registrar gastos pelo WhatsApp e visualizá-los em um dashboard web responsivo.

## Funcionalidades

- **Registro de despesas via WhatsApp**
  - Envie mensagens como: "Almoço R$ 25,90" 
  - Categorização automática de despesas
  - Relatórios por períodos (dia, semana, mês, ano)
  
- **Dashboard web completo**
  - Visualização de gastos por categoria
  - Análise de tendências ao longo do tempo
  - Exportação de dados para CSV
  
- **Sistema de usuários e assinaturas**
  - Cadastro e login de usuários
  - Plano gratuito e premium
  - Exportação de dados

## Estrutura do Projeto

```
DespeZap/
│
├── app.py                  # Arquivo principal
├── config.py               # Configurações
├── requirements.txt        # Dependências
│
├── database/               # Banco de dados
│   ├── __init__.py
│   ├── models.py           # Modelos de dados
│   └── financas.db         # Banco SQLite
│
├── templates/              # Templates HTML
│   ├── base.html           # Template base
│   ├── index.html          # Página inicial
│   ├── dashboard.html      # Painel de controle
│   ├── login.html          # Página de login
│   └── cadastro.html       # Cadastro de usuários
│
├── static/                 # Arquivos estáticos
│   └── img/
│       └── favicon.ico
│
└── rotas/                  # Rotas da aplicação
    ├── __init__.py
    ├── web_rotas.py        # Rotas web
    ├── api_rotas.py        # Rotas API
    └── webhook_rotas.py    # Webhook WhatsApp
```

## Tecnologias Utilizadas

- **Backend**: Python + Flask
- **Banco de dados**: SQLite
- **Frontend**: HTML, CSS, JavaScript, Bootstrap 5
- **Gráficos**: Plotly.js
- **Integração WhatsApp**: Twilio API

## Como Executar Localmente

### Pré-requisitos

- Python 3.9+
- Conta na Twilio

### Instalação

1. Clone o repositório:
   ```
   git clone https://github.com/seu-usuario/DespeZap.git
   cd DespeZap
   ```

2. Instale as dependências:
   ```
   pip install -r requirements.txt
   ```

3. Configure as variáveis de ambiente:
   ```
   # No Windows
   set TWILIO_ACCOUNT_SID=seu_account_sid
   set TWILIO_AUTH_TOKEN=seu_auth_token
   
   # No Linux/Mac
   export TWILIO_ACCOUNT_SID=seu_account_sid
   export TWILIO_AUTH_TOKEN=seu_auth_token
   ```

4. Execute o aplicativo:
   ```
   python app.py
   ```

5. Acesse no navegador:
   ```
   http://localhost:8080/
   ```

## Configuração do Webhook WhatsApp

1. Use ngrok para expor seu servidor local:
   ```
   ngrok http 8080
   ```

2. Configure o webhook na Twilio:
   - URL: https://seu-dominio-ngrok.io/webhook
   - Método: HTTP POST

3. Conecte seu WhatsApp ao Sandbox da Twilio:
   - Envie a mensagem "join successful-angle" para +1 415 523 8886

## Deploy no Render

Este projeto está configurado para deploy fácil no Render:

1. Crie uma conta no [Render](https://render.com/)

2. Clique em "New +" e selecione "Blueprint"

3. Conecte seu repositório GitHub

4. Selecione o repositório e configure as variáveis de ambiente:
   - `TWILIO_ACCOUNT_SID`: Seu Account SID da Twilio
   - `TWILIO_AUTH_TOKEN`: Seu Auth Token da Twilio
   - `TWILIO_PHONE_NUMBER`: Número do WhatsApp da Twilio (formato: whatsapp:+14155238886)

5. Clique em "Apply" para iniciar o deploy

6. Após o deploy, configure o webhook na Twilio com a URL do seu aplicativo no Render:
   - URL: https://DespeZap.onrender.com/webhook
   - Método: HTTP POST

## Planos e Assinaturas

### Plano Gratuito
- 5 categorias personalizáveis
- Exportação básica em CSV
- 1 usuário

### Plano Premium
- 20 categorias personalizáveis 
- Reconhecimento de imagens (em breve)
- Até 5 usuários
- Exportação avançada

## Licença

Este projeto é licenciado sob a licença MIT.