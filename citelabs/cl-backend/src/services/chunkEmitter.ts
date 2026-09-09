/**
 * Centralized chunk emission utility for persisting streamed sandbox output.
 * 
 * This utility:
 * - Persists chunks into sandbox_chunks table
 * - Maintains monotonic sequence per run
 * - Never blocks execution on DB failures
 * - Maintains backward compatibility
 */

import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

// In-memory sequence counter per run (fallback if DB query fails)
const sequenceCounters: Map<string, number> = new Map();

interface EmitChunkParams {
  runId: string;
  conversationId?: string;
  role: 'user' | 'assistant' | 'system' | 'log' | 'error';
  content: string;
}

/**
 * Emit a chunk: persist to DB and maintain sequence.
 * Never throws - always continues execution even if DB write fails.
 */
export async function emitChunk(params: EmitChunkParams): Promise<void> {
  const { runId, conversationId, role, content } = params;

  if (!content || !content.trim()) {
    return; // Skip empty chunks
  }

  try {
    // Get or initialize sequence counter for this run
    let sequence = sequenceCounters.get(runId) || 0;
    
    // Try to get the highest chunkId from DB for this run to ensure monotonic sequence
    try {
      const maxChunk = await prisma.sandboxChunk.findFirst({
        where: {
          runId: runId,
          url: `stream:${role}`, // Use url field to identify stream chunks
        },
        orderBy: {
          chunkId: 'desc',
        },
        select: {
          chunkId: true,
        },
      });
      
      if (maxChunk && maxChunk.chunkId >= sequence) {
        sequence = maxChunk.chunkId + 1;
      }
    } catch (dbError) {
      // If DB query fails, use in-memory counter (fallback)
      sequence = (sequenceCounters.get(runId) || 0) + 1;
    }

    // Update in-memory counter
    sequenceCounters.set(runId, sequence + 1);

    // Prepare chunk data
    // Repurpose fields: url = source identifier, chunkId = sequence, text = content
    const chunkData = {
      id: `chunk_${runId}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      runId: runId,
      url: conversationId ? `stream:${role}:${conversationId}` : `stream:${role}`,
      chunkId: sequence,
      text: content.substring(0, 100000), // Limit to 100KB to avoid DB issues
      summary: role === 'error' ? 'Error chunk' : null,
      isClient: false,
      domain: conversationId || null, // Use domain field for conversationId
      sourceType: role, // Use sourceType for role
      domainType: null, // Not used for stream chunks
    };

    // Persist to DB (non-blocking - wrapped in try/catch)
    await prisma.sandboxChunk.create({
      data: chunkData as any, // Type assertion needed for repurposed fields
    });

  } catch (error) {
    // Never throw - log error and continue
    console.error(`[emitChunk] Failed to persist chunk for run ${runId}:`, error);
    // Continue execution - streaming should still work
  }
}

/**
 * Get the current sequence number for a run (for external use if needed).
 */
export function getCurrentSequence(runId: string): number {
  return sequenceCounters.get(runId) || 0;
}

/**
 * Reset sequence counter for a run (useful for testing or cleanup).
 */
export function resetSequence(runId: string): void {
  sequenceCounters.delete(runId);
}

