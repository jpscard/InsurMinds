# Plataforma Inteligente para Análise e Comparação de Apólices D&O

MVP que recebe apólices de seguro D&O em **PDF ou imagem**, extrai o conteúdo (texto nativo ou OCR),
usa **IA generativa** para estruturar as informações (coberturas, limites, franquias, exclusões,
vigência, retroatividade...), armazena tudo em **SQLite** e permite **consultar** e **comparar**
duas ou mais apólices em uma interface **Streamlit**.

A arquitetura, os agentes e as decisões técnicas estão em [`docs/ARQUITETURA.md`](docs/ARQUITETURA.md).

## Funcionalidades

- Upload de PDF digital, PDF digitalizado e imagens (PNG/JPG/TIFF...) com OCR automático por página
- 5 agentes especializados: Triagem, Extração, Validação, Comparação e Consulta
- Provedor de LLM configurável: **Anthropic, OpenAI, Gemini** ou **offline** (regras, sem chave)
- Comparação de N apólices: dados gerais, coberturas, exclusões e franquias lado a lado, com
  destaque do que difere, métricas (LMG, prêmio, prêmio/LMG) e análise executiva gerada pelo LLM
- Perguntas em linguagem natural com citação de página, e consultas SQL
- Revisão humana: correção do JSON extraído pela interface
- Exportação da comparação em Excel e Markdown
- Linha de comando (`cli.py`) e testes automatizados (`pytest`)

## Estrutura

```
Projeto_Final/
├── app.py                  Interface Streamlit
├── cli.py                  Linha de comando
├── do_platform/
│   ├── config.py           Configuração (.env)
│   ├── schema.py           Modelo de dados ApoliceDO
│   ├── pipeline.py         Orquestrador
│   ├── llm/                Provedores de LLM
│   ├── ingestion/          PDF/imagem + OCR
│   ├── agents/             Triagem, Extração, Validação, Comparação, Consulta, prompts
│   ├── comparison/         Diferenças determinísticas
│   └── storage/            Repositório SQLite
├── samples/                Apólices fictícias de exemplo
├── scripts/gerar_amostras.py
├── tests/
└── docs/ARQUITETURA.md
```

## Instalação

Pré-requisitos: **Python 3.10+** e **Tesseract OCR** (para PDFs digitalizados e imagens).

### Windows (PowerShell)

```powershell
cd D:\InsurMinds_repo\Projeto_Final
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

Instale o Tesseract pelo instalador da UB Mannheim (https://github.com/UB-Mannheim/tesseract/wiki),
marcando o idioma **Portuguese** em "Additional language data". Se ele não ficar no PATH, defina no `.env`:

```
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
```

### Linux / macOS

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
sudo apt install tesseract-ocr tesseract-ocr-por     # ou: brew install tesseract tesseract-lang
```

### Configurar o LLM

Edite o `.env`:

```
LLM_PROVIDER=anthropic          # anthropic | openai | gemini | offline
ANTHROPIC_API_KEY=sua-chave
```

Sem chave, use `LLM_PROVIDER=offline` para ver a interface funcionando (extração por regras). O
provedor e a chave também podem ser trocados na barra lateral da interface; a chave digitada ali
fica só na memória da sessão.

## Execução

```bash
streamlit run app.py
```

Abra http://localhost:8501, clique em **Processar 3 apólices de exemplo** e vá para **Comparar**.

Linha de comando:

```bash
python cli.py processar samples/*.pdf
python cli.py listar
python cli.py comparar 1 2 --saida comparacao.json
python cli.py perguntar "Qual apólice cobre multas administrativas?" 1 2 3
python cli.py --provedor offline processar samples/imagem/apolice_cruzeiro_pagina1.png
```

Testes (não precisam de chave de API):

```bash
pytest -q
```

## Apólices de exemplo

`samples/` contém três apólices **fictícias** do mesmo tomador, com condições diferentes, para
demonstrar a comparação:

| Arquivo | Tipo | Destaques |
|---|---|---|
| `apolice_aurora_do.pdf` | PDF digital | LMG R$ 20 mi, Lados A/B/C, 9 coberturas |
| `apolice_boreal_do.pdf` | PDF digital | LMG R$ 15 mi, sem Lado C, mais exclusões (ex.: Segurado vs. Segurado), franquias maiores |
| `apolice_cruzeiro_digitalizada.pdf` | PDF só imagem | LMG R$ 25 mi, retroatividade ilimitada; exercita o OCR |
| `imagem/apolice_cruzeiro_pagina1.png` | Imagem | Entrada por imagem |

Para regenerar: `python scripts/gerar_amostras.py`. Para testar com documentos reais, use modelos de
apólices e condições gerais D&O publicados por seguradoras ou consultados na SUSEP, citando a fonte no
relatório.

## Segurança

- Chaves de API só no `.env` (ignorado pelo Git) ou na memória da sessão.
- A consulta SQL da interface abre o banco em modo somente leitura e aceita apenas `SELECT`.
