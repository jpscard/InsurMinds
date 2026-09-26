import subprocess
import os

def run():
    print("=== Preparando commit e push do Desafio 5 para o GitHub ===")

    # 1. Garantir que todas as alterações locais estão no stage
    subprocess.run(['git', 'add', '-A'], check=True)
    tree_d5 = subprocess.check_output(['git', 'write-tree']).strip().decode('ascii')
    print(f"Tree Desafio_5 gerada: {tree_d5}")

    # 2. Obter commit e tree atuais de origin/main
    origin_commit = subprocess.check_output(['git', 'rev-parse', 'origin/main']).strip().decode('ascii')
    origin_tree = subprocess.check_output(['git', 'rev-parse', 'origin/main^{tree}']).strip()
    print(f"Origin commit atual: {origin_commit}")

    # 3. Preparar novo README.md da raiz do repositório
    root_readme_content = """# InsurMinds – Repositório de Desafios

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
"""

    p_hash = subprocess.Popen(['git', 'hash-object', '-w', '--stdin'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    readme_blob, _ = p_hash.communicate(input=root_readme_content.encode('utf-8'))
    readme_blob = readme_blob.strip().decode('ascii')
    print(f"Blob README.md da raiz gerado: {readme_blob}")

    # 4. Montar a nova árvore da raiz
    raw_lines = subprocess.check_output(['git', 'ls-tree', origin_tree]).split(b'\n')
    new_entries = []
    for line in raw_lines:
        if not line.strip():
            continue
        mode_type, rest = line.split(b' ', 1)
        type_, rest = rest.split(b' ', 1)
        sha, name = rest.split(b'\t', 1)
        if name == b'Desafio_5':
            new_entries.append(f"040000 tree {tree_d5}\tDesafio_5".encode('utf-8'))
        elif name == b'README.md':
            new_entries.append(f"100644 blob {readme_blob}\tREADME.md".encode('utf-8'))
        else:
            new_entries.append(line)

    p_tree = subprocess.Popen(['git', 'mktree'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    new_root_tree, _ = p_tree.communicate(input=b'\n'.join(new_entries) + b'\n')
    new_root_tree = new_root_tree.strip().decode('ascii')
    print(f"Nova árvore da raiz criada: {new_root_tree}")

    # 5. Criar o commit apontando para origin/main como parent
    commit_msg = """feat(desafio-5): InsureAlert - Sistema Multi-Agente de Comunicação Proativa com Segurados

- Implementa arquitetura multi-agente em Python puro (OOP) com 4 agentes autônomos:
  1. WeatherCollectorAgent (API INMET em tempo real + contingência)
  2. EventAnalyzerAgent (7 tipos de evento, 4 níveis de severidade)
  3. RulesEngineAgent (matriz de suscetibilidade atuarial, scoring e deduplicação)
  4. MessageGeneratorAgent (Google Gemini 2.5 Flash Lite + templates corporativos sem emojis)
- Adiciona PipelineOrchestrator em Python puro desacoplado para execução CLI e API
- API FastAPI com 20+ endpoints REST (autenticação, pipeline, CRUD segurados, métricas)
- Dashboard corporativo responsivo com Side Menu colapsável e Dark/Light Theme
- Central de Mensagens WhatsApp Web com preview multicanal (WhatsApp, SMS, E-mail, Push)
- Respostas rápidas interativas (Quick Replies) com despacho de protocolos de assistência
- Painel atuarial de mitigação de risco (ROI preventivo, perda evitada, loss ratio)
- Barramento de auditoria em tempo real (Event Bus)
- Relatório técnico completo atualizado em PDF, Word (.docx) e Markdown (.md)
- Suporte a deploy em nuvem com Render.com e Docker"""

    p_commit = subprocess.Popen(
        ['git', 'commit-tree', new_root_tree, '-p', origin_commit, '-m', commit_msg],
        stdout=subprocess.PIPE
    )
    new_commit, _ = p_commit.communicate()
    new_commit = new_commit.strip().decode('ascii')
    print(f"Novo commit criado: {new_commit}")

    # 6. Atualizar a referência da branch 'main'
    subprocess.run(['git', 'update-ref', 'refs/heads/main', new_commit], check=True)
    subprocess.run(['git', 'symbolic-ref', 'HEAD', 'refs/heads/main'], check=True)
    print("Branch local 'main' atualizada com sucesso!")

    # 7. Executar git push para o GitHub
    print("Executando git push origin main...")
    push_res = subprocess.run(['git', 'push', 'origin', 'main'], capture_output=True, text=True)
    print("STDOUT:", push_res.stdout)
    print("STDERR:", push_res.stderr)
    if push_res.returncode == 0:
        print("\n>>> PUSH CONCLUIDO COM SUCESSO NO GITHUB! <<<")
    else:
        print(f"\nPush retornou código {push_res.returncode}")

if __name__ == '__main__':
    run()
