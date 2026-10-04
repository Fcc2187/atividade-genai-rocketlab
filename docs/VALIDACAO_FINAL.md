# Validação do fechamento CineData Analytics

Data: 04/10/2026. Referência dos 25 casos: 30/09/2026. Modelo: `openai/gpt-oss-120b`, via Groq.

**Resultado final: 25 corretos, zero incorretos, zero erros e zero pendentes na última tentativa de cada caso.** A avaliação foi incremental, com a mesma versão, modelo, banco e referência temporal. A bateria principal teve 23 acertos e dois HTTP413; os casos 05 e 14 passaram em retestes manuais. Todas as tentativas continuam no histórico. As explicações foram revisadas separadamente, e o fluxo integrado foi repetido na versão atual, com filmes, pôsteres, agregação, reformulação, CSV e histórico.

Na fonte dessa aprovação, a pausa diagnóstica existia somente no executor local de avaliação. O backend passou posteriormente a respeitar os headers de reposição da cota; veja a validação manual abaixo. O resultado comprova os cenários executados; não garante disponibilidade geral do provedor ou correção de qualquer pergunta futura.

## Ajustes após a validação manual

O usuário encontrou IDs de filmes no texto da resposta e HTTP429 ao enviar perguntas consecutivas. O prompt já proibia esses IDs na explicação, mas a saída do modelo não era higienizada. Agora o backend remove chaves presentes nas evidências da narrativa, incluindo hashes de 64 caracteres com ou sem rótulo; chaves curtas só são removidas com rótulo explícito. IDs, SQL, parâmetros, métricas e URLs de pôster permanecem nas evidências.

O diagnóstico anterior à correção recebeu HTTP200 na primeira chamada e HTTP429 na segunda chamada da mesma pergunta: limite de 8.000 tokens/minuto, reposição indicada em 32,257 segundos e `retry-after: 10`. A produção agora serializa chamadas por modelo/processo e aguarda `x-ratelimit-reset-tokens`, com fallback de 60 segundos se ausente ou inválido. HTTP429 não gera retry; `retry-after` bloqueia novas chamadas prematuras no mesmo processo. A espera também conta no prazo da pergunta. O frontend informa que a consulta pode aguardar a liberação da cota.

Verificação posterior: **62 testes Python aprovados**, cobrindo limpeza da narrativa sem perda de evidências, perguntas seguidas e concorrentes, cancelamento durante a espera, headers ausentes e HTTP429 sem reenvio. Os 25 casos capturados de `8c559f3` preservaram respostas, evidências, avisos e vereditos em novo replay offline (`runtime/replay-manual-fixes.json`); não houve inferência Groq nesse replay. Prompt e avaliador de dados não mudaram. Relatórios futuros também registram o hash do módulo de controle de cota.

`npm.cmd run verify` terminou com exit 0: typecheck, lint, build e 93 testes frontend aprovados. A primeira execução restrita travou no encerramento; somente a árvore desse teste foi encerrada, e a repetição fora da restrição concluiu. Os 25 gabaritos SQL também passaram novamente, sem truncamento; SHA-256 do SQLite original permaneceu igual.

**Histórico de bloqueios antes da nova chave.** A tentativa posterior recebeu HTTP429 na primeira chamada, em 0,547 segundo, com `retry-after: 772` (aproximadamente 13 minutos naquele instante). O roteiro parou sem retry nem segunda pergunta. `runtime/manual-quota-before.json` e `runtime/manual-quota-after.json` preservam os diagnósticos; o segundo contém os hashes do agente, controle de cota e prompt. Essa tentativa não comprova o fluxo real corrigido nem identifica qual cota causou esse último bloqueio. Reinícios, outras instâncias e uso externo da conta continuam sujeitos à cota compartilhada.

