from fastapi import FastAPI, Body
from fastapi.middleware.cors import CORSMiddleware
import requests
import os, re
from dotenv import load_dotenv
import ast
import textwrap

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

HF_TOKEN = os.getenv("HF_TOKEN")
CHAT_URL = "https://router.huggingface.co/v1/chat/completions"
MODEL_ID = "meta-llama/Meta-Llama-3-8B-Instruct:novita"

def strip_code_fences(text: str) -> str:
    if not isinstance(text, str):
        return ""
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```[a-zA-Z]*\n?", "", t)
        t = re.sub(r"\n?```$", "", t)
    return t.strip()

def extract_assistant_text(data: dict) -> str | None:
    choices = (data or {}).get("choices") or []
    if not choices:
        return None
    ch0 = choices[0]
    msg = ch0.get("message") or {}

    if isinstance(msg.get("content"), str) and msg["content"].strip():
        return msg["content"]

    if isinstance(msg.get("reasoning_content"), str) and msg["reasoning_content"].strip():
        text = msg["reasoning_content"]
        code_blocks = re.findall(r"```(?:python)?\n(.*?)```", text, re.DOTALL)
        if code_blocks:
            return code_blocks[0].strip()
        return text

    if isinstance(ch0.get("text"), str) and ch0["text"].strip():
        return ch0["text"]

    return None

def looks_like_code(text: str) -> bool:
    if not isinstance(text, str) or not text.strip():
        return False
    try:
        ast.parse(text)
        return True
    except Exception:
        return False

def naive_pytest_fallback(code_snippet: str) -> str:
    header = (
        "import pytest\n\n"
        "ns = {}\n"
        f'CODE = r"""{(code_snippet or "").strip()}"""\n'
        "try:\n"
        "    exec(CODE, ns)\n"
        "except Exception as e:\n"
        "    USER_CODE_EXEC_ERROR = e\n"
        "else:\n"
        "    USER_CODE_EXEC_ERROR = None\n\n"
    )

    if not isinstance(code_snippet, str) or not code_snippet.strip():
        return header + (
            "def test_skeleton_no_code():\n"
            "    pytest.skip('No user code provided.')\n"
        )

    try:
        tree = ast.parse(code_snippet)
    except Exception:
        return header + (
            "def test_skeleton_parse_error():\n"
            "    if USER_CODE_EXEC_ERROR is not None:\n"
            "        pytest.skip(f'User code failed to exec: {USER_CODE_EXEC_ERROR}')\n"
            "    pytest.skip('Failed to parse user code; please check syntax.')\n"
        )

    fn_defs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    if not fn_defs:
        return header + (
            "def test_skeleton_no_functions():\n"
            "    if USER_CODE_EXEC_ERROR is not None:\n"
            "        pytest.skip(f'User code failed to exec: {USER_CODE_EXEC_ERROR}')\n"
            "    pytest.skip('No top-level functions detected in provided code.')\n"
        )

    lines = [header]

    for f in fn_defs:
        fn = f.name
        lines.append(
            textwrap.dedent(f"""
            def test_{fn}_exists_and_callable():
                if USER_CODE_EXEC_ERROR is not None:
                    pytest.skip(f'User code failed to exec: {{USER_CODE_EXEC_ERROR}}')
                obj = ns.get("{fn}")
                assert obj is not None, "Function '{fn}' not found in namespace."
                assert callable(obj), "Object '{fn}' is not callable."
            """).strip() + "\n"
        )

        params = [a.arg for a in f.args.args if a.arg not in ("self", "cls")]
        has_varargs = bool(f.args.vararg)
        has_varkw = bool(f.args.kwarg)
        defaults = f.args.defaults or []
        num_defaults = len(defaults)
        num_positional = len(params)
        num_required = max(0, num_positional - num_defaults)

        if num_required == 0 and not has_varargs and not has_varkw:
            lines.append(
                textwrap.dedent(f"""
                def test_{fn}_smoke_no_required_args():
                    if USER_CODE_EXEC_ERROR is not None:
                        pytest.skip(f'User code failed to exec: {{USER_CODE_EXEC_ERROR}}')
                    ns["{fn}"]()
                """).strip() + "\n"
            )
        else:
            placeholder_call = ", ".join(["None"] * max(1, num_required))
            comment_params = ", ".join(params) if params else "(none)"
            lines.append(
                textwrap.dedent(f"""
                def test_{fn}_smoke_placeholders():
                    if USER_CODE_EXEC_ERROR is not None:
                        pytest.skip(f'User code failed to exec: {{USER_CODE_EXEC_ERROR}}')
                    pytest.skip(
                        "Add realistic sample inputs for '{fn}' and remove this skip. "
                        "Detected params: {comment_params}; varargs={has_varargs}, varkw={has_varkw}."
                    )
                    # Example call (adjust types/values!):
                    # ns["{fn}"]({placeholder_call})
                """).strip() + "\n"
            )

    return "".join(lines)

@app.post("/generate-test")
async def generate_test(code: str = Body(..., embed=True)):
    try:
        payload = {
            "model": MODEL_ID,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a code generator that outputs ONLY valid Python pytest code. "
                        "Do not include explanations, natural language, or markdown fences. "
                        "Your first line MUST be 'import pytest'."
                    ),
                },
                {
                    "role": "user",
                    "content": "Write pytest tests for:\n\ndef inc(x): return x+1",
                },
                {
                    "role": "assistant",
                    "content": (
                        "import pytest\n\n"
                        "def test_inc_basic():\n"
                        "    assert inc(1) == 2\n"
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "Given the following Python code, write pytest unit tests. "
                        "Return only the Python test code, starting with 'import pytest'.\n\n"
                        f"{code}"
                    ),
                },
            ],
            "temperature": 0,
            "max_tokens": 2500,
            "stream": False,
            "stop": ["\n\nWe", "\nExplanation", "\nReasoning"],
        }

        resp = requests.post(
            CHAT_URL,
            headers={"Authorization": f"Bearer {HF_TOKEN}", "Content-Type": "application/json"},
            json=payload,
            timeout=60,
        )

        if resp.status_code != 200:
            return {"error": f"API Error: {resp.status_code} {resp.text}"}

        data = resp.json()
        print("RAW HF RESPONSE:", data)
        content = extract_assistant_text(data)
        if not content:
            return {"error": "Unexpected response format", "raw": data}

        content = strip_code_fences(content)

        if not looks_like_code(content):
            content = naive_pytest_fallback(code)

        if not content.lstrip().startswith("import pytest"):
            content = "import pytest\n\n" + content.lstrip()

        injection = f'''
            ns = {{}}
            CODE = r\"\"\"{code.strip()}\"\"\"
            exec(CODE, ns)
            globals().update(ns)

        '''
        final_code = content.strip()
        if final_code.startswith("import pytest"):
            parts = final_code.split("\n", 1)
            final_code = parts[0] + "\n" + injection.strip() + "\n" + (parts[1] if len(parts) > 1 else "")

        return {"test_code": final_code.strip()}

    except Exception as e:
        return {"error": str(e)}
