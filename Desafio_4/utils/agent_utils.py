# utils/agent_utils.py

import io
import re
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_experimental.agents.agent_toolkits import create_pandas_dataframe_agent

MODELOS_GEMINI_DISPONIVEIS = [
    "gemini-2.0-flash",
    "gemini-1.5-flash-latest",
    "gemini-1.5-flash",
    "gemini-2.5-flash",
    "gemini-1.5-pro",
    "gemini-pro"
]


def extrair_texto_parser_error(err_str: str) -> str | None:
    """Extrai o texto útil retornado pelo LLM quando o parser de ReAct falha por falta de formatação."""
    if "Could not parse LLM output:" in err_str:
        part = err_str.split("Could not parse LLM output:")[1]
        if "For troubleshooting, visit:" in part:
            part = part.split("For troubleshooting, visit:")[0]
        part = part.strip().strip("`").strip()
        if part:
            return part
    return None


def parsing_error_handler(error) -> str:
    """Instrui o modelo a corrigir o formato ReAct ou retorna o texto direto."""
    err_str = str(error)
    recovered = extrair_texto_parser_error(err_str)
    if recovered:
        return f"Formato inválido. Se esta for sua resposta final, use obrigatoriamente:\nFinal Answer: {recovered}"
    return "Erro de formato. Lembre-se de sempre responder usando: Thought: ... seguido de Final Answer: ..."


def capturar_figuras_matplotlib() -> list[bytes]:
    """Captura e serializa em bytes PNG quaisquer figuras geradas pelo matplotlib durante a execução."""
    figuras = []
    try:
        for fig_num in plt.get_fignums():
            f = plt.figure(fig_num)
            buf = io.BytesIO()
            f.savefig(buf, format='png', bbox_inches='tight', dpi=130)
            buf.seek(0)
            figuras.append(buf.getvalue())
            plt.close(f)
    except Exception:
        pass
    return figuras


def invocar_agente_com_fallback(
    df,
    google_api_key: str,
    prefix: str,
    input_data: dict,
    preferred_model: str = "gemini-2.0-flash",
    temperature: float = 0.0,
    handler = None
) -> tuple[dict, str]:
    """
    Invoca o agente tentando primeiro o modelo preferido e realizando failover transparente.
    Captura automaticamente tabelas Markdown e figuras gráficas geradas por código Python.
    Retorna: (resposta_dict, modelo_utilizado)
    """
    google_api_key_clean = str(google_api_key).strip().strip('"').strip("'")
    modelos_a_testar = [preferred_model] + [m for m in MODELOS_GEMINI_DISPONIVEIS if m != preferred_model]
    
    # Limpa figuras anteriores do matplotlib
    plt.clf()
    plt.close('all')

    # Adiciona diretrizes de formatação (tabelas e gráficos) ao prefixo
    prefix_com_formato = (
        prefix
        + "\n\nDIRETRIZES DE FORMATAÇÃO E RESPOSTA:"
        + "\n1. TABELAS: Quando solicitado ou quando houver rankings/comparações, apresente SEMPRE em formato de TABELA MARKDOWN completa e legível."
        + "\n2. GRÁFICOS: Se o usuário pedir um gráfico, visualização ou plotagem, gere o gráfico em Python utilizando matplotlib.pyplot (ou seaborn) com títulos, eixos e cores claros. Não utilize plt.show()."
        + "\n3. RESPOSTA FINAL: Quando tiver a resposta para o usuário (ou quando precisar pedir esclarecimentos), você DEVE SEMPRE terminar com o prefixo 'Final Answer: <sua resposta aqui>'."
    )

    ultimo_erro = None
    for modelo in modelos_a_testar:
        try:
            llm = ChatGoogleGenerativeAI(
                model=modelo,
                google_api_key=google_api_key_clean,
                temperature=temperature
            )
            agent = create_pandas_dataframe_agent(
                llm,
                df,
                prefix=prefix_com_formato,
                verbose=False,
                allow_dangerous_code=True,
                max_iterations=6,
                agent_executor_kwargs={"handle_parsing_errors": True}
            )
            config = {"callbacks": [handler]} if handler else {}
            resposta = agent.invoke(input_data, config=config)
            
            # Captura figuras geradas
            figuras_geradas = capturar_figuras_matplotlib()
            if isinstance(resposta, dict):
                resposta["imagens"] = figuras_geradas
            else:
                resposta = {"output": str(resposta), "imagens": figuras_geradas}

            return resposta, modelo
        except Exception as e:
            err_msg = str(e)
            ultimo_erro = e

            # 1. Se o LLM respondeu diretamente mas sem a tag 'Final Answer:', recupera o texto gerado
            recovered_text = extrair_texto_parser_error(err_msg)
            if recovered_text:
                figuras_geradas = capturar_figuras_matplotlib()
                return {"output": recovered_text, "imagens": figuras_geradas}, modelo

            # 2. Se o erro for 404 / NOT_FOUND, tenta o próximo modelo
            if "404" in err_msg or "NOT_FOUND" in err_msg or "not found" in err_msg.lower() or "is not supported for generatecontent" in err_msg.lower():
                continue
            else:
                # Tenta recuperar texto mesmo em exceções aninhadas
                if "Could not parse LLM output" in err_msg:
                    recovered_text = extrair_texto_parser_error(err_msg)
                    if recovered_text:
                        figuras_geradas = capturar_figuras_matplotlib()
                        return {"output": recovered_text, "imagens": figuras_geradas}, modelo
                raise e

    if ultimo_erro:
        recovered_text = extrair_texto_parser_error(str(ultimo_erro))
        if recovered_text:
            figuras_geradas = capturar_figuras_matplotlib()
            return {"output": recovered_text, "imagens": figuras_geradas}, preferred_model
        raise ultimo_erro


