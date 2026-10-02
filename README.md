# CineData Analytics

Backend FastAPI para consultar o catálogo CineData em português. Usa Pydantic AI e **openai/gpt-oss-120b via Groq**, com SQLite somente leitura. API e banco ficam locais; a inferência exige internet e chave Groq. Perguntas são independentes, sem memória.

**Estado em 02/10/2026:** checkpoint do backend validado e revisão independente sem achados críticos ou importantes. A refatoração preserva os cenários originais e organiza 44 testes, com módulos separados para prompt e comparação. As 22 perguntas foram avaliadas: 21 aprovadas automaticamente e uma confirmada por revisão manual dos números, com formato de evidência diferente. Reprodução em ambiente limpo e demonstração HTTP real aprovadas. A estrutura refatorada aguarda revisão final antes da etapa de interface.

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

Até três chamadas de modelo e duas tentativas SQL por pergunta. Raciocínio `medium`, até 2048 tokens de geração por chamada, temperatura zero e ferramentas sequenciais. O limite de geração inclui raciocínio e passou nos cinco casos iniciais; a avaliação ampliada verifica casos maiores. Prazo total 600 segundos é um teto herdado da avaliação, não uma promessa de latência.

Pergunta, esquema do banco e resultados da ferramenta são enviados ao Groq. O arquivo SQLite permanece local e as consultas rodam no computador. O cliente aceita somente o endpoint HTTPS oficial, sem proxies do ambiente, redirects, retries ou fallback.

