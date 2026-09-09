import { FastifyInstance, RouteShorthandOptions } from 'fastify';

import { worker } from '../services/pythonClient';

type SchemaGenerateBody = {
  url: string;
  page_type: string;
  title: string;
  ai_summary: string;
};

const registerSchemaRoute = (app: FastifyInstance, url: string, opts?: RouteShorthandOptions) => {
  app.post(url, opts ?? {}, async (request, reply) => {
    const body = request.body as SchemaGenerateBody;

    app.log.debug({ body }, 'Received schema generation request');

    try {
      const schemaResponse = await worker.generateSchema(body);
      return reply.status(200).send(schemaResponse);
    } catch (error) {
      app.log.error({ err: error, body }, 'Failed to generate schema block via worker');
      return reply.status(502).send({ error: 'Unable to reach schema generation service' });
    }
  });
};

export default async function schemaRoutes(app: FastifyInstance) {
  registerSchemaRoute(app, '/schema/generate');
  registerSchemaRoute(app, '/api/schema');
}

