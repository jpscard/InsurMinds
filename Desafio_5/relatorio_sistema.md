# InsureAlert — Comunicação Proativa com Segurados
### Desafio 5 — InsurMinds

---

## Integrantes

| Nome | E-mail | Telefone |
|---|---|---|
| Leonardo Pereira | ligueproleo@gmail.com | +55 11 98479-6122 |
| João Cardoso | jpscardoso@ufpa.br | +55 91 98273-6292 |

**Github:** https://github.com/jpscard/InsurMinds/tree/main/Desafio_5  
**Aplicação:** http://localhost:8000 *(executar localmente com `uvicorn backend.main:app --reload`)*

---

## 1. FRAMEWORK E STACK TECNOLÓGICA ESCOLHIDA

Para atender aos requisitos de monitoramento em tempo real, inteligência contextual e geração de mensagens personalizadas, a solução foi construída utilizando o ecossistema Python moderno para APIs assíncronas e IA generativa:

| Componente | Tecnologia / Versão | Justificativa e Papel na Solução |
|---|---|---|
| Framework Web / API | **FastAPI** (≥ 0.100.0) | Framework assíncrono de alta performance para expor os endpoints REST e servir o frontend estático com mínima latência. |
| Servidor ASGI | **Uvicorn** (≥ 0.23.0) | Servidor de produção compatível com ASGI, suportando operações `async/await` exigidas pelo pipeline de 4 agentes. |
| Modelo de Linguagem (LLM) | **Google Gemini 2.0 Flash** | Modelo com alta velocidade de resposta, ampla janela de contexto e custo reduzido, ideal para geração de mensagens personalizadas em lote para múltiplos segurados. |
| Orquestração dos Agentes | **Python puro (OOP)** | Pipeline sequencial de 4 agentes especializados implementados como classes Python, com passagem de dados tipados entre etapas. |
| Validação de Dados | **Pydantic** (≥ 2.0.0) | Modelagem e validação declarativa de todos os modelos de domínio (WeatherEvent, Policyholder, Notification, PipelineResult). |
| Cliente HTTP Assíncrono | **HTTPX** (≥ 0.24.0) | Consultas assíncronas às APIs externas (INMET, OpenWeatherMap) com suporte nativo a timeout e tratamento de erros HTTP. |
| Configuração de Ambiente | **python-dotenv** (≥ 1.0.0) | Carregamento seguro de API keys e variáveis sensíveis a partir de arquivo `.env`. |
| Interface de Usuário | **HTML5 / CSS3 / JavaScript** | Dashboard web interativo servido diretamente pelo FastAPI via `StaticFiles`, sem dependências de framework frontend externo. |

---

## 2. ARQUITETURA DA SOLUÇÃO

A solução foi concebida sob uma **arquitetura em camadas com pipeline multi-agente**, garantindo baixo acoplamento, alta modularidade e separação clara entre coleta de dados, inteligência de negócio e apresentação:

```
┌───────────────────────────────────────────────────────────────────┐
│             CAMADA DE APRESENTAÇÃO (frontend/)                     │
│  Landing Page · Login · Registro · Dashboard Operacional          │
│  Servidos pelo FastAPI via /static mount                          │
└─────────────────────────┬─────────────────────────────────────────┘
                          │ HTTP REST (JSON)
┌─────────────────────────▼─────────────────────────────────────────┐
│             CAMADA DE ORQUESTRAÇÃO (backend/main.py)              │
│  FastAPI · Autenticação · Roteamento · Estado do Pipeline          │
└──────┬──────────────────────────────────────────────┬─────────────┘
       │                                              │
┌──────▼──────────────────────────────────────────────▼─────────────┐
│             CAMADA DE AGENTES (backend/agents/)                    │
│                                                                    │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐  │
│  │  Agente 1  │→ │  Agente 2  │→ │  Agente 3  │→ │  Agente 4  │  │
│  │  Coletor   │  │ Analisador │  │  Regras    │  │Comunicador │  │
│  └────────────┘  └────────────┘  └────────────┘  └────────────┘  │
└──────┬────────────────────────────────────────────────┬───────────┘
       │                                                │
┌──────▼────────────┐                      ┌───────────▼────────────┐
│  APIs EXTERNAS    │                      │  IA GENERATIVA         │
│  · INMET (pública)│                      │  Google Gemini 2.0     │
│  · OpenWeatherMap │                      │  Flash                 │
└───────────────────┘                      └────────────────────────┘
```

