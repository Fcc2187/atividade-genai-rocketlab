# CineData Analytics

Backend FastAPI para consultar o catálogo CineData em português. Usa Pydantic AI e **openai/gpt-oss-120b via Groq**, com SQLite somente leitura. API e banco ficam locais; a inferência exige internet e chave Groq. Perguntas são independentes, sem memória.

**Estado em 01/10/2026:** migração para Groq implementada e testes automatizados aprovados. A avaliação real do Groq aguarda uma chave configurada. Resultados antigos do Qwen local não comprovam a qualidade deste modelo. Interface será discutida depois do backend validado.

## Preparar o ambiente

Na raiz do projeto, com [uv](https://docs.astral.sh/uv/getting-started/installation/) instalado:

```powershell
uv venv --python 3.12.14 .venv
uv pip install --python .venv\Scripts\python.exe --link-mode copy -r requirements.txt
uv pip check --python .venv\Scripts\python.exe
Copy-Item .env.example .env
```

Os comandos criam um ambiente novo; nesta máquina, Python e dependências já estão instalados. Não sobrescrever um `.env` já preenchido. As 34 dependências estão fixadas em [requirements.txt](requirements.txt). O SDK OpenAI instalado acessa o endpoint compatível do Groq, conforme a [documentação oficial](https://console.groq.com/docs/openai); não utiliza conta OpenAI ou assinatura Plus.

Obter `cinerocket (1).db` nos materiais da atividade e colocá-lo na raiz. A base não acompanha o Git. Deve permanecer estática e intacta, sem limpeza, índices ou migrações. SHA-256 original: `410f5beef6ab9fb34b9044d5dd191f56f3f0dc30a56e6432386ecef0d977b012`.

## Configurar o Groq

1. Entrar ou criar uma conta no [Groq Console](https://console.groq.com/).
2. Abrir [API Keys](https://console.groq.com/keys) e criar uma chave.
3. Preencher somente no arquivo local `.env`:

```dotenv
DATABASE_PATH="cinerocket (1).db"
MODEL_PROVIDER=groq
MODEL_NAME=openai/gpt-oss-120b
MODEL_BASE_URL=https://api.groq.com/openai/v1
GROQ_API_KEY=SUA_CHAVE_GROQ
QUESTION_TIMEOUT_SECONDS=600
```

Substituir `SUA_CHAVE_GROQ` pelo valor real. `.env` está ignorado no Git; não enviar a chave em mensagens ou commits. Variáveis já definidas no terminal têm precedência sobre `.env`. Reiniciar a API após mudar a configuração.

Não é necessário baixar pesos, instalar Groq SDK ou iniciar um servidor de modelo. O guia completo está em [INSTALACAO_MODELO.md](docs/INSTALACAO_MODELO.md).

## Executar e consultar

```powershell
.\.venv\Scripts\python.exe -X utf8 -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Abrir `http://127.0.0.1:8000/docs`. `GET /health` verifica somente o banco, sem consumir inferência ou validar a chave.

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
$body = @{ pergunta = 'Quantos filmes existem por gênero?' } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8000/perguntas' -ContentType 'application/json; charset=utf-8' -Body ([System.Text.Encoding]::UTF8.GetBytes($body))
```

`POST /perguntas` recebe uma pergunta com até 2000 caracteres. Retorna `status`, `resposta`, `avisos`, `consultas` (SQL, parâmetros, colunas, linhas e truncamento), `modelo` e `uso` (chamadas, tokens e tentativas SQL). Status: resultado, esclarecimento, recusa ou sem_dados. Referência temporal: data local do computador.

Erros: 422 para entrada inválida; 503 para banco/configuração/Groq indisponível ou cota excedida; 502 para resposta inválida/limite operacional; 504 para prazo. `detail` contém código e mensagem, sem chave ou detalhes internos. `cota_excedida` identifica HTTP429 recebido do Groq; a aplicação não repete automaticamente. Encerrar com `Ctrl+C`.

## Limites e dados enviados

Até três chamadas de modelo e duas tentativas SQL por pergunta. Raciocínio inicial `medium`, até 2048 tokens de geração por chamada, temperatura zero e ferramentas sequenciais. O limite de geração precisa ser validado com o modelo real e inclui o orçamento de raciocínio. Prazo total 600 segundos é um teto herdado da avaliação, não uma promessa de latência.

Pergunta, esquema do banco e resultados da ferramenta são enviados ao Groq. O arquivo SQLite permanece local e as consultas rodam no computador. O cliente aceita somente o endpoint HTTPS oficial, sem proxies do ambiente, redirects, retries ou fallback.

Na consulta de 01/10/2026, o plano gratuito publica 30 requisições/minuto, 1000/dia, 8000 tokens/minuto e 200000/dia para esse modelo. Limites são da organização e podem variar; verificar o painel da conta. Tokens, inclusive raciocínio, podem limitar o uso antes das requisições. Não tratar 1000 requisições como 500 perguntas garantidas. [Limites oficiais](https://console.groq.com/docs/rate-limits).

## Proteção SQL

Uma ferramenta de dados, `consultar_sql`, e resposta estruturada `responder`. Banco estático aberto com `mode=ro&immutable=1`, após verificar ausência de WAL/journal pendente. Conexões fechadas após a consulta; cancelamento interrompe e aguarda o worker.

Autorização SQLite permite somente dez tabelas de negócio e funções analíticas aprovadas. Escrita, DDL, anexação, PRAGMAs do modelo e metadados técnicos são bloqueados. Uma instrução por chamada, com parâmetros vinculados.

Limites: 20 segundos por SQL, 100 linhas, 10000 caracteres de SQL, 50 parâmetros escalares finitos, 12000 caracteres de colunas/linhas e 2000 caracteres por célula de texto. Truncamento é sinalizado. SQL e parâmetros originais ficam preservados como evidência. Mapeamento de leitura até 1 GiB é configuração da conexão, sem alterar o banco. Não usar `immutable=1` com uma base em atualização.

## Testes e avaliação

```powershell
# Testes sintéticos: não precisam de chave e não chamam a nuvem.
.\.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -v

# Gabaritos SQL locais: também é o comportamento sem flags.
.\.venv\Scripts\python.exe -X utf8 -m evaluation.run --references-only

# Chamadas reais ao Groq: exigem chave e consomem cotas.
.\.venv\Scripts\python.exe -X utf8 -m evaluation.run --smoke
.\.venv\Scripts\python.exe -X utf8 -m evaluation.run --all --case 17_melhores --output runtime/groq-reteste.json
```

`evaluation/cases.json` contém 14 exemplos do enunciado e oito complementares associados às 20 regras, com data fixa 30/09/2026. `--smoke` seleciona cinco categorias; `--all` inclui os 22 casos. Executar os casos com intervalo compatível com a cota de tokens/minuto; uma bateria sequencial rápida também pode atingir HTTP429.

Relatórios incrementais ficam em `runtime/`. Registram fatos/status, duração e uso; memória e quantização do servidor remoto não são medidas. Erro de cota, indisponibilidade ou prazo interrompe a bateria. Comparação admite SQL diferente, colunas extras e aliases declarados, sem aceitar truncamento ou métricas erradas. Contagens e identificadores são exatos; tolerâncias financeiras 0,01 e notas/margens 0,000001. Explicações e motivos de recusa/esclarecimento exigem revisão manual.

A migração ainda não tem métricas reais de velocidade, consumo ou acerto. Preservamos os relatórios anteriores para comparação; não apresentamos seus resultados como validação do Groq.

## Repositório

Código em `app/`, avaliação em `evaluation/`, testes em `tests/`. README e guia de instalação são publicados. `.env`, `.venv`, banco, relatórios e documentos internos ficam excluídos do Git. Não há deploy público; frontend permanece para a etapa posterior.
