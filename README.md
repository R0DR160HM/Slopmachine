# Lodemar.IA

Chat no terminal com um modelo Ollama que pesquisa na web (ddgs), faz deep
research e forja ferramentas novas em tempo de execução.

## Requisitos

- [Ollama](https://ollama.com) instalado (`irm https://ollama.com/install.ps1 | iex`
  no PowerShell como administrador). Na inicialização o app verifica isso e
  baixa automaticamente os modelos que faltarem (`qwen2.5:0.5b`, `qwen2.5:7b`
  e `qwen2.5-coder:7b`).

## Rodando do código-fonte

```powershell
pip install -r requirements.txt
python -m lodemaria                      # ou: python lodemaria.py
python -m lodemaria --model qwen2.5:3b --results 5
python -m lodemaria Qual é o seu nome?   # já envia o primeiro prompt
```

## Gerando o .exe

```powershell
.\build.ps1
```

O script instala o PyInstaller (se necessário) e gera `dist\lodemaria.exe` —
um executável único (~35 MB) que embute o Python e todas as dependências.
Equivale a rodar manualmente:

```powershell
pip install pyinstaller
pyinstaller --onefile --name lodemaria --clean --noconfirm lodemaria.py
```

Os diretórios `build/` e `dist/` e o arquivo `lodemaria.spec` são gerados pelo
PyInstaller e estão no `.gitignore`.

## Usando o .exe

```powershell
.\dist\lodemaria.exe                     # inicia o chat
.\dist\lodemaria.exe --help              # opções
.\dist\lodemaria.exe -m qwen2.5:3b -r 8  # modelo e nº de resultados de busca
.\dist\lodemaria.exe Qual é o seu nome?  # primeiro prompt direto
```

O `.exe` pode ser copiado para qualquer máquina Windows 64 bits — não precisa
de Python instalado. Precisa apenas do **Ollama**: se ele não estiver
instalado, o app mostra o comando de instalação e encerra; se estiver, os
modelos que faltarem são baixados na primeira execução.

Notas:

- Digite `quit` ou `exit` (ou Ctrl+C) para sair.
- Em máquinas de terceiros o Windows SmartScreen pode alertar sobre o
  executável não assinado — "Mais informações → Executar assim mesmo".