**● Camada de Apresentação (`frontend/`):** Interface web completa com 4 páginas HTML e 3 arquivos CSS. Autenticação dual com fallback local em `localStorage`. Comunicação via `fetch()` com os endpoints REST.

**● Camada de Orquestração (`backend/main.py`):** Centraliza as 11 rotas REST, o estado global do pipeline, a autenticação em memória e o ciclo de vida do servidor (startup/shutdown).

**● Camada de Agentes (`backend/agents/`):** 4 classes Python especializadas, cada uma com responsabilidade única e interface de entrada/saída bem definida via modelos Pydantic.

**● Camada de Modelos (`backend/models/`):** Modelos de dados validados (WeatherEvent, Policyholder, Notification, PipelineResult) compartilhados entre todos os agentes.

**● Camada de Persistência (`backend/data/`):** Base JSON com 20 segurados simulados, carregada na inicialização do servidor.

---

## 3. DESCRIÇÃO DOS AGENTES DESENVOLVIDOS

A solução emprega **4 agentes autônomos especializados** que operam em pipeline sequencial:

---

### Agente 1 — Coletor de Dados Meteorológicos (`weather_collector.py`)

Operando na primeira etapa do pipeline, este agente é responsável por consultar fontes externas de dados climáticos e normalizar todos os dados em um formato unificado (`WeatherEvent`).

- **Fonte primária:** API pública do INMET (`/avisos/ativos`), consultando os períodos `hoje` e `amanhã` simultaneamente.
- **Fonte secundária:** OpenWeatherMap (previsão de 5 dias, intervalos de 3h) — ativada quando a API key correspondente está configurada.
- **Resiliência:** Caso o INMET não retorne alertas ativos, o agente gera automaticamente 3 eventos de demonstração realistas (Tempestade Sul/Sudeste, Chuva Intensa MG/SP, Geada Sul), garantindo que o pipeline sempre produza um resultado demonstrável.
- **Cliente HTTP:** HTTPX assíncrono com timeout de 30 segundos.
- **Saída:** `list[WeatherEvent]` — lista de eventos meteorológicos normalizados e prontos para análise.

---

### Agente 2 — Analisador de Eventos Climáticos (`event_analyzer.py`)

Especializado na classificação e enriquecimento semântico dos eventos brutos recebidos do Agente 1.

- **Classificação por tipo:** Utiliza NLP baseado em correspondência de palavras-chave para identificar 7 categorias de eventos: Chuva Intensa, Granizo, Vento Forte, Tempestade, Onda de Calor, Geada e Raios.
- **Classificação por severidade:** Mapeia os níveis de alerta do INMET (Perigo Potencial → MÉDIA, Perigo → ALTA, Grande Perigo → CRÍTICA). Para outras fontes, usa análise textual.
- **Priorização:** Em eventos com múltiplas características, prioriza sempre a classificação como `TEMPESTADE`, por ser o tipo de maior impacto sistêmico.
- **Filtro de relevância:** Descarta eventos de severidade BAIXA, exceto Granizo e Tempestade, que sempre são considerados relevantes independentemente da severidade.
- **Saída:** `list[WeatherEvent]` — apenas os eventos relevantes para notificação, enriquecidos com tipo e severidade.

---

### Agente 3 — Motor de Regras de Negócio (`rules_engine.py`)

