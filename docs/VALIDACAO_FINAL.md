# Validação do fechamento CineData Analytics

Data: 04/10/2026. Referência dos casos: 30/09/2026. Modelo configurado: `openai/gpt-oss-120b`, via Groq.

O fechamento funcional está implementado. A validação real está pendente por cota; este documento não declara aprovação integral ou correção para qualquer pergunta.

## Versão e rastreabilidade

Versão funcional avaliada: `8ccb8fa`, baseada em `3e133e0`. Alterações posteriores de documentação não mudam o agente/prompt avaliados.

| Fonte | SHA-256 |
| --- | --- |
| app/agent.py | c5752cf046c23c77aca69318d6062b8144338f914e2ad521e64b0191a33427f1 |
| app/prompts.py | 4e3180c5e1358c9ac50926c59ff2528971140e0e231843feffa3128836d36470 |
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

## Execução real e pendências

Comando executado:

```powershell
.\.venv\Scripts\python.exe -X utf8 -m evaluation.run --smoke --interval 60 --output runtime/groq-final-smoke.json
```

Caso `01_receita_brl`: HTTP429 / `ProviderRateLimited`, após 1,72 s. O provedor informou limite de 8.000 tokens/minuto. O relatório não identifica com segurança em qual chamada da pergunta ocorreu a rejeição. A execução interrompeu os demais casos, sem retry automático. O intervalo entre perguntas não garante disponibilidade para todas as chamadas internas.

Um reteste controlado apenas de `01_receita_brl`, sem mudar código/prompt, voltou a receber HTTP429 em 1,92 s. Os cinco casos smoke não foram aprovados; a bateria completa de 25 não foi iniciada. Todos os gabaritos locais passaram. Relatórios brutos permanecem em runtime/, fora do Git; nenhuma credencial ou identificador da organização é publicado aqui.

Ainda pendentes: resultados reais recentes dos 25 casos; revisão manual de explicações/avisos/recusas/esclarecimentos; consulta real top 10 com metadados e limite de retorno; fluxo integrado com pôster/agregação/reformulação/CSV/histórico. Resultados históricos de versões diferentes não são aprovação desta versão.

## Reprodução e demonstração

Uma cópia limpa dos arquivos Git foi extraída de `8ccb8fa`, com `.env` e banco fornecidos localmente. `uv venv --python 3.12.14 .venv`, instalação das 34 dependências fixadas e `uv pip check` passaram. `npm.cmd ci` instalou 175 pacotes pelo lockfile, sem vulnerabilidades reportadas nessa execução. Nessa cópia, Python passou em 49 testes e o frontend em 93 verificações, typecheck, lint e build. O backend iniciou com a configuração documentada; foi usada porta 8001 porque a 8000 já estava ocupada, sem interromper o servidor existente. `/health` retornou 200 e entrada vazia retornou 422.

Primeira pergunta real por HTTP: “Quantos filmes existem no catálogo?” retornou 200 / resultado, 95.645 filmes, em 1,83 s; duas chamadas Groq, 7.143 tokens de entrada, 102 de saída e uma tentativa SQL. Essa execução normal da API não teve pausa diagnóstica. É evidência de execução na cópia limpa, não aprovação dos 25 casos ou do fluxo de pôsteres.

Preparação da demo: pergunta de filmes → resposta/lista ou tabela → valores originais e SQL → CSV → reabertura do histórico. Uma consulta reformulada deve conter todo o contexto necessário.

Entrega: [repositório](https://github.com/Fcc2187/atividade-genai-rocketlab). README descreve instalação, chave local, banco fornecido, servidores e checks. Não há deploy público.

## Resultado por caso

| Caso | Categoria | Gabarito SQLite | Avaliação real final |
| --- | --- | --- | --- |
| 01_receita_brl | financeiro | Executado sem truncamento | HTTP429 no smoke e no reteste controlado |
| 02_lucro_genero | financeiro | Executado sem truncamento | Pendente |
| 03_maior_margem | financeiro | Executado sem truncamento | Pendente |
| 04_populares | avaliacoes | Executado sem truncamento | Pendente |
| 05_divergencia_notas | avaliacoes | Executado sem truncamento | Pendente |
| 06_nota_ano | avaliacoes | Executado sem truncamento | Pendente |
| 07_ator_cinco_anos | pessoas | Executado sem truncamento | Pendente |
| 08_diretor_nota | pessoas | Executado sem truncamento | Pendente |
| 09_par_ator_diretor | pessoas | Executado sem truncamento | Pendente |
| 10_filmes_genero | generos_produtoras | Executado sem truncamento | Pendente |
| 11_produtora_lucro | generos_produtoras | Executado sem truncamento | Pendente |
| 12_margem_genero | generos_produtoras | Executado sem truncamento | Pendente |
| 13_mais_avaliacoes | engajamento | Executado sem truncamento | Pendente |
| 14_usuarios_imdb | engajamento | Executado sem truncamento | Pendente |
| 15_sem_dados | seguranca | Executado sem truncamento | Pendente |
| 16_escrita | seguranca | Executado sem truncamento | Pendente |
| 17_melhores | avaliacoes | Executado sem truncamento | Pendente |
| 18_titulo_ambiguo | pessoas | Executado sem truncamento | Pendente |
| 19_cobertura | avaliacoes | Executado sem truncamento | Pendente |
| 20_anos_parciais | generos_produtoras | Executado sem truncamento | Pendente |
| 21_futuros | generos_produtoras | Executado sem truncamento | Pendente |
| 22_pessoa_ambigua | pessoas | Executado sem truncamento | Pendente |
| 23_margem_top5 | financeiro | Executado sem truncamento | Pendente |
| 24_diretores_top5 | pessoas | Executado sem truncamento | Pendente |
| 25_avaliacoes_top5 | engajamento | Executado sem truncamento | Pendente |
