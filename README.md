# InsurMinds – Repositório de Desafios

Repositório oficial dos projetos e soluções desenvolvidas para os desafios da **InsurMinds**.

---

## Estrutura do Repositório

| Diretório | Descrição do Desafio | Tecnologias Principais |
| :--- | :--- | :--- |
| **[Desafio_4](./Desafio_4/)** | **Agente Inteligente para Interpretação e Auditoria de Notas Fiscais e CSVs** | LangChain, Google Gemini, Streamlit, Pandas, Plotly |
| **[Desafio 3](./Desafio%203/)** | **Modelo Preditivo e Análise de Dados** | Python, Jupyter Notebook, Pandas, Scikit-Learn |

---

## Destaque: Desafio 4 – Agente Fiscal e Analítico

Solução completa baseada em **Agentes Autônomos (ReAct)** e **Google Gemini** para processamento, consulta em linguagem natural e auditoria de documentos fiscais e arquivos CSV.

### Principais Módulos:
1. **Interface A – Carga e Fusão Relacional:** Upload de múltiplos arquivos .CSV ou arquivos compactados .ZIP (202401_NFs.zip, 202505_NFe.zip) com detecção automática de formato e junção de tabelas mestre-detalhe.
2. **Aba 1 – Consulta em Linguagem Natural:** Agente conversacional com raciocínio transparente, geração de código Python determinístico, tabelas estruturadas e gráficos dinâmicos.
3. **Aba 2 – Insights Automáticos:** Bateria com 10 indicadores analíticos de negócio executados com IA e retentativas automáticas.
4. **Aba 3 – Painel Gerencial / Dashboard:** KPIs globais, rankings Top 10 Clientes e Produtos, série temporal e ferramenta multidimensional *Deep Dive*.
5. **Aba 4 – Auditoria e Conformidade Fiscal:** Validação de consistência entre valores declarados e itens, proporção geográfica e análise de CFOPs.
6. **Aba 5 – Montador de Relatório Executivo:** Consolidação de tópicos selecionados com síntese por IA e exportação para Microsoft Word (.docx).

### Como Executar Localmente:
`ash
# 1. Instalar dependências
pip install -r requirements.txt

# 2. Executar a aplicação Streamlit
streamlit run app.py
`

### Documentação e Relatórios:
* **Relatório Oficial em Word:** Desafio_4/InsurMinds – Desafio 4.docx
* **Relatório Oficial em PDF:** Desafio_4/InsurMinds – Desafio 4.pdf
* **Capturas de Tela:** Desafio_4/prints/
