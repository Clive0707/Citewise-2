import { PrismaClient } from '@prisma/client';

export type PageRecordData = {
  id?: string;
  url: string;
  pageType?: string | null;
  title?: string | null;
  metaDescription?: string | null;
  headings?: string | null;
  mainContent?: string | null;
  lastModified?: string | null;
  pagePurposeSummary?: string | null;
  primaryKeywordGuess?: string | null;
  aiSummary?: string | null;
  createdAt?: Date;
};

export class PageStore {
  constructor(private readonly prisma = new PrismaClient()) {}

  /**
   * Insert or update a page record in the database
   */
  async upsertByUrl(record: PageRecordData) {
    try {
      const result = await this.prisma.pageRecord.upsert({
        where: { url: record.url },
        update: {
          pageType: record.pageType,
          title: record.title,
          metaDescription: record.metaDescription,
          headings: record.headings,
          mainContent: record.mainContent,
          lastModified: record.lastModified,
          pagePurposeSummary: record.pagePurposeSummary,
          primaryKeywordGuess: record.primaryKeywordGuess,
          aiSummary: record.aiSummary,
        },
        create: {
          url: record.url,
          pageType: record.pageType,
          title: record.title,
          metaDescription: record.metaDescription,
          headings: record.headings,
          mainContent: record.mainContent,
          lastModified: record.lastModified,
          pagePurposeSummary: record.pagePurposeSummary,
          primaryKeywordGuess: record.primaryKeywordGuess,
          aiSummary: record.aiSummary,
        },
      });
      return result;
    } catch (error) {
      console.error('Failed to upsert page record:', error);
      throw error;
    }
  }

  /**
   * Find a page record by URL
   */
  async findByUrl(url: string) {
    try {
      const result = await this.prisma.pageRecord.findUnique({
        where: { url },
      });
      return result;
    } catch (error) {
      console.error('Failed to find page record:', error);
      throw error;
    }
  }

  /**
   * Find all page records (with optional pagination)
   */
  async findAll(limit = 100, offset = 0) {
    try {
      const results = await this.prisma.pageRecord.findMany({
        take: limit,
        skip: offset,
        orderBy: {
          createdAt: 'desc',
        },
      });
      return results;
    } catch (error) {
      console.error('Failed to fetch page records:', error);
      throw error;
    }
  }
}

export const pageStore = new PageStore();

