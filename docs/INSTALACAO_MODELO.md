# Configurar GPT-OSS 120B no Groq

Atualizado em 01/10/2026. Provedor atual: **Groq**. Modelo: **openai/gpt-oss-120b**. API e SQLite continuam locais; inferência usa internet. O modelo Qwen e seus runtimes locais foram descontinuados por decisão do usuário.

## 1. Criar a chave

1. Acessar [Groq Console](https://console.groq.com/) e entrar ou criar uma conta.
2. Abrir [API Keys](https://console.groq.com/keys).
3. Criar uma chave, com um nome como `cinedata-local`, e copiar seu valor.
4. Consultar os limites da organização no painel. O plano Free permite começar com cotas; não é necessário contratar um plano pago para esta configuração.

Referência: [início rápido oficial](https://console.groq.com/docs/quickstart).

## 2. Preencher o arquivo local

Nesta máquina, `D:\atividade-genai-rocketlab\.env` já foi preparado. Abrir esse arquivo no editor e preencher:

```dotenv
GROQ_API_KEY=SUA_CHAVE_GROQ
```

Substituir o texto pelo valor copiado. Não enviar a chave em chat nem publicar o arquivo. O `.env` está ignorado no Git.

A configuração restante já usa:

```dotenv
DATABASE_PATH="cinerocket (1).db"
MODEL_PROVIDER=groq
MODEL_NAME=openai/gpt-oss-120b
MODEL_BASE_URL=https://api.groq.com/openai/v1
QUESTION_TIMEOUT_SECONDS=600
```

Em uma cópia nova, criar `.env` a partir de `.env.example` antes de preencher a chave. Não sobrescrever um arquivo já configurado. Variáveis do terminal têm precedência sobre o arquivo.

## 3. Iniciar o backend

Na raiz do projeto:

```powershell
.\.venv\Scripts\python.exe -X utf8 -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Abrir `http://127.0.0.1:8000/docs`, expandir `POST /perguntas`, clicar em `Try it out` e enviar:

```json
{"pergunta":"Quantos filmes existem por gênero?"}
```

Essa operação chama o Groq e consome cota. `GET /health` verifica apenas o banco, portanto um health aprovado não confirma a chave. Reiniciar a API após editar `.env`. Parar com `Ctrl+C`.

Não instalar pesos nem iniciar servidor de modelo. O ambiente Python existente já tem tudo necessário; o SDK OpenAI é usado como cliente compatível do Groq, conforme a [documentação oficial](https://console.groq.com/docs/openai). Não utiliza Plus ou API OpenAI.

## 4. Diagnóstico

- `configuracao_invalida`: conferir chave preenchida, provedor, endpoint e prazo.
- `modelo_indisponivel`: conferir internet, chave válida e permissão do modelo na conta.
- `cota_excedida`: limite do Groq atingido; aguardar conforme o painel, sem repetir rapidamente.
- `resposta_invalida`: resposta/SQL do modelo não cumpriu o contrato; preservar o caso para avaliação.
- `prazo_excedido`: tempo máximo atingido.

O plano gratuito publica para esse modelo 30 requisições/minuto, 1000/dia, 8000 tokens/minuto e 200000/dia na consulta de 01/10/2026. O primeiro limite atingido restringe o uso; conferir valores exatos da organização. [Limites oficiais](https://console.groq.com/docs/rate-limits).

## Validação

29 testes automatizados aprovados e cinco categorias avaliadas com Groq real, com status e linhas corretos, entre 2,05 e 4,50 segundos. A bateria ampliada continua em andamento. Não publicar a chave nos relatórios. Para avaliar respeitando a cota, usar `python -X utf8 -m evaluation.run --smoke --interval 60`; a espera entre perguntas não é incluída na latência. As instruções completas de instalação Python, banco e avaliação estão no [README](../README.md).
