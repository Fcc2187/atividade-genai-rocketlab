# Skill interface-craft

A `interface-craft` foi criada neste projeto para orientar agentes no design, na prototipação, na implementação e na revisão de interfaces de produto. Seu método parte do objetivo do usuário e conecta direção visual, hierarquia, conteúdo, componentes, estados de interação e verificação do resultado.

O CineData foi seu primeiro caso de uso: a skill apoiou a criação do [protótipo editável no Figma](https://www.figma.com/design/w838J7ZohM6pp2n2TXZUCN?node-id=78-206) e a implementação da interface web. A skill é reutilizável para outros produtos e para web, iOS e Android; não fixa a marca, a paleta, a tipografia ou a stack do CineData.

## Modos de uso

| Modo | Quando usar | Entrega esperada |
| --- | --- | --- |
| Prototipação | Desenhar telas ou fluxos no Figma | Elementos nativos editáveis, fundamentos visuais, componentes, estados e interações suportadas |
| Implementação | Construir ou alterar uma interface | Interface na stack do projeto, estados funcionais e verificações pertinentes |
| Revisão | Avaliar uma interface existente | Problemas localizados, evidências, impacto e correções dentro do escopo autorizado |

## Referências e plataformas

- **Web:** semântica, teclado, foco, contraste, reflow e estados acessíveis, com referência à WCAG 2.2 AA.
- **iOS:** convenções da Apple HIG, VoiceOver e ampliação de texto.
- **Android:** Material Design 3, adaptação ao espaço disponível, TalkBack e escala de fontes.
- **Figma MCP:** descoberta das capacidades disponíveis, criação de elementos editáveis, organização de componentes e tokens, inspeção e passagem do design para a implementação.

As referências orientam decisões conforme a plataforma. A identidade pode ser compartilhada entre plataformas, enquanto navegação e controles se adaptam ao contexto. A revisão exige evidências do que foi verificado; um protótipo ou screenshot não comprova conformidade integral de acessibilidade.

## Como usar

Em um agente com suporte a skills, invoque `$interface-craft` com o objetivo, a plataforma e o escopo. Exemplos:

```text
$interface-craft Crie no Figma um fluxo editável de consulta para web,
com versões desktop e mobile, usando a identidade aprovada do produto.
```

```text
$interface-craft Implemente esta tela no frontend existente,
preservando os componentes e os contratos da API.
```

```text
$interface-craft Revise os estados de carregamento, erro e recuperação
desta interface Android e registre os problemas com evidências.
```

Para prototipar, o ambiente precisa ter uma conexão Figma MCP disponível e acesso ao arquivo de destino. A skill utiliza as capacidades documentadas do ambiente e as skills oficiais do Figma quando disponíveis. Ela não instala nem autentica o MCP.

## Arquivos do pacote

| Arquivo | Finalidade |
| --- | --- |
| [SKILL.md](../.agents/skills/interface-craft/SKILL.md) | Escopo, modos, método e critérios de entrega |
| [agents/openai.yaml](../.agents/skills/interface-craft/agents/openai.yaml) | Nome exibido, descrição curta e prompt inicial |
| [visual-direction.md](../.agents/skills/interface-craft/references/visual-direction.md) | Direção visual, composição e identidade do produto |
| [apple-hig.md](../.agents/skills/interface-craft/references/apple-hig.md) | Convenções e acessibilidade para iOS |
| [material-design.md](../.agents/skills/interface-craft/references/material-design.md) | Material Design 3 e adaptação para Android |
| [web-accessibility.md](../.agents/skills/interface-craft/references/web-accessibility.md) | WCAG 2.2 AA e verificações para web |
| [figma-workflow.md](../.agents/skills/interface-craft/references/figma-workflow.md) | Fluxo de prototipação editável com Figma MCP |
| [quality-review.md](../.agents/skills/interface-craft/references/quality-review.md) | Revisão de qualidade e evidências de verificação |

A skill é documentação de trabalho para o agente e não participa da execução da aplicação CineData.
