import { FastifyInstance, RouteShorthandOptions } from 'fastify';

import { worker } from '../services/pythonClient';

type SimulationRunBody = {
  url: string;
  query: string;
};

const registerSimulationRoute = (
  app: FastifyInstance,
  url: string,
  opts?: RouteShorthandOptions,
) => {
  app.post(url, opts ?? {}, async (request, reply) => {
    const body = request.body as SimulationRunBody;

    app.log.debug({ body }, 'Received simulation request');

    try {
      const simulationResult = await worker.runSimulation(body);
      return reply.status(200).send(simulationResult);
    } catch (error) {
      app.log.error({ err: error, body }, 'Failed to run simulation via worker service');
      return reply.status(502).send({ error: 'Unable to reach simulation service' });
    }
  });
};

export default async function simulationRoutes(app: FastifyInstance) {
  registerSimulationRoute(app, '/simulation/run');
  registerSimulationRoute(app, '/simulate');
  registerSimulationRoute(app, '/api/simulate');
}

