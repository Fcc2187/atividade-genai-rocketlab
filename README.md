# CineData Analytics

Backend local com SQL protegido, agente Qwen e rotas FastAPI implementados. Os 22 testes simulados passam; a avaliação analítica com o modelo real ainda está pendente.

## Ambiente Python

Python **3.12.14** foi localizado na instalação existente do uv e reutilizado. O ambiente virtual do projeto está em `.venv`, no D:. O `python` do PATH pode apontar para o atalho da Microsoft Store; usar diretamente o executável do ambiente:

```powershell
.\.venv\Scripts\python.exe --version
```

Para reproduzir o ambiente com [uv](https://docs.astral.sh/uv/guides/install-python/), na raiz do projeto:

```powershell
uv venv --python 3.12.14 .venv
uv pip install --python .venv\Scripts\python.exe --link-mode copy -r requirements.txt
uv pip check --python .venv\Scripts\python.exe
```

Esses comandos são para criar um ambiente novo. A `.venv` desta máquina já está pronta. O uv pode obter o Python se necessário; a instalação inicial das bibliotecas exige internet. `--link-mode copy` permite copiar os pacotes do cache no C: para o ambiente no D:.

As 34 dependências diretas e transitivas estão fixadas em [requirements.txt](requirements.txt). Bibliotecas utilizadas diretamente:

| Biblioteca | Versão |
|---|---|
| FastAPI | 0.142.2 |
| Uvicorn | 0.54.0 |
| Pydantic AI slim, extra OpenAI-compatible | 2.52.0 |
| Pydantic | 2.13.5 |
| SDK OpenAI, usado para o protocolo local | 3.22.1 |
| python-dotenv | 1.2.3 |
| HTTPX | 0.28.1 |

`requirements.txt` contém também as dependências do extra `[openai]`. Fixar versões torna reproduzível este ambiente; nenhuma dependência de provedor Groq/OpenRouter foi adicionada.

## Configuração local

`.env.example` é a referência versionável; `.env` já foi criado e está ignorado no Git. Para uma cópia nova do projeto, criar `.env` a partir do exemplo:

```powershell
Copy-Item .env.example .env
```

Configuração atual: banco `cinerocket (1).db`, provedor `llamafile`, alias `qwen3.5-9b`, URL `http://127.0.0.1:8081/v1` e prazo provisório de 180 segundos. Nenhuma chave de nuvem é necessária. A `.python-version` registra a versão do interpretador.

## Verificações do setup

- Python 3.12.14 e importações das bibliotecas: aprovados.
- Compatibilidade das 34 dependências: `uv pip check` aprovado.
- Reprodução de `requirements.txt` em ambiente virtual limpo: instalação e importações aprovadas; ambiente temporário removido após o teste.
- Construção de `OpenAIChatModel`/`OpenAIProvider` com cliente local e `max_retries=0`: aprovada sem chamada de inferência. Saída tipada do agente ainda será testada na implementação.
- Banco aberto com URI `mode=ro&immutable=1`, após verificar ausência de WAL; 11 tabelas encontradas. SHA-256 preservado: `410f5beef6ab9fb34b9044d5dd191f56f3f0dc30a56e6432386ecef0d977b012`.
- `.env`, `.venv`, pesos, runtime, banco e materiais locais estão ignorados no Git. O README e o guia de instalação acompanham o setup versionado.

As verificações acima são do setup. A suíte atual também cobre SQL protegido, gabaritos e agente simulado; o contrato HTTP e a qualidade analítica do modelo ainda precisam ser verificados.

## Ferramenta SQL protegida

`app/database.py` fornece `read_schema` e `execute_readonly`. A ferramenta usa URI `mode=ro&immutable=1` para a base estática, recusa arquivos com WAL ou journal pendente e fecha a conexão após cada consulta. Não usar esse modo com uma base em atualização.

A autorização do SQLite permite leitura somente das dez tabelas de negócio e funções analíticas aprovadas. Escrita, DDL, anexação de outros bancos, PRAGMAs, funções não autorizadas e tabelas técnicas são bloqueados. Valores são vinculados como parâmetros; apenas uma instrução SQL é executada.

Limites calibrados: 20 segundos por consulta, até 100 linhas, SQL com até 10.000 caracteres e até 50 parâmetros escalares finitos. A consulta de pares ator/diretor na base fornecida precisou de aproximadamente 12,5 segundos após revisão dos joins; o limite inicial de cinco segundos era insuficiente. Nenhum índice foi criado. O resultado enviado ao agente terá até 12.000 caracteres de colunas/linhas, com textos de até 2.000 caracteres por célula. Truncamento é sinalizado; SQL e parâmetros originais são preservados como evidência. Operações SQL internas também têm limites de tamanho. O prazo externo da pergunta pode reduzir o prazo SQL.

Para executar os testes sintéticos, sem iniciar o modelo:

```powershell
.\.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -v
```

Os testes usam SQLite temporário. Leituras de contagem, receita, lucro médio por gênero e diretores também foram verificadas na base fornecida; o hash permaneceu inalterado e nenhum arquivo WAL/SHM foi criado.

## Referências analíticas

`evaluation/cases.json` contém os 14 exemplos do enunciado e oito casos complementares. Cada caso declara data fixa (30/09/2026), status esperado, convenções, tolerância e SQL revisado. O campo `regras` associa os casos às 20 convenções: moeda/valores ausentes (1–6), margem/médias/notas (7–11), datas/diretores/empates/joins (12–15), ausência/ambiguidade/cobertura/anos parciais (16–20).

```powershell
.\.venv\Scripts\python.exe -X utf8 -m evaluation.run --references-only
```

O comando executa somente SQL local e grava `runtime/reference-results.json`, ignorado pelo Git. Sem flags, o comportamento é o mesmo. Não chama o Qwen. Valores financeiros usam tolerância absoluta de 0,01; notas e margens, 0,000001; contagens e identificadores são exatos. A comparação aceita SQL diferente e considera os resultados, a ordem solicitada e o truncamento. Casos de esclarecimento avaliam a necessidade de informação adicional, sem exigir uma frase literal.

## Agente local

`app/agent.py` usa Pydantic AI com uma ferramenta de dados (`consultar_sql`) e saída tipada (`status`, `resposta`, `avisos`). SQL, parâmetros, linhas e uso são registrados pelo backend. Cada pergunta tem estado próprio, sem histórico ou memória.

Até três chamadas de modelo e duas tentativas SQL, incluindo argumentos inválidos e erros. Um erro SQL corrigível permite uma correção; bloqueio de segurança encerra com recusa. SQL roda fora do event loop; ao cancelar a pergunta, o worker recebe um sinal de interrupção e é aguardado. Resultados analíticos exigem uma consulta válida. Transporte sem retries, proxies do ambiente ou redirects; URL obrigatoriamente de loopback. Não usa OpenAI Plus nem API de nuvem.

Prova real de compatibilidade: ferramenta sintética `somar(7, 5)` e saída `AgentAnswer` aprovadas no Qwen. A repetição com cache levou 39,45 s, duas chamadas, 1.003 tokens de entrada (963 em cache) e 97 de saída. Isso não mede perguntas sobre o catálogo. Prompt real com esquema e 20 regras: 2.570 tokens antes de resultados, com geração máxima de 1.024 e contexto de 8.192. Prazo total inicial de 180 s ainda depende da avaliação analítica em CPU.

## Modelo local no Windows

Usar a pasta do projeto no D:. O llamafile é portátil; não é necessário alterar o PATH ou instalar o modelo globalmente. Runtime e pesos separados ocupam cerca de 6,73 GB no disco e estão ignorados no Git. A prova local atingiu aproximadamente 6,5 GB de RAM residente no processo; tamanho do arquivo não equivale à memória total necessária.

1. Criar os diretórios `runtime` e `models` na raiz do projeto.
2. Baixar o [runtime completo llamafile 0.10.6](https://github.com/mozilla-ai/llamafile/releases/download/0.10.6/llamafile-0.10.6) como `runtime/llamafile.exe` e os [pesos Qwen3.5 9B Q5_K_S na revisão fixada](https://huggingface.co/unsloth/Qwen3.5-9B-GGUF/resolve/3885219b6810b007914f3a7950a8d1b469d598a5/Qwen3.5-9B-Q5_K_S.gguf) como `models/Qwen3.5-9B-Q5_K_S.gguf`.
3. Conferir os SHA-256 com `Get-FileHash -Algorithm SHA256` e os valores em [registro de instalação](docs/INSTALACAO_MODELO.md).
4. Em PowerShell, na raiz do projeto, iniciar o servidor:

   ```powershell
   .\run-model.ps1
   ```

   Se a política de execução bloquear scripts locais, executar em um processo isolado, sem alterar a política do sistema:

   ```powershell
   powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\run-model.ps1
   ```

5. Aguardar o carregamento. Em outro terminal, verificar `http://127.0.0.1:8081/health` e `http://127.0.0.1:8081/v1/models`. O alias configurado é `qwen3.5-9b`.

Configuração inicial: CPU com quatro threads, contexto de 8192 tokens, uma geração ativa e ferramentas internas desativadas. A API está restrita ao próprio computador. As chamadas do cliente devem enviar `chat_template_kwargs: {"enable_thinking": false}` e limitar a geração inicialmente a 1024 tokens.

Para parar o servidor, usar `Ctrl+C` no terminal em que ele foi iniciado. O modelo continua instalado no disco e será carregado novamente na próxima execução. Internet é necessária para os downloads; inferência local dispensa internet, conta e chave de nuvem.

## Prova da instalação

Com o servidor iniciado e Node.js disponível (22.16 usado nesta sessão), executar:

```powershell
node .\test-model.mjs
```

O script verifica o alias, uma saudação e um ciclo sintético de ferramenta com soma 7 + 5 = 12. Os resultados e tempos são gravados em `runtime/smoke-result.json`. Ele não acessa o SQLite. O Node é usado apenas nesta prova; o backend planejado será Python.

Inferência verificada não substitui avaliação analítica: integração Pydantic AI, regras analíticas e exemplos do enunciado serão implementados e testados nas próximas etapas.

## API local

Com o modelo iniciado, abrir outro terminal na raiz do projeto:

```powershell
.\.venv\Scripts\python.exe -X utf8 -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Documentação interativa: `http://127.0.0.1:8000/docs`. `GET /health` verifica somente o banco, sem inferência. Exemplo:

```powershell
$body = @{ pergunta = 'Quantos filmes existem por gênero?' } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8000/perguntas' -ContentType 'application/json; charset=utf-8' -Body ([System.Text.Encoding]::UTF8.GetBytes($body))
```

`POST /perguntas` devolve `status`, `resposta`, `consultas` (SQL, parâmetros, colunas, linhas e truncamento), `avisos`, `modelo` e `uso`. Perguntas são independentes, com até 2.000 caracteres após remover espaços externos. Data de referência é a data local do computador. Configuração inválida não troca provedor automaticamente.

Erros: 422 para entrada inválida; 503 para banco/modelo/configuração indisponível; 502 para resposta inválida ou limite/contexto excedido; 504 para prazo excedido. O corpo `detail` traz `codigo` e `mensagem`, sem detalhes internos. Encerrar a API com `Ctrl+C`; o cliente do modelo é fechado no ciclo de vida da aplicação.

## Banco e desenvolvimento posterior

O SQLite fornecido se chama `cinerocket (1).db` e deve permanecer intacto. Obter a base nos materiais da atividade; ela não será incluída no Git. Interface será discutida somente depois do backend. Planejamento interno e materiais da atividade ficam apenas no computador local.