Na consulta de 01/10/2026, o plano gratuito publica 30 requisições/minuto, 1000/dia, 8000 tokens/minuto e 200000/dia para esse modelo. Limites são da organização e podem variar; verificar o painel da conta. Tokens, inclusive raciocínio, podem limitar o uso antes das requisições. Não tratar 1000 requisições como 500 perguntas garantidas. [Limites oficiais](https://console.groq.com/docs/rate-limits).

## Proteção SQL

Uma ferramenta de dados, `consultar_sql`, e resposta JSON com status, explicação e avisos. O modelo pode concluir pela ferramenta `json` (`ToolOutput`) ou por texto JSON; ambos são validados pelo mesmo contrato Pydantic, com `avisos` obrigatório, podendo ser vazio. Até duas tentativas SQL e três chamadas permitem obter evidências e corrigir uma consulta inválida. O Groq não permite combinar modo JSON nativo com ferramentas nessa API; respostas inválidas são rejeitadas sem extrair conteúdo de erros e sem retry da saída. Banco estático aberto com `mode=ro&immutable=1`, após verificar ausência de WAL/journal pendente. Conexões fechadas após a consulta; cancelamento interrompe e aguarda o worker.

Autorização SQLite permite somente dez tabelas de negócio e funções analíticas aprovadas. Escrita, DDL, anexação, PRAGMAs do modelo e metadados técnicos são bloqueados. Uma instrução por chamada, com parâmetros vinculados.

Limites: 20 segundos por SQL, 100 linhas, 10000 caracteres de SQL, 50 parâmetros escalares finitos, 12000 caracteres de colunas/linhas e 2000 caracteres por célula de texto. Truncamento é sinalizado. SQL e parâmetros originais ficam preservados como evidência. Mapeamento de leitura até 1 GiB é configuração da conexão, sem alterar o banco. Não usar `immutable=1` com uma base em atualização.

## Testes e avaliação

```powershell
# Testes sintéticos: não precisam de chave e não chamam a nuvem.
.\.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -v

# Gabaritos SQL locais: também é o comportamento sem flags.
.\.venv\Scripts\python.exe -X utf8 -m evaluation.run --references-only

# Chamadas reais ao Groq: exigem chave e consomem cotas.
.\.venv\Scripts\python.exe -X utf8 -m evaluation.run --smoke --interval 60
.\.venv\Scripts\python.exe -X utf8 -m evaluation.run --all --interval 60
.\.venv\Scripts\python.exe -X utf8 -m evaluation.run --all --case 17_melhores --output runtime/groq-reteste.json
```

`evaluation/cases.json` contém 14 exemplos do enunciado e oito complementares associados às 20 regras, com data fixa 30/09/2026. `--smoke` seleciona cinco categorias; `--all` inclui os 22 casos. `--interval 60` espera 60 segundos entre perguntas; essa espera não entra na duração de cada resposta. Não há retry automático ou espera dentro da API. Ajustar o intervalo à cota da organização; perguntas maiores ainda podem atingir HTTP429.

Relatórios incrementais ficam em `runtime/`. Registram fatos/status, duração e uso; memória e quantização do servidor remoto não são medidas. `codigo_agente_sha256` identifica o código do agente e `codigo_prompts_sha256` identifica o módulo de instruções; relatórios anteriores à extração do prompt mantêm o formato original. Erro de cota, indisponibilidade ou prazo interrompe a bateria. Comparação admite SQL diferente, colunas extras e aliases declarados, sem aceitar truncamento ou métricas erradas. Contagens e identificadores são exatos; tolerâncias financeiras 0,01 e notas/margens 0,000001. Explicações e motivos de recusa/esclarecimento exigem revisão manual.

As cinco categorias iniciais passaram na comparação de status/linhas: receita BRL 3,89 s; popularidade 2,25 s; ator na janela móvel 4,50 s; gêneros 2,42 s; avaliações de usuários 2,05 s. Soma de latências 15,11 s, sem contar os intervalos da cota. São medições desta bateria, não uma garantia de tempo ou correção geral.

O consolidado ampliado usa a última execução de cada caso, inclusive falhas, e reúne versões diferentes do prompt e protocolo. Não é uma bateria completa da versão atual. Todos os 22 casos foram avaliados: 21 aprovados automaticamente; a contagem de 2025/2026 foi confirmada manualmente (5 e 1 filmes), pois o SQL retornou anos em colunas e o gabarito usa linhas. O veredito automático desse caso permanece registrado como incorreto por formato; não foi convertido silenciosamente em acerto.

Os retestes corrigiram a inclusão de futuros na média anual e a consulta do par ator/diretor, que retornou Joe Anoa’i e Kevin Dunn, com 37 filmes. Os últimos testes de média anual, pares e margens levaram 14,28/31,72/16,83 segundos, incluindo uma pausa diagnóstica de 10 segundos entre chamadas para respeitar TPM. Essa espera pertence somente à avaliação local; a API não introduz pausa nem retry. Não usar esses tempos como latência normal ou garantia de desempenho.

Explicações também foram revisadas: esclarecimentos pedem identificação sem afirmar homônimos como fato sem SQL. Permanece uma limitação de apresentação: a média anual declarou o ano parcial no texto, com `avisos` vazio. Aprovação nos casos avaliados não garante correção em qualquer pergunta futura.

Foram observados bloqueios por tokens/dia e tokens/minuto, inclusive entre as duas chamadas de uma pergunta. Os diagnósticos registram a espera daquele instante; não são saldo atual nem garantia de completar uma pergunta após a espera. Uma chave válida e a disponibilidade da organização são necessárias para reproduzir a avaliação.

O ambiente limpo instalado exclusivamente por `requirements.txt` foi verificado novamente com os testes reorganizados. Na demonstração do backend, `/health`, `/docs` e uma pergunta real por HTTP retornaram 200; a contagem dos 95.645 filmes levou 1,92 s, com duas chamadas ao Groq e uma SQL, sem pausa diagnóstica. A refatoração manteve instruções e ferramenta SQL idênticas e não repetiu essa chamada à nuvem. O servidor de demonstração foi encerrado e o hash do SQLite permaneceu igual ao original.

## Repositório

`app/main.py` expõe a API; `app/agent.py` executa o agente; `app/prompts.py` contém as instruções e seu builder; `app/database.py` protege a leitura SQLite. `evaluation/run.py` executa a CLI e grava relatórios; `evaluation/grading.py` compara evidências; `evaluation/cases.json` guarda os gabaritos.

Os testes usam fixtures sintéticas em `tests/helpers.py` e se distribuem em `test_database.py`, `test_analytics.py`, `test_agent.py`, `test_groq_adapter.py`, `test_api.py` e `test_evaluation.py`. O comando de descoberta permanece o mesmo, sem dependências adicionais. README e guia de instalação são publicados; `.env`, `.venv`, banco, relatórios e documentos internos ficam excluídos do Git. Não há deploy público; frontend permanece para a etapa posterior.
