/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  output: "standalone",   // required for the Docker multi-stage build
};
export default nextConfig;

