# Apólis — Plataforma Inteligente para Análise e Comparação de Apólices D&O

MVP que recebe apólices de seguro D&O em **PDF ou imagem**, extrai o conteúdo (texto nativo ou OCR),
usa **IA generativa** para estruturar as informações (coberturas, limites, franquias, exclusões,
vigência, retroatividade...), armazena tudo em **SQLite** e permite **consultar** e **comparar**
duas ou mais apólices em uma **aplicação web** (API FastAPI + interface própria, tema claro/escuro).

A arquitetura, os agentes e as decisões técnicas estão em [`docs/ARQUITETURA.md`](docs/ARQUITETURA.md) e,
de forma visual, na página **Sobre a solução** da plataforma. O relatório técnico fica em
[`docs/relatorio/`](docs/relatorio/) (veja [Relatório](#relatório)).

## Demonstração online

**https://insurminds.onrender.com** — já vem com os sete documentos de exemplo processados. Funciona no
modo offline (regras) ou com a sua própria chave de API em **Modelo de IA**; a chave fica só no seu
navegador. As apólices de exemplo são protegidas e os documentos enviados são apagados quando o
servidor reinicia. No plano gratuito o servidor dorme sem uso: o primeiro acesso leva cerca de 50 s.

O deploy usa o `Dockerfile` desta pasta (Render, serviço Docker com *Root Directory* `Projeto_Final`)
e é refeito automaticamente a cada push no `main`.

## Funcionalidades

- Upload de PDF digital, PDF digitalizado e imagens (PNG/JPG/TIFF...) com OCR automático por página
- 6 agentes especializados: Triagem, Extração, Validação, Indexação, Comparação e Consulta
- Provedor de LLM configurável: **Anthropic, OpenAI, Gemini** ou **offline** (regras, sem chave)
- Comparação de N apólices: dados gerais, coberturas, exclusões e franquias lado a lado, com
  destaque do que difere, métricas (LMG, prêmio, prêmio/LMG) e análise executiva gerada pelo LLM
- Perguntas em linguagem natural por **RAG com índice hierárquico** (abordagem PageIndex, orquestrada
  em LangGraph): a IA navega o sumário da apólice, abre as seções certas e cita seção e página; e consultas SQL
- Revisão humana: correção do JSON extraído pela interface
- Exportação da comparação: relatório completo em **PDF** (com a marca Apólis), planilha Excel e Markdown
- Landing page de apresentação e página **Sobre a solução** com os diagramas da arquitetura
- Modo demonstração para o deploy público: amostras carregadas e protegidas, limite de envio
- Linha de comando (`cli.py`) e testes automatizados (`pytest`)

## Estrutura

```
Projeto_Final/
├── api/main.py             API REST (FastAPI) que também serve a interface
├── web/                    Interface web (HTML/CSS/JS, sem build)
│   ├── landing.html        Landing page (/)
│   ├── index.html          Plataforma (/app)
│   └── js/pages/           Uma página por tela (painel, carteira, comparar, consultar, sobre...)
├── cli.py                  Linha de comando
├── do_platform/
│   ├── config.py           Configuração (.env)
│   ├── schema.py           Modelo de dados ApoliceDO
│   ├── pipeline.py         Orquestrador
│   ├── llm/                Provedores de LLM
│   ├── ingestion/          PDF/imagem + OCR
│   ├── agents/             Triagem, Extração, Validação, Indexação, Comparação, Consulta (grafo), prompts
│   ├── indexing.py         Índice hierárquico do documento (PageIndex)
│   ├── comparison/         Diferenças determinísticas
│   ├── exports.py          Comparação em PDF, Excel e Markdown
│   └── storage/            Repositório SQLite
├── samples/                Apólices fictícias de exemplo
├── scripts/
│   ├── gerar_amostras.py   Gera as apólices de exemplo
│   └── gerar_relatorio.py  Gera o relatório (.docx e .pdf)
├── tests/
├── Dockerfile              Imagem do deploy (Tesseract com português)
└── docs/
    ├── ARQUITETURA.md
    └── relatorio/          Texto do relatório, imagens e diagramas
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

Instale o Tesseract (o projeto encontra o executável no local padrão do Windows, mesmo fora do PATH):

```powershell
winget install --id UB-Mannheim.TesseractOCR -e
```

O instalador silencioso traz só inglês. Para o português sem precisar de administrador, baixe o
modelo para a pasta local do projeto, que é usada automaticamente quando existe:

```powershell
mkdir data\tessdata
copy "C:\Program Files\Tesseract-OCR\tessdata\eng.traineddata" data\tessdata\
curl.exe -L -o data\tessdata\por.traineddata https://github.com/tesseract-ocr/tessdata/raw/main/por.traineddata
```

Se o Tesseract estiver em outro lugar, defina `TESSERACT_CMD` no `.env` (e `TESSDATA_DIR` para
outra pasta de idiomas).

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
provedor, o modelo e a chave também podem ser escolhidos em **Modelo de IA**, na interface; a chave
digitada ali fica só na aba do navegador.

## Execução

```bash
python -m api
```

Abra http://localhost:8000 (landing page) e clique em **Abrir a plataforma**, ou vá direto a
http://localhost:8000/app. No **Painel**, use **Usar apólices de exemplo** (ou arraste seus PDFs em
**Enviar documentos**) e depois vá para **Comparar**. O provedor, o modelo e a chave de API são
escolhidos em **Modelo de IA** (menu lateral ou selo no topo): a lista de modelos vem da própria API
do provedor, e a chave fica só na aba do navegador — nunca é gravada no servidor.

A documentação interativa da API fica em http://localhost:8000/docs. Para desenvolvimento, com
recarga automática: `uvicorn api.main:app --reload`.

Links diretos para um resultado (úteis em apresentações):

| Link | Abre |
|---|---|
| `/app#/comparar?ids=1,2,3&run=1` | a comparação dessas apólices, já executada |
| `/app#/consultar?q=Existe exclusão de Segurado contra Segurado?` | a consulta, já respondida |
| `/app#/apolices/2?tab=idx` | a apólice 2 na aba Índice (também `cob`, `exc`, `fra`, `txt`, `rev`) |
| `/app#/sobre?tab=consulta` | a página Sobre na aba do grafo (também `agentes`, `decisoes`, `dados`) |

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

`samples/` contém documentos **fictícios** (seguradoras, tomadores e valores inventados), pensados
para exercitar a comparação, o OCR, a triagem e o índice:

| Arquivo | Tipo | Págs. | Destaques |
|---|---|---|---|
| `apolice_aurora_do.pdf` | PDF digital | 2 | LMG R$ 20 mi, Lados A/B/C, 9 coberturas |
| `apolice_boreal_do.pdf` | PDF digital | 2 | LMG R$ 15 mi, sem Lado C, mais exclusões (ex.: Segurado vs. Segurado), franquias maiores |
| `apolice_cruzeiro_digitalizada.pdf` | PDF só imagem | 2 | LMG R$ 25 mi, retroatividade ilimitada; exercita o OCR |
| `apolice_equinocio_do.pdf` | PDF digital | 10 | Apólice completa (particulares, gerais e especiais), LMG R$ 50 mi, custos de defesa fora do LMG, subsidiárias |
| `apolice_meridiana_do.pdf` | PDF digital | 10 | Companhia aberta: LMG R$ 80 mi, Cobertura C, investigações CVM/SEC, exclusões com exceções, EUA |
| `apolice_pampa_digitalizada.pdf` | PDF só imagem | 6 | Cooperativa, LMG R$ 8 mi; OCR em documento longo |
| `condicoes_gerais_equinocio_do.pdf` | PDF digital | 11 | Condições gerais (não é apólice): a triagem deve identificar o tipo |
| `imagem/apolice_cruzeiro_pagina1.png` | Imagem | 1 | Entrada por imagem |

Os três primeiros são do mesmo tomador, para a comparação direta. Os documentos longos têm cláusulas
numeradas com subitens (5 → 5.6 → 5.6.1) e exceções, como apólices reais.

### Base de demonstração pré-processada

O site público importa as amostras já processadas de `samples/processados/` ao iniciar, em vez de
processá-las a cada reinício (o plano gratuito tem pouca CPU e apaga o disco quando o servidor dorme).
Assim tudo aparece na hora, sem OCR nem chamadas à IA. Para gerar ou atualizar a base:

```bash
python scripts/gerar_base_demo.py                     # por regras (offline)
python scripts/gerar_base_demo.py --provedor gemini   # com IA (chave do .env); o site mostra a extração da IA
```

Cada JSON guarda o hash do documento de origem: se uma amostra mudar e a base não for regerada, o
servidor ignora o JSON antigo e processa a amostra por regras.

Para gerar o que faltar: `python scripts/gerar_amostras.py` (`--todas` regera tudo; os longos ficam em
`scripts/amostras_longas.py`). Para testar com documentos reais, use modelos de
apólices e condições gerais D&O publicados por seguradoras ou consultados na SUSEP, citando a fonte no
relatório.

## Relatório

O relatório técnico é escrito em [`docs/relatorio/relatorio.md`](docs/relatorio/relatorio.md), com as
imagens em `docs/relatorio/img/` e os diagramas em `docs/relatorio/diagramas/`. Versões prontas:
[`InsurMinds – Projeto Final.pdf`](docs/relatorio/InsurMinds%20–%20Projeto%20Final.pdf) e
[`.docx`](docs/relatorio/InsurMinds%20–%20Projeto%20Final.docx). Para gerar de novo o `.docx` e o `.pdf`
(o PDF é exportado pelo Microsoft Word, no Windows):

```bash
pip install python-docx
python scripts/gerar_relatorio.py
```

## Segurança

- Chaves de API só no `.env` (ignorado pelo Git) ou na aba do navegador; o servidor não grava a
  chave digitada na interface.
- A consulta SQL da interface abre o banco em modo somente leitura e aceita apenas `SELECT`.
- No modo demonstração (`DEMO_MODE=true`), as apólices de exemplo não podem ser editadas nem
  excluídas e os envios são limitados a `MAX_UPLOAD_MB`.
