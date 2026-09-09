import { FastifyInstance } from 'fastify';
import { worker } from '../services/pythonClient';
import { PrismaClient } from '@prisma/client';
import { URL } from 'url';

const prisma = new PrismaClient();

/**
 * Sanitize text by removing null bytes (0x00) which PostgreSQL cannot store in UTF-8 text fields.
 */
function sanitizeText(text: string | null | undefined): string | null {
  if (!text) return null;
  // Remove null bytes (0x00) which PostgreSQL cannot store
  return text.replace(/\0/g, '');
}

/**
 * Extract root domain from a URL for use as sandboxUrl.
 * Example: https://staging.example.com/page -> https://staging.example.com
 */
function getRootDomain(urlString: string): string {
  try {
    const url = new URL(urlString);
    return `${url.protocol}//${url.hostname}`;
  } catch {
    // Fallback: try to extract domain manually
    const match = urlString.match(/^(https?:\/\/[^\/]+)/);
    return match ? match[1] : urlString;
  }
}

type StagingUploadBody = {
  url: string;
  title?: string;
  metaDescription?: string;
  html?: string;
  textContent?: string;
};

export default async function stagingRoutes(app: FastifyInstance) {
  // ==========================================
  // POST /api/staging/upload - Upload staging page content
  // ==========================================
  app.post('/api/staging/upload', async (request, reply) => {
    const body = request.body as StagingUploadBody;
    const { url, title, metaDescription, html, textContent } = body;

    app.log.debug({ url, hasTitle: !!title, hasContent: !!textContent }, 'Received staging upload request');

    // Validate required fields
    if (!url || typeof url !== 'string') {
      return reply.status(400).send({ error: 'Invalid URL provided' });
    }

    if (!textContent && !html) {
      return reply.status(400).send({ error: 'Either textContent or html must be provided' });
    }

    try {
      // Extract root domain for sandboxUrl
      const rootDomain = getRootDomain(url);

      // Find or create SandboxRun for this root domain
      // For staging, we'll create a new run each time (or you could find existing pending runs)
      const runId = `run_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

      // Create run record with status "pending" (will be updated to "processing" when worker starts)
      const run = await prisma.sandboxRun.create({
        data: {
          id: runId,
          sandboxUrl: rootDomain,
          status: 'pending',
        },
      });

      app.log.info({ runId, url: rootDomain }, 'Created staging SandboxRun');

      // Extract H1 from HTML if available, otherwise use title
      let h1: string | null = null;
      if (html) {
        try {
          // Simple regex to extract first h1 (for V1, keep it simple)
          const h1Match = html.match(/<h1[^>]*>([^<]+)<\/h1>/i);
          if (h1Match) {
            h1 = sanitizeText(h1Match[1].trim());
          }
        } catch (err) {
          app.log.debug({ err }, 'Failed to extract H1 from HTML');
        }
      }

      // Use textContent if available, otherwise try to extract from HTML
      const fullText = textContent || (html ? sanitizeText(html.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim()) : null);

      // Create SandboxPage for this URL
      const pageId = `${runId}_page`;
      await prisma.sandboxPage.create({
        data: {
          id: pageId,
          runId: runId,
          url: url,
          title: sanitizeText(title),
          h1: h1,
          pageSummary: sanitizeText(metaDescription),
          fullText: fullText,
          isClient: true,
        },
      });

      app.log.info({ runId, pageId }, 'Created/updated staging SandboxPage');

      // Update run status to "processing" and kick off the worker pipeline
      await prisma.sandboxRun.update({
        where: { id: runId },
        data: { status: 'processing' },
      });

      // Fire-and-forget: Start job in Python worker
      // Note: The worker will try to crawl the URL, which may fail for staging URLs behind VPN.
      // For V1, we've already stored the content in the database (SandboxPage.fullText).
      // The worker's async_job.py will attempt to crawl, but if it fails, the pipeline may error.
      // TODO (V2): Modify worker to check database first for existing page content before crawling,
      // or pass the content directly to the worker via a new endpoint.
      worker.startJob({ run_id: runId, url: rootDomain }).catch((err) => {
        app.log.error({ err, runId }, 'Failed to start job in worker');
        // Update status to error
        prisma.sandboxRun
          .update({
            where: { id: runId },
            data: { status: 'error' },
          })
          .catch((updateErr) => {
            app.log.error({ err: updateErr, runId }, 'Failed to update run status to error');
          });
      });

      return reply.status(200).send({ run_id: runId });
    } catch (error) {
      app.log.error({ err: error, body }, 'Failed to process staging upload');
      return reply.status(500).send({ error: 'Internal server error' });
    }
  });
}

