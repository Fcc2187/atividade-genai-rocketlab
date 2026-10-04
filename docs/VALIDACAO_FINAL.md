# Validação do fechamento CineData Analytics

Data: 04/10/2026. Referência dos casos: 30/09/2026. Modelo configurado: `openai/gpt-oss-120b`, via Groq.

O smoke final passou nas cinco categorias e o fluxo integrado funcionou com a pausa diagnóstica autorizada. Na avaliação incremental dos 25 casos, 11 estão corretos, um foi bloqueado por cota diária e 13 continuam pendentes. A validação não está concluída; os resultados não demonstram disponibilidade da API normal sob a cota atual nem correção para qualquer pergunta.

## Versão e rastreabilidade

Versão funcional final: `d152201`, baseada em `3e133e0`. Duas correções pequenas do prompt reforçaram os metadados dos filmes e impediram sua repetição na explicação. A avaliação final usa somente essa fonte; resultados de outros hashes não compõem sua aprovação.

| Fonte | SHA-256 |
| --- | --- |
| app/agent.py | c5752cf046c23c77aca69318d6062b8144338f914e2ad521e64b0191a33427f1 |
| app/prompts.py | 51c6160042a272163624ce09cbc0c44bb00658fc54a912021097963613ba15a8 |
| SQLite original, antes | 410f5beef6ab9fb34b9044d5dd191f56f3f0dc30a56e6432386ecef0d977b012 |
| SQLite original, depois das leituras finais | 410f5beef6ab9fb34b9044d5dd191f56f3f0dc30a56e6432386ecef0d977b012 |

Banco permanece local e somente leitura. Nenhuma migração, índice ou limpeza foi feita no original. Imagens vêm das URLs existentes no SQLite; ausência ou falha de download conserva o filme e suas métricas.

## Verificação local

| Comando / inspeção | Resultado |
| --- | --- |
| `.\.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -v` | 49 testes aprovados |
| `npm.cmd run verify` em frontend/ | 93 verificações aprovadas; typecheck, lint e build exit 0 |
| `node node_modules/@playwright/test/cli.js install chromium` | Exit 0; Chromium da versão local disponível |
| `.\.venv\Scripts\python.exe -X utf8 -m evaluation.run --references-only` | 25 gabaritos SQL executados no original, sem inferência |
| Auditoria renderizada claro/escuro, 1440/390/320 px | 72 cenas, sem overflow da página ou erros JS; fontes/logos carregadas e botões >=48 px |

As verificações frontend usam fixtures sintéticas. Não comprovam SQL criado pelo modelo. Novas fixtures analíticas têm pelo menos seis candidatos elegíveis para conferir top 5, filtros de margem, mínimo de notas válidas, desempates e distinção entre avaliações/popularidade.

