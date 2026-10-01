# Instalação local do Qwen3.5 9B

Data dos testes: 30/09/2026. Instalação no D: e prova local; backend ainda pendente.

Runtime e pesos portáteis na pasta do projeto, sem alterar PATH ou instalar globalmente. O banco original não foi acessado durante a prova do modelo.

## Arquivos fixados

| Arquivo | Origem | Bytes | SHA-256 publicado |
|---|---|---:|---|
| `runtime/llamafile.exe` | [llamafile 0.10.6 completo](https://github.com/mozilla-ai/llamafile/releases/download/0.10.6/llamafile-0.10.6) | 368094430 | `d579f61dcd3a306f518e6d90e599d77793ed5f09543023d09c96ad35fcfa63f0` |
| `models/Qwen3.5-9B-Q5_K_S.gguf` | [Unsloth, revisão fixa](https://huggingface.co/unsloth/Qwen3.5-9B-GGUF/resolve/3885219b6810b007914f3a7950a8d1b469d598a5/Qwen3.5-9B-Q5_K_S.gguf) | 6361146592 | `be88613a50ba792bd5a2bc07b74bcd97c9ed9dbac028d27a44c6888e712323c3` |

Hashes obtidos da API de releases do GitHub e dos metadados LFS do Hugging Face. Os dois diretórios estão ignorados no Git. Não baixar projetor de imagens.

## Registro

- Espaço confirmado: 855658369024 bytes livres no D:.
- RAM disponível antes da instalação: 10651111424 bytes; total visível: 25479716864 bytes.
- Downloads concluídos; os dois SHA-256 calculados coincidem com os publicados acima.
- `llamafile --version`: v0.10.6. Argumentos confirmados pelo `--help` da versão instalada.
- Servidor carregado em CPU, quatro threads, um slot e contexto 8192; log do carregamento final: aproximadamente 3,5 segundos. Esse tempo inclui abertura com mapeamento; não mede leitura antecipada de todos os pesos.
- `/health`: `status=ok`; `/v1/models`: alias `qwen3.5-9b` disponível.
- `node test-model.mjs`: aprovado com a configuração final. Saudação: `Olá! Como posso ajudar?`; chamada automática `somar` com `{"a":7,"b":5}`; resposta após devolver resultado: `12`.
- Evidências locais, ignoradas no Git: `runtime/smoke-result.json`, `runtime/memory-result.json` e logs do servidor.
- Servidor encerrado após os testes para liberar RAM; runtime e pesos continuam instalados.

## Medições da prova final

| Etapa | Tempo | Tokens de entrada | Tokens gerados |
|---|---:|---:|---:|
| Saudação | 5,68 s | 24 | 8 |
| Chamada de ferramenta | 47,66 s | 310 | 36 |
| Interpretação do resultado | 3,26 s | 365, dos quais 345 reaproveitados | 3 |

A geração observada ficou aproximadamente entre 2,2 e 2,7 tokens/s. O processo atingiu 6464778240 bytes, cerca de 6,5 GB de RAM residente; outros programas e o sistema operacional usam memória adicional. Essas medições são de exemplos sintéticos pequenos, não de consultas do projeto ou de carga concorrente.

O prazo de 180 segundos do planejamento permanece provisório. O esquema e as 20 regras poderão tornar o primeiro prompt mais demorado; medir esse caso antes de fixar o prazo. Não há cota diária de provedor local, mas a vazão observada em CPU limita o uso prático.

## Ajustes confirmados

- Executável e pesos separados no Windows; instalação apenas dentro do projeto no D:, sem PATH global.
- Web UI e ferramentas internas desativadas; CORS limitado a origens localhost. Uma requisição com origem `https://example.org` não recebeu permissão CORS.
- A primeira prova mostrou aviso ao receber `tool_choice` como objeto nomeado: o servidor o ignorou e usou o padrão automático. A prova final usa `tool_choice: "auto"` e passa sem esse aviso. Conferir essa particularidade na integração do Pydantic AI; saída tipada do framework continua pendente para a tarefa 3.
- No momento da instalação do modelo, ainda não havia Git ou backend. A instalação não exigiu worktree, commit ou execução das tarefas 1–6. O banco original não foi acessado nessa tarefa.

## Iniciar e verificar

Na raiz do projeto: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\run-model.ps1`. Aguardar o carregamento e, em outro terminal com Node.js, executar `node .\test-model.mjs`. Encerrar o servidor com `Ctrl+C`. Instruções de download e hashes estão no [README](../README.md).

## Setup Python posterior

Por instrução do usuário, esta etapa posterior preparou somente o ambiente, sem implementar backend ou ferramenta SQL. Python 3.12.14 e uv 0.12.5 existentes foram reutilizados; `.venv` no D:, 34 dependências fixadas, `.env`, `.env.example` e Git local em `main` estão prontos. Compatibilidade, importações, construção do adapter e reprodução em ambiente limpo foram aprovadas. Abertura do banco em modo somente leitura confirmou 11 tabelas e SHA-256 inalterado, registrado no README.

O setup será versionado em [atividade-genai-rocketlab](https://github.com/Fcc2187/atividade-genai-rocketlab). README e este guia de instalação são publicados; planejamento interno, materiais da atividade, `.env`, `.venv`, banco, runtime e pesos permanecem excluídos do Git.
