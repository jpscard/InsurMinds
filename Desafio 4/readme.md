# 🧠 Desafio 4: Interface Inteligente para Consulta de Arquivos CSV
**Equipe First Class Agents**  

Solução completa e inteligente para interpretação de perguntas em linguagem natural sobre conjuntos de dados armazenados em arquivos CSV e notas fiscais eletrônicas (NF-e).

---

## 🚀 Visão Geral da Solução

Esta plataforma combina **Agentes Inteligentes**, **LLMs (Google Gemini)** e **LangChain** para transformar arquivos CSV brutos e compactados em informações estruturadas, visualizações gráficas e relatórios executivos sob demanda.

### 🌟 Destaques do Projeto
1. **Interface A (Carga de Dados):**
   - Upload de arquivos compactados (`.ZIP`) contendo um ou múltiplos arquivos `.CSV` (ex: `202401_NFs.zip` e `202505_NFe.zip`) **OU** seleção direta de múltiplos arquivos `.CSV` simultaneamente (ex: Cabeçalho e Itens juntos).
   - Detecção automática de formato, delimitadores (`,` ou `;`), casas decimais (`.` ou `,`) e encodings (`UTF-8`, `Latin-1`).
   - Leitura e ingestão automática de **Dicionários de Dados** (`.txt`, `.md`, `.json`, `.csv`) para enriquecimento contextual do agente.
   - Cruzamento inteligente (*merge*) automático entre tabelas mestre (Cabeçalho/NotaFiscal) e detalhes (Itens/NotaFiscalItem).

2. **Interface B (Consulta em Linguagem Natural):**
   - **💬 Agente Q&A:** Chat com agente autônomo baseado em LangChain DataFrame Agent capaz de interpretar consultas complexas, executar código Python em segundo plano e retornar respostas explicadas e tabelas formatadas em Markdown.
   - **💡 Insights Automáticos da IA:** Bateria automatizada de 10 perguntas analíticas de negócio com política de retentativas (*retry/tenacity*).
   - **📊 Dashboard Interativo:** KPIs dinâmicos, ranking Top 10 Clientes e Produtos, análise temporal e ferramenta *Deep Dive* com gráficos Plotly.
   - **✅ Auditoria Fiscal:** Verificação automática de consistência de valores (cabeçalho vs. itens), distribuição geográfica e análise de CFOPs.
   - **📄 Montador de Relatório:** Sistema de "pinagem" de itens gerados (tabelas, gráficos e respostas do agente) com sumário executivo gerado por IA e exportação para `.docx`.

---

## 🛠️ Stack Tecnológica

| Componente | Tecnologia | Finalidade |
| :--- | :--- | :--- |
| **Linguagem** | Python 3.10+ | Desenvolvimento principal |
| **Framework de Agentes** | **LangChain** (`langchain`, `langchain-experimental`) | Orquestração do agente autônomo e ferramentas |
| **LLM** | **Google Gemini 1.5 Flash / Pro** (`langchain-google-genai`) | Modelo de linguagem para raciocínio e geração de código |
| **Interface Web** | **Streamlit** | Interface reativa para Carga e Consulta |
| **Manipulação de Dados** | **Pandas & NumPy** | Ingestão, limpeza e agregação de dados |
| **Visualização** | **Plotly Express** | Gráficos interativos |
| **Geração de Documentos** | **python-docx & Kaleido** | Exportação profissional do relatório |
| **Resiliência** | **Tenacity** | Política de retentativas em chamadas de IA |

---

## 📂 Estrutura de Diretórios

```bash
.
├── Dados/                      # Conjuntos de dados de exemplo (.ZIP)
│   ├── 202401_NFs.zip
│   └── 202505_NFe.zip
│
├── tabs/
│   ├── __init__.py
│   ├── agent_tab.py            # Aba de Chat Q&A com Agente LangChain
│   ├── insights_tab.py         # Aba de Bateria de Insights Automáticos
│   ├── dashboard_tab.py        # Aba do Painel Visual e KPIs
│   ├── fiscal_tab.py           # Aba de Auditoria Fiscal e CFOP
│   └── report_tab.py           # Aba do Montador e Exportador de Relatório
│
├── utils/
│   ├── __init__.py
│   ├── callbacks.py            # Log semântico de raciocínio (Thought/Action/Observation)
│   └── processing.py           # Processamento universal de ZIP, CSVs e DOCX
│
├── app.py                      # Ponto de entrada principal da aplicação Streamlit
├── requirements.txt            # Dependências do projeto
└── README.md                   # Documentação da solução
```

---

## ⚙️ Como Executar a Aplicação

### 1. Instalação das Dependências
Clone o repositório ou descompacte o arquivo e instale os pacotes necessários:
```bash
pip install -r requirements.txt
```

### 2. Configuração da Chave de API Google Gemini
Você pode configurar a chave de duas formas:
- **Opção A (Recomendada):** Criar o arquivo `.streamlit/secrets.toml` com:
  ```toml
  GOOGLE_API_KEY = "sua_chave_aqui"
  ```
- **Opção B:** Inserir a chave diretamente no campo de texto da barra lateral da aplicação.

### 3. Execução da Aplicação
Execute o Streamlit:
```bash
streamlit run app.py
```

---

## 🧠 Explicabilidade do Agente

Ao realizar perguntas na aba **Agente Q&A**, o agente utiliza a metodologia ReAct (*Reasoning + Acting*). Seu fluxo de raciocínio é registrado em tempo real no console/terminal com cores semânticas:
- **🤔 PENSAMENTO:** Raciocínio formulado pelo modelo sobre como abordar o problema.
- **⚡ AÇÃO / FERRAMENTA:** Código Python gerado e executado contra o DataFrame.
- **📝 OBSERVAÇÃO:** Dados brutos retornados pela execução do código.
- **✅ RESPOSTA FINAL:** Síntese final estruturada entregue ao usuário na interface.
