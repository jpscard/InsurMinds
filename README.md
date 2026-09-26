# InsurMinds – Repositório de Desafios

Repositório oficial dos projetos e soluções desenvolvidas para os desafios da **InsurMinds**.

---

## Estrutura do Repositório

| Diretório | Descrição do Desafio | Tecnologias Principais |
| :--- | :--- | :--- |
| **[Desafio_5](./Desafio_5/)** | **Ferramenta Inteligente para Comunicação Proativa com o Segurado** | Multi-Agente Autônomo, Google Gemini 2.5 Flash Lite, FastAPI, INMET, CPaaS Omnicanal |
| **[Desafio_4](./Desafio_4/)** | **Agente Inteligente para Interpretação e Auditoria de Notas Fiscais e CSVs** | LangChain, Google Gemini, Streamlit, Pandas, Plotly |
| **[Desafio 3](./Desafio%203/)** | **Modelo Preditivo e Análise de Dados** | Python, Jupyter Notebook, Pandas, Scikit-Learn |

---

## Destaque: Desafio 5 – InsureAlert: Comunicação Proativa com o Segurado

Solução completa baseada em **Arquitetura Multi-Agente em Python Puro** e **Google Gemini 2.5 Flash Lite** para monitoramento em tempo real de eventos meteorológicos (INMET), análise preditiva de risco atuarial e envio proativo de comunicados preventivos com preview omnicanal (WhatsApp, SMS, E-mail e Push).

### Principais Módulos:
1. **Agente 1 — Coleta Meteorológica:** Monitoramento contínuo de avisos meteorológicos ativos do INMET com fallback de contingência resiliente.
2. **Agente 2 — Análise de Eventos:** Classificação em 7 tipos de evento climático e mapeamento de 4 níveis de severidade com filtro de relevância atuarial.
3. **Agente 3 — Motor de Regras e Cruzamento Atuarial:** Mapeamento geoespacial e matriz de suscetibilidade de apólices (Auto, Residencial, Agro, Empresarial, Vida) com scoring de prioridade e deduplicação de contatos.
4. **Agente 4 — Geração de Mensagens com IA:** Síntese empática contextualizada via Google Gemini 2.5 Flash Lite com tags estruturadas, diretriz formal sem emojis e contingência por templates institucionais.
5. **Dashboard Operacional Omnicanal:** Layout WhatsApp Web com Side Menu colapsável, suporte nativo a Dark/Light Theme, simulação de envio e botões de resposta rápida interativa (Quick Replies) gerando Protocolos de Assistência com SLA.
6. **Métricas Atuariais & Event Bus:** Cálculo em tempo real de ROI preventivo, capital sob risco, estimativa de sinistros evitados e barramento de auditoria regulatória (LGPD / SUSEP).

### Como Executar Localmente:
```bash
cd Desafio_5
pip install -r requirements.txt
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

### Documentação e Relatórios:
* **Relatório Oficial em PDF:** [Desafio_5/InsurMinds – Desafio 5.pdf](./Desafio_5/InsurMinds%20–%20Desafio%205.pdf)
* **Relatório Oficial em Word:** [Desafio_5/InsurMinds – Desafio 5.docx](./Desafio_5/InsurMinds%20–%20Desafio%205.docx)
* **Relatório Técnico Completo:** [Desafio_5/relatorio_sistema.md](./Desafio_5/relatorio_sistema.md)

---

## Destaque: Desafio 4 – Agente Fiscal e Analítico

Solução completa baseada em **Agentes Autônomos (ReAct)** e **Google Gemini** para processamento, consulta em linguagem natural e auditoria de documentos fiscais e arquivos CSV.

### Principais Módulos:
1. **Interface A – Carga e Fusão Relacional:** Upload de múltiplos arquivos .CSV ou arquivos compactados .ZIP com detecção automática de formato e junção de tabelas mestre-detalhe.
2. **Aba 1 – Consulta em Linguagem Natural:** Agente conversacional com raciocínio transparente, geração de código Python determinístico, tabelas estruturadas e gráficos dinâmicos.
3. **Aba 2 – Insights Automáticos:** Bateria com 10 indicadores analíticos de negócio executados com IA e retentativas automáticas.
4. **Aba 3 – Painel Gerencial / Dashboard:** KPIs globais, rankings Top 10 Clientes e Produtos, série temporal e ferramenta multidimensional Deep Dive.
5. **Aba 4 – Auditoria e Conformidade Fiscal:** Validação de consistência entre valores declarados e itens, proporção geográfica e análise de CFOPs.
6. **Aba 5 – Montador de Relatório Executivo:** Consolidação de tópicos selecionados com síntese por IA e exportação para Microsoft Word (.docx).
