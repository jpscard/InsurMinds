# utils/callbacks.py

import sys
import re
from typing import Any

# Reconfigura stdout e stderr para UTF-8 caso esteja em terminal Windows (charmap/cp1252)
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

if hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass


def safe_print(*args, **kwargs):
    """Garante que prints para o console nunca quebrem por erros de encoding (charmap/cp1252)."""
    try:
        print(*args, **kwargs)
    except (UnicodeEncodeError, Exception):
        safe_args = []
        for arg in args:
            if isinstance(arg, str):
                safe_args.append(arg.encode(sys.stdout.encoding or 'ascii', errors='replace').decode(sys.stdout.encoding or 'ascii', errors='replace'))
            else:
                safe_args.append(arg)
        try:
            print(*safe_args, **kwargs)
        except Exception:
            pass

try:
    from langchain_core.callbacks.base import BaseCallbackHandler
except ImportError:
    try:
        from langchain_core.callbacks import BaseCallbackHandler
    except ImportError:
        from langchain.callbacks.base import BaseCallbackHandler
from langchain_core.agents import AgentAction, AgentFinish

# A classe de cores permanece a mesma, apenas a forma como a usamos vai mudar.
class BColors:
    HEADER = '\033[95m'    # Magenta
    OKBLUE = '\033[94m'    # Azul
    OKCYAN = '\033[96m'    # Ciano
    OKGREEN = '\033[92m'   # Verde
    WARNING = '\033[93m'   # Amarelo
    FAIL = '\033[91m'      # Vermelho (reservado para erros)
    ENDC = '\033[0m'       # Fim da formatação
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

# Callback Handler com cores padronizadas e profissionais
class PolishedCallbackHandler(BaseCallbackHandler):
    """
    Formata os logs com um esquema de cores semântico e profissional.
    """
    def __init__(self, agent_name="Analista de Dados"):
        super().__init__()
        self.agent_name = agent_name
        safe_print(f"\n{BColors.BOLD}{BColors.OKCYAN}🚀 Iniciando nova execução para o agente: {self.agent_name}{BColors.ENDC}")
        safe_print("─" * 80)

    def on_agent_action(self, action: AgentAction, **kwargs: Any) -> Any:
        """
        Formata o Pensamento (Azul) e a Ação (Verde).
        """
        try:
            thought = re.split(r'Action:|Thought:', action.log)[1].strip()
        except Exception:
            thought = action.log
        
        safe_print(f"{BColors.BOLD}{BColors.OKBLUE}🤔 PENSAMENTO{BColors.ENDC}")
        safe_print(thought)
        
        safe_print(f"\n{BColors.BOLD}{BColors.OKGREEN}⚡ AÇÃO{BColors.ENDC}")
        safe_print(f"   - Ferramenta: {BColors.BOLD}{action.tool}{BColors.ENDC}")
        
        clean_input = action.tool_input.strip().strip("```python").strip("```").strip() if isinstance(action.tool_input, str) else str(action.tool_input)
        safe_print(f"   - Código a executar:\n{BColors.WARNING}```python\n{clean_input}\n```{BColors.ENDC}")

    def on_tool_end(self, output: str, **kwargs: Any) -> Any:
        """
        Formata a Observação (Magenta).
        """
        safe_print(f"\n{BColors.BOLD}{BColors.HEADER}📝 OBSERVAÇÃO{BColors.ENDC}")
        safe_print(output)
        safe_print("─" * 80)

    def on_agent_finish(self, finish: AgentFinish, **kwargs: Any) -> Any:
        """
        Formata a Resposta Final (Ciano, igual ao cabeçalho).
        """
        final_answer = finish.return_values.get('output', 'N/A')
        safe_print(f"\n{BColors.BOLD}{BColors.OKCYAN}✅ RESPOSTA FINAL{BColors.ENDC}")
        safe_print(final_answer)
        safe_print("\n" + "="*80 + "\n")