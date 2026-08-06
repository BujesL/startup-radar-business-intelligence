/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  experimental: {
    // Server Components como padrão: menos JS no cliente, dados sensíveis
    // (chaves de API) nunca chegam ao bundle do browser.
    serverActions: { allowedOrigins: ["*"] },
  },
};

export default nextConfig;