Reteste solicitado pelo usuário, com `QUESTION_TIMEOUT_SECONDS=600` efetivamente passado ao agente: primeira chamada HTTP429 em 0,500 segundo, `retry-after: 190`. Desta vez o diagnóstico capturou a mensagem do provedor sem chave ou ID da organização: **tokens/dia (TPD), limite 200.000, usados 196.044, solicitados 4.394**, espera indicada de 3m9,216s. O roteiro encerrou sem retry ou segunda pergunta; histórico preservado em `runtime/manual-quota-retest-tpd.json`. Esse reteste identifica a cota diária como causa dessa tentativa. O prazo de 600 segundos é o tempo máximo de processamento, não um intervalo entre consultas; seu esgotamento gera `prazo_excedido`/HTTP504, enquanto o HTTP429 do Groq gera `cota_excedida`/HTTP503 na API. Alterar o prazo não repõe tokens. A liberação indicada pelo provedor não garante saldo para todas as chamadas das duas perguntas.

**Reteste real aprovado após a troca da chave.** Um processo novo carregou o `.env`, conservando o prazo de 600 segundos e o controle de cota da produção. As perguntas foram enviadas consecutivamente ao mesmo modelo, sem pausa adicional do roteiro nem retry:

| Pergunta | Resultado | Tempo incluindo espera da cota |
| --- | --- | --- |
| 5 filmes com maior nota IMDb | Cinco filmes, notas e URLs de pôster; explicação sem IDs | 34,688 s |
| 5 filmes com maior bilheteria USD | Cinco filmes, valores e URLs de pôster; explicação sem IDs | 72,266 s |

As quatro chamadas ao Groq retornaram HTTP200; não houve HTTP429 ou timeout. O módulo de produção aguardou os resets informados (31,44 s, 38,535 s e 29,752 s) entre as chamadas. IDs, títulos, anos, URLs, métricas e ordem das duas listas coincidiram exatamente com rankings SQL independentes no SQLite original; nomes e valores narrados também foram conferidos. A narrativa usa hífen sem quebra em Spider-man, sem alterar o título original nas evidências. Fontes e resultados reais: `runtime/manual-quota-retest.json`; conferência independente: `runtime/manual-quota-retest-verified.json`. Esses dois rankings não substituem a bateria histórica de 25 casos, e este roteiro não renderizou nem baixou as imagens no navegador. A disponibilidade futura permanece sujeita às cotas do provedor.

| Fonte dos ajustes manuais | SHA-256 |
| --- | --- |
| app/agent.py | 735d4ff76fcab5a9a9f63bb30899a31e168c0583fe8e660d1cc66bb9f1ad1ec6 |
| app/groq_quota.py | 14aac9deed006aa6655507ed47cf6a740147af1e2a4e032abb52b16bddfbdeb6 |

## Versão e rastreabilidade

Fonte da inferência e integração reais: `8c559f3`. Fonte entregue após a correção de avisos: `8d86941`. Os resultados de `d152201` e de prompts anteriores são históricos e não compõem os 25 acertos.

A revisão independente encontrou um caso de borda posterior à avaliação: o décimo aviso de truncamento podia ser descartado ao acrescentar o aviso de ano parcial. `8d86941` preserva os últimos nove avisos antes de acrescentar o parcial, mantendo ambos os avisos automáticos. A regressão falhou antes e passou depois, com nove/dez avisos e 101 filmes num SQLite temporário; a suíte completa passou em 55 testes. Prompt, SQL, ferramenta e chamadas ao modelo não mudaram. As SQLs e respostas capturadas dos 25 casos foram reexecutadas pelo agente atual com modelo local de replay e SQLite original: evidências, respostas, avisos e vereditos preservados. Isso é revalidação offline, sem nova inferência; não se atribuem as chamadas Groq de `8c559f3` ao hash posterior.

| Fonte | SHA-256 |
| --- | --- |
| app/agent.py, inferência e integração reais | 49fe3f254b4a324a4610d4eed09fdf802d68a4415bd2466b69123cd29c3ac021 |
| app/agent.py, entregue e revalidado offline | faa43bfda9c72a0c6a23bedf20e933823a278ce6bfa2e91df6314a7394edf6f7 |
| app/prompts.py | 2206c360c6699066057b082385630e6f7519b881c8956cccf0b90f0cea7c439a |
| evaluation/grading.py | 01b2e04df442fa71db23df4e752098c365ec02b9d640a20e6319f6809287d85f |
| SQLite original, antes e depois | 410f5beef6ab9fb34b9044d5dd191f56f3f0dc30a56e6432386ecef0d977b012 |

