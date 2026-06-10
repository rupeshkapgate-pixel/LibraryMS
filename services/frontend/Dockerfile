# ── Stage 1: Install dependencies ────────────────────────────────────────────
FROM node:20-alpine AS deps
WORKDIR /app

# Copy package manifest only (no lock file - use npm install)
COPY package.json ./

# Install all deps; --legacy-peer-deps handles minor peer conflicts
RUN npm install --legacy-peer-deps

# ── Stage 2: Build the Next.js application ────────────────────────────────────
FROM node:20-alpine AS builder
WORKDIR /app

# Bring in installed node_modules from deps stage
COPY --from=deps /app/node_modules ./node_modules

# Copy all source files
COPY . .

# Disable Next.js telemetry during build
ENV NEXT_TELEMETRY_DISABLED=1

# The API URL is baked in at build time for static pages
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

# Build the Next.js app (produces .next/standalone because next.config.js has output:"standalone")
RUN npm run build

# ── Stage 3: Production runtime ───────────────────────────────────────────────
FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV PORT=3000
ENV HOSTNAME=0.0.0.0

# Create a non-root user for security
RUN addgroup --system --gid 1001 nodejs \
 && adduser  --system --uid 1001 nextjs

# The standalone output is self-contained - copy it first
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./

# Copy static assets
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

# Copy public directory (create it if the builder didn't produce one)
RUN mkdir -p ./public
COPY --from=builder /app/public ./public

USER nextjs

EXPOSE 3000

# The standalone output produces server.js at the root of the workdir
CMD ["node", "server.js"]
