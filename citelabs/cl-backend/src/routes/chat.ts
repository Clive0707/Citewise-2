import { FastifyInstance, FastifyRequest } from 'fastify';
import { PrismaClient } from '@prisma/client';
import { Worker } from '../services/pythonClient';

const prisma = new PrismaClient();
const worker = new Worker();

// Simple in-memory rate limiter (v1: in-memory, future: Redis)
const rateLimitStore = new Map<string, { count: number; resetAt: number }>();

function checkRateLimit(userId: string, limit: number, windowMs: number): { allowed: boolean; retryAfter?: number } {
  const key = `rate_limit:${userId}`;
  const now = Date.now();
  const record = rateLimitStore.get(key);

  if (!record || now > record.resetAt) {
    // Create new window
    rateLimitStore.set(key, { count: 1, resetAt: now + windowMs });
    return { allowed: true };
  }

  if (record.count >= limit) {
    const retryAfter = Math.ceil((record.resetAt - now) / 1000);
    return { allowed: false, retryAfter };
  }

  // Increment count
  record.count++;
  rateLimitStore.set(key, record);
  return { allowed: true };
}

// Clean up old entries periodically (every 5 minutes)
setInterval(() => {
  const now = Date.now();
  for (const [key, record] of rateLimitStore.entries()) {
    if (now > record.resetAt) {
      rateLimitStore.delete(key);
    }
  }
}, 5 * 60 * 1000);

/**
 * Sanitize text by removing null bytes (0x00) which PostgreSQL cannot store in UTF-8 text fields.
 */
function sanitizeText(text: string | null | undefined): string | null {
  if (!text) return null;
  return text.replace(/\0/g, '');
}

/**
 * Estimate tokens from text (rough: 1 token ≈ 4 characters)
 */
function estimateTokens(text: string): number {
  return Math.ceil(text.length / 4);
}

/**
 * Get or create usage log for user and date
 */
async function getOrCreateUsageLog(userId: string, date: Date) {
  const dateStr = date.toISOString().split('T')[0]; // YYYY-MM-DD
  const usageDate = new Date(dateStr);

  const existing = await prisma.usageLog.findUnique({
    where: {
      userId_date: {
        userId,
        date: usageDate,
      },
    },
  });

  if (existing) {
    return existing;
  }

  return await prisma.usageLog.create({
    data: {
      userId,
      date: usageDate,
      tokensUsed: 0,
      messagesCount: 0,
    },
  });
}

/**
 * Check if user has exceeded daily quota
 */
async function checkQuota(userId: string, estimatedTokens: number): Promise<{ allowed: boolean; quotaUsed: number; quotaLimit: number }> {
  // For v1: Hardcoded limits (future: read from user_quotas table)
  const DAILY_LIMIT = 100000; // 100k tokens per day
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const usageLog = await getOrCreateUsageLog(userId, today);

  const quotaUsed = usageLog.tokensUsed;
  const quotaLimit = DAILY_LIMIT;
  const allowed = quotaUsed + estimatedTokens <= quotaLimit;

  return { allowed, quotaUsed, quotaLimit };
}

/**
 * Extract user ID from request (v1: simple header, future: JWT)
 */
function getUserId(request: FastifyRequest): string {
  // For v1: Use X-User-Id header (future: extract from JWT)
  const userId = (request.headers['x-user-id'] as string) || 'anonymous';
  return userId;
}

type CreateSessionBody = {
  title?: string;
  scope: 'sandbox_only' | 'sandbox_competitors' | 'web_only';
  run_id?: string;
};

type SendMessageBody = {
  content: string;
  idempotency_key?: string;
};