Banco local, estático e somente leitura; nenhuma migração, índice ou limpeza no original. Imagens usam as URLs existentes no SQLite. Ausência ou falha de download conserva o filme e suas métricas.

Fontes locais desta aprovação: `groq-final-aceite-v4-30.json`, `groq-final-aceite-reteste-05-14-30.json` e `groq-final-trace-v4-05.json`. O consolidado `groq-final-consolidado-v4.json` usa a última tentativa cronológica por caso, preserva as falhas anteriores e confere hashes, modelo, data, IDs únicos e gabaritos. O grade foi recalculado contra as referências atuais, com as tolerâncias originais. A revalidação posterior está separada em `replay-final-warning-fix.json`, com os hashes anterior/atual e os 25 resultados preservados. Relatórios brutos, logs, capturas e ferramentas diagnósticas ficam fora do Git.

## Correções e revisão manual

- **Cobertura do catálogo (19):** o prompt distingue catálogo completo de consultas com recorte temporal. O novo SQL não acrescenta a exclusão de lançamentos futuros; médias e contagens correspondem ao gabarito original.
- **Aliases (11, 14 e 25):** o avaliador aceita `produtora`, `diferenca` e `qtd_avaliacoes` como equivalentes aos nomes canônicos. IDs, métricas, valores e ordem continuam conferidos; testes negativos rejeitam dados incorretos e truncamento. Nenhum gabarito foi alterado.
- **Anos em colunas (20):** aceita somente pivot explícito `cnt_YYYY`, com exatamente os anos esperados. Confere os valores, sem preencher ausências: 2025 = 5 e 2026 = 1. Ano ausente, adicional, duplicado, valor errado ou truncamento continuam falhando.
- **Ano parcial (06 e 20):** ambas as respostas agora têm aviso estruturado de 2026 parcial até 30/09/2026. O agente acrescenta um aviso quando a pergunta contém o ano atual e o SQL anual limita os lançamentos à referência; uma pergunta explícita sobre futuros não recebe esse aviso.
- **Margens e explicações (03, 12 e 23):** a maior margem foi descrita como 99,999%, arredondamento correto de 99,99925279424306. O caso 12 lista os 19 gêneros na ordem da evidência, incluindo Tv Movie; o antigo resumo incorreto dos cinco menores não se repetiu. O top 5 conserva a fórmula percentual e o arredondamento observado.

Os textos dos 25 casos foram conferidos contra suas evidências: moedas, notas, contagens, ordem, filtros, amostras e avisos. Recusa de escrita e esclarecimentos não executaram SQL nem inventaram fatos do catálogo. Popularidade permanece distinta de avaliações de usuários. Homônimos permanecem registros separados, e pôster nulo não exclui filmes.

O grade automático avalia status e linhas, não certifica explicações. Alguns SQLs ainda agrupam gêneros somente pelo nome ou omitem desempates de agregações sem empate no banco original; os dados observados coincidem com os gabaritos. Isso não comprova aderência universal em outros bancos. A seleção de metadados de filmes é orientada pelo prompt, sem enriquecimento determinístico para toda pergunta futura.

## Verificação local

| Comando / inspeção | Resultado |
| --- | --- |
| `.\.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -v` | 55 testes aprovados na fonte entregue |
| `npm.cmd run verify` em frontend/ | 93 testes aprovados; typecheck, lint e build exit 0 |
| `.\.venv\Scripts\python.exe -X utf8 -m evaluation.run --references-only` | 25 gabaritos SQL executados no original, sem inferência ou truncamento |
| Consolidação e regrade offline | 25 IDs únicos; hashes/modelo/data iguais; gabaritos atuais; histórico HTTP413 preservado |
| Replay posterior à correção de avisos | 25 SQLs/respostas reexecutadas no agente atual; evidências e avisos idênticos; sem chamadas Groq |
| Fluxo integrado atual | Filmes, agregação, esclarecimento/reformulação, CSV e histórico aprovados |

Os testes frontend usam fixtures sintéticas. Não comprovam SQL criado pelo modelo; essa evidência vem dos casos e fluxos reais. Fixtures analíticas com seis candidatos verificam top 5, filtros de margem, mínimo de notas válidas, desempates e distinção entre popularidade e avaliações.

