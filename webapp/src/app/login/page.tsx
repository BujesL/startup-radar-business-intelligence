"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";

export default function LoginPage() {
  const router = useRouter();
  const supabase = createClient();
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [carregando, setCarregando] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setCarregando(true);
    setErro(null);

    const { error } = await supabase.auth.signInWithPassword({ email, password: senha });

    setCarregando(false);
    if (error) {
      setErro("Credenciais inválidas. Verifique e-mail e senha.");
      return;
    }
    router.push("/");
    router.refresh();
  }

  return (
    <main className="min-h-screen flex items-center justify-center bg-base-950 px-6">
      <form onSubmit={handleSubmit} className="card w-full max-w-sm">
        <p className="text-accent font-mono text-xs uppercase tracking-widest mb-1">
          Startup Radar POA
        </p>
        <h1 className="text-lg font-semibold mb-6">Entrar</h1>

        <label className="text-sm text-base-400 block mb-1">E-mail</label>
        <input
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="w-full bg-base-850 border border-base-700 rounded-md px-3 py-2 text-sm mb-4
                     focus:outline-none focus:ring-2 focus:ring-accent/50"
        />

        <label className="text-sm text-base-400 block mb-1">Senha</label>
        <input
          type="password"
          required
          value={senha}
          onChange={(e) => setSenha(e.target.value)}
          className="w-full bg-base-850 border border-base-700 rounded-md px-3 py-2 text-sm mb-4
                     focus:outline-none focus:ring-2 focus:ring-accent/50"
        />

        {erro && <p className="text-danger text-sm mb-4">{erro}</p>}

        <button
          type="submit"
          disabled={carregando}
          className="w-full bg-accent text-base-950 font-medium rounded-md py-2 text-sm
                     hover:bg-accent-bright transition-colors disabled:opacity-60"
        >
          {carregando ? "Entrando..." : "Entrar"}
        </button>
      </form>
    </main>
  );
}
