import { createBrowserClient } from "@supabase/ssr";

/**
 * Cliente Supabase para Client Components.
 *
 * Usa apenas a chave `anon` pública — nunca a `service_role`. A anon key é
 * segura no browser porque toda a proteção real vem das políticas de Row
 * Level Security definidas em database/schema.sql, não da chave em si.
 */
export function createClient() {
  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
  );
}
