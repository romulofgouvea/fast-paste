import { useEffect, useState } from "react";
import { load } from "@tauri-apps/plugin-store";
import { enable, disable, isEnabled } from "@tauri-apps/plugin-autostart";
import { emit } from "@tauri-apps/api/event";
import { invoke } from "@tauri-apps/api/core";
import { ACCENT_PRESETS, useTheme, type ThemeMode } from "../hooks/useTheme";
import {
  exportBackup,
  getAutoPaste,
  getHotkey,
  importBackup,
  resumeHotkey,
  setAutoPaste,
  setHotkey,
  suspendHotkey,
  openLinuxKeyboardSettings,
  hideSettings,
  type ImportSummary,
} from "../lib/api";
import {
  currentModifiers,
  displayShortcut,
  eventToShortcut,
  isModifierKey,
} from "../lib/shortcut";
import { AccentButton } from "../components/ui/AccentButton";

type Tab = "appearance" | "shortcuts" | "storage" | "backup";

const TABS: { id: Tab; label: string; icon: string }[] = [
  { id: "appearance", label: "Aparência", icon: "🎨" },
  { id: "shortcuts", label: "Geral", icon: "⚙️" },
  { id: "storage", label: "Armazenamento", icon: "💾" },
  { id: "backup", label: "Backup", icon: "🗄️" },
];

async function saveSetting(key: string, value: string) {
  const store = await load("settings.json");
  await store.set(key, value);
  await store.save();
  await emit("fpaste://settings-changed");
}

export default function Settings() {
  useTheme();
  const [tab, setTab] = useState<Tab>("appearance");

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        void hideSettings();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  return (
    <div className="h-full flex fpaste-shell text-zinc-800 dark:text-zinc-100 relative rounded-2xl overflow-hidden" data-tauri-drag-region>
      <button
        onClick={() => void hideSettings()}
        title="Fechar"
        className="absolute top-2 right-2 w-6 h-6 flex items-center justify-center rounded-md text-zinc-400 hover:bg-red-500 hover:!text-white transition-colors text-xs leading-none font-bold z-50 cursor-pointer"
      >
        ✕
      </button>
      <aside className="w-48 shrink-0 border-r border-black/10 dark:border-white/10 p-3 space-y-1 z-10" data-tauri-drag-region>
        <h1 className="px-2 py-2 text-sm font-semibold tracking-wide" data-tauri-drag-region>FPaste</h1>
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`w-full flex items-center gap-2 px-2 py-1.5 rounded-lg text-sm text-left transition-colors ${
              tab === t.id
                ? "text-white"
                : "hover:bg-black/5 dark:hover:bg-white/10"
            }`}
            style={tab === t.id ? { backgroundColor: "var(--accent-color)" } : undefined}
          >
            <span>{t.icon}</span>
            {t.label}
          </button>
        ))}
      </aside>

      <main className="grow overflow-y-auto p-6">
        {tab === "appearance" && <AppearanceTab />}
        {tab === "shortcuts" && <ShortcutsTab />}
        {tab === "storage" && <StorageTab />}
        {tab === "backup" && <BackupTab />}
      </main>
    </div>
  );
}

