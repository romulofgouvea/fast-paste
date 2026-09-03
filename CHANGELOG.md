# Changelog

## [0.1.8] - 2026-09-03

### Corrigido
- **Cantos no macOS**: A janela renderizava um fundo branco fora dos cantos arredondados no macOS. Agora os cantos e a sombra são feitos pela camada nativa da janela (`cornerRadius`/`masksToBounds` + `NSColor.clearColor`), usando só API pública — sem a `macOSPrivateApi` do Tauri, que barra o app na Mac App Store.

### Adicionado
- **Colar Automaticamente no macOS**: O "Colar Automaticamente" agora funciona no macOS (Cmd+V) além do Windows — o FPaste reativa o app que estava em uso e injeta o atalho de colar. Requer conceder a permissão de Acessibilidade ao FPaste.
- **Aviso de permissão (macOS)**: Quando o colar automático está ligado mas o FPaste não tem a permissão de Acessibilidade, as configurações mostram um aviso com um botão que abre direto o painel Ajustes → Privacidade e Segurança → Acessibilidade. O aviso some sozinho assim que a permissão é concedida.

## [0.1.6] - 2026-09-01

### Corrigido
- **Lightshot / Captura de Tela no Windows**: Corrigido um problema onde cópias de imagens feitas por utilitários como o Lightshot eram ignoradas em decorrência de bloqueio temporário (lock) na área de transferência. Adicionado mecanismo de tolerância e _retry_ para suportar estes utilitários.
## [0.1.5] - 2026-08-28

### Adicionado
- **Abrir Centralizado**: Nova opção nas configurações (aba Geral) para escolher se o FPaste deve abrir perto do cursor do mouse (padrão) ou centralizado na tela.
- **Novas Cores de Destaque**: Adicionadas cores para agradar os usuários de Linux, como "GNOME (Adwaita)" (que agora é o azul padrão), "Debian Red", "Rosa" e "Ciano", todas reordenadas da cor mais quente para a mais fria.
- **Botão Customizado na Configuração**: A janela de configurações agora usa o mesmo estilo translúcido e minimalista da janela principal, com direito a um "X" vermelho no canto para fechar e possibilidade de fechar com o atalho "Esc".
- **Atalho no Linux**: Adicionado um alerta educativo na tela de atalhos para usuários Linux (especialmente em sessões Wayland, onde atalhos globais costumam ser ignorados) ensinando a configurar nativamente, incluindo um botão direto para as configurações de teclado do GNOME.

### Corrigido
- **Busca Numérica**: Corrigido um problema incômodo onde digitar números no início da barra de pesquisa colava o item imediatamente ao invés de prosseguir com a pesquisa do texto.
- **Iniciar com o Sistema**: O switch "Iniciar com o Sistema" agora é devidamente salvo nas configurações e respeitado na inicialização após falhas de permissão no Tauri terem sido resolvidas.
- **Menu da Bandeja (Tray)**: Corrigido o botão "Sair" do ícone de bandeja, que era ignorado pelo app.
- **Renderização Invisível**: Corrigido o bug onde a tela de configurações ficava 100% invisível no Windows (deixando só a sombra fantasma) por conta de uma combinação errada de fundo transparente sem o corte de sombra adequado do Tauri.

