# CineData Analytics

Aplicação local para consultar o catálogo CineData em português, com interface React e backend FastAPI. Usa Pydantic AI e **openai/gpt-oss-120b via Groq**, com SQLite somente leitura. Interface, API e banco ficam locais; a inferência exige internet e chave Groq. Perguntas são independentes, sem memória.

## Vídeo instrutivo

Conheça o **CineData Analytics em ação** e acompanhe o uso da aplicação em uma demonstração guiada. O vídeo complementa a documentação com uma apresentação prática da experiência de consulta.


https://github.com/user-attachments/assets/93d392f0-f24c-46e9-9885-1924fb363b89


## Preparar o ambiente

Na raiz do projeto, com [uv](https://docs.astral.sh/uv/getting-started/installation/) instalado:

```powershell
uv venv --python 3.12.14 .venv
uv pip install --python .venv\Scripts\python.exe --link-mode copy -r requirements.txt
uv pip check --python .venv\Scripts\python.exe
if (-not (Test-Path -LiteralPath .env)) {
    Copy-Item -LiteralPath .env.example -Destination .env
}
```

Os comandos criam um ambiente novo; se ele já existir, reutilizá-lo e conferir as dependências. Executar a cópia de `.env.example` somente se `.env` não existir. As 34 dependências de execução estão fixadas em [requirements.txt](requirements.txt). O [guia complementar](docs/INSTALACAO_MODELO.md) inclui instalação nova em PowerShell e Linux/macOS. O SDK OpenAI instalado acessa o endpoint compatível do Groq, conforme a [documentação oficial](https://console.groq.com/docs/openai); não utiliza conta OpenAI ou assinatura Plus.

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

Erros: 413 para solicitação grande demais; 422 para entrada inválida; 503 para banco/configuração/Groq indisponível ou cota excedida; 502 para resposta inválida/limite operacional; 504 para prazo. `detail` contém código e mensagem, sem chave ou detalhes internos. `solicitacao_grande_demais` identifica HTTP413 recebido do Groq e orienta pedir menos resultados ou usar filtros; esperar não reduz o tamanho. `cota_excedida` identifica HTTP429. A aplicação não repete automaticamente. [Erros oficiais](https://console.groq.com/docs/errors). Encerrar com `Ctrl+C`.

## Logs do backend

O terminal do backend exibe os eventos da aplicação como linhas JSON em `stderr`,
com `timestamp` UTC, `level`, `logger`, `event` e `request_id`. Os logs próprios do
Uvicorn continuam no formato dele: acesso HTTP e inicialização do servidor não
substituem os eventos correlacionados do CineData.

`LOG_LEVEL=INFO` é o padrão. Para diagnóstico adicional, definir `LOG_LEVEL=DEBUG`
no `.env` e reiniciar o backend, ou usar no PowerShell antes de iniciar o Uvicorn:

```powershell
$env:LOG_LEVEL = 'DEBUG'
.\.venv\Scripts\python.exe -X utf8 -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Um nível inválido volta para INFO com o evento constante `log_level_invalid`, sem
imprimir o valor recebido. O nível da aplicação não ativa DEBUG em SDKs ou clientes
HTTP. Em INFO, sucessos de `/health` ficam ocultos; falhas continuam visíveis.

Cada requisição recebe um ID gerado pelo servidor, retornado no header
`X-Request-ID`, inclusive nos erros tratados e na validação 422. Localize esse ID
no terminal para acompanhar `request_started`, `question_received`, as operações
observadas e um único evento terminal: `request_completed`, `request_failed` ou
`request_cancelled`. IDs enviados pelo cliente são ignorados. Exceções inesperadas
são registradas com segurança e continuam propagando; a resposta 500 produzida
pela camada externa do servidor pode não ter esse header.

As durações usam relógio monotônico e são expressas em milissegundos:

- `quota_lock_wait_finished` (DEBUG): espera para adquirir a trava do modelo.
- `quota_wait_started` e `quota_wait_finished`: previsão e duração observada da
  espera pela janela de cota; `cancelled` indica uma espera interrompida.
- `model_request_started`, `model_request_finished` e `model_request_failed`:
  chamadas efetivamente iniciadas, numeradas por pergunta, e tempo somente da
  chamada, após as esperas. Tokens não informados permanecem `null`.
  A conclusão informa `token_limit`, `remaining_tokens`, `reset_tokens_ms` e
  `cached_tokens`; valores inválidos viram `null`. Headers completos não são registrados.
- `sql_started` e `sql_finished`: execuções reais da ferramenta SQL, tentativa,
  duração, número de linhas e truncamento. Argumentos rejeitados antes da execução
  continuam consumindo a tentativa existente, mas não geram início SQL.
- `sql_retry_requested`, `sql_rejected` e `quota_blocked`: correção já prevista,
  rejeição ou bloqueio local, com códigos e categorias constantes.
- `sql_reused`: uma chamada idêntica, já recebida na mesma resposta do modelo,
  reutilizou a evidência da pergunta, sem outra execução SQL ou evidência duplicada.
- `answer_validated`: status de domínio e número de avisos. `recusa`,
  `esclarecimento` e `sem_dados` são respostas válidas.

Estes dois JSONs são **exemplos fictícios e ilustrativos**, não resultados de uma
execução real:

```json
{"timestamp":"2026-10-05T12:00:00+00:00","level":"INFO","logger":"cinedata","event":"request_completed","request_id":"11111111111111111111111111111111","http_status":200,"duration_ms":3200,"response_status":"resultado","chamadas":2,"tokens_entrada":null,"tokens_saida":null,"tentativas_sql":1}
{"timestamp":"2026-10-05T12:01:00+00:00","level":"WARNING","logger":"cinedata","event":"request_failed","request_id":"22222222222222222222222222222222","http_status":503,"duration_ms":800,"code":"cota_excedida","stage":"model","exception_type":"ProviderRateLimited"}
```

Mesmo em DEBUG, essa camada omite pergunta, prompts, esquema, SQL, parâmetros,
linhas de resultados, raciocínio, credenciais e mensagens/corpos de erros do
provedor. Diagnóstico de exceções pode mostrar apenas arquivo, função e linha,
sem caminhos completos, código-fonte, variáveis locais ou causas encadeadas.
Não há opção para liberar payloads. Logs não acrescentam chamadas, consultas ou
retries. A cota continua coordenada **por processo**; os eventos não corrigem a
coordenação entre múltiplas instâncias. A CLI de avaliação mantém sua saída atual.

## Interface web

Instalar Node.js 22.16+ na linha 22, ou 24+, e npm. Versão usada nesta implementação: Node 22.16.0 / npm 10.9.2. Com o backend configurado acima, usar dois terminais na raiz:

```powershell
# Terminal 1 — backend, com .env e banco locais.
.\.venv\Scripts\python.exe -X utf8 -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# Terminal 2 — instalar pelo lockfile e iniciar a interface.
cd frontend
npm.cmd ci
npm.cmd run dev
```

Abrir `http://127.0.0.1:5173`. Os comandos `npm.cmd` evitam o bloqueio de `npm.ps1` na política padrão do PowerShell; em outros terminais, usar `npm`. Encerrar cada servidor com `Ctrl+C`.

React + TypeScript + Vite, com [plugin oficial Tailwind para Vite](https://tailwindcss.com/docs/installation/using-vite). `frontend/vite.config.ts` encaminha `/api/perguntas` e `/api/health` para o FastAPI em `127.0.0.1:8000`, removendo `/api`. O frontend envia apenas `{ "pergunta": "..." }`, sem conversa anterior. A chave Groq fica exclusivamente no `.env` do backend; não criar uma variável `VITE_*` para ela.

Seis perguntas sugeridas cobrem bilheteria em USD, popularidade, nota IMDb, avaliações de usuários, quantidade por gênero e média IMDb por diretor. Aparecem em duas colunas no desktop e uma no mobile; clicar preenche e foca o campo, e enviar é uma ação explícita. Limite de 2000 caracteres Unicode, tempo decorrido real em segundos e bloqueio de envio duplicado. A tela representa resultado, esclarecimento, ausência de dados, recusa e erros, sem progresso fictício nem retries automáticos. Para conferir o banco, use o endpoint `/health` descrito acima; esse check não garante disponibilidade ou cota do Groq.

Histórico fica na memória da aba e desaparece ao recarregar. No desktop, aparece na lateral; no mobile, o botão “Histórico” abre um drawer modal, com foco contido e fechamento por Escape. Revisitar respostas não chama o modelo. “Reformular pergunta” e “Revisar filtros” recuperam a pergunta original completa e focam o campo; cada novo envio é independente. “Fazer outra pergunta” limpa o formulário na recusa, preservando o histórico. Cada consulta mostra sua lista ou tabela diretamente no resultado; esclarecimentos usam tabelas de contexto. SQL, parâmetros e valores originais permanecem expansíveis. Avisos e truncamento aparecem antes dos dados. Modelo e uso ficam em detalhes adicionais. A resposta é texto, sem executar HTML do modelo. “Como usar” explica o fluxo e seus limites.

Copiar usa a área de transferência do navegador; se a permissão falhar, a interface orienta copiar manualmente. Há um botão CSV por consulta, acessível sem abrir SQL. Exportar usa BOM UTF-8, vírgulas, aspas escapadas e linhas CRLF. Textos que poderiam virar fórmulas em planilhas recebem apóstrofo de proteção; números negativos continuam números. Valores nulos e textos vazios têm rótulos distintos na tela e viram células vazias no CSV. Exportações truncadas contêm somente os dados recebidos e usam nome com `-truncada.csv`. A apresentação formata moedas e margens pelos aliases explícitos; SQL e CSV mantêm valores e precisão originais.

Identidade editorial com Lora, DM Sans e IBM Plex Mono servidas localmente, com licenças em `frontend/public/fonts/`; fontes obtidas do [repositório oficial Google Fonts](https://github.com/google/fonts). Logo cinematográfica com versões clara/escura e wordmark nativo “cinedata”. Lua/sol alternam o tema: sem escolha explícita, a interface segue a preferência do sistema; a escolha fica em `localStorage`, independentemente do histórico. Storage bloqueado não impede usar o tema. Layout responsivo, foco visível, navegação por teclado e tabelas com rolagem horizontal interna. A interface respeita `prefers-reduced-motion`.

Filmes identificados nas evidências incluem pôster, título, ano quando recebido e valores. O agente recebe instruções para selecionar `sk_movie_id`, `titulo`, `ano_lancamento` e `url_poster` quando disponíveis em resultados individuais, sem incluir esses campos em agregações nem excluir filmes por falta de imagem. Isso orienta o modelo, mas não garante todas as consultas futuras. URL ausente/inválida ou download com erro usa “Pôster indisponível”. Resultados sem metadados suficientes, títulos incompletos e agregações continuam visíveis em tabelas. A interface não chama o modelo novamente nem consulta outra API para completar imagens. Os pôsteres em `frontend/tests/assets/` são fixtures visuais do protótipo, não um catálogo fixo do produto.

Build e verificação, dentro de `frontend/`:

```powershell
npm.cmd run typecheck
npm.cmd run lint
npm.cmd run build
npm.cmd run format:check
npx.cmd playwright install chromium
npm.cmd test
# Ou todas as verificações após instalar o navegador:
npm.cmd run verify

# Conferir o build local, mantendo o backend em execução:
npm.cmd run preview
```

Build gera `frontend/dist/`; preview abre `http://127.0.0.1:4173` com o mesmo proxy local. Preview é para conferir o build, não uma configuração de deploy público. Testes Playwright exercitam o cliente, CSV e os estados reais da interface em desktop e mobile emulado com fixtures do contrato; não precisam de chave, banco ou Groq. O navegador de testes é uma instalação separada. Teclado virtual, safe areas e sensação de toque ainda precisam ser confirmados em celular físico.

## Protótipo no Figma

O [protótipo editável CineData Analytics · Protótipo editorial](https://www.figma.com/design/w838J7ZohM6pp2n2TXZUCN?node-id=78-206) foi criado e aprovado antes da implementação do frontend. Ele reúne a identidade visual, os fluxos de consulta, as telas desktop/mobile e os estados de resultado, carregamento, esclarecimento, ausência de dados e erro.

O arquivo separa telas e componentes em quatro páginas:

- **Telas e fluxos · Claro** e **Telas e fluxos · Escuro**: janelas para navegar pelo fluxo e composições completas para consultar durante o desenvolvimento.
- **Componentes e estilos · Claro** e **Componentes e estilos · Escuro**: controles, variantes, tipografia, cores, listas de filmes, fallback de pôster e referências de cabeçalho.

Os temas compartilham componentes e tokens semânticos. A marca tem versões clara e escura da logo ao lado de “cinedata”, com o controle de tema no cabeçalho. O protótipo serviu de referência para a interface web; seu conteúdo ilustrativo não substitui os resultados reais do SQLite.

## Limites e dados enviados

Até três chamadas de modelo e duas tentativas SQL por pergunta. Raciocínio `medium`, até 2048 tokens de geração por chamada, temperatura zero e ferramentas sequenciais. O limite de geração inclui raciocínio e passou nos cinco casos iniciais; a avaliação ampliada verifica casos maiores. Prazo total 600 segundos é um teto herdado da avaliação, não uma promessa de latência.

O planejamento e a correção de SQL recebem todas as regras analíticas, o esquema e a pergunta. Após uma consulta bem-sucedida, a finalização conserva a pergunta, o SQL e seus resultados, mas recebe somente instruções de resposta e apresentação, sem reenviar o esquema ou as instruções para construir consultas. O esforço `medium`, o modelo e o teto de 2048 tokens permanecem iguais. Essa redução de contexto não omite linhas, valores ou avisos do contrato.

A coluna `url_poster` é omitida somente do retorno SQL enviado ao modelo; a API conserva as evidências completas, incluindo URLs, SQL e parâmetros. Títulos, anos, identificadores e métricas continuam disponíveis ao modelo. O raciocínio intermediário recebido não é reenviado à chamada seguinte. A URL ainda pode aparecer no esquema ou no texto SQL; a redução não garante que qualquer solicitação caiba no limite. O arquivo SQLite permanece local e as consultas rodam no computador. O cliente aceita somente o endpoint HTTPS oficial, sem proxies do ambiente, redirects, retries ou fallback.

Na consulta de 01/10/2026, o plano gratuito publica 30 requisições/minuto, 1000/dia, 8000 tokens/minuto e 200000/dia para esse modelo. Limites são da organização e podem variar; verificar o painel da conta. Tokens, inclusive raciocínio, podem limitar o uso antes das requisições. Não tratar 1000 requisições como 500 perguntas garantidas. [Limites oficiais](https://console.groq.com/docs/rate-limits).

## Proteção SQL

Uma ferramenta de dados, `consultar_sql`, e resposta JSON com status, explicação e avisos. O modelo pode concluir pela ferramenta `json` (`ToolOutput`) ou por texto JSON; ambos são validados pelo mesmo contrato Pydantic, com `avisos` obrigatório, podendo ser vazio. Até duas tentativas SQL e três chamadas permitem obter evidências e corrigir uma consulta inválida. O Groq não permite combinar modo JSON nativo com ferramentas nessa API; respostas inválidas são rejeitadas sem extrair conteúdo de erros e sem retry da saída. Banco estático aberto com `mode=ro&immutable=1`, após verificar ausência de WAL/journal pendente. Conexões fechadas após a consulta; cancelamento interrompe e aguarda o worker.

Após uma consulta SQL bem-sucedida, `consultar_sql` é retirada das ferramentas da chamada seguinte: o modelo recebe a evidência e finaliza por `json` ou texto JSON validado. O fluxo normal usa duas chamadas ao modelo e uma execução SQL; a espera depende do saldo de cota. A segunda tentativa SQL fica reservada para corrigir uma consulta inválida; esse caminho pode usar três chamadas ao modelo. Comparações e análises precisam ser resolvidas na consulta principal, por exemplo com CTEs. As instruções mantêm as regras estáticas antes do esquema e da data para ampliar o prefixo reutilizável pelo cache.

Se uma resposta do modelo já trouxer duas chamadas SQL idênticas, a segunda reutiliza a evidência da própria pergunta, sem executar ou guardar outra consulta. A comparação exige SQL, nomes, valores e tipos dos parâmetros iguais, independentemente da ordem das chaves. Essas chamadas continuam consumindo o limite de tentativas existente. Uma consulta diferente após sucesso, ou uma chamada à ferramenta já retirada, resulta em resposta inválida, sem retry adicional. O reaproveitamento não atravessa perguntas.

Autorização SQLite permite somente dez tabelas de negócio e funções analíticas aprovadas. Escrita, DDL, anexação, PRAGMAs do modelo e metadados técnicos são bloqueados. Uma instrução por chamada, com parâmetros vinculados.

Limites: 20 segundos por SQL, 100 linhas, 10000 caracteres de SQL, 50 parâmetros escalares finitos, 12000 caracteres de colunas/linhas e 2000 caracteres por célula de texto. Truncamento é sinalizado. SQL e parâmetros originais ficam preservados como evidência. Mapeamento de leitura até 1 GiB é configuração da conexão, sem alterar o banco. Não usar `immutable=1` com uma base em atualização.

## Testes e avaliação

Formatação Python com Ruff 0.16.10 e frontend com Prettier 3.9.9, fixados na configuração e no lockfile. Na raiz:

```powershell
uvx --from ruff==0.16.10 ruff format app tests evaluation
uvx --from ruff==0.16.10 ruff format --check app tests evaluation
```

Em `frontend/`, `npm.cmd run format` aplica a formatação; `npm.cmd run format:check` apenas verifica. O check faz parte de `npm.cmd run verify`. Essas ferramentas são de desenvolvimento e não alteram as dependências Python de execução.

```powershell
# Testes sintéticos: não precisam de chave e não chamam a nuvem.
.\.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -v

# Gabaritos SQL locais: também é o comportamento sem flags.
.\.venv\Scripts\python.exe -X utf8 -m evaluation.run --references-only

# Chamadas reais ao Groq: exigem chave e consomem cotas.
.\.venv\Scripts\python.exe -X utf8 -m evaluation.run --smoke --interval 60
.\.venv\Scripts\python.exe -X utf8 -m evaluation.run --all --interval 60
.\.venv\Scripts\python.exe -X utf8 -m evaluation.run --all --case 17_melhores --output runtime/groq-reteste.json

# Benchmark de 10 perguntas; --all mede todos os 25 casos e sua acurácia.
.\.venv\Scripts\python.exe -X utf8 -m evaluation.benchmark --interval 60 --output runtime/latency.json
.\.venv\Scripts\python.exe -X utf8 -m evaluation.benchmark --all --interval 60 --output runtime/latency-all.json

# Experimento com tools estáveis, mantendo os bloqueios internos de SQL.
.\.venv\Scripts\python.exe -X utf8 -m evaluation.benchmark --stable-tools --interval 60 --output runtime/latency-stable.json
```

`evaluation/cases.json` contém 25 casos: os 22 originais e três rankings plurais de margem, diretores e avaliações de usuários. Data fixa 30/09/2026. `--smoke` seleciona cinco categorias; `--all` inclui os 25 casos. `--interval 60` acrescenta 60 segundos entre perguntas; essa espera não entra na duração de cada resposta. API e CLI interpretam `x-ratelimit-limit-tokens`, `x-ratelimit-remaining-tokens` e `x-ratelimit-reset-tokens` como capacidade, saldo e prazo de reposição. Uma resposta bem-sucedida com saldo positivo não gera espera especulativa baseada no consumo anterior ou no teto de geração. Saldo esgotado aguarda o reset; se esse prazo não vier, usa 60 segundos. Headers ausentes não inventam uma janela de bloqueio. Um saldo positivo não garante que a chamada caiba: o provider continua sendo a autoridade. As chamadas compartilham uma trava por processo, e a espera faz parte do prazo da pergunta. HTTP429 interrompe a pergunta, sem retry, e `retry-after` bloqueia novos envios prematuros nesse processo (60 segundos quando ausente ou inválido). Reinício, outras instâncias ou consumo externo da mesma conta ainda podem provocar bloqueios.

Relatórios incrementais ficam em `runtime/`. Registram fatos/status, duração e uso; memória e quantização do servidor remoto não são medidas. `codigo_agente_sha256` identifica o agente, `codigo_cota_sha256` o controle de espera, `codigo_prompts_sha256` as instruções e `codigo_avaliador_sha256` o comparador; relatórios históricos mantêm seu formato original. Erro de cota, indisponibilidade ou prazo interrompe a bateria. Comparação admite SQL diferente, colunas extras, aliases declarados e pivot explícito `cnt_YYYY` com exatamente os anos esperados, sem aceitar truncamento, anos ausentes ou métricas erradas. Contagens e identificadores são exatos; tolerâncias financeiras 0,01 e notas/margens 0,000001. Explicações e motivos de recusa/esclarecimento exigem revisão manual.

O benchmark registra por pergunta tempo total, esperas de quota, chamadas do modelo, SQL, tokens, cache e quantidade de execuções; calcula média, mediana e p95 por posto mais próximo para respostas obtidas. Erros permanecem separados no relatório, com a dimensão do limite quando identificável, sem texto de erro ou identificador da conta. `--all` também gera um resumo dos dez casos representativos, que pode ter ordem e consumo anterior diferentes do benchmark dedicado. Comparações exigem a mesma ordem e intervalo e devem declarar diferenças de cache/cota. Evite rodar avaliação e testes manuais do backend simultaneamente: ambos consomem a cota da organização, e as travas locais de processos diferentes não coordenam esse consumo.

Na validação final de 05/10/2026, a prioridade foi revista para perguntas comuns em menos de 20 segundos. Seis perguntas reais levaram: contagem de gêneros 2,41 s; receita BRL 2,88 s; filmes por gênero 4,98 s; par ator/diretor 13,84 s; anos parciais 2,56 s; ausência de dados 1,48 s. Média 4,69 s, mediana 2,72 s e p95 13,84 s. Todas usaram duas chamadas ao modelo, um SQL e zero espera local de quota. As perguntas tiveram intervalo de 60 segundos fora dos tempos medidos; não é validação de carga contínua ou concorrente. A finalização passou a usar cerca de 745–1.361 tokens de entrada nesses casos, preservando as evidências. Os 106 testes locais passaram.

Cinco casos passaram automaticamente. O anual retornou os valores corretos 5/1 em colunas `qtd_2025/qtd_2026`, enquanto o gabarito usa anos em linhas; a conferência independente confirmou os números e o aviso de ano parcial. Seu veredito automático permanece incorreto por formato. As explicações foram revisadas: dez filmes na receita, todos os 19 gêneros e avisos compatíveis com as evidências. Este conjunto curto não aprova a avaliação real completa de 25 casos nem garante tempo sob cota esgotada. Experimentos históricos interrompidos por `429` e erros de finalização foram preservados nos relatórios locais. Permanecem tools dinâmicas, raciocínio `medium` e teto de 2.048 tokens; não houve troca de modelo. Reinicie a API para carregar alterações no código.

### Histórico de versões anteriores

Os resultados seguintes descrevem avaliações anteriores às instruções finais de metadados. Não compõem a aprovação de `8c559f3`; os resultados atuais estão no [resumo de validação](docs/VALIDACAO_FINAL.md).

As cinco categorias iniciais passaram na comparação de status/linhas: receita BRL 3,89 s; popularidade 2,25 s; ator na janela móvel 4,50 s; gêneros 2,42 s; avaliações de usuários 2,05 s. Soma de latências 15,11 s, sem contar os intervalos da cota. São medições daquela bateria, não uma garantia de tempo ou correção geral.

O consolidado ampliado usa a última execução de cada caso, inclusive falhas, e reúne versões diferentes do prompt e protocolo. Não é uma bateria completa da versão atual. Todos os 22 casos foram avaliados: 21 aprovados automaticamente; a contagem de 2025/2026 foi confirmada manualmente (5 e 1 filmes), pois o SQL retornou anos em colunas e o gabarito usa linhas. O veredito automático desse caso permanece registrado como incorreto por formato; não foi convertido silenciosamente em acerto.

Os retestes corrigiram a inclusão de futuros na média anual e a consulta do par ator/diretor, que retornou Joe Anoa’i e Kevin Dunn, com 37 filmes. Os últimos testes de média anual, pares e margens levaram 14,28/31,72/16,83 segundos, incluindo uma pausa diagnóstica de 10 segundos entre chamadas para respeitar TPM. Naquela fonte, essa espera existia somente na avaliação local. Não usar esses tempos como latência atual ou garantia de desempenho.

Explicações também foram revisadas: esclarecimentos pedem identificação sem afirmar homônimos como fato sem SQL. Permanece uma limitação de apresentação: a média anual declarou o ano parcial no texto, com `avisos` vazio. Aprovação nos casos avaliados não garante correção em qualquer pergunta futura.

Foram observados bloqueios por tokens/dia e tokens/minuto, inclusive entre as duas chamadas de uma pergunta. Os diagnósticos registram a espera daquele instante; não são saldo atual nem garantia de completar uma pergunta após a espera. Uma chave válida e a disponibilidade da organização são necessárias para reproduzir a avaliação.

O ambiente limpo instalado exclusivamente por `requirements.txt` foi verificado novamente com os testes reorganizados. Na demonstração do backend, `/health`, `/docs` e uma pergunta real por HTTP retornaram 200; a contagem dos 95.645 filmes levou 1,92 s, com duas chamadas ao Groq e uma SQL, sem pausa diagnóstica. A refatoração manteve instruções e ferramenta SQL idênticas e não repetiu essa chamada à nuvem. O servidor de demonstração foi encerrado e o hash do SQLite permaneceu igual ao original.

## Documentação

- [Instalação e configuração do modelo](docs/INSTALACAO_MODELO.md).
- [Validação final, resultados e limites](docs/VALIDACAO_FINAL.md).
- [Guia da skill interface-craft](docs/INTERFACE_CRAFT.md).

### Skill interface-craft

A [interface-craft](.agents/skills/interface-craft/SKILL.md) foi criada neste projeto para orientar agentes no design, na prototipação editável pelo Figma MCP, na implementação e na revisão de interfaces. É reutilizável para web, iOS e Android, com referências de Apple HIG, Material Design 3 e WCAG 2.2 AA. O CineData é seu primeiro caso de uso; a skill adapta identidade, conteúdo e interação a cada produto.

O pacote em `.agents/skills/interface-craft/` inclui `SKILL.md`, `agents/openai.yaml` e seis referências de apoio. Em um agente com suporte a skills, use `$interface-craft` junto do objetivo, plataforma e escopo desejados. O [guia](docs/INTERFACE_CRAFT.md) explica os modos de uso e a organização dos arquivos. A skill não é uma dependência para executar o CineData.

## Repositório

`app/main.py` expõe a API; `app/agent.py` executa o agente; `app/prompts.py` contém as instruções e seu builder; `app/database.py` protege a leitura SQLite. `evaluation/run.py` executa a CLI e grava relatórios; `evaluation/grading.py` compara evidências; `evaluation/cases.json` guarda os gabaritos.

Os testes do backend usam fixtures sintéticas em `tests/helpers.py` e se distribuem em `test_database.py`, `test_analytics.py`, `test_agent.py`, `test_groq_adapter.py`, `test_groq_quota.py`, `test_api.py` e `test_evaluation.py`. O comando de descoberta permanece o mesmo, sem dependências Python adicionais. `frontend/src/` separa componentes, cliente HTTP, tipos, exportação CSV e estilos; `frontend/tests/` guarda fixtures e verificações Playwright. README, guias de instalação e da skill, resumo de validação e `.agents/skills/` são publicados; `.env`, `.venv`, banco, JSONs brutos, ferramentas locais e documentos internos ficam excluídos do Git. Não há deploy público.
