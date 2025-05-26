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

##### Estrutura da despezap
├── app.py                     # 🚀 Aplicação principal + Factory + Blueprints
├── config.py                  # ⚙️ Configurações do sistema
├── requirements.txt           # 📦 Dependências Python
├── database/
│   ├── __init__.py
│   └── models.py              # 🗄️ Modelos de dados + ORM + TextProcessor
├── logs/                      # 📝 Arquivos de log do sistema
├── rotas/                    
│   ├── __init__.py
│   ├── auth.py               # 🔐 WEB: Login/Cadastro/Logout + Recuperação senha
│   ├── dashboard.py          # 📊 WEB: Dashboard principal + Resumos + Widgets
│   ├── despesas.py           # 💸 WEB + API + WEBHOOK: CRUD despesas + Relatórios + WhatsApp
│   ├── receitas.py           # 💰 WEB + API + WEBHOOK: CRUD receitas + Relatórios + WhatsApp
│   ├── lembretes.py          # ⏰ WEB + API + WEBHOOK: CRUD lembretes + Notificações + WhatsApp
│   ├── dividas.py            # 💳 WEB + API + WEBHOOK: CRUD dívidas + Pagamentos + WhatsApp
│   ├── categorias.py         # 🏷️ WEB + API: CRUD categorias personalizadas (Premium+)
│   ├── membros.py            # 👥 WEB + API: Gestão membros família/empresa (Família+)
│   ├── relatorios.py         # 📈 WEB + API: Relatórios avançados + Gráficos (Premium+)
│   ├── planos.py             # 💎 WEB + API: Assinaturas + Pagamentos + Upgrades
│   ├── webhooks.py           # 🔗 WEBHOOK: Centralizador WhatsApp + Roteamento + Twilio
│   └── uploads.py            # 📤 API: Upload arquivos + OCR + Transcrição áudio
├── templates/   
│   ├── js/
│   │   ├── dashboard.js      # 📊 JavaScript do dashboard + Gráficos + AJAX
│   │   ├── dividas.js        # 💳 JavaScript gestão dívidas + Calculadoras
│   │   └── lembretes.js      # ⏰ JavaScript lembretes + Notificações browser
│   ├── base.html             # 🎨 Template base + Menu + Layout responsivo
│   ├── index.html            # 🏠 Página inicial + Landing page + WhatsApp link
│   ├── login.html            # 🔐 Formulário login + Validação + Links
│   ├── dashboard.html        # 📊 Dashboard principal + Cards + Resumos
│   ├── despesas.html         # 💸 Lista/Formulário despesas + Filtros + Tabelas
│   ├── receitas.html         # 💰 Lista/Formulário receitas + Filtros + Tabelas
│   ├── lembretes.html        # ⏰ Lista/Formulário lembretes + Calendar + Notifs
│   ├── dividas.html          # 💳 Lista/Formulário dívidas + Calculadoras + Status
│   ├── categorias.html       # 🏷️ CRUD categorias + Ícones + Cores (Premium+)
│   ├── admin_cupons.html     # 🎫 Admin cupons desconto + Gestão promocional
│   ├── relatorios.html       # 📈 Relatórios + Gráficos interativos (Premium+)
│   ├── configuracoes.html    # ⚙️ Configurações usuário + Preferências + Tema
│   ├── metas_financeiras.html # 🎯 Gestão metas + Progresso + Motivação
│   ├── recuperar_senha.html  # 🔑 Formulário recuperação senha + Email
│   ├── orcamentos.html       # 💰 Gestão orçamentos + Limites + Alertas
│   ├── notificacoes.html     # 🔔 Central notificações + Histórico + Config
│   ├── planos.html           # 💎 Comparação planos + Assinatura + Pagamento
│   ├── perfil.html           # 👤 Perfil usuário + Dados pessoais + Segurança
│   └── cadastro.html         # 📝 Formulário cadastro + Validação + Termos
└── static/                  
   ├── images/               # 🖼️ Imagens estáticas + Logos + Ícones
   └── uploads/              # 📁 Arquivos enviados usuários + Comprovantes + Áudios

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