function AppearanceTab() {
  const [theme, setThemeState] = useState<ThemeMode>("system");
  const [accent, setAccentState] = useState(ACCENT_PRESETS["GNOME (Adwaita)"]);

  useEffect(() => {
    void load("settings.json").then(async (store) => {
      setThemeState(((await store.get<string>("theme")) as ThemeMode) || "system");
      setAccentState((await store.get<string>("accent")) || ACCENT_PRESETS["GNOME (Adwaita)"]);
    });
  }, []);

  const themeOptions: { id: ThemeMode; label: string; desc: string }[] = [
    { id: "light", label: "Claro", desc: "Tons brancos e cinzas claros" },
    { id: "dark", label: "Escuro", desc: "Grafite escuro e preto" },
    { id: "system", label: "Seguir Sistema", desc: "Acompanha o modo do SO" },
  ];

  return (
    <div className="space-y-8 max-w-lg">
      <section>
        <h2 className="text-base font-semibold mb-3">Modo de Tema</h2>
        <div className="grid grid-cols-3 gap-3">
          {themeOptions.map((opt) => (
            <button
              key={opt.id}
              onClick={() => {
                setThemeState(opt.id);
                void saveSetting("theme", opt.id);
              }}
              className={`rounded-xl border p-3 text-left transition-colors ${
                theme === opt.id
                  ? "border-[var(--accent-color)] ring-1 ring-[var(--accent-color)]"
                  : "border-black/10 dark:border-white/15 hover:border-black/30 dark:hover:border-white/30"
              }`}
            >
              <div
                className={`h-10 rounded-lg mb-2 border border-black/10 ${
                  opt.id === "light"
                    ? "bg-white"
                    : opt.id === "dark"
                      ? "bg-zinc-900"
                      : "bg-gradient-to-r from-white to-zinc-900"
                }`}
              />
              <p className="text-sm font-medium">{opt.label}</p>
              <p className="text-xs text-zinc-500 dark:text-zinc-400">{opt.desc}</p>
            </button>
          ))}
        </div>
      </section>

      <section>
        <h2 className="text-base font-semibold mb-3">Cor de Destaque</h2>
        <div className="flex flex-wrap gap-3">
          {Object.entries(ACCENT_PRESETS).map(([name, color]) => (
            <button
              key={name}
              title={name}
              onClick={() => {
                setAccentState(color);
                void saveSetting("accent", color);
              }}
              className={`w-9 h-9 rounded-full transition-transform hover:scale-110 ${
                accent === color ? "ring-2 ring-offset-2 ring-zinc-500 dark:ring-offset-zinc-900" : ""
              }`}
              style={{ backgroundColor: color }}
            />
          ))}
        </div>
      </section>
    </div>
  );
}

