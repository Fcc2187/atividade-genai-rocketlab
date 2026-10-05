# Instalar e configurar o modelo no CineData

Atualizado em 04/10/2026. Provedor integrado: **Groq**. Modelo: **openai/gpt-oss-120b**. A API e o SQLite rodam localmente; a inferência exige internet e uma chave Groq. Não é necessário baixar pesos nem instalar um servidor de modelo.

## 1. Preparar uma cópia do projeto

Clonar este repositório e abrir um terminal na raiz. Instalar [uv](https://docs.astral.sh/uv/getting-started/installation/); ele obtém a versão Python solicitada ao criar o ambiente. Para usar a interface, instalar também Node.js 22.16+ na linha 22, ou 24+, e npm.

Em uma instalação nova, no Windows com PowerShell:

```powershell
uv venv --python 3.12.14 .venv
uv pip install --python .venv\Scripts\python.exe --link-mode copy -r requirements.txt
uv pip check --python .venv\Scripts\python.exe
if (-not (Test-Path -LiteralPath .env)) {
    Copy-Item -LiteralPath .env.example -Destination .env
}
```

Em Linux/macOS, usar o executável do ambiente em `.venv/bin/python`:

```sh
uv venv --python 3.12.14 .venv
uv pip install --python .venv/bin/python -r requirements.txt
uv pip check --python .venv/bin/python
test -f .env || cp .env.example .env
```

Se o ambiente já existir, reutilizá-lo e conferir as dependências com `uv pip check`; não recriar um ambiente em uso nem sobrescrever um `.env` preenchido. As dependências de execução estão fixadas em [requirements.txt](../requirements.txt). O SDK OpenAI atua como cliente compatível do Groq; não utiliza conta OpenAI ou assinatura Plus. [Compatibilidade oficial](https://console.groq.com/docs/openai).

## 2. Disponibilizar o banco

Obter `cinerocket (1).db` nos materiais da atividade e colocá-lo na raiz do projeto. Ele não acompanha o Git. Se estiver em outro local, configurar seu caminho em `DATABASE_PATH`; caminhos relativos são resolvidos a partir da raiz do projeto.

O SQLite deve permanecer estático e somente leitura. SHA-256 do banco usado na validação: `410f5beef6ab9fb34b9044d5dd191f56f3f0dc30a56e6432386ecef0d977b012`. No PowerShell:

```powershell
Get-FileHash -Algorithm SHA256 -LiteralPath 'cinerocket (1).db'
```

Fechar editores que mantenham o banco em atualização antes de iniciar a aplicação. O backend rejeita arquivos WAL/journal pendentes para evitar ler uma base inconsistente; não apagar esses arquivos sem verificar o estado do banco.

## 3. Criar a chave e preencher o .env

1. Entrar ou criar uma conta no [Groq Console](https://console.groq.com/).
2. Abrir [API Keys](https://console.groq.com/keys), criar uma chave e copiar seu valor.
3. Abrir o `.env` local e preencher a configuração completa:

```dotenv
DATABASE_PATH="cinerocket (1).db"
MODEL_PROVIDER=groq
MODEL_NAME=openai/gpt-oss-120b
MODEL_BASE_URL=https://api.groq.com/openai/v1
GROQ_API_KEY=SUA_CHAVE_GROQ
QUESTION_TIMEOUT_SECONDS=600
```

Substituir `SUA_CHAVE_GROQ` pelo valor real. O `.env` está ignorado no Git; não publicar a chave. Variáveis já definidas no terminal têm precedência sobre o arquivo. Reiniciar o backend após editar a configuração.

O provedor integrado é Groq: trocar apenas o endpoint ou o nome da variável da chave não habilita outro provedor. Conferir modelo e cotas da organização no painel. Referências: [início rápido](https://console.groq.com/docs/quickstart) e [limites](https://console.groq.com/docs/rate-limits).

## 4. Iniciar e verificar o backend

Na raiz, em PowerShell:

```powershell
.\.venv\Scripts\python.exe -X utf8 -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Em Linux/macOS, substituir o executável por `.venv/bin/python`. Abrir `http://127.0.0.1:8000/docs`. Primeiro executar `GET /health`: ele verifica somente o banco, sem chamar o modelo nem validar a chave.

Depois, em `POST /perguntas`, selecionar `Try it out` e enviar:

```json
{"pergunta":"Quantos filmes existem por gênero?"}
```

Essa operação chama o Groq e consome cota. Cada pergunta é independente; o backend faz até três chamadas de modelo e duas tentativas SQL. Encerrar o servidor com `Ctrl+C`.

Para abrir a interface, manter o backend rodando e usar outro terminal:

```powershell
cd frontend
npm.cmd ci
npm.cmd run dev
```

Abrir `http://127.0.0.1:5173`. Em outros terminais, usar `npm` no lugar de `npm.cmd`. A chave fica exclusivamente no backend. Mais detalhes de uso e build no [README](../README.md#interface-web).

## 5. Diagnóstico

| Código da aplicação | HTTP da API | Ação |
| --- | --- | --- |
| `banco_indisponivel` | 503 | Conferir caminho, arquivo, permissões e ausência de WAL/journal pendente. |
| `configuracao_invalida` | 503 | Conferir chave preenchida, provedor, endpoint, nome do modelo e prazo. |
| `modelo_indisponivel` | 503 | Conferir internet, chave válida, permissão do modelo e disponibilidade do Groq. |
| `cota_excedida` | 503 | O Groq retornou HTTP429; aguardar a reposição indicada pelo provedor. |
| `solicitacao_grande_demais` | 413 | Pedir menos resultados ou usar filtros mais específicos; esperar não reduz a solicitação. |
| `resposta_invalida` | 502 | O resultado do modelo não cumpriu o contrato ou um limite operacional; reformular e preservar o caso para avaliação. |
| `prazo_excedido` | 504 | A pergunta excedeu o prazo total, incluindo a espera da cota; reduzir o recorte e conferir a disponibilidade. |

O controle de cota respeita os headers de reposição entre chamadas, inclusive dentro de uma pergunta. Não há retry automático. `QUESTION_TIMEOUT_SECONDS=600` define o prazo máximo da pergunta, não o intervalo entre perguntas. Cotas são compartilhadas com outras instâncias e usos da conta; consultar os valores atuais no painel. [Erros oficiais do Groq](https://console.groq.com/docs/errors).

URLs de pôster permanecem nas evidências retornadas pela API e usadas pela interface. A coluna `url_poster` é retirada apenas do retorno SQL enviado ao modelo, que conserva títulos, anos, identificadores e métricas. Essa redução não garante que qualquer consulta caiba no limite do provedor.

## 6. Validar a instalação

Na raiz, os checks locais não precisam de chave nem chamam o Groq:

```powershell
.\.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -X utf8 -m evaluation.run --references-only
```

Os testes usam bases sintéticas; os gabaritos SQL usam o banco configurado. Dentro de `frontend/`, após `npm.cmd ci`:

```powershell
npx.cmd playwright install chromium
npm.cmd run verify
```

Para uma avaliação real, com chave válida e cota disponível, executar na raiz:

```powershell
.\.venv\Scripts\python.exe -X utf8 -m evaluation.run --smoke --interval 60
```

O intervalo adicional da avaliação não elimina limites por tamanho, tokens/minuto ou tokens/dia. Os relatórios ficam em `runtime/`, fora do Git. Consultar o [resumo de validação atual](VALIDACAO_FINAL.md) para a contagem de testes, os casos aprovados, as fontes e as limitações; números de versões anteriores permanecem no histórico desse documento.