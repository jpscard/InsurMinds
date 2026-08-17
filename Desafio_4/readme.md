# Desafio 4: Interface Inteligente para Consulta e Auditoria de Arquivos CSV
**Equipe First Class Agents**  

Solução computacional para interpretação de consultas em linguagem natural sobre conjuntos de dados fiscais e arquivos CSV estruturados.

---

## 1. Visão Geral da Solução

A plataforma integra **Agentes Autônomos**, **Modelos de Linguagem (Google Gemini)** e o framework **LangChain** para converter bases de dados e arquivos compactados em análises quantitativas, representações gráficas e relatórios executivos.

### Recursos Principais
1. **Interface A (Carga e Integração de Dados):**
   - Suporte ao envio de arquivos compactados (`.ZIP`) contendo múltiplos arquivos `.CSV` (ex: `202401_NFs.zip` e `202505_NFe.zip`) ou seleção direta de múltiplos arquivos `.CSV` simultâneos.
   - Identificação automática de delimitadores (`,` ou `;`), formatação decimal (`.` ou `,`) e codificações (`UTF-8`, `Latin-1`).
   - Ingestão de Dicionários de Dados complementares (`.txt`, `.md`, `.json`, `.csv`) para fornecimento de contexto semântico ao agente.
   - Consolidação relacional automática (*merge*) entre registros de cabeçalho e itens detalhados.

2. **Interface B (Consulta e Análise Analítica):**
   - **Consulta em Linguagem Natural:** Agente conversacional baseado em ReAct capaz de formular e executar rotinas em Python (Pandas) para retornar dados estruturados e tabelas Markdown.
   - **Insights Automáticos de Negócio:** Execução automatizada de indicadores fundamentais com controle de contingência e retentativas.
   - **Painel Gerencial / Dashboard:** Indicadores-chave (KPIs), classificações Top 10, evolução temporal e módulo de análise multidimensional com Plotly.
   - **Auditoria Fiscal:** Verificação de consistência entre valores declarados e somatórios de itens, segregação geográfica e análise por CFOP.
   - **Montador de Relatório Executivo:** Consolidação de tópicos selecionados com síntese executiva por IA e exportação em formato Microsoft Word (`.docx`).

---

## 2. Tecnologias Utilizadas

| Componente | Tecnologia | Finalidade |
| :--- | :--- | :--- |
| **Linguagem** | Python 3.10+ | Desenvolvimento e processamento de dados |
| **Orquestração de Agentes** | LangChain (`langchain`, `langchain-experimental`) | Gerenciamento do ciclo de raciocínio e ferramentas |
| **Modelos de Linguagem** | Google Gemini (2.0-flash / 1.5-flash / Pro) | Raciocínio, geração de rotinas e síntese textual |
| **Interface Web** | Streamlit | Interface para operação e visualização |
| **Manipulação de Dados** | Pandas & NumPy | Carga, transformação e agregação estruturada |
| **Visualização Gráfica** | Plotly Express | Gráficos interativos e dinâmicos |
| **Geração de Documentos** | python-docx | Compilação e exportação do relatório formal |
| **Resiliência** | Tenacity | Controle de retentativas em chamadas de API |

---

## 3. Estrutura de Diretórios

```bash
.
├── Dados/                      # Conjuntos de dados de exemplo (.ZIP)
│   ├── 202401_NFs.zip
│   └── 202505_NFe.zip
│
├── tabs/
│   ├── __init__.py
│   ├── agent_tab.py            # Aba de Consulta em Linguagem Natural
│   ├── insights_tab.py         # Aba de Insights Automáticos de Negócio
│   ├── dashboard_tab.py        # Aba do Painel Gerencial e KPIs
│   ├── fiscal_tab.py           # Aba de Auditoria Fiscal e CFOP
│   └── report_tab.py           # Aba do Montador de Relatório Executivo
│
├── utils/
│   ├── __init__.py
│   ├── agent_utils.py          # Mecanismo de failover e execução resiliente
│   ├── callbacks.py            # Monitoramento e registro de raciocínio no terminal
│   └── processing.py           # Ingestão de arquivos e geração de relatórios
│
├── app.py                      # Aplicação principal
├── requirements.txt            # Dependências do projeto
└── README.md                   # Documentação técnica
```

---

## 4. Instruções de Execução

### 4.1 Instalação das Dependências
Instale os pacotes requeridos através do gerenciador `pip`:
```bash
pip install -r requirements.txt
```

### 4.2 Configuração da Chave de API
A credencial de acesso ao Google Gemini pode ser configurada:
- No arquivo `.streamlit/secrets.toml`:
  ```toml
  GOOGLE_API_KEY = "sua_chave_aqui"
  ```
- Ou informada diretamente no painel lateral da aplicação web.

### 4.3 Inicialização do Servidor
Inicie a aplicação com o comando:
```bash
streamlit run app.py
```

---

## 5. Rastreabilidade e Auditoria do Agente

As consultas realizadas são processadas sob o padrão ReAct (*Reasoning + Acting*). O fluxo de resolução é registrado em tempo real no console de execução:
- **[RACIOCINIO]:** Hipótese e plano de execução formulado pelo modelo.
- **[ACAO]:** Rotina Python gerada para execução sobre os dados.
- **[OBSERVACAO]:** Retorno bruto resultante da execução.
- **[RESPOSTA FINAL]:** Conclusão estruturada apresentada ao usuário.