A auditoria visual anterior, com a mesma interface, cobriu 72 cenas em claro/escuro e 1440/390/320 px: sem overflow da página ou erros JS, fontes/logos carregadas e botões de pelo menos 48 px. Incluiu múltiplas consultas/métricas, títulos longos, imagem ausente, truncamento, avisos extensos, teclado, diálogos, Escape, texto 200% e recuperação. O fluxo real atual foi renderizado em claro/1440 e escuro/390 e inspecionado novamente. Comparação com D04 claro/escuro no [Figma aprovado](https://www.figma.com/design/w838J7ZohM6pp2n2TXZUCN/?node-id=78-206).

Dados sempre visíveis por consulta; avisos antes dos dados; CSV acessível fora do SQL; estados com ações; contador real e ajuda do produto. Não se afirma fidelidade pixel a pixel ou certificação WCAG. Celular físico e leitor de tela não foram avaliados. A otimização das logos foi dispensada como item opcional; identidade aprovada preservada.

## Protocolo e histórico do provedor

O executor diagnóstico envolve `model.request` sem alterar argumentos, ferramenta, guardrails ou referências, e mantém mínimo de 30 segundos entre chamadas. Na bateria de casos há 60 segundos de espera inicial e entre perguntas. Sem retry automático. As durações abaixo incluem a pausa interna; não incluem a espera inicial/entre perguntas e não representam latência normal da API.

Nas tentativas históricas, houve HTTP429 por TPM e TPD, inclusive com chaves recém-configuradas. Uma instrumentação local confirmou rejeição na segunda chamada de uma pergunta. A chave não foi publicada. Dez segundos de pausa foram insuficientes; o usuário autorizou o diagnóstico, posteriormente ampliado para 30 segundos. As fontes anteriores terminaram em 21/25 automáticos, com três equivalências de formato/alias e um erro real de cobertura, além de uma falha narrativa. As correções foram seguidas de uma nova bateria completa, sem reaproveitar acertos da fonte antiga.

Na fonte atual, uma tentativa anterior à última troca de chave parou por HTTP429 diário no primeiro caso. Após a troca, a bateria v4 concluiu 25 tentativas: 23 corretos e HTTP413 nos casos 05 e 14. O reteste focado passou em 14, mas 05 voltou a receber HTTP413 (solicitação de 10.522 tokens, limite TPM de 8.000). O reteste instrumentado seguinte de 05 passou com duas chamadas, 3.839 e 5.260 tokens de entrada reportados, metadados completos e dez linhas corretas. Todos esses erros e retestes ficam registrados; não houve conversão silenciosa de falhas em sucesso.

## Fluxo integrado real na fonte atual

Frontend compilado → handlers originais de `app.main` → Groq → SQLite original, com pausa somente no modelo da instância temporária de avaliação. Não usou fixtures ou replays. Perguntas HTTP usam 04/10/2026; casos CLI usam 30/09/2026. Rankings e agregação conferidos independentemente no SQLite.

| Fluxo | Resultado |
| --- | --- |
| Top 10 de bilheteria USD | HTTP200, 38,22 s diagnósticos; dez filmes, IDs/valores/ordem corretos, título/ano/URL/métrica e dez pôsteres carregados; sem truncamento |
| Quantidade por gênero | HTTP200, 33,92 s diagnósticos; 19 gêneros, contagens/ordem corretas; sem metadados de filmes nas agregações |
| “Quais são os melhores filmes?” | HTTP200/esclarecimento, 1,05 s diagnósticos; pede critério, sem SQL ou fatos inventados |
| Reformulação explícita | Pergunta original/foco preservados, sem envio automático; maior bilheteria USD retorna Avengers: Endgame, 2019, USD 2.800.000.000; HTTP200 em 62,83 s diagnósticos |
| Cópia, CSV e histórico | Cópia fiel normalizando CRLF; CSV fiel a colunas e valores originais; ações sem POST extra; um envio nos resultados e dois no fluxo reformulado |
| Renderização | Claro/1440 e escuro/390, sem overflow ou erro JS |

Relatórios atuais: `real-ui-filmes-v4-network.json`, `real-ui-agregacao-v4-network.json`, `real-ui-esclarecimento-v4-network.json`; incluem os hashes da fonte. Na primeira tentativa isolada houve falha de conexão, sem resultado. Com rede no avaliador, o resultado passou, mas o navegador isolado não carregou as imagens; a nova execução do fluxo com rede no navegador carregou os dez pôsteres. Essas tentativas permanecem separadas dos fluxos aprovados. Replays históricos de popularidade conferiram fallback, sem chamar a API, e não compõem a integração real atual.

## Reprodução e entrega

Uma cópia limpa de `8ccb8fa`, anterior às últimas correções do agente/prompt/avaliador, foi instalada com banco e `.env` fornecidos localmente. Python 3.12.14, 34 dependências fixadas, `uv pip check` e `npm.cmd ci` passaram; 49 testes Python e 93 testes frontend, typecheck, lint e build passaram naquela cópia. Health retornou 200, entrada vazia 422 e a primeira consulta real retornou 95.645 filmes via HTTP200 em 1,83 s, sem pausa. Essa evidência comprova o procedimento de instalação naquela fonte; as verificações e a integração da fonte atual estão acima.

Demo: pergunta de filmes → resposta e lista/tabela → valores originais e SQL → CSV → reabertura do histórico. Reformulação inclui todo o contexto necessário. README documenta instalação, chave local, banco, servidores e checks. [Repositório da entrega](https://github.com/Fcc2187/atividade-genai-rocketlab); não há deploy público. Credenciais, banco e artefatos locais ficam fora do Git.

## Resultado por caso

Última tentativa de cada caso, fonte `8c559f3`: **25 corretos, 0 incorretos, 0 erros e 0 pendentes**. Avaliação incremental, com revisão textual separada e histórico de falhas preservado.

| Caso | Categoria | Gabarito SQLite | Status/linhas | Segundos diagnósticos |
| --- | --- | --- | --- | --- |
| 01_receita_brl | financeiro | Sem truncamento | Corretos | 33,50 |
| 02_lucro_genero | financeiro | Sem truncamento | Corretos | 34,80 |
| 03_maior_margem | financeiro | Sem truncamento | Corretos | 32,88 |
| 04_populares | avaliacoes | Sem truncamento | Corretos | 32,59 |
| 05_divergencia_notas | avaliacoes | Sem truncamento | Corretos no reteste; HTTP413 anterior registrado | 33,73 |
| 06_nota_ano | avaliacoes | Sem truncamento | Corretos | 33,03 |
| 07_ator_cinco_anos | pessoas | Sem truncamento | Corretos | 32,97 |
| 08_diretor_nota | pessoas | Sem truncamento | Corretos | 33,11 |
| 09_par_ator_diretor | pessoas | Sem truncamento | Corretos | 33,23 |
| 10_filmes_genero | generos_produtoras | Sem truncamento | Corretos | 33,36 |
| 11_produtora_lucro | generos_produtoras | Sem truncamento | Corretos | 33,20 |
| 12_margem_genero | generos_produtoras | Sem truncamento | Corretos | 33,27 |
| 13_mais_avaliacoes | engajamento | Sem truncamento | Corretos | 32,64 |
| 14_usuarios_imdb | engajamento | Sem truncamento | Corretos no reteste; HTTP413 anterior registrado | 33,33 |
| 15_sem_dados | seguranca | Sem truncamento | Corretos | 32,02 |
| 16_escrita | seguranca | Sem truncamento | Corretos | 1,11 |
| 17_melhores | avaliacoes | Sem truncamento | Corretos | 1,64 |
| 18_titulo_ambiguo | pessoas | Sem truncamento | Corretos | 0,97 |
| 19_cobertura | avaliacoes | Sem truncamento | Corretos | 34,75 |
| 20_anos_parciais | generos_produtoras | Sem truncamento | Corretos | 32,41 |
| 21_futuros | generos_produtoras | Sem truncamento | Corretos | 32,56 |
| 22_pessoa_ambigua | pessoas | Sem truncamento | Corretos | 2,02 |
| 23_margem_top5 | financeiro | Sem truncamento | Corretos | 33,16 |
| 24_diretores_top5 | pessoas | Sem truncamento | Corretos | 33,53 |
| 25_avaliacoes_top5 | engajamento | Sem truncamento | Corretos | 32,36 |
