import sys
from core import history

def main():
    """Lê da entrada padrão (injetada pelo wl-paste) e salva no histórico SQLite."""
    if len(sys.argv) < 2:
        print("[FastPaste] Uso: clip_handler.py [text|image]", file=sys.stderr)
        sys.exit(1)
        
    mode = sys.argv[1].lower()
    
    try:
        if mode == "text":
            # Lê todo o conteúdo textual da entrada padrão
            content = sys.stdin.read()
            if content and content.strip():
                history.add_text(content)
                preview = content.replace('\n', ' ')[:50]
                print(f"[FastPaste] Salvo texto: {preview}", flush=True)
                
        elif mode == "image":
            # Lê os bytes binários brutos da entrada padrão
            image_bytes = sys.stdin.buffer.read()
            if image_bytes:
                history.add_image(image_bytes)
                print(f"[FastPaste] Salva imagem ({len(image_bytes)} bytes)", flush=True)
                
    except Exception as e:
        print(f"[FastPaste] Erro ao processar clipe: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()
