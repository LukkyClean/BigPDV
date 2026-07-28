# Template do instalador NSIS — como manter

`frontend/src-tauri/nsis/installer.nsi` é um **fork do template oficial do Tauri**,
declarado em `tauri.conf.json` → `bundle.windows.nsis.template`.

Ele existe por **uma única razão**: instalar em `C:\StartBigERP` (raiz do C) em vez
de `C:\Program Files\StartBigERP`. O Tauri não tem opção nativa para isso
(tauri-apps/tauri#11015), então o template é o único caminho.

**Versão de origem: `tauri-cli 2.9.6`.**

## ⚠️ Ao atualizar o Tauri, o template precisa ser refeito

Um template forkado fica preso à versão. Se o Tauri mudar os placeholders e o
template não acompanhar, o build quebra com erro críptico **só na hora do bundle**
— depois de compilar tudo. Foi o que aconteceu entre 08/07 e 16/07/2026: o
arquivo versionado era a **saída gerada** na máquina de um dev (`C:\dev\bigpdv\...`),
com caminhos absolutos e zero placeholders, então **ninguém mais conseguia gerar
instalador**. O último que funcionou era de 13/06.

### Receita

1. Descubra a versão do CLI:
   ```bash
   cd frontend && npx tauri --version      # ex.: tauri-cli 2.9.6
   ```

2. Baixe o template oficial **da tag correspondente**:
   ```bash
   curl -o installer-oficial.nsi \
     https://raw.githubusercontent.com/tauri-apps/tauri/tauri-cli-v<VERSAO>/crates/tauri-bundler/src/bundle/windows/nsis/installer.nsi
   ```

3. Reaplique **somente** este bloco (procure por `PLACEHOLDER_INSTALL_DIR`):

   ```nsis
   ${If} $INSTDIR == "${PLACEHOLDER_INSTALL_DIR}"
     !if "${INSTALLMODE}" == "perMachine"
       StrCpy $INSTDIR "C:\${PRODUCTNAME}"          ; <- a customização
     !else if "${INSTALLMODE}" == "currentUser"
       StrCpy $INSTDIR "$LOCALAPPDATA\${PRODUCTNAME}"
     !endif

     Call RestorePreviousInstallLocation
   ${EndIf}
   ```
   O original tem, no lugar, um bloco maior com `$PROGRAMFILES64` / `$PROGRAMFILES`
   ramificado por arquitetura. Substitua o bloco inteiro.

4. Salve como `frontend/src-tauri/nsis/installer.nsi` e valide:
   ```bash
   grep -c "{{" frontend/src-tauri/nsis/installer.nsi   # deve ser ~80, NUNCA 0
   grep -n "C:\\\\dev\|C:\\\\Users" frontend/src-tauri/nsis/installer.nsi   # deve ser vazio
   cd frontend && npm run tauri build
   ```

## Como saber que o template está errado

| Sintoma | Causa |
|---|---|
| `grep -c "{{"` retorna **0** | Alguém versionou a **saída gerada** no lugar do template |
| `!include: could not find "C:\dev\..."` | Idem — caminho absoluto da máquina de outra pessoa |
| Erro no bundle depois de compilar tudo | Placeholder que o template forkado não conhece |

**A regra:** o template tem placeholders (`{{product_name}}`, `{{main_binary_path}}`…),
**nunca** caminhos absolutos. O que tem caminho absoluto é o arquivo que o Tauri
**gera** em `target/release/nsis/x64/installer.nsi` — esse é saída, não fonte.

## Vale a pena manter o fork?

O ganho é só o diretório de instalação. `C:\Program Files\StartBigERP` **também é
disco C**, é o padrão do Windows, e dispensaria o fork inteiro — bastaria remover a
chave `template` do `tauri.conf.json`. Foi decisão de produto manter na raiz
(reconfirmada em 16/07/2026). Se um dia o custo de manutenção incomodar, remover a
chave `template` resolve e o build passa a ser à prova de upgrade.