O agente mais estratégico do sistema, responsável por determinar exatamente quais segurados devem ser notificados e com qual prioridade.

- **Cruzamento Evento × Segurado:** Para cada evento relevante, verifica cada segurado ativo quanto a: (1) localização na área afetada (por estado/cidade) e (2) tipo de apólice coberto pelo evento.
- **Regras de mapeamento:** 7 mapeamentos configurados determinam quais tipos de seguro são afetados por cada tipo de evento (ex.: Granizo afeta Automóvel, Residencial e Agro).
- **Sistema de prioridade:** Calcula uma pontuação numérica por notificação, combinando severidade do evento (+25 a +100), tipo do evento (+5 a +20) e combinações críticas de tipo de evento × tipo de seguro (+10 extra para pares de maior risco).
- **Deduplicação:** Chave composta `{policyholder_id}_{event_id}_{insurance_type}` impede notificações duplicadas no mesmo ciclo de execução.
- **Saída:** `list[NotificationMatch]` — lista ordenada por prioridade (maior prioridade primeiro) dos pares segurado × evento × apólice a serem notificados.

---

### Agente 4 — Gerador de Mensagens Personalizadas (`message_generator.py`)

O agente de inteligência artificial da solução, responsável por transformar dados técnicos em comunicações humanizadas e contextualizadas.

- **Geração com IA (primária):** Utiliza o Google Gemini 2.0 Flash via prompt estruturado, fornecendo contexto completo do evento (tipo, severidade, riscos, instruções oficiais) e do segurado (nome, cidade/estado, tipo de seguro, canal preferido). Exige resposta em 4 componentes via tags XML: assunto, mensagem longa, SMS (≤ 160 chars) e lista de recomendações.
- **Geração com templates (fallback):** Caso o Gemini não esteja disponível, utiliza 6 templates pré-definidos por tipo de evento, com substituição dinâmica de variáveis (nome, cidade, estado, tipo de seguro).
- **Canais suportados:** SMS, E-mail, Push Notification e WhatsApp — a escolha é feita automaticamente conforme a preferência cadastrada do segurado.
- **Saída:** `list[Notification]` — notificações completas, marcadas com status `ENVIADA` (envio simulado), prontas para exibição no dashboard.

---

## 4. FLUXO DE FUNCIONAMENTO DA APLICAÇÃO

O ciclo operacional da aplicação segue um fluxo em 6 etapas, ativado pelo usuário através do dashboard:

**Etapa 1 — Acesso e Autenticação:**
O usuário acessa a landing page (`/`), navega para login (`/login`) e autentica com suas credenciais. O sistema tenta autenticação na API REST e, se o backend estiver offline, usa fallback em `localStorage` com a conta demo `admin@insure.com / admin123`.

**Etapa 2 — Dashboard e Visão Geral:**
Após autenticação, o usuário é redirecionado para o dashboard (`/dashboard`), onde visualiza a base de 20 segurados cadastrados, as regras de negócio configuradas e o status do último pipeline executado.

**Etapa 3 — Execução do Pipeline:**
O usuário aciona o botão "Executar Pipeline", que dispara uma requisição `POST /api/pipeline/run`. O backend inicia a execução sequencial dos 4 agentes, registrando o tempo de execução de cada etapa.

**Etapa 4 — Coleta e Análise em Tempo Real:**
O Agente Coletor consulta o INMET em tempo real. Os alertas ativos (ou eventos de demonstração, em caso de ausência de alertas) são repassados ao Agente Analisador, que filtra e classifica os eventos relevantes.

**Etapa 5 — Aplicação de Regras e Geração de Mensagens:**
O Agente de Regras cruza os eventos relevantes com os 20 segurados cadastrados, identifica os pares elegíveis e calcula as prioridades. O Agente Comunicador gera então mensagens personalizadas via Gemini (ou templates de fallback) para cada match.