function ShortcutsTab() {
  const [shortcut, setShortcut] = useState("");
  const [recording, setRecording] = useState(false);
  const [partial, setPartial] = useState("");
  const [error, setError] = useState("");
  const [autoPaste, setAutoPasteState] = useState(false);
  const [autostart, setAutostart] = useState(false);
  const [openCentered, setOpenCentered] = useState(false);

  useEffect(() => {
    void getHotkey().then(setShortcut).catch(() => {});
    void getAutoPaste().then(setAutoPasteState).catch(() => {});
    void isEnabled().then(setAutostart).catch(() => {});
    void load("settings.json").then(async (store) => {
      setOpenCentered(await store.get<boolean>("openCentered") || false);
    });
  }, []);

  useEffect(() => {
    if (!recording) return;

    // Silencia o atalho ativo enquanto grava — do contrário, apertar a
    // combinação atual abriria a janela principal em vez de ser capturada aqui.
    void suspendHotkey();
    let resolved = false;
    const finishRecording = () => {
      resolved = true;
      setRecording(false);
      setPartial("");
    };

    const onKeyDown = (e: KeyboardEvent) => {
      e.preventDefault();
      if (e.key === "Escape") {
        e.stopPropagation();
        void resumeHotkey();
        finishRecording();
        return;
      }
      if (isModifierKey(e)) {
        // Exibe os modificadores em tempo real: "Ctrl +", "Ctrl + Shift +"…
        const mods = currentModifiers(e);
        setPartial(mods.length ? `${displayShortcut(mods.join("+"))} +` : "");
        return;
      }
      const combo = eventToShortcut(e);
      if (!combo) {
        setError("Combinação inválida — use ao menos um modificador (Ctrl, Alt, Shift).");
        void resumeHotkey();
        finishRecording();
        return;
      }
      setHotkey(combo)
        .then(() => {
          setShortcut(combo);
          setError("");
        })
        .catch((err) => {
          setError(String(err));
          void resumeHotkey();
        })
        .finally(finishRecording);
    };
    const onKeyUp = (e: KeyboardEvent) => {
      if (isModifierKey(e)) {
        const mods = currentModifiers(e);
        setPartial(mods.length ? `${displayShortcut(mods.join("+"))} +` : "");
      }
    };
    window.addEventListener("keydown", onKeyDown, true);
    window.addEventListener("keyup", onKeyUp, true);
    return () => {
      window.removeEventListener("keydown", onKeyDown, true);
      window.removeEventListener("keyup", onKeyUp, true);
      // Se o componente desmontar (ex.: trocou de aba) no meio da gravação,
      // garante que o atalho anterior volte a funcionar.
      if (!resolved) void resumeHotkey();
    };
  }, [recording]);

  return (
    <div className="space-y-8 max-w-lg">
      <section className="space-y-4">
        <h2 className="text-base font-semibold">Atalho de Abertura</h2>
        <p className="text-sm text-zinc-500 dark:text-zinc-400">
          Clique no campo e pressione a nova combinação de teclas.
        </p>
        <button
          onClick={() => {
            setRecording(true);
            setError("");
            setPartial("");
          }}
          className={`w-full rounded-xl border px-4 py-3 text-center font-mono text-sm transition-colors ${
            recording
              ? "border-[var(--accent-color)] ring-1 ring-[var(--accent-color)] animate-pulse"
              : "border-black/15 dark:border-white/20 hover:border-black/40 dark:hover:border-white/40"
          }`}
        >
          {recording
            ? partial || "Pressione a nova combinação…"
            : shortcut
              ? displayShortcut(shortcut)
              : "…"}
        </button>
        {error && <p className="text-sm text-red-500">{error}</p>}
        {navigator.userAgent.toLowerCase().includes("linux") && !navigator.userAgent.toLowerCase().includes("android") && (
          <div className="mt-2 p-3 rounded-lg bg-blue-500/10 border border-blue-500/20">
            <p className="text-sm text-blue-600 dark:text-blue-400 mb-2">
              No Linux (especialmente Wayland), atalhos globais podem não funcionar. 
              Configure um atalho nativo do sistema executando o comando <code>fpaste</code>.
            </p>
            <button
              onClick={() => void openLinuxKeyboardSettings()}
              className="text-sm px-3 py-1.5 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
            >
              Abrir Configurações de Teclado
            </button>
          </div>
        )}
      </section>

      <section className="space-y-2">
        <h2 className="text-base font-semibold">Colar Automaticamente</h2>
        <label className="flex items-center justify-between gap-4 rounded-xl border border-black/10 dark:border-white/15 px-4 py-3 cursor-pointer">
          <span className="text-sm text-zinc-600 dark:text-zinc-300">
            Após selecionar um item, cola direto na janela que estava em uso
            (equivalente a um Ctrl+V automático). Disponível apenas no Windows.
          </span>
          <input
            type="checkbox"
            checked={autoPaste}
            onChange={(e) => {
              setAutoPasteState(e.target.checked);
              void setAutoPaste(e.target.checked);
            }}
            className="shrink-0 w-4 h-4 accent-[var(--accent-color)]"
          />
        </label>
      </section>
      <section className="space-y-2">
        <h2 className="text-base font-semibold">Iniciar com o Sistema</h2>
        <label className="flex items-center justify-between gap-4 rounded-xl border border-black/10 dark:border-white/15 px-4 py-3 cursor-pointer">
          <span className="text-sm text-zinc-600 dark:text-zinc-300">
            Abre o FPaste em segundo plano quando você iniciar o computador,
            deixando-o pronto para uso imediatamente.
          </span>
          <input
            type="checkbox"
            checked={autostart}
            onChange={async (e) => {
              const checked = e.target.checked;
              setAutostart(checked);
              if (checked) {
                await enable();
              } else {
                await disable();
              }
            }}
            className="shrink-0 w-4 h-4 accent-[var(--accent-color)]"
          />
        </label>
      </section>

      <section className="space-y-2">
        <h2 className="text-base font-semibold">Abrir Centralizado</h2>
        <label className="flex items-center justify-between gap-4 rounded-xl border border-black/10 dark:border-white/15 px-4 py-3 cursor-pointer">
          <span className="text-sm text-zinc-600 dark:text-zinc-300">
            Abre a janela do FPaste centralizada na tela em vez de perto do cursor do mouse.
          </span>
          <input
            type="checkbox"
            checked={openCentered}
            onChange={(e) => {
              const checked = e.target.checked;
              setOpenCentered(checked);
              void load("settings.json").then(async (store) => {
                await store.set("openCentered", checked);
                await store.save();
              });
            }}
            className="shrink-0 w-4 h-4 accent-[var(--accent-color)]"
          />
        </label>
      </section>
    </div>
  );
}