Revisão visual conferiu início, preenchimento, processamento, filmes, agregações, múltiplas consultas/métricas, evidências, histórico, ajuda, recuperação, títulos longos, pôsteres ausentes, truncamento e avisos extensos. Testes cobrem teclado, foco contido nos diálogos, Escape, texto 200%, rolagem interna e recuperação em 320 px. Comparação renderizada com D04 claro/escuro no [Figma aprovado](https://www.figma.com/design/w838J7ZohM6pp2n2TXZUCN/?node-id=78-206).

Adaptações: dados sempre visíveis por consulta; avisos antes dos dados; CSV fora do painel SQL; estados reais com ações; contador real; ajuda do produto. Não se afirma fidelidade pixel a pixel ou certificação WCAG. Celular físico e leitor de tela não foram avaliados.

## Histórico dos bloqueios de cota

Comando executado:

```powershell
.\.venv\Scripts\python.exe -X utf8 -m evaluation.run --smoke --interval 60 --output runtime/groq-final-smoke.json
```

Caso `01_receita_brl`: HTTP429 / `ProviderRateLimited`, após 1,72 s. O provedor informou limite de 8.000 tokens/minuto. O relatório não identifica com segurança em qual chamada da pergunta ocorreu a rejeição. A execução interrompeu os demais casos, sem retry automático. O intervalo entre perguntas não garante disponibilidade para todas as chamadas internas.

Um reteste controlado apenas de `01_receita_brl`, sem mudar código/prompt, voltou a receber HTTP429 em 1,92 s. Os cinco casos smoke não foram aprovados; a bateria completa de 25 não foi iniciada. Todos os gabaritos locais passaram. Relatórios brutos permanecem em runtime/, fora do Git; nenhuma credencial ou identificador da organização é publicado aqui.

Naquele checkpoint, a avaliação de 25 casos e o fluxo integrado estavam pendentes. As seções seguintes registram a retomada e o resultado atual; evidências de versões anteriores não aprovam a fonte final.

### Retomada com a nova chave

Em 04/10/2026, a chave local foi trocada e o backend reiniciado para carregá-la. Foi conferida apenas a presença da chave e a ausência de uma chave herdada que pudesse sobrepor o `.env`; nenhuma credencial foi registrada. Essa tentativa histórica usava a fonte de `8ccb8fa`, anterior às duas correções finais do prompt.

O novo smoke (`--smoke --interval 60 --output runtime/groq-final-chave-nova-smoke.json`) voltou a interromper no caso `01_receita_brl`: HTTP429, 1,72 s, limite de 8.000 tokens/minuto. A mensagem informou 3.648 usados e 4.650 solicitados. Esses números descrevem somente aquela rejeição; não identificam por si só a chamada interna. A bateria de 25 não foi iniciada.

Na interface real, “Quais são os 10 filmes com maior bilheteria em dólares?” recebeu HTTP503 / `cota_excedida` em 1,83 s. Houve exatamente um POST, sem retry ou erro JavaScript. Como não houve resultado, essa execução **não comprova pôsteres**, metadados, truncamento, CSV ou histórico.

“Quais são os melhores filmes?” recebeu HTTP200 / `esclarecimento` em 1,34 s, com uma chamada ao modelo e nenhuma SQL. Revisão manual: a resposta pede critério (IMDb, TMDB, popularidade, lucro) e possíveis filtros sem afirmar fatos do catálogo. “Reformular pergunta” preservou a pergunta original, devolveu foco ao campo e não enviou outro POST. Renderização real conferida em claro/1440 e escuro/390, sem overflow ou erro JavaScript. Naquele teste, o envio reformulado ainda não havia sido comprovado; ele foi conferido posteriormente no avaliador.

As 25 referências SQL, os 49 testes Python e as 93 verificações do frontend (mais typecheck, lint e build) foram executados novamente com sucesso nesta retomada. A agregação real “Quantos filmes existem por gênero?” também recebeu HTTP503 / `cota_excedida`, em 2,03 s, com um POST e sem erro JavaScript; seu CSV e histórico não foram comprovados. O SHA-256 do SQLite permaneceu igual.

Depois de o usuário fornecer uma chave de outra conta inicialmente sem uso, o smoke foi executado em um processo novo (`runtime/groq-final-conta-zerada-smoke.json`). Novamente houve HTTP429 no primeiro caso, em 1,88 s: TPM 8.000, usados 3.613, solicitados 4.741. Um único reteste controlado de `01_receita_brl`, com instrumentação local que registra somente número, status e uso de chamadas, localizou a rejeição: **chamada 1 bem-sucedida** (3.533 tokens de entrada e 403 de saída reportados pelo modelo); **chamada 2 HTTP429**, sem retry. A pergunta terminou em 1,89 s. Essa evidência identifica a segunda chamada apenas nesse reteste, sem reinterpretar o estágio das rejeições anteriores.

Naquelas tentativas, o backend foi reiniciado para carregar a chave atual; não houve alteração de produção ou pausa no avaliador. Posteriormente o usuário autorizou a pausa diagnóstica descrita abaixo. A API normal continua sem pausa ou retry; o prompt recebeu somente as correções identificadas na avaliação.

## Avaliação final com pausa autorizada

O executor diagnóstico envolve `model.request` sem mudar argumentos, agente, ferramenta, guardrails ou referências. Dez segundos foram insuficientes ao incluir imagens; o intervalo mínimo foi ampliado para 30 segundos, informado ao usuário. Há também 60 segundos de espera no início de cada execução e entre perguntas. Não há retry automático.

Cada duração por caso abaixo **inclui a pausa entre chamadas do modelo**. As esperas inicial e entre perguntas não entram nessa duração. São tempos diagnósticos, não latência normal da API. O CLI publicado permanece sem pausa interna; o wrapper e relatórios brutos são locais e ignorados pelo Git.

| Smoke final | Categoria | Status e linhas | Segundos diagnósticos |
| --- | --- | --- | --- |
| 01_receita_brl | financeiro | Corretos | 33,58 |
| 04_populares | avaliações | Corretos | 34,06 |
| 07_ator_cinco_anos | pessoas | Corretos | 33,31 |
| 10_filmes_genero | gêneros/produtoras | Corretos | 32,80 |
| 13_mais_avaliacoes | engajamento | Corretos | 33,36 |

Fonte local: groq-final-editorial-smoke30.json, hash final acima. Textos revisados: moedas, fontes e rankings correspondem às evidências, sem IDs ou URLs de imagem na explicação. Popularidade e contagem de avaliações permanecem distintas. Gêneros compartilham filmes; suas contagens não devem ser somadas como total do catálogo.

A bateria parcial01–07 recebeu HTTP413 em05_divergencia_notas: o provedor estimou 10.412 tokens para uma solicitação, acima de8.000. Dois retestes manuais, sem mudar a fonte, passaram; o último trouxe todos os metadados e LIMIT10. Não foi capturado o SQL da primeira falha, portanto não se atribui uma causa SQL que não foi comprovada. A falha permanece registrada, sem retry automático ou conversão silenciosa em sucesso.

A continuação08–25 parou em11_produtora_lucro por HTTP429/TPD: limite diário200.000, usados197.358 e solicitados4.431. O provedor indicou12min52,848s naquele instante; essa espera se refere à solicitação rejeitada, não garante disponibilidade para as chamadas seguintes ou todos os casos restantes. Não foram feitas novas tentativas após esse bloqueio.

### Fluxo integrado real no avaliador

Uma instância temporária usou o frontend compilado, handlers originais de `app.main`, Groq e SQLite reais. A pausa foi aplicada somente ao modelo dessa instância; a API de uso normal foi preservada. As perguntas HTTP usam 04/10/2026 e os casos CLI 30/09/2026. Valores do ranking e da agregação foram conferidos independentemente no banco original.

| Fluxo | Resultado |
| --- | --- |
| Top 10 de bilheteria em USD | HTTP200, 34,32 s diagnósticos; IDs, valores e ordem corretos; título/ano/URL/métrica; dez pôsteres reais carregados |
| Limite com imagens | 1.877 caracteres, abaixo de 12.000; dez linhas e sem truncamento |
| Quantidade por gênero | HTTP200, 33,15 s diagnósticos; 19 gêneros e contagens/ordem corretas; sem metadados de filmes nas agregações |
| “Quais são os melhores filmes?” | HTTP200/esclarecimento, 1,25 s; pede critério e tamanho, sem SQL ou fatos inventados |
| Reformulação explícita | Pergunta original preservada e foco recuperado, sem envio automático; pedido completo de maior bilheteria USD retorna Avengers: Endgame, 2019, USD2,8 bilhões; 62,69 s com esperas |
| Cópia, CSV e histórico | CSV fiel às colunas/linhas originais, cópia correta, ações sem POST extra; um envio nos resultados e dois na reformulação |
| Renderização real | Claro/1440 e escuro/390, sem overflow ou erro JavaScript |

Uma agregação foi repetida após corrigir uma seleção ambígua no roteiro de teste (sugestão e entrada do histórico tinham o mesmo nome). O produto não mudou para essa correção. A cópia foi comparada normalizando CRLF do Windows, preservando o conteúdo.

Separadamente, replays identificados dos retornos reais verificaram imagens ausentes de popularidade: cinco filmes preservados, duas imagens carregadas e três fallbacks. Os replays não chamam a API; os fluxos HTTP da tabela acima foram reais.

### Revisão manual e limites

O grade automático avalia status e linhas, não certifica explicações. No caso de maior margem, o valor SQL é 99,99925279424306%; o texto escreveu 99,99%, embora o arredondamento a duas casas seja 100,00%. É uma imprecisão da explicação; a apresentação determinística, a evidência e o CSV preservam o valor correto. Nenhum gabarito foi alterado para ocultar isso.

Na média anual, valores e amostras estão corretos e o texto declara 2026 parcial, mas `avisos` veio vazio apesar da instrução. Essa execução não comprova o alerta estruturado de ano parcial. Na média de lucro por gênero, a ordenação SQL omitiu desempates por nome/chave; as médias do banco original são distintas e o resultado observado está correto. Essas limitações de aderência às instruções ficam separadas do acerto dos dados.

A disponibilidade de consultas grandes na API normal continua limitada pela cota do provedor. O prompt orienta a seleção de imagens; não existe enriquecimento determinístico que garanta esses campos para toda pergunta futura. As logos originais foram mantidas; sua otimização é opcional.

## Reprodução e demonstração

Uma cópia limpa dos arquivos Git foi extraída de `8ccb8fa`, com `.env` e banco fornecidos localmente. `uv venv --python 3.12.14 .venv`, instalação das 34 dependências fixadas e `uv pip check` passaram. `npm.cmd ci` instalou 175 pacotes pelo lockfile, sem vulnerabilidades reportadas nessa execução. Nessa cópia, Python passou em 49 testes e o frontend em 93 verificações, typecheck, lint e build. O backend iniciou com a configuração documentada; foi usada porta 8001 porque a 8000 já estava ocupada, sem interromper o servidor existente. `/health` retornou 200 e entrada vazia retornou 422.

Primeira pergunta real por HTTP: “Quantos filmes existem no catálogo?” retornou 200 / resultado, 95.645 filmes, em 1,83 s; duas chamadas Groq, 7.143 tokens de entrada, 102 de saída e uma tentativa SQL. Essa execução normal da API não teve pausa diagnóstica. É evidência de execução na cópia limpa, não aprovação dos 25 casos ou do fluxo de pôsteres.

Preparação da demo: pergunta de filmes → resposta/lista ou tabela → valores originais e SQL → CSV → reabertura do histórico. Uma consulta reformulada deve conter todo o contexto necessário.

Entrega: [repositório](https://github.com/Fcc2187/atividade-genai-rocketlab). README descreve instalação, chave local, banco fornecido, servidores e checks. Não há deploy público.

## Resultado por caso

Avaliação incremental de uma única versão: **11 corretos, um bloqueado por cota diária, 13 pendentes**. O caso05 teve HTTP413 na primeira tentativa e dois retestes corretos; essa falha permanece no histórico. Fontes locais: smoke final, bateria parcial01–07, reteste capturado05 e continuação08–25; mesmos hashes/modelo/data. Não foi uma única bateria ininterrupta.

| Caso | Categoria | Gabarito SQLite | Status/linhas automáticos | Segundos diagnósticos |
| --- | --- | --- | --- | --- |
| 01_receita_brl | financeiro | Executado sem truncamento | Corretos | 33,25 |
| 02_lucro_genero | financeiro | Executado sem truncamento | Corretos | 33,77 |
| 03_maior_margem | financeiro | Executado sem truncamento | Corretos | 33,08 |
| 04_populares | avaliacoes | Executado sem truncamento | Corretos | 32,56 |
| 05_divergencia_notas | avaliacoes | Executado sem truncamento | Corretos no último reteste; HTTP413 inicial registrado | 33,64 |
| 06_nota_ano | avaliacoes | Executado sem truncamento | Corretos | 34,39 |
| 07_ator_cinco_anos | pessoas | Executado sem truncamento | Corretos | 33,19 |
| 08_diretor_nota | pessoas | Executado sem truncamento | Corretos | 33,83 |
| 09_par_ator_diretor | pessoas | Executado sem truncamento | Corretos | 33,36 |
| 10_filmes_genero | generos_produtoras | Executado sem truncamento | Corretos | 32,78 |
| 11_produtora_lucro | generos_produtoras | Executado sem truncamento | HTTP429 — cota diária | 0,38 |
| 12_margem_genero | generos_produtoras | Executado sem truncamento | Não executado | — |
| 13_mais_avaliacoes | engajamento | Executado sem truncamento | Corretos | 33,36 |
| 14_usuarios_imdb | engajamento | Executado sem truncamento | Não executado | — |
| 15_sem_dados | seguranca | Executado sem truncamento | Não executado | — |
| 16_escrita | seguranca | Executado sem truncamento | Não executado | — |
| 17_melhores | avaliacoes | Executado sem truncamento | Não executado | — |
| 18_titulo_ambiguo | pessoas | Executado sem truncamento | Não executado | — |
| 19_cobertura | avaliacoes | Executado sem truncamento | Não executado | — |
| 20_anos_parciais | generos_produtoras | Executado sem truncamento | Não executado | — |
| 21_futuros | generos_produtoras | Executado sem truncamento | Não executado | — |
| 22_pessoa_ambigua | pessoas | Executado sem truncamento | Não executado | — |
| 23_margem_top5 | financeiro | Executado sem truncamento | Não executado | — |
| 24_diretores_top5 | pessoas | Executado sem truncamento | Não executado | — |
| 25_avaliacoes_top5 | engajamento | Executado sem truncamento | Não executado | — |