**Etapa 6 — Visualização dos Resultados:**
O dashboard exibe o resumo da execução (eventos coletados, relevantes, segurados notificados), o log passo-a-passo de cada agente com tempo de execução, a lista de notificações geradas e os detalhes completos de cada mensagem ao clicar.

---

## 5. CONSULTAS / DEMONSTRAÇÕES REALIZADAS

Abaixo são detalhadas 5 situações demonstradas pelo sistema, ilustrando o raciocínio de cada agente e o resultado estruturado gerado:

---

### Demonstração 1 — Pipeline com Alertas Reais do INMET

**Situação:** Execução do pipeline em dia com alertas ativos publicados pelo INMET.

**Raciocínio do Agente Coletor:** Realiza GET em `https://apiprevmet3.inmet.gov.br/avisos/ativos`, itera pelos períodos `hoje` e `amanhã`, parseia os campos de estados afetados, municípios, severidade e instruções, e normaliza tudo em objetos `WeatherEvent`.

**Resultado:**

| Métrica | Valor |
|---|---|
| Eventos brutos coletados | Variável (depende dos alertas ativos do INMET) |
| Eventos relevantes identificados | Apenas os de severidade MÉDIA ou superior |
| Segurados a notificar | Conforme cruzamento por estado/apólice |
| Notificações geradas | 1 por par segurado × evento × apólice |

---

### Demonstração 2 — Pipeline em Modo de Demonstração (Sem Alertas Ativos)

**Situação:** Execução do pipeline quando o INMET não possui alertas ativos no momento.

**Raciocínio do Agente Coletor:** Detecta lista vazia retornada pela API e aciona o método `generate_demo_events()`, criando 3 eventos realistas que cobrem o cenário mais comum de alertas no Brasil.

**Eventos de demonstração gerados:**

| Evento | Severidade | Estados Afetados | Cidades |
|---|---|---|---|
| Tempestade | MÉDIA (Perigo Potencial) | PR, SC, RS, SP | Curitiba, Florianópolis, Porto Alegre, São Paulo + 15 cidades |
| Chuva Intensa | ALTA (Perigo) | MG, SP | Belo Horizonte, São Paulo, Guarulhos, Campinas, Sorocaba |
| Geada | MÉDIA (Perigo Potencial) | PR, SC, RS | Guarapuava, Ponta Grossa, Curitiba, Caxias do Sul, Chapecó |

---

### Demonstração 3 — Cruzamento de Regras e Priorização

**Situação:** Com os 3 eventos de demonstração, o Agente de Regras cruza com os 20 segurados e determina quais devem ser notificados.

**Raciocínio do Agente de Regras:** Para cada evento, identifica os tipos de seguro afetados pelas regras. Para cada segurado ativo, verifica se seu estado/cidade é coberto e se possui apólice do tipo afetado. Calcula prioridade e descarta duplicatas.

**Exemplo de priorização para evento Tempestade (MÉDIA + boost +20):**

| # | Segurado | Cidade/UF | Apólice | Prioridade |
|---|---|---|---|---|
| 1 | Maria Silva | Curitiba/PR | Automóvel | 80 pts (50+20+10) |
| 2 | Carlos Pereira | Porto Alegre/RS | Automóvel | 80 pts |
| 3 | Luciana Mendes | Blumenau/SC | Residencial | 70 pts (50+20) |
| 4 | Ana Oliveira | São Paulo/SP | Residencial | 70 pts |
| 5 | Fernanda Costa | Londrina/PR | Agro | 70 pts |

---

### Demonstração 4 — Geração de Mensagem com Google Gemini

**Situação:** Agente Comunicador gera mensagem personalizada para Maria Silva (Curitiba/PR, seguro residencial + automóvel) sobre alerta de tempestade.

