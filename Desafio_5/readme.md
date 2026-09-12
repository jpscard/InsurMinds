# InsureAlert — Ferramenta Inteligente para Comunicação Proativa com Segurados

> Sistema baseado em IA para comunicação proativa com segurados de seguros, monitorando eventos climáticos em tempo real e gerando alertas personalizados antes que sinistros ocorram.

![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-brightgreen.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688.svg)

## 📋 Sobre o Projeto

Este projeto foi desenvolvido como parte do **Desafio 5** do curso, com o objetivo de criar uma solução baseada em **Inteligência Artificial** capaz de realizar comunicação proativa com segurados a partir da análise de eventos climáticos externos.

### O Problema
Grande parte das interações entre seguradoras e clientes acontece **apenas após** a ocorrência de um sinistro.

### A Solução
O **InsureAlert** transforma o modelo reativo em uma abordagem **preventiva**, monitorando eventos climáticos e enviando orientações personalizadas **antes** que um problema aconteça.

## 🏗️ Arquitetura da Solução

O sistema utiliza uma **arquitetura multi-agente** com 4 agentes especializados que trabalham em pipeline:

```
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│  📡 Agente       │───▶│  🔍 Agente       │───▶│  📋 Agente de    │───▶│  ✍️ Agente       │
│  Coletor         │    │  Analisador      │    │  Regras          │    │  Comunicador     │
│                  │    │                  │    │                  │    │                  │
│  Coleta dados    │    │  Classifica      │    │  Cruza eventos   │    │  Gera mensagens  │
│  do INMET e      │    │  eventos por     │    │  com segurados   │    │  personalizadas  │
│  OpenWeatherMap  │    │  tipo e          │    │  aplicando       │    │  com IA          │
│                  │    │  severidade      │    │  regras de       │    │  (Google Gemini) │
│                  │    │                  │    │  negócio         │    │                  │
└──────────────────┘    └──────────────────┘    └──────────────────┘    └──────────────────┘
```

### Agentes Inteligentes

| Agente | Responsabilidade |
|--------|-----------------|
| **Agente Coletor** | Consulta APIs externas (INMET, OpenWeatherMap) e normaliza os dados |
| **Agente Analisador** | Classifica eventos por tipo (chuva, granizo, vento, etc.) e severidade |
| **Agente de Regras** | Cruza eventos com segurados por localização e tipo de apólice |
| **Agente Comunicador** | Gera mensagens personalizadas usando IA Generativa (Google Gemini) |

## 🛠️ Tecnologias Utilizadas

| Tecnologia | Uso |
|-----------|-----|
| **Python 3.10+** | Linguagem principal |
| **FastAPI** | Framework web para a API REST |
| **Google Gemini API** | IA Generativa para personalização de mensagens |
| **INMET API** | Fonte de dados de alertas meteorológicos do Brasil |
| **OpenWeatherMap API** | Previsão do tempo por cidade (opcional) |
| **HTML/CSS/JS** | Dashboard web interativo |
| **Pydantic** | Validação e modelagem de dados |
| **HTTPX** | Cliente HTTP assíncrono |

## 📦 Instalação e Execução

### Pré-requisitos

- **Python 3.10** ou superior
- **pip** (gerenciador de pacotes Python)

### 1. Clone o repositório

```bash
git clone <url-do-repositorio>
cd insure-alert
```

### 2. Crie um ambiente virtual (recomendado)

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Instale as dependências

```bash
pip install -r requirements.txt
```

### 4. Configure as variáveis de ambiente

```bash
# Copie o arquivo de exemplo
cp .env.example .env

# Edite o arquivo .env com suas chaves
# GEMINI_API_KEY é recomendada (obtenha em https://aistudio.google.com/apikey)
# OPENWEATHERMAP_API_KEY é opcional
```

> **Nota:** O sistema funciona sem API keys — usará templates de mensagem em vez de IA generativa, e apenas dados do INMET.

### 5. Execute o servidor

```bash
uvicorn backend.main:app --reload --port 8000
```

### 6. Acesse o dashboard

