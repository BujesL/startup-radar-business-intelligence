import { createServerClient, type CookieOptionsWithName } from "@supabase/ssr";
import { cookies } from "next/headers";

type CookieToSet = {
  name: string;
  value: string;
  options?: CookieOptionsWithName;
};

/**
 * Cliente Supabase para Server Components / Server Actions / Route Handlers.
 * Propaga a sessão via cookies HTTP-only — o token nunca fica acessível a
 * JavaScript do cliente (mitiga roubo de sessão via XSS).
 */
export async function createClient() {
  const cookieStore = await cookies();

  return createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return cookieStore.getAll();
        },
        setAll(cookiesToSet: CookieToSet[]) {
          try {
            cookiesToSet.forEach(({ name, value, options }) =>
              cookieStore.set(name, value, options),
            );
          } catch {
            // Chamado de um Server Component sem permissão de escrita de
            // cookie — seguro ignorar quando há middleware renovando a sessão.
          }
        },
      },
    },
  );
}
