"use client";

import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";

export function SignOutButton() {
  const router = useRouter();
  const supabase = createClient();

  async function handleSignOut() {
    await supabase.auth.signOut();
    router.push("/login");
    router.refresh();
  }

  return (
    <button
      onClick={handleSignOut}
      className="text-sm text-base-400 hover:text-base-50 border border-base-700 hover:border-base-600
                 rounded-md px-3 py-1.5 transition-colors"
    >
      Sair
    </button>
  );
}
