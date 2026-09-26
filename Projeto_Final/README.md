# Plataforma Inteligente para Análise e Comparação de Apólices D&O

MVP que recebe apólices de seguro D&O em **PDF ou imagem**, extrai o conteúdo (texto nativo ou OCR),
usa **IA generativa** para estruturar as informações (coberturas, limites, franquias, exclusões,
vigência, retroatividade...), armazena tudo em **SQLite** e permite **consultar** e **comparar**
duas ou mais apólices em uma **aplicação web** (API FastAPI + interface própria, tema claro/escuro).

A arquitetura, os agentes e as decisões técnicas estão em [`docs/ARQUITETURA.md`](docs/ARQUITETURA.md).

## Demonstração online

**https://insurminds.onrender.com** — já vem com as três apólices de exemplo processadas. Funciona no
modo offline (regras) ou com a sua própria chave de API em **Modelo de IA**; a chave fica só no seu
navegador. As apólices de exemplo são protegidas e os documentos enviados são apagados quando o
servidor reinicia. No plano gratuito o servidor dorme sem uso: o primeiro acesso leva cerca de 50 s.

O deploy usa o `Dockerfile` desta pasta (Render, serviço Docker com *Root Directory* `Projeto_Final`)
e é refeito automaticamente a cada push no `main`.

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
├── api/main.py             API REST (FastAPI) que também serve a interface
├── web/                    Interface web (HTML/CSS/JS, sem build)
├── app.py                  Interface Streamlit (legada)
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
provedor e a chave também podem ser trocados na barra lateral da interface; a chave digitada ali
fica só na memória da sessão.

## Execução

```bash
python -m api
```

Abra http://localhost:8000. No **Painel**, use **Usar apólices de exemplo** (ou arraste seus PDFs em
**Enviar documentos**) e depois vá para **Comparar**. O provedor, o modelo e a chave de API são
escolhidos em **Modelo de IA** (menu lateral ou selo no topo): a lista de modelos vem da própria API
do provedor, e a chave fica só na aba do navegador — nunca é gravada no servidor.

A documentação interativa da API fica em http://localhost:8000/docs. Para desenvolvimento, com
recarga automática: `uvicorn api.main:app --reload`.

A interface Streamlit anterior continua disponível com `streamlit run app.py`.

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
