# MVP de atendimento automático no WhatsApp com IA

Backend local em FastAPI que recebe mensagens de texto da WhatsApp Cloud API,
gera respostas com Ollama local ou OpenAI e as envia ao cliente. O Ollama é o provedor
padrão para permitir testes locais sem custo de API.

## Demo comercial visual

Com `DEMO_MODE=true`, a página inicial oferece uma demonstração completa sem Meta,
WhatsApp, Ollama ou qualquer API externa. O catálogo e as regras comerciais ficam no
serviço `app/services/demo_chat_service.py`, e o histórico é mantido em memória por
`session_id`.

Depois de iniciar o Uvicorn, abra:

```text
http://localhost:8000/
```

A interface possui sugestões rápidas, indicador de digitação, contexto entre mensagens
e botão **Nova conversa**. O endpoint usado pela tela é `POST /chat`; `POST /reset`
limpa a sessão. Para voltar a usar uma IA no endpoint da demo, altere
`DEMO_MODE=false`; Ollama ou OpenAI será escolhido por `AI_PROVIDER`.

## Arquitetura

```text
app/
├── main.py                       # Endpoints, validação do webhook e orquestração
├── config.py                     # Ambiente e contexto editável da loja
├── models.py                     # Modelos Pydantic
├── prompts/sales_assistant.py    # System prompt comercial
├── services/ai_service.py        # Seleção do provedor de IA
├── services/demo_chat_service.py # Catálogo, regras e sessões da demo
├── services/ollama_service.py    # Integração local com Ollama
├── services/openai_service.py    # Integração opcional com OpenAI
├── services/whatsapp_service.py  # Envio pela WhatsApp Cloud API
└── utils/
    ├── logger.py                 # Logs e mascaramento de telefone
    └── message_store.py          # Deduplicação em memória
```

Os arquivos `app/static/index.html`, `styles.css` e `app.js` formam a interface web.

O histórico não é persistido. A deduplicação é perdida ao reiniciar e deve ser
substituída por Redis ou banco de dados em produção. A separação em serviços permite
adicionar depois PostgreSQL, catálogo, estoque, preços, handoff humano, CRM, painel,
follow-up e RAG sem incluí-los neste MVP.

## Executar no Windows (PowerShell)

Requer Python 3.12 ou superior.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

## Configurar o Ollama gratuito

Instale o Ollama para Windows e baixe o modelo configurado no `.env`:

```powershell
ollama pull llama3.2:3b
ollama run llama3.2:3b
```

Após o download, você pode encerrar o chat do terminal com `/bye`. O aplicativo do
Ollama continua servindo sua API local em `http://localhost:11434`.

O `.env` padrão deve conter:

```env
AI_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:3b
```

Não é necessário preencher `OPENAI_API_KEY` ao usar Ollama. Depois, inicie a API:

```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Teste o health check:

```powershell
Invoke-RestMethod http://localhost:8000/health
```

Teste a IA antes de configurar a Meta (`APP_ENV=development`):

```powershell
Invoke-RestMethod -Method Post `
  -Uri http://localhost:8000/test-chat `
  -ContentType 'application/json' `
  -Body '{"message":"Quero um iPhone 15 Pro"}'
```

Também há documentação interativa em `http://localhost:8000/docs`.

## Expor o webhook com ngrok

1. Crie uma conta e instale o ngrok seguindo a documentação do serviço.
2. Configure o token de autenticação fornecido pelo ngrok.
3. Com a API na porta 8000, execute:

```powershell
ngrok http 8000
```

4. Copie a URL HTTPS, por exemplo `https://abc123.ngrok-free.app`.
5. No painel Meta for Developers, configure a Callback URL como
   `https://abc123.ngrok-free.app/webhook`.
6. Informe exatamente o mesmo valor criado por você em `WHATSAPP_VERIFY_TOKEN`.
7. Valide o webhook e assine o campo/evento `messages`.
8. No painel de configuração da API, autorize seu telefone como destinatário de teste.
9. Envie uma mensagem ao número de teste do WhatsApp fornecido pela Meta.

A URL gratuita do ngrok pode mudar após reiniciar. Nesse caso, atualize a Callback URL.
Cloudflare Tunnel também pode ser usado, apontando uma URL HTTPS para `localhost:8000`.

## Dados necessários na Meta

Em **Meta for Developers > seu app > WhatsApp > API Setup/Configuration**, obtenha:

- **Access Token** temporário para teste ou permanente para uso contínuo → `WHATSAPP_TOKEN`;
- **Phone Number ID** (não é o número em si) → `WHATSAPP_PHONE_NUMBER_ID`;
- versão ativa da Graph API → `WHATSAPP_API_VERSION` (incluindo o `v`);
- **App Secret** em configurações básicas → `META_APP_SECRET` (recomendado);
- WhatsApp Business Account (WABA) ID, necessário no painel, mas não usado diretamente pelo código;
- número de teste do WhatsApp;
- seu telefone destinatário, autorizado no painel durante os testes.

Crie você mesmo um segredo aleatório para `WHATSAPP_VERIFY_TOKEN`; ele não é fornecido
pela Meta. O valor deve ser idêntico no `.env` e na configuração do webhook.

Para usar OpenAI no lugar do Ollama, configure `AI_PROVIDER=openai`, crie uma API key →
`OPENAI_API_KEY` e escolha um modelo disponível na sua conta → `OPENAI_MODEL`. Não
coloque nenhuma credencial no repositório.

## Segurança e comportamento

- Quando `META_APP_SECRET` está preenchido, todo POST precisa ter uma assinatura válida
  `X-Hub-Signature-256`. Deixá-lo vazio desativa essa validação somente para facilitar
  testes locais manuais.
- O payload é lido defensivamente; status e mídias são ignorados.
- Os logs mascaram telefones e nunca imprimem tokens, mas exibem texto e resposta para
  depuração. Avalie remover esse conteúdo dos logs em produção por privacidade.
- Exceções internas não são retornadas aos clientes.
- Em falha do provedor de IA, o bot tenta enviar uma resposta genérica. Falhas do WhatsApp são
  somente registradas.

## Limitações intencionais

Somente texto, uma resposta por evento, sem contexto entre mensagens, banco, Redis,
Docker, autenticação, frontend, painel, catálogo, RAG ou transferência humana. Para
produção, use uma fila de tarefas, persistência idempotente, política de retenção de
logs, observabilidade e testes automatizados.
