import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'media.daft.ie',
        port: '',
        pathname: '/**',
      },
    ],
  },
};

export default nextConfig;
