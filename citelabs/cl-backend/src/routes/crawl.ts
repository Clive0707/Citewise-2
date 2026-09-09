import { FastifyInstance, RouteShorthandOptions } from 'fastify';

import { worker } from '../services/pythonClient';

type CrawlRequestBody = {
  url: string;
};

const isValidUrl = (value: string): boolean => {
  try {
    // eslint-disable-next-line no-new
    new URL(value);
    return true;
  } catch {
    return false;
  }
};

const registerCrawlRoute = (app: FastifyInstance, url: string, opts?: RouteShorthandOptions) => {
  app.post(url, opts ?? {}, async (request, reply) => {
    const body = request.body as CrawlRequestBody | undefined;

    if (!body?.url || !isValidUrl(body.url)) {
      return reply.status(400).send({ error: 'Invalid URL provided' });
    }

    try {
      const crawlResult = await worker.crawl(body.url);
      return reply.status(200).send(crawlResult);
    } catch (error) {
      app.log.error({ err: error, url: body.url }, 'Failed to crawl URL via worker service');
      return reply.status(502).send({ error: 'Unable to reach crawler service' });
    }
  });
};

export default async function crawlRoutes(app: FastifyInstance) {
  registerCrawlRoute(app, '/crawl');
  registerCrawlRoute(app, '/api/crawl');
}