Abra o navegador em: **http://localhost:8000**

## 🎮 Como Usar

1. **Acesse o dashboard** no navegador
2. **Clique em "Executar Pipeline"** para iniciar o fluxo completo
3. **Acompanhe** a execução passo-a-passo com as animações dos agentes
4. **Visualize** os eventos detectados e as notificações geradas
5. **Clique em uma notificação** para ver os detalhes completos da mensagem

## 📏 Regras de Negócio

### Mapeamento Evento → Tipo de Seguro

| Evento Climático | Seguros Afetados |
|-----------------|-----------------|
| Chuva Intensa (>20mm/h) | Residencial, Automóvel, Empresarial |
| Granizo | Automóvel, Residencial, Agro |
| Ventos Fortes (>50km/h) | Residencial, Empresarial, Agro |
| Tempestade | Todos os tipos |
| Onda de Calor (>38°C) | Vida, Agro |
| Geada (<3°C) | Agro, Residencial |

### Critérios de Notificação

1. O segurado deve estar em um **estado/cidade afetado** pelo evento
2. O segurado deve ter uma **apólice do tipo afetado**
3. Eventos com severidade **média ou superior** geram notificação
4. Eventos de **granizo e tempestade** sempre geram notificação
5. Notificações são **priorizadas** por severidade e tipo de exposição

## 💬 Exemplos de Mensagens Geradas

### Alerta de Tempestade — Segurado Residencial (Email)

```
Prezado(a) Maria,

O Instituto Nacional de Meteorologia (INMET) emitiu um alerta de tempestade
para a região de Curitiba/PR.

Como titular de um seguro residencial, recomendamos:
• Busque abrigo seguro imediatamente
• Desligue aparelhos eletrônicos da tomada
• Feche janelas e portas com segurança
• Em caso de emergência: Bombeiros (193), Defesa Civil (199)

Estamos aqui para ajudar. Sua segurança é nossa prioridade.

Atenciosamente,
Sua Seguradora
```

### Alerta de Granizo — Segurado Automóvel (SMS)

```
🧊 Alerta: Granizo previsto em Florianópolis. Proteja seu veículo em local
coberto. Evite áreas externas.
```

## 📡 APIs Externas Utilizadas

### INMET (Instituto Nacional de Meteorologia)
- **Endpoint:** `https://apiprevmet3.inmet.gov.br/avisos/ativos`
- **Tipo:** API pública sem autenticação
- **Dados:** Alertas meteorológicos ativos em todo o Brasil

### OpenWeatherMap (opcional)
- **Endpoint:** `https://api.openweathermap.org/data/2.5/forecast`
- **Tipo:** API com free tier (1.000 chamadas/dia)
- **Dados:** Previsão do tempo por cidade

## 📁 Estrutura do Projeto

```
├── README.md                    # Este arquivo
├── LICENSE                      # Licença MIT
├── .env.example                 # Template de variáveis de ambiente
├── .gitignore                   # Arquivos ignorados pelo Git
├── requirements.txt             # Dependências Python
│
├── backend/
│   ├── main.py                  # FastAPI app + rotas
│   ├── config.py                # Configurações e constantes
│   ├── agents/
│   │   ├── weather_collector.py # Agente 1: Coleta de dados
│   │   ├── event_analyzer.py    # Agente 2: Análise de eventos
│   │   ├── rules_engine.py      # Agente 3: Regras de negócio
│   │   └── message_generator.py # Agente 4: Geração de mensagens
│   ├── models/
│   │   ├── weather.py           # Modelos de dados meteorológicos
│   │   ├── policyholder.py      # Modelos de segurados
│   │   └── notification.py      # Modelos de notificações
│   └── data/
│       └── policyholders.json   # Base de segurados simulada
│
└── frontend/
    ├── index.html               # Dashboard principal
    ├── css/styles.css            # Estilos premium
    └── js/app.js                # Lógica do frontend
```

## 📄 Licença

Este projeto está licenciado sob a licença **MIT** — consulte o arquivo [LICENSE](LICENSE) para detalhes.
