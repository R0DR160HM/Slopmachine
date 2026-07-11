# Pyth.IA

Chat no terminal com um modelo Ollama que pesquisa na web (ddgs), faz deep
research e forja ferramentas novas em tempo de execução.

## Requisitos

- [Ollama](https://ollama.com) instalado. Na inicialização o app verifica isso
  e baixa automaticamente os modelos que faltarem (`qwen2.5:1.5b`, `qwen2.5:7b`
  e `qwen2.5-coder:7b`).

  - **Windows** (PowerShell como administrador):

    ```powershell
    irm https://ollama.com/install.ps1 | iex
    ```

  - **Linux / macOS**:

    ```bash
    curl -fsSL https://ollama.com/install.sh | sh
    ```

    > No Linux, evite instalar o Ollama pelo Homebrew: o pacote costuma vir sem
    > o binário `llama-server`, e o modelo falha ao carregar. Use o script
    > oficial acima.

## Rodando do código-fonte

```bash
pip install -r requirements.txt
python -m pythia                      # ou: python pythia.py
python -m pythia --model qwen2.5:3b --results 5
python -m pythia --slop               # modelos mínimos (0.5b), veja abaixo
python -m pythia Qual é o seu nome?   # já envia o primeiro prompt
```

## Gerando o executável

O PyInstaller **não** faz cross-compile: ele gera um executável para o mesmo
sistema em que roda. Ou seja, no Windows você obtém um `.exe` que roda só no
Windows; no Linux, um binário que roda só no Linux. Não dá para gerar um `.exe`
a partir do Linux (nem vice-versa).

- **Windows** — gera `dist\pythia.exe`:

  ```powershell
  .\build.ps1
  ```

- **Linux / macOS** — gera `dist/pythia`:

  ```bash
  ./build.sh
  ```

Ambos os scripts instalam o PyInstaller (se necessário) e produzem um
executável único (~35 MB) que embute o Python e todas as dependências.
Equivalem a rodar manualmente:

```bash
pip install pyinstaller
pyinstaller --onefile --name pythia --clean --noconfirm pythia.py
```

Os diretórios `build/` e `dist/` e o arquivo `pythia.spec` são gerados pelo
PyInstaller e estão no `.gitignore`.

## Instalando (chamar de qualquer lugar com `pythia`)

Depois de gerar o executável, copie-o para um diretório que esteja no `PATH`.

- **Linux / macOS**:

  ```bash
  mkdir -p ~/.local/bin
  cp dist/pythia ~/.local/bin/
  ```

  Se `pythia` ainda não for encontrado, `~/.local/bin` não está no `PATH`.
  Adicione ao seu `~/.bashrc` (ou `~/.zshrc`) e abra um novo terminal:

  ```bash
  echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
  ```

- **Windows** (PowerShell) — copia o `.exe` para uma pasta do usuário e a
  adiciona ao `PATH`:

  ```powershell
  $dest = "$env:LOCALAPPDATA\Programs\pythia"
  New-Item -ItemType Directory -Force -Path $dest | Out-Null
  Copy-Item dist\pythia.exe $dest -Force
  [Environment]::SetEnvironmentVariable(
      "Path",
      [Environment]::GetEnvironmentVariable("Path", "User") + ";$dest",
      "User")
  ```

  Abra um **novo** terminal para o `PATH` atualizado valer.

Feito isso, basta digitar `pythia` em qualquer terminal.

## Usando

```bash
pythia                     # inicia o chat
pythia --help              # opções
pythia -m qwen2.5:3b -r 8  # modelo e nº de resultados de busca
pythia --slop              # modo slop: modelos mínimos
pythia Qual é o seu nome?  # primeiro prompt direto
```

Com `--slop`, o chat e a síntese de documentação usam `qwen2.5:0.5b`, e a
forja de ferramentas e a documentação por arquivo usam `qwen2.5-coder:0.5b` —
os menores modelos da família, para máquinas fracas ou respostas rápidas (com
qualidade proporcional). A flag sobrepõe `--model`.

O executável pode ser copiado para qualquer máquina do **mesmo** sistema
operacional (mesma arquitetura, 64 bits) — não precisa de Python instalado.
Precisa apenas do **Ollama**: se ele não estiver instalado, o app mostra o
comando de instalação e encerra; se estiver, os modelos que faltarem são
baixados na primeira execução.

Notas:

- Digite `quit` ou `exit` (ou Ctrl+C) para sair.
- No Windows, em máquinas de terceiros o SmartScreen pode alertar sobre o
  executável não assinado — "Mais informações → Executar assim mesmo".
