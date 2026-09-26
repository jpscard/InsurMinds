"""Configuração central da plataforma.

Todas as credenciais e parâmetros vêm de variáveis de ambiente (ou de um
arquivo `.env` na raiz do projeto). Nenhuma chave de API é escrita no código.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Provedor de LLM: anthropic | openai | gemini | offline
    llm_provider: str = "offline"
    llm_model: str | None = None  # se vazio, usa o padrão de cada provedor
    llm_temperature: float = 0.0
    # Modelos com raciocínio gastam parte deste limite "pensando": apólices longas precisam de folga
    llm_max_tokens: int = 32000
    llm_timeout_s: int = 180
    llm_max_retries: int = 3

    anthropic_api_key: str | None = None
    openai_api_key: str | None = None
    gemini_api_key: str | None = None

    # Ingestão / OCR
    ocr_lang: str = "por+eng"
    ocr_dpi: int = 300
    # PSM 6 (bloco uniforme) preserva as linhas de tabelas, comuns em quadros de cobertura
    ocr_psm: int = 6
    # Página com menos caracteres que isto é considerada "digitalizada" e vai para OCR
    min_chars_per_page: int = 80
    tesseract_cmd: str | None = None  # caminho do tesseract.exe no Windows, se preciso
    max_pages: int = 300  # documentos maiores são recusados (protege o servidor)
    # Pasta de idiomas do OCR. Se vazia, usa data/tessdata quando existir (idiomas instalados
    # pelo projeto sem permissão de administrador) ou a pasta padrão do Tesseract.
    tessdata_dir: Path | None = None

    # Resumos das seções do índice pelo LLM (1 chamada por documento); False usa resumos por regras
    index_llm_summaries: bool = True

    # Extração: textos maiores que isto são processados em blocos
    chunk_chars: int = 60000

    # Demonstração pública (deploy): carrega as amostras ao iniciar, protege-as contra
    # exclusão/edição e limita o tamanho dos envios.
    demo_mode: bool = False
    max_upload_mb: int = 20

    # Armazenamento
    database_path: Path = ROOT_DIR / "data" / "apolices.db"
    uploads_dir: Path = ROOT_DIR / "data" / "uploads"


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    s.database_path.parent.mkdir(parents=True, exist_ok=True)
    s.uploads_dir.mkdir(parents=True, exist_ok=True)
    return s