**Prompt enviado ao Gemini (síntese):** Contexto do evento: Tempestade, severidade MÉDIA, riscos de granizo e ventos 40-60 km/h, instruções do INMET. Contexto do segurado: Maria (primeiro nome), Curitiba/PR, seguro residencial + automóvel, canal e-mail.

**Resposta gerada (exemplo):**

> **Assunto:** ⛈️ Alerta de Tempestade em Curitiba — Proteja seu Lar e Veículo
>
> Prezada Maria,
>
> O Instituto Nacional de Meteorologia (INMET) emitiu um alerta de **tempestade com risco de granizo** para a região de Curitiba/PR. Como titular de um seguro residencial e automóvel, recomendamos ação preventiva imediata:
>
> • Estacione seu veículo em garagem ou local coberto
> • Recolha objetos soltos em áreas externas (vasos, móveis, tendas)
> • Feche janelas e portas com segurança
> • Desligue aparelhos eletrônicos da tomada
> • Em caso de emergência: Bombeiros (193), Defesa Civil (199)
>
> **SMS:** ⛈️ Alerta Curitiba: Tempestade c/ granizo. Proteja veículo em local coberto. Recolha objetos externos. Defesa Civil: 199

---

### Demonstração 5 — Geração de Mensagem com Template de Fallback

**Situação:** Gemini não está configurado (sem API key). O sistema usa o template pré-definido para o evento de Geada, direcionado à Fazenda São José Agrícola (Guarapuava/PR, seguro agro).

**Raciocínio do Agente Comunicador:** Seleciona `FALLBACK_TEMPLATES[EventType.GEADA]`, substitui variáveis (`{name}` → "Fazenda", `{city}` → "Guarapuava", `{state}` → "PR", `{insurance_type}` → "seguro agrícola") e extrai as recomendações das linhas que começam com `•`.

**Mensagem gerada:**

> **Assunto:** ❄️ Alerta de Geada — Proteja suas plantações
>
> Prezado(a) Fazenda,
>
> Há risco de geada na região de Guarapuava/PR.
>
> Recomendações para seu seguro agrícola:
> • Proteja plantações sensíveis ao frio
> • Verifique sistemas de aquecimento
> • Proteja tubulações expostas contra congelamento
> • Mantenha animais em abrigos adequados
>
> **SMS:** ❄️ Alerta: Geada prevista em Guarapuava. Proteja plantações e tubulações. Verifique aquecimento.

---

## 6. DEMONSTRAÇÃO VISUAL DAS TELAS DA APLICAÇÃO

**Landing Page (`/`):** Apresentação do produto InsureAlert com seções de benefícios, fluxo de funcionamento, chamada para ação (CTA) e animações de entrada. Botões de acesso ao Login e Dashboard.

**Página de Login (`/login`):** Formulário de autenticação com validação inline, toggle de visibilidade de senha, opção "Lembrar de mim" e conta demo pré-configurada para apresentação.

**Página de Registro (`/register`):** Formulário completo com validação em tempo real, indicador visual de força de senha (4 níveis: Fraca / Média / Forte / Excelente) e seleção de tipo de seguro.

**Dashboard Principal (`/dashboard`):** Painel operacional central com:
- **Aba Visão Geral:** KPIs do último pipeline (eventos, segurados, notificações), log passo-a-passo dos agentes com tempos de execução e badges de status.
- **Aba Notificações:** Lista de todas as notificações geradas com filtro por severidade, tipo e canal. Clique em qualquer notificação abre o painel de detalhes com a mensagem completa, recomendações e metadados.
- **Aba Segurados:** Tabela com os 20 segurados cadastrados, suas apólices e canais preferidos.
- **Aba Regras:** Exibição das regras de negócio configuradas e do mapeamento Evento → Tipo de Seguro.
- **Botão "Executar Pipeline":** Aciona o pipeline completo com feedback visual de progresso em tempo real.

---

*Relatório técnico completo do sistema InsureAlert — Desafio 5 — InsurMinds.*
