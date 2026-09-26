# Apólis — Plataforma Inteligente para Análise e Comparação de Apólices D&O

**Equipe:** JL

| Nome | E-mail | Telefone |
|---|---|---|
| Leonardo Pereira | ligueproleo@gmail.com | +55 11 98479-6122 |
| João Cardoso | jpscardoso@ufpa.br | +55 91 98273-6292 |

**GitHub:** [github.com/jpscard/InsurMinds/tree/main/Projeto_Final](https://github.com/jpscard/InsurMinds/tree/main/Projeto_Final)

**Aplicação online:** [insurminds.onrender.com](https://insurminds.onrender.com) (landing page) · [insurminds.onrender.com/app](https://insurminds.onrender.com/app) (plataforma)

> **Resumo.** O Apólis recebe apólices de seguro D&O (Responsabilidade Civil de Administradores e Diretores) em PDF digital, PDF digitalizado ou imagem, lê o conteúdo com OCR quando necessário, usa IA generativa para estruturar coberturas, limites, franquias, exclusões e vigência, e permite **comparar** duas ou mais apólices lado a lado e **consultar** a carteira em linguagem natural. A consulta usa um **RAG por raciocínio sobre o índice hierárquico de cada documento** (abordagem PageIndex), orquestrado como um grafo **LangGraph**, e cita a seção e a página de onde veio cada informação.

## 1. Framework e stack tecnológica

| Componente | Tecnologia | Papel na solução |
|---|---|---|
| API e servidor web | FastAPI + Uvicorn | Endpoints REST e entrega da interface; documentação automática em /docs. |
| Orquestração da consulta | LangGraph | Grafo com estado: roteador, navegador do índice, leitor, avaliador e respondedor, com arestas condicionais e ciclo de nova navegação. |
| IA generativa | Anthropic (Claude), OpenAI (GPT), Google (Gemini) | Provedor e modelo escolhidos pelo usuário; a lista de modelos vem da API do próprio provedor. Modo offline por regras para testes. |
| Leitura de documentos | pdfplumber, pypdfium2, Tesseract OCR (português) | Texto nativo quando existe; OCR página a página nas páginas digitalizadas e em imagens. |
| Modelo de dados | Pydantic v2 | Esquema canônico `ApoliceDO`, contrato entre os agentes e validação da saída da IA. |
| Armazenamento | SQLite | Dados relacionais (apólices, coberturas, exclusões), JSON completo, texto por página e índice de cada documento. |
| Interface | HTML, CSS e JavaScript sem framework e sem build | Landing page e plataforma com tema claro/escuro, responsivas, no mesmo design system do Desafio 5. |
| Exportação | reportlab, pandas + openpyxl | Relatório de comparação em PDF (com a marca Apólis, métricas, análise e detalhamento), planilha Excel e Markdown. |
| Deploy | Docker + Render | Imagem com Tesseract e português; deploy automático a cada push no `main`. |
| Testes | pytest + TestClient | 47 testes automatizados, sem chave de API (LLM simulado e modo offline). |

## 2. Arquitetura da solução

![Arquitetura em camadas do Apólis](img/00_arquitetura.png)

- **Apresentação (`web/`):** landing page em `/` e plataforma em `/app`. O provedor, o modelo e a chave de API ficam no navegador e seguem em cabeçalhos a cada requisição; o servidor nunca grava a chave.
- **API (`api/main.py`):** expõe envio, detalhe, revisão, índice e documento original das apólices; comparação e exportação; consulta por IA e SQL somente leitura; e a lista de modelos de cada provedor.
- **Pipeline (`do_platform/pipeline.py`):** orquestra os agentes. Interface web, API e linha de comando usam só o pipeline, nunca os agentes diretamente.
- **Agentes (`do_platform/agents`):** seis agentes especializados, cada um com uma responsabilidade e um prompt (seção 3).
- **Camada de LLM (`do_platform/llm`):** interface única para Anthropic, OpenAI, Gemini e modo offline, com novas tentativas, backoff e leitura tolerante de JSON.
- **Armazenamento (SQLite):** modelo híbrido, com colunas relacionais para consultas SQL diretas e o JSON completo de cada apólice, além do texto original por página e da árvore de seções usada pela consulta.

## 3. Descrição dos agentes desenvolvidos

### Agente 1 — Triagem
Lê o início do documento e classifica: é uma apólice D&O? É apólice, condições gerais, proposta ou cotação? Evita processar documentos errados e sinaliza ao usuário quando o arquivo não parece ser do tipo esperado.

### Agente 2 — Extração
Núcleo da solução. Lê a linguagem jurídica heterogênea das apólices e produz o JSON no esquema `ApoliceDO`: identificação, vigência, Limite Máximo de Garantia, prêmio, base de cobertura, retroatividade, prazo complementar, territorialidade, custos de defesa, coberturas (classificadas em Lado A, B e C), exclusões, franquias e segurados. Cada cobertura guarda o trecho de origem. Documentos longos são extraídos em blocos de páginas e consolidados (estratégia map-reduce).

### Agente 3 — Validação
Revisor determinístico: normaliza datas e valores e aponta inconsistências, como sublimite maior que o LMG, vigência invertida ou campos ausentes. Não corrige em silêncio: gera alertas que aparecem na tela da apólice.

### Agente 4 — Indexação
Monta o **sumário em árvore** de cada documento (abordagem PageIndex). A estrutura vem do próprio layout, sem IA: títulos em maiúsculas (EXCLUSÕES, CLÁUSULAS PARTICULARES) viram seções e cláusulas numeradas (1., 5.2, 5.2.1) viram subseções, com as páginas de cada uma. A IA só escreve um resumo curto das seções principais, numa única chamada por documento.

### Agente 5 — Comparação
As diferenças objetivas (valores, presença ou ausência de coberturas e exclusões, franquias, custo relativo prêmio/LMG) são **calculadas por código**, o que as torna exatas e reprodutíveis. Coberturas com nomes diferentes em cada seguradora são alinhadas por similaridade. Só depois a IA interpreta os fatos já calculados e redige a análise executiva, as diferenças-chave por impacto, os pontos de atenção e a recomendação.

### Agente 6 — Consulta
Responde perguntas em linguagem natural navegando o índice das apólices, como descrito na seção 4.

## 4. Consulta: RAG por raciocínio sobre o índice (PageIndex + LangGraph)

Apólices são contratos longos e estruturados, em que a resposta depende de achar a cláusula certa e ler o contexto dela (exceções, remissões a outras cláusulas). Em vez de dividir o texto em pedaços soltos e buscar por similaridade, a consulta segue a abordagem **PageIndex**: cada documento vira uma árvore de seções com resumos, e a IA **lê o sumário e decide o que abrir**, como um especialista folheando a apólice. A orquestração é um grafo **LangGraph**, no mesmo padrão de supervisor com arestas condicionais usado no projeto SeguraBot da equipe.

![Grafo da consulta em LangGraph](img/00_grafo_consulta.png)

| Nó | O que faz |
|---|---|
| roteador | Decide se os dados já extraídos bastam ("qual tem o maior LMG?") ou se é preciso ler o documento ("a exclusão X tem exceções?"). |
| navegador | Recebe o sumário de cada apólice (id, título, páginas e resumo, sem o texto) e escolhe até 6 seções, com o motivo. Ids inexistentes ou repetidos são descartados. |
| leitor | Traz o texto das seções escolhidas, incluindo as subseções. |
| avaliador | Verifica se o que foi lido basta; se não, informa o que falta e o grafo navega de novo (no máximo 2 rodadas). |
| busca_lexical | Busca por palavras-chave (BM25) nas seções: caminho do modo offline e reserva quando a navegação falha. |
| respondedor | Responde apenas com os dados estruturados e as seções lidas, citando apólice, seção e página. |

**Decisões de projeto:**

- **Multiprovedor:** os nós chamam a camada de LLM do projeto, e não os modelos do LangChain; por isso a consulta funciona com Claude, GPT ou Gemini. A biblioteca oficial do PageIndex não foi usada porque a versão open source só aceita OpenAI.
- **Transparência:** cada nó registra o que fez. A interface mostra esse "caminho da consulta" junto da resposta, e cada citação informa por que a seção foi aberta.
- **Resiliência:** se a IA devolver uma resposta inválida, o grafo segue por um caminho alternativo (busca por palavras) em vez de falhar.
- **Custo:** uma pergunta sobre cláusulas usa até 5 chamadas à IA (roteador, navegador, avaliador, segunda navegação e resposta); perguntas respondidas pelos dados estruturados usam 2.

## 5. Fluxo de funcionamento da aplicação

1. **Acesso:** o usuário abre a landing page e entra na plataforma. Em **Modelo de IA**, escolhe o provedor, cola a chave e seleciona o modelo na lista trazida da API do provedor (ou usa o modo offline).
2. **Envio:** arrasta os PDFs ou imagens em **Enviar documentos**. Cada arquivo entra numa fila e as etapas aparecem **ao vivo**, à medida que terminam (leitura, triagem, extração, validação, gravação e indexação).
3. **Processamento:** leitura (com OCR quando preciso), triagem, extração, validação, armazenamento e indexação. Um arquivo já processado é reconhecido pelo hash e não é processado de novo, a menos que o usuário peça.
4. **Carteira e detalhe:** a carteira lista as apólices com vigência, LMG, prêmio e custo relativo. O detalhe mostra os dados extraídos, os alertas da validação, o índice, o texto de cada página, o documento original e a **revisão humana**, em que o usuário corrige o JSON extraído.
5. **Comparação:** o usuário escolhe duas ou mais apólices e recebe métricas lado a lado, análise executiva, pontos de atenção e o detalhamento de coberturas, exclusões e franquias, com exportação de um relatório completo em PDF, de uma planilha Excel e de Markdown.
6. **Consulta:** perguntas em linguagem natural com citação de seção e página, ou consultas SQL somente leitura sobre a carteira. Enquanto a IA trabalha, a tela mostra os nós do grafo concluídos e o que está em andamento ("Leitor: abrindo as seções escolhidas…").

No modo offline, o painel, a comparação e a consulta explicam o que o modo faz e oferecem ativar a IA; a comparação por regras classifica as diferenças pelo impacto e mostra as seis mais importantes primeiro.

## 6. Demonstrações realizadas

As demonstrações abaixo foram executadas no **modo offline** (extração por regras, sem chamar IA), para serem reproduzíveis por qualquer avaliador sem chave de API. Foram usados sete documentos **fictícios** (seguradoras, tomadores e valores inventados): três apólices curtas do mesmo tomador, com condições propositalmente diferentes, para a comparação; duas apólices completas de 10 páginas, com condições particulares, gerais e especiais e cláusulas numeradas com subitens e exceções; e dois documentos que exercitam casos difíceis: uma apólice longa digitalizada e um documento de condições gerais, que não é uma apólice. Dois deles são PDFs só com imagem, para exercitar o OCR.

### Demonstração 1 — Processamento dos sete documentos

| Documento | Tipo | Leitura | Coberturas | Exclusões | Seções no índice | Tempo total |
|---|---|---|---|---|---|---|
| Aurora · 1010.0045871 | Apólice, PDF digital | 2 páginas, texto nativo | 9 | 5 | 23 | 0,24 s |
| Boreal · 7702.2026.00913 | Apólice, PDF digital | 2 páginas, texto nativo | 6 | 8 | 22 | 0,12 s |
| Cruzeiro Austral · 3300.558120 | Apólice, PDF digitalizado | 2 páginas via OCR | 7 | 4 | 19 | 3,94 s |
| Equinócio · 4400.771205 | Apólice completa, PDF digital | 10 páginas, texto nativo | 10 | 10 | 163 | 0,48 s |
| Meridiana · ME-2026-000517 | Apólice completa, PDF digital | 10 páginas, texto nativo | 11 | 12 | 177 | 0,57 s |
| Pampa · PS-88.2026.1142 | Apólice, PDF digitalizado | 6 páginas via OCR | 5 | 7 | 101 | 15,80 s |
| Condições gerais Equinócio | Condições gerais, PDF digital | 11 páginas, texto nativo | — | 11 | 174 | 0,74 s |

A triagem reconheceu as seis apólices e identificou corretamente o documento de condições gerais como um documento que não é apólice. Nas apólices completas, as exceções das exclusões ("5.6.1 Exceção: não se aplica a ações derivativas de acionistas minoritários…") ficam ligadas à exclusão correspondente, e exclusões repetidas entre as condições particulares e gerais são unificadas. O OCR em português reconheceu as apólices digitalizadas com os acentos corretos na maior parte do texto; ainda aparecem erros pontuais típicos de digitalização (por exemplo, "Investigagdes" no lugar de "Investigações"), que a revisão humana permite corrigir.

### Demonstração 2 — Índice hierárquico de uma apólice

O índice da Boreal tem 22 seções: 8 de primeiro nível (Dados da apólice, Quadro de coberturas, Franquias, Segurados, Exclusões, Cláusulas particulares, Disposições finais e o cabeçalho) e as subseções numeradas. A seção **EXCLUSÕES** (páginas 1 e 2) reúne 8 itens, entre eles "6. Segurado contra Segurado" e "8. Oferta pública de valores mobiliários". Linhas no formato "rótulo: valor", como "CNPJ: 00.000.001/0001-91", não são confundidas com títulos. Nos documentos longos, a árvore acompanha a numeração das cláusulas em três níveis: na Meridiana, por exemplo, **CLÁUSULA 5 – RISCOS EXCLUÍDOS** → **5.6 Segurado contra Segurado** → **5.6.1 Exceção**, e cada cobertura contratada tem o seu capítulo de condições especiais.

### Demonstração 3 — Comparação das três apólices

| Métrica | Aurora | Boreal | Cruzeiro Austral |
|---|---|---|---|
| Limite Máximo de Garantia | R$ 20 mi | R$ 15 mi | **R$ 25 mi** |
| Prêmio total | R$ 148,5 mil | R$ 96,3 mil | R$ 201 mil |
| Prêmio / LMG | 0,743% | **0,642%** | 0,804% |
| Coberturas | **9** | 6 | 7 |
| Exclusões | 5 | 8 | **4** |

Foram identificadas **28 diferenças objetivas**. Entre os destaques: a cobertura de **Lado C** (mercado de capitais) não está prevista na Boreal; custos emergenciais e gerenciamento de crise só existem na Aurora; a exclusão **"Segurado contra Segurado"** aparece apenas na Boreal, que é mais restritiva nesse ponto; e a Cruzeiro Austral é a única com cobertura para investigações de órgãos reguladores.

### Demonstração 4 — Consulta com citação da seção

Pergunta: *"Existe exclusão de Segurado contra Segurado?"*. No modo offline, o grafo segue pela busca por palavras nas seções do índice e traz em primeiro lugar a cláusula certa: **Boreal · 6. Segurado contra Segurado · página 2**. Com um provedor de IA configurado, o mesmo grafo segue pelo roteador e pelo navegador do índice, abre a seção EXCLUSÕES de cada apólice e redige a resposta citando seção e página, mostrando o caminho percorrido.

### Demonstração 5 — Ambiente público de demonstração

No site publicado, os sete documentos de exemplo vêm de uma **base pré-processada**, gerada fora do servidor e importada ao iniciar: tudo fica disponível em cerca de 2 segundos, sem OCR nem chamadas à IA, mesmo quando o servidor "acorda" (o disco do plano gratuito é apagado a cada reinício). Antes, só o OCR das amostras digitalizadas levava minutos na CPU do plano gratuito. As amostras são **protegidas**: a tentativa de excluir ou editar uma delas retorna erro 403 com uma mensagem explicativa. Os envios são limitados a 20 MB por arquivo, e o servidor não tem nenhuma chave de API configurada: cada visitante usa o modo offline ou a própria chave.

## 7. Demonstração visual das telas

| Landing page — tema escuro | Landing page — tema claro |
|---|---|
| ![Landing page, tema escuro](img/01_landing.png) | ![Landing page, tema claro](img/02_landing_claro.png) |

![Painel com os indicadores da carteira](img/03_painel.png)

![Carteira de apólices com busca, filtro de vigência e seleção para comparar](img/04_carteira.png)

![Detalhe da apólice: indicadores, visão geral, segurados e cláusulas](img/05_apolice.png)

![Aba Índice: sumário em árvore que a IA percorre na consulta](img/06_indice.png)

![Índice de uma apólice completa de 10 páginas (Meridiana): 177 seções, com cláusulas, subitens e exceções](img/13_indice_longo.png)

![Envio de documentos com fila de processamento e apólices de exemplo](img/07_enviar.png)

![Comparação de três apólices: métricas, diferenças classificadas por impacto e pontos de atenção](img/08_comparar.png)

![Primeira página do relatório de comparação exportado em PDF, com a marca Apólis](img/14_relatorio_pdf.png)

![Consulta com citação de apólice, seção e página](img/09_consulta.png)

![Página Sobre a solução: fluxo de processamento e camadas da arquitetura](img/11_sobre.png)

![Página Sobre a solução, aba Consulta: o grafo LangGraph desenhado no tema claro](img/12_sobre_grafo.png)

![Documentação interativa da API (FastAPI)](img/10_api_docs.png)

## 8. Qualidade e testes

A suíte tem **47 testes automatizados** que rodam sem chave de API, usando o modo offline e um LLM simulado com respostas roteirizadas:

- **Ingestão e OCR:** PDF digital, PDF digitalizado e imagem; formatos inválidos.
- **Extração e validação:** extração em blocos e consolidação, correção de JSON fora do esquema, detecção de inconsistências.
- **Documentos longos:** extração das apólices completas (exclusões com exceções, sem duplicatas), triagem das condições gerais e índice com níveis contínuos.
- **Índice:** detecção de seções e subseções, numeração hierárquica, rótulos que não são títulos, índice por página quando não há estrutura, resumos pela IA e queda para resumos automáticos se a IA falhar.
- **Grafo de consulta:** navegação com segunda rodada, descarte de seções inexistentes ou repetidas, rota direta pelos dados estruturados, queda para busca por palavras quando a IA devolve JSON inválido, modo offline.
- **API:** envio, detalhe, revisão humana, exclusão, comparação e exportação, progresso ao vivo (streaming), consulta, SQL somente leitura, proteção das amostras no modo demonstração, limite de tamanho e tentativa de acessar arquivos fora da pasta de amostras.
- **Segurança:** cabeçalhos de segurança e política de conteúdo (CSP), consulta SQL sem fim interrompida, limite de páginas por documento.

## 9. Deploy e operação

- **Plataforma:** Render, serviço Docker com *Root Directory* `Projeto_Final`. A imagem instala o Tesseract com português e serve a API e a interface.
- **Atualização:** deploy automático a cada push no `main` que altere a pasta do projeto (cerca de 3 a 4 minutos, sem tirar a versão anterior do ar durante o build).
- **Modo demonstração:** amostras carregadas na inicialização e protegidas, limite de envio e selo "Demonstração" na interface.
- **Limites do plano gratuito:** o servidor hiberna após 15 minutos sem uso (o primeiro acesso seguinte leva cerca de 50 segundos) e os documentos enviados são apagados a cada reinício.

## 10. Segurança e privacidade

- **Chave de API:** fica apenas na aba do navegador, segue ao provedor em cada requisição e nunca é gravada no servidor.
- **Injeção de código na interface:** todo dado vindo dos documentos é escapado antes de ir para a tela, e uma política de conteúdo (CSP) só permite executar os scripts do próprio sistema. Uma falha desse tipo foi encontrada na revisão de segurança (datas e moeda extraídas eram exibidas sem escape) e corrigida, com a correção verificada no navegador.
- **Consultas SQL:** banco aberto em modo somente leitura, apenas um SELECT por vez, interrupção após 3 segundos e no máximo 5.000 linhas.
- **Documentos enviados:** limite de tamanho (20 MB) e de páginas (60 no ambiente público), e limite de resolução na renderização para OCR, para que um arquivo malicioso não esgote o servidor.
- **Ambiente público:** as amostras não podem ser alteradas nem excluídas, e a tela de envio avisa que os documentos enviados ficam visíveis para outros visitantes. Não há login nem separação por usuário (ver seção 11).
- Os documentos de exemplo são fictícios; nenhum dado real de segurado é usado.

## 11. Limitações e próximos passos

- **Condições gerais separadas:** muitas exclusões ficam nas Condições Gerais; se só a apólice for enviada, a comparação de exclusões fica incompleta.
- **Índice depende do layout:** documentos sem títulos nem cláusulas numeradas viram uma seção por página, e a navegação perde precisão.
- **Alinhamento de coberturas por similaridade de palavras:** nomes muito diferentes para o mesmo conceito podem não ser pareados.
- **OCR:** depende da qualidade da digitalização; tabelas complexas podem perder a estrutura.
- **Sem login:** no ambiente público todos os visitantes compartilham a mesma carteira; não há limite de requisições por visitante.
- **Avaliação quantitativa:** o próximo passo é montar um gabarito das apólices de exemplo e medir a taxa de acerto por campo com cada provedor de IA.
- **Evolução:** memória de conversa no grafo de consulta (perguntas de acompanhamento), embeddings para o alinhamento de cláusulas, autenticação com carteira por usuário e fila de processamento para lotes grandes.

## 12. Referências

- VectifyAI. PageIndex: vectorless, reasoning-based RAG. https://github.com/VectifyAI/PageIndex
- LangChain. LangGraph. https://github.com/langchain-ai/langgraph
- SUSEP. Circular SUSEP nº 637, de 27 de julho de 2021 — seguros do grupo Responsabilidades, incluindo RC D&O.
- Tesseract OCR. https://github.com/tesseract-ocr/tesseract