export default async function chatRoutes(app: FastifyInstance) {
  // ==========================================
  // POST /api/chat/sessions - Create new chat session
  // ==========================================
  app.post('/api/chat/sessions', async (request, reply) => {
    const userId = getUserId(request);
    const body = request.body as CreateSessionBody;

    if (!body.scope || !['sandbox_only', 'sandbox_competitors', 'web_only'].includes(body.scope)) {
      return reply.status(400).send({ error: 'Invalid scope. Must be: sandbox_only, sandbox_competitors, or web_only' });
    }

    // Validate run_id if provided
    if (body.run_id) {
      const run = await prisma.sandboxRun.findUnique({
        where: { id: body.run_id },
      });
      if (!run) {
        return reply.status(404).send({ error: 'Sandbox run not found' });
      }
    }

    try {
      app.log.info({
        userId,
        scope: body.scope,
        run_id: body.run_id,
        has_run_id: !!body.run_id,
      }, 'Creating chat session');
      
      const session = await prisma.chatSession.create({
        data: {
          userId,
          title: body.title || null,
          scope: body.scope,
          runId: body.run_id || null,
        },
      });
      
      // Verify run exists and has chunks if run_id provided
      if (body.run_id) {
        const run = await prisma.sandboxRun.findUnique({
          where: { id: body.run_id },
          include: {
            _count: {
              select: {
                ragResults: true,
              },
            },
          },
        });
        
        if (run) {
          // Check chunk count from database
          const chunkCount = await prisma.sandboxChunk.count({
            where: { runId: body.run_id },
          });
          
          app.log.info({
            session_id: session.id,
            run_id: body.run_id,
            run_status: run.status,
            rag_results_count: run._count.ragResults,
            chunks_in_db: chunkCount,
          }, 'Session created with run_id - verifying chunks');
        } else {
          app.log.warn({
            session_id: session.id,
            run_id: body.run_id,
          }, 'Session created with run_id but run not found in database');
        }
      }

      return reply.status(200).send({
        session_id: session.id,
        title: session.title,
        scope: session.scope,
        created_at: session.createdAt.toISOString(),
        run_id: session.runId,
      });
    } catch (error) {
      app.log.error({ err: error, userId, body }, 'Failed to create chat session');
      return reply.status(500).send({ error: 'Internal server error' });
    }
  });

  // ==========================================
  // GET /api/chat/sessions - List user's chat sessions
  // ==========================================
  app.get('/api/chat/sessions', async (request, reply) => {
    const userId = getUserId(request);
    const query = request.query as { limit?: string; offset?: string; run_id?: string };

    const limit = Math.min(parseInt(query.limit || '20', 10), 100);
    const offset = parseInt(query.offset || '0', 10);

    try {
      const where: any = {
        userId,
        deletedAt: null,
      };

      if (query.run_id) {
        where.runId = query.run_id;
      }

      const [sessions, total] = await Promise.all([
        prisma.chatSession.findMany({
          where,
          orderBy: { updatedAt: 'desc' },
          take: limit,
          skip: offset,
          select: {
            id: true,
            title: true,
            scope: true,
            createdAt: true,
            updatedAt: true,
            runId: true,
            _count: {
              select: { messages: true },
            },
          },
        }),
        prisma.chatSession.count({ where }),
      ]);

      const sessionsWithCounts = sessions.map((s) => ({
        session_id: s.id,
        title: s.title,
        scope: s.scope,
        message_count: s._count.messages,
        last_message_at: s.updatedAt.toISOString(),
        created_at: s.createdAt.toISOString(),
        run_id: s.runId,
      }));

      return reply.status(200).send({
        sessions: sessionsWithCounts,
        total,
        has_more: offset + limit < total,
      });
    } catch (error) {
      app.log.error({ err: error, userId }, 'Failed to list chat sessions');
      return reply.status(500).send({ error: 'Internal server error' });
    }
  });

  // ==========================================
  // GET /api/chat/sessions/:session_id - Get session with messages
  // ==========================================
  app.get('/api/chat/sessions/:session_id', async (request, reply) => {
    const userId = getUserId(request);
    const { session_id } = request.params as { session_id: string };

    try {
      const session = await prisma.chatSession.findFirst({
        where: {
          id: session_id,
          userId,
          deletedAt: null,
        },
        include: {
          messages: {
            orderBy: { createdAt: 'asc' },
            include: {
              citations: true,
            },
          },
        },
      });

      if (!session) {
        return reply.status(404).send({ error: 'Session not found' });
      }

      // Calculate total tokens
      const totalTokens = session.messages.reduce((sum, msg) => {
        return sum + (msg.tokensIn || 0) + (msg.tokensOut || 0);
      }, 0);

      return reply.status(200).send({
        session_id: session.id,
        title: session.title,
        scope: session.scope,
        created_at: session.createdAt.toISOString(),
        run_id: session.runId,
        messages: session.messages.map((msg) => ({
          message_id: msg.id,
          role: msg.role,
          content: msg.content,
          created_at: msg.createdAt.toISOString(),
          tokens_in: msg.tokensIn,
          tokens_out: msg.tokensOut,
          model_used: msg.modelUsed,
          latency_ms: msg.latencyMs,
          citations: msg.citations.map((cit) => ({
            url: cit.url,
            domain_type: cit.domainType,
            chunk_id: cit.chunkId,
            relevance_score: cit.relevanceScore,
          })),
        })),
        total_tokens: totalTokens,
      });
    } catch (error) {
      app.log.error({ err: error, session_id, userId }, 'Failed to get chat session');
      return reply.status(500).send({ error: 'Internal server error' });
    }
  });

  // ==========================================
  // POST /api/chat/sessions/:session_id/messages - Send message and get response
  // ==========================================
  app.post('/api/chat/sessions/:session_id/messages', async (request, reply) => {
    const userId = getUserId(request);
    const { session_id } = request.params as { session_id: string };
    const body = request.body as SendMessageBody;

    if (!body.content || typeof body.content !== 'string' || body.content.trim().length === 0) {
      return reply.status(400).send({ error: 'Message content is required' });
    }

    if (body.content.length > 2000) {
      return reply.status(400).send({ error: 'Message too long (max 2000 characters)' });
    }

    // Basic prompt injection protection: strip control characters (except newlines)
    const sanitizedContent = body.content.replace(/[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]/g, '');
    if (sanitizedContent !== body.content) {
      app.log.warn({ userId, session_id }, 'Stripped control characters from message');
    }
    body.content = sanitizedContent;

    try {
      // Verify session exists and belongs to user
      const session = await prisma.chatSession.findFirst({
        where: {
          id: session_id,
          userId,
          deletedAt: null,
        },
      });

      if (!session) {
        return reply.status(404).send({ error: 'Session not found' });
      }

      // Check idempotency (if key provided)
      if (body.idempotency_key) {
        const existingMessage = await prisma.chatMessage.findFirst({
          where: {
            sessionId: session_id,
            content: body.content,
            createdAt: {
              gte: new Date(Date.now() - 5 * 60 * 1000), // Within last 5 minutes
            },
          },
        });

        if (existingMessage) {
          // Return cached response
          const citations = await prisma.chatCitation.findMany({
            where: { messageId: existingMessage.id },
          });

          return reply.status(200).send({
            message_id: existingMessage.id,
            role: existingMessage.role,
            content: existingMessage.content,
            citations: citations.map((c) => ({
              url: c.url,
              domain_type: c.domainType,
              chunk_id: c.chunkId,
              relevance_score: c.relevanceScore,
            })),
            tokens_in: existingMessage.tokensIn,
            tokens_out: existingMessage.tokensOut,
            model_used: existingMessage.modelUsed,
            created_at: existingMessage.createdAt.toISOString(),
          });
        }
      }

      // Rate limiting: 10 messages per minute per user
      const rateLimit = checkRateLimit(userId, 10, 60 * 1000);
      if (!rateLimit.allowed) {
        return reply.status(429).send({
          error: 'Rate limit exceeded',
          retry_after: rateLimit.retryAfter,
        });
      }

      // Estimate tokens for quota check (rough: prompt + response estimate)
      const estimatedTokens = estimateTokens(body.content) + 500; // Add buffer for response

      // Check quota BEFORE processing
      const quotaCheck = await checkQuota(userId, estimatedTokens);
      if (!quotaCheck.allowed) {
        return reply.status(402).send({
          error: 'Quota exceeded',
          quota_limit: quotaCheck.quotaLimit,
          quota_used: quotaCheck.quotaUsed,
        });
      }

      // Store user message
      const userMessage = await prisma.chatMessage.create({
        data: {
          sessionId: session_id,
          role: 'user',
          content: sanitizeText(body.content) || '',
        },
      });

      // Update session title if this is the first message
      if (!session.title) {
        const title = body.content.substring(0, 100).trim();
        await prisma.chatSession.update({
          where: { id: session_id },
          data: { title },
        });
      }

      // Call worker to process message
      const startTime = Date.now();
      let workerResponse: any;
      try {
        // Type assertion: scope is validated at session creation to be one of the allowed values
        const scope = session.scope as 'sandbox_only' | 'sandbox_competitors' | 'web_only';
        
        // Get sandbox URL from run if available
        let sandboxUrl: string | undefined = undefined;
        if (session.runId) {
          const run = await prisma.sandboxRun.findUnique({
            where: { id: session.runId },
            select: { sandboxUrl: true },
          });
          if (run) {
            sandboxUrl = run.sandboxUrl;
            app.log.info({ run_id: session.runId, sandbox_url: sandboxUrl }, 'Fetched sandboxUrl from run');
          } else {
            app.log.warn({ run_id: session.runId }, 'Run not found when fetching sandboxUrl');
          }
        } else {
          app.log.warn({ session_id: session_id }, 'No runId in session, cannot fetch sandboxUrl');
        }
        
        app.log.info({
          session_id: session_id,
          run_id: session.runId,
          scope: scope,
          sandbox_url: sandboxUrl,
          message_length: body.content.length,
          message_preview: body.content.substring(0, 100),
        }, 'Sending chat message to worker');
        
        workerResponse = await worker.processChatMessage({
          session_id: session_id,
          content: body.content,
          scope: scope,
          run_id: session.runId || undefined,
          sandbox_url: sandboxUrl,
        });
        
        app.log.info({
          session_id: session_id,
          response_length: workerResponse.content?.length || 0,
          citations_count: workerResponse.citations?.length || 0,
          tokens_in: workerResponse.tokens_in,
          tokens_out: workerResponse.tokens_out,
        }, 'Received response from worker');
      } catch (error: any) {
        app.log.error({ err: error, session_id }, 'Worker chat processing failed');
        // Still create error message
        const errorMessage = await prisma.chatMessage.create({
          data: {
            sessionId: session_id,
            role: 'assistant',
            content: 'Sorry, I encountered an error processing your message. Please try again.',
            tokensIn: 0,
            tokensOut: 0,
          },
        });

        return reply.status(200).send({
          message_id: errorMessage.id,
          role: errorMessage.role,
          content: errorMessage.content,
          citations: [],
          tokens_in: 0,
          tokens_out: 0,
          model_used: null,
          created_at: errorMessage.createdAt.toISOString(),
        });
      }

      const latencyMs = Date.now() - startTime;
      const tokensIn = workerResponse.tokens_in || estimateTokens(body.content);
      const tokensOut = workerResponse.tokens_out || estimateTokens(workerResponse.content || '');

      // Store assistant message
      const assistantMessage = await prisma.chatMessage.create({
        data: {
          sessionId: session_id,
          role: 'assistant',
          content: sanitizeText(workerResponse.content) || '',
          tokensIn,
          tokensOut,
          modelUsed: workerResponse.model_used || 'gemini-2.5-flash',
          latencyMs,
        },
      });

      // Store citations
      if (workerResponse.citations && workerResponse.citations.length > 0) {
        await prisma.chatCitation.createMany({
          data: workerResponse.citations.map((cit: any) => ({
            messageId: assistantMessage.id,
            url: cit.url || '',
            domainType: cit.domain_type || null,
            chunkId: cit.chunk_id || null,
            relevanceScore: cit.relevance_score || null,
          })),
        });
      }

      // Update usage log atomically
      const today = new Date();
      today.setHours(0, 0, 0, 0);
      await prisma.usageLog.upsert({
        where: {
          userId_date: {
            userId,
            date: today,
          },
        },
        create: {
          userId,
          date: today,
          tokensUsed: tokensIn + tokensOut,
          messagesCount: 1,
        },
        update: {
          tokensUsed: { increment: tokensIn + tokensOut },
          messagesCount: { increment: 1 },
        },
      });

      // Return response
      return reply.status(200).send({
        message_id: assistantMessage.id,
        role: assistantMessage.role,
        content: assistantMessage.content,
        citations: workerResponse.citations || [],
        tokens_in: tokensIn,
        tokens_out: tokensOut,
        model_used: assistantMessage.modelUsed,
        created_at: assistantMessage.createdAt.toISOString(),
      });
    } catch (error) {
      app.log.error({ err: error, session_id, userId }, 'Failed to process chat message');
      return reply.status(500).send({ error: 'Internal server error' });
    }
  });

  // ==========================================
  // DELETE /api/chat/sessions/:session_id - Soft delete session
  // ==========================================
  app.delete('/api/chat/sessions/:session_id', async (request, reply) => {
    const userId = getUserId(request);
    const { session_id } = request.params as { session_id: string };

    try {
      const session = await prisma.chatSession.findFirst({
        where: {
          id: session_id,
          userId,
          deletedAt: null,
        },
      });

      if (!session) {
        return reply.status(404).send({ error: 'Session not found' });
      }

      await prisma.chatSession.update({
        where: { id: session_id },
        data: { deletedAt: new Date() },
      });

      return reply.status(200).send({
        message: 'Session deleted',
        session_id: session_id,
      });
    } catch (error) {
      app.log.error({ err: error, session_id, userId }, 'Failed to delete chat session');
      return reply.status(500).send({ error: 'Internal server error' });
    }
  });

  // ==========================================
  // GET /api/chat/usage - Get user's token usage stats
  // ==========================================
  app.get('/api/chat/usage', async (request, reply) => {
    const userId = getUserId(request);
    const query = request.query as { period?: 'today' | 'week' | 'month' };

    const period = query.period || 'today';
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    let startDate: Date;
    if (period === 'today') {
      startDate = today;
    } else if (period === 'week') {
      startDate = new Date(today);
      startDate.setDate(startDate.getDate() - 7);
    } else {
      // month
      startDate = new Date(today);
      startDate.setMonth(startDate.getMonth() - 1);
    }

    try {
      const usageLogs = await prisma.usageLog.findMany({
        where: {
          userId,
          date: {
            gte: startDate,
          },
        },
      });

      const tokensUsed = usageLogs.reduce((sum, log) => sum + log.tokensUsed, 0);
      const messagesCount = usageLogs.reduce((sum, log) => sum + log.messagesCount, 0);
      const sessionsCount = await prisma.chatSession.count({
        where: {
          userId,
          createdAt: { gte: startDate },
          deletedAt: null,
        },
      });

      // For v1: Hardcoded limit (future: read from user_quotas)
      const DAILY_LIMIT = 100000;

      return reply.status(200).send({
        period,
        tokens_used: tokensUsed,
        tokens_limit: DAILY_LIMIT,
        messages_count: messagesCount,
        sessions_count: sessionsCount,
      });
    } catch (error) {
      app.log.error({ err: error, userId }, 'Failed to get usage stats');
      return reply.status(500).send({ error: 'Internal server error' });
    }
  });
}

