# Controle Financeiro via WhatsApp

Um sistema completo de controle financeiro que permite registrar gastos através do WhatsApp usando fotos de comprovantes, mensagens de texto ou áudio.

## Visão Geral

Este aplicativo permite:

- **Registrar gastos via WhatsApp** de 3 maneiras:
  - 📸 **Foto do comprovante**: Reconhecimento automático do valor, data e estabelecimento
  - 💬 **Mensagem de texto**: Ex: "Almoço R$ 25,90" 
  - 🎙️ **Mensagem de áudio**: Sua voz é transcrita e interpretada

- **Dashboard responsivo** para acompanhar suas finanças:
  - 📊 Gráficos de gastos por categoria
  - 📈 Análise de tendências e evolução
  - 📱 Interface otimizada para celular

## Requisitos

- Python 3.8 ou superior
- Conta no Twilio para integração com WhatsApp
- Tesseract OCR (para reconhecimento de comprovantes)
- Vosk (opcional, para reconhecimento de fala)

## Instalação

1. Clone este repositório:
```
git clone https://github.com/seu-usuario/controle-financeiro-whatsapp.git
cd controle-financeiro-whatsapp
```

2. Instale as dependências:
```
pip install -r requirements.txt
```

3. Instale o Tesseract OCR (opcional, para reconhecimento de imagens):
   - Windows: [Baixe o instalador](https://github.com/UB-Mannheim/tesseract/wiki)
   - macOS: `brew install tesseract`
   - Linux: `sudo apt install tesseract-ocr`

4. Configure o Vosk (opcional, para reconhecimento de áudio):
   - Baixe um modelo em português: https://alphacephei.com/vosk/models
   - Descompacte e configure o caminho:
   ```
   # Windows PowerShell
   $env:VOSK_MODEL_PATH = "C:\caminho\para\vosk-model-small-pt-0.3"
   
   # Linux/macOS
   export VOSK_MODEL_PATH="/caminho/para/vosk-model-small-pt-0.3"
   ```

## Configuração

1. Configure suas credenciais do Twilio:
```
# Windows PowerShell
$env:TWILIO_ACCOUNT_SID = "AC44f80c30e4bb518bd8c4a0e48ce0e5cb"
$env:TWILIO_AUTH_TOKEN = "seu_auth_token_aqui"
$env:TWILIO_PHONE_NUMBER = "whatsapp:+14155238886"

# Linux/macOS
export TWILIO_ACCOUNT_SID="AC44f80c30e4bb518bd8c4a0e48ce0e5cb"
export TWILIO_AUTH_TOKEN="seu_auth_token_aqui"
export TWILIO_PHONE_NUMBER="whatsapp:+14155238886"
```

2. Configure o ambiente de sandbox do WhatsApp:
   - Acesse o [Console da Twilio](https://www.twilio.com/console)
   - Vá para "Messaging" → "Try it Out" → "Send a WhatsApp message"
   - Siga as instruções para configurar seu sandbox

## Executando o aplicativo

1. Execute o aplicativo:
```
python app.py
```

2. Configure o webhook do Twilio:
   - Use [ngrok](https://ngrok.com/) para expor seu servidor local:
   ```
   ngrok http 5000
   ```
   - Configure o webhook: `https://seu-dominio-ngrok.io/webhook`

3. Adicione o bot ao seu WhatsApp:
   - Envie a mensagem "join apple-yellow" para o número do sandbox (+1 415 523 8886)

## Como usar

### Via WhatsApp:

1. **Registrar despesa por foto**:
   - Tire uma foto do comprovante/recibo
   - Ele será processado automaticamente

2. **Registrar despesa por texto**:
   - Envie uma mensagem como: "Almoço R$ 25,90"
   - Ou: "Paguei 50 reais de uber hoje"

3. **Registrar despesa por áudio**:
   - Envie uma mensagem de voz descrevendo seu gasto

4. **Comandos disponíveis**:
   - "ajuda" - Ver instruções
   - "resumo" - Ver resumo geral
   - "hoje" - Gastos de hoje
   - "semana" - Relatório da última semana
   - "mês" - Relatório do mês atual

### Via Navegador:

Acesse http://localhost:5000/ para:
- Visualizar o dashboard completo
- Ver gráficos de gastos por categoria
- Analisar tendências ao longo do tempo
- Adicionar despesas/receitas manualmente
- Exportar dados para CSV

## Recursos

- **Reconhecimento automático de categorias**
- **Extração de informações de comprovantes**
- **Transcrição de mensagens de voz**
- **Dashboard responsivo**
- **Relatórios detalhados**
- **Exportação de dados**

## Tecnologias

- **Backend**: Python, Flask
- **Banco de Dados**: SQLite
- **Interface**: HTML, CSS, JavaScript, Bootstrap
- **Gráficos**: Plotly.js
- **WhatsApp**: Twilio API
- **OCR**: Tesseract, OpenCV
- **Reconhecimento de voz**: Vosk

## Limitações e Observações

- Este projeto usa o Sandbox do WhatsApp da Twilio, que tem algumas limitações:
  - Você só pode enviar mensagens para números que já enviaram a mensagem de ativação
  - A conexão precisa ser renovada a cada 72 horas

- Para uso em produção:
  - Solicite a aprovação oficial do WhatsApp Business
  - Use um banco de dados mais robusto (como PostgreSQL)
  - Implemente um sistema de autenticação

## Contribuição

Contribuições são bem-vindas! Sinta-se à vontade para abrir issues ou enviar pull requests.

## Licença

Este projeto está licenciado sob a licença MIT.