interface StorageInfo {
  path: string;
  dbSizeBytes: number;
  itemCount: number;
}

function StorageTab() {
  const [info, setInfo] = useState<StorageInfo | null>(null);
  const [confirming, setConfirming] = useState(false);

  const refresh = () => void invoke<StorageInfo>("get_storage_info").then(setInfo);
  useEffect(refresh, []);

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 ** 2) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / 1024 ** 2).toFixed(1)} MB`;
  };

  return (
    <div className="space-y-6 max-w-lg">
      <h2 className="text-base font-semibold">Armazenamento</h2>
      {info && (
        <dl className="space-y-2 text-sm">
          <div className="flex justify-between gap-4">
            <dt className="text-zinc-500 dark:text-zinc-400 shrink-0">Banco de dados</dt>
            <dd className="font-mono text-xs break-all text-right select-text">{info.path}</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-zinc-500 dark:text-zinc-400">Tamanho</dt>
            <dd>{formatSize(info.dbSizeBytes)}</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-zinc-500 dark:text-zinc-400">Itens no histórico</dt>
            <dd>{info.itemCount}</dd>
          </div>
        </dl>
      )}
      <div className="pt-2">
        {confirming ? (
          <div className="flex items-center gap-3">
            <span className="text-sm text-red-500">Apagar todo o histórico?</span>
            <button
              onClick={() => {
                void invoke("clear_history").then(() => {
                  setConfirming(false);
                  refresh();
                });
              }}
              className="px-3 py-1.5 rounded-lg bg-red-500 text-white text-sm hover:bg-red-600"
            >
              Sim, apagar
            </button>
            <button
              onClick={() => setConfirming(false)}
              className="px-3 py-1.5 rounded-lg text-sm border border-black/15 dark:border-white/20"
            >
              Cancelar
            </button>
          </div>
        ) : (
          <button
            onClick={() => setConfirming(true)}
            className="px-3 py-1.5 rounded-lg text-sm border border-red-300 dark:border-red-800 text-red-500 hover:bg-red-50 dark:hover:bg-red-950"
          >
            Limpar histórico
          </button>
        )}
      </div>
    </div>
  );
}

function BackupTab() {
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<{ text: string; error?: boolean } | null>(null);

  const doExport = () => {
    setBusy(true);
    setMessage(null);
    exportBackup(password || undefined)
      .then((path) => setMessage({ text: `Backup salvo em ${path}` }))
      .catch((err) => setMessage({ text: String(err), error: true }))
      .finally(() => setBusy(false));
  };

  const doImport = () => {
    setBusy(true);
    setMessage(null);
    importBackup(password || undefined)
      .then((summary: ImportSummary) =>
        setMessage({
          text: `Importação concluída — ${summary.imported} novo(s) item(ns), ${summary.skipped} já existiam.`,
        }),
      )
      .catch((err) => setMessage({ text: String(err), error: true }))
      .finally(() => setBusy(false));
  };

  return (
    <div className="space-y-6 max-w-lg">
      <h2 className="text-base font-semibold">Backup e Restauração</h2>
      <p className="text-sm text-zinc-500 dark:text-zinc-400">
        Exporta um snapshot cifrado do histórico e da mídia em um único .zip.
        A senha abaixo é opcional e protege o próprio arquivo .zip para
        compartilhamento.
      </p>

      <div className="space-y-2">
        <label className="text-sm font-medium">Senha do backup (opcional)</label>
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Deixe em branco para não proteger"
          className="w-full rounded-lg border border-black/15 dark:border-white/20 bg-transparent px-3 py-2 text-sm outline-none focus:ring-1 focus:ring-[var(--accent-color)]"
        />
      </div>

      <div className="flex gap-3">
        <AccentButton disabled={busy} onClick={doExport}>
          Gerar Backup
        </AccentButton>
        <button
          disabled={busy}
          onClick={doImport}
          className="px-4 py-2 rounded-lg text-sm border border-black/15 dark:border-white/20 disabled:opacity-50"
        >
          Importar Backup
        </button>
      </div>

      {message && (
        <p className={`text-sm ${message.error ? "text-red-500" : "text-emerald-600 dark:text-emerald-400"}`}>
          {message.text}
        </p>
      )}
    </div>
  );
}
