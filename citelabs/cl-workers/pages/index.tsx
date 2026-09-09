import { FormEvent, useState } from 'react';
import Head from 'next/head';

type SandboxPage = {
  url: string;
  title?: string | null;
  h1?: string | null;
  intent?: string | null;
  pageSummary?: string | null;
  aiSummary?: string | null;
};

type SandboxQuestion = {
  id: string;
  type: string;
  question: string;
};

type SandboxCompetitor = {
  id: string;
  url: string;
  domain: string;
  title?: string | null;
  aiSummary?: string | null;
};

type SandboxRagResult = {
  id: string;
  question: string;
  answer: string;
  didSandboxAppear: boolean;
  chunksUsed: number;
  competitorCitations: string[];
  sandboxCitations: string[];
  questionRef?: {
    type: string;
  };
};

type SandboxScores = {
  geoScore: number;
  aeoScore: number;
  citationRate: number;
  coverage?: number | null;
  competitorDominance?: number | null;
  recommendations: string[];
};

type SandboxResponse = {
  run_id: string;
  status: string;
  sandbox: SandboxPage | null;
  generated_questions: SandboxQuestion[];
  competitors: SandboxCompetitor[];
  rag_results: SandboxRagResult[];
  scores: SandboxScores | null;
  recommendations: string[];
};

const Home = () => {
  const [url, setUrl] = useState('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<SandboxResponse | null>(null);
  const [currentStep, setCurrentStep] = useState<string>('idle');

  const handleAnalyze = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setResults(null);
    setCurrentStep('analyzing');

    if (!url.trim()) {
      setError('Please enter a URL to analyze.');
      return;
    }

    setIsAnalyzing(true);

    try {
      const response = await fetch('http://localhost:4000/api/sandbox/analyze', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ url: url.trim() }),
      });

      const data = (await response.json()) as SandboxResponse & { error?: string };

      if (!response.ok || data.error) {
        setError(data.error || 'Failed to analyze sandbox page.');
        setCurrentStep('error');
      } else {
        setResults(data);
        setCurrentStep('completed');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unexpected error occurred.');
      setCurrentStep('error');
    } finally {
      setIsAnalyzing(false);
    }
  };

  const getStepStatus = (step: string) => {
    if (currentStep === 'error') return 'error';
    if (currentStep === 'completed') return 'completed';
    if (currentStep === step || (step === 'analyzing' && currentStep === 'analyzing')) return 'active';
    if (step === 'idle') return 'pending';
    return 'pending';
  };

  return (
    <>
      <Head>
        <title>CiteLabs AEO/GEO Evaluation</title>
      </Head>
      <main className="flex min-h-screen flex-col items-center bg-slate-100 p-8">
        <section className="w-full max-w-6xl space-y-8">
          <header className="rounded-lg border border-dashed border-slate-300 bg-white p-8 shadow-sm">
            <h1 className="text-3xl font-semibold text-slate-900">AEO/GEO Sandbox Evaluation</h1>
            <p className="mt-3 text-slate-600">
              Analyze your page's performance in AI-powered search engines. This evaluation runs
              through 7 steps to generate comprehensive AEO (Answer Engine Optimization) and GEO
              (Generative Engine Optimization) scores.
            </p>
          </header>

          {/* Input Form */}
          <section className="rounded-lg border border-slate-200 bg-white p-8 shadow-sm">
            <h2 className="text-2xl font-semibold text-slate-900">Start Analysis</h2>
            <p className="mt-2 text-slate-600">Enter your sandbox page URL to begin the evaluation.</p>
            <form className="mt-6 flex flex-col gap-4" onSubmit={handleAnalyze}>
              <label className="flex flex-col gap-2 text-left">
                <span className="text-sm font-medium text-slate-700">Sandbox Page URL</span>
                <input
                  className="rounded border border-slate-300 px-3 py-2 text-base text-slate-900 focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200"
                  placeholder="https://example.com"
                  value={url}
                  onChange={(event) => setUrl(event.target.value)}
                  type="url"
                  required
                  disabled={isAnalyzing}
                />
              </label>
              <div className="flex flex-wrap items-center gap-3">
                <button
                  className="inline-flex items-center justify-center rounded bg-sky-600 px-4 py-2 text-white transition hover:bg-sky-700 disabled:cursor-not-allowed disabled:bg-slate-400"
                  type="submit"
                  disabled={isAnalyzing}
                >
                  {isAnalyzing ? 'Analyzing...' : 'Start Analysis'}
                </button>
                {error && <span className="text-sm text-red-600">{error}</span>}
              </div>
            </form>
          </section>

          {/* Step Progress Indicator */}
          {currentStep !== 'idle' && (
            <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
              <h3 className="text-lg font-semibold text-slate-900 mb-4">Analysis Progress</h3>
              <div className="space-y-2">
                {[
                  { key: 'analyzing', label: 'Step 1-2: Page Analysis & Intent Extraction' },
                  { key: 'questions', label: 'Step 3: Generating User Questions' },
                  { key: 'competitors', label: 'Step 4: Extracting Competitors' },
                  { key: 'crawling', label: 'Step 5: Crawling Competitors' },
                  { key: 'rag', label: 'Step 6: RAG Simulation' },
                  { key: 'finalizing', label: 'Step 7: Calculating Scores' },
                ].map((step) => {
                  const status = getStepStatus(step.key);
                  return (
                    <div key={step.key} className="flex items-center gap-3">
                      <div
                        className={`h-2 w-2 rounded-full ${
                          status === 'completed'
                            ? 'bg-emerald-500'
                            : status === 'active'
                              ? 'bg-sky-500 animate-pulse'
                              : status === 'error'
                                ? 'bg-red-500'
                                : 'bg-slate-300'
                        }`}
                      />
                      <span
                        className={`text-sm ${
                          status === 'completed'
                            ? 'text-emerald-700 font-medium'
                            : status === 'active'
                              ? 'text-sky-700 font-medium'
                              : status === 'error'
                                ? 'text-red-700'
                                : 'text-slate-500'
                        }`}
                      >
                        {step.label}
                      </span>
                    </div>
                  );
                })}
              </div>
            </section>
          )}

          {/* Results */}
          {results && (
            <div className="space-y-6">
              {/* Step 1: Page Analysis */}
              {results.sandbox && (
                <section className="rounded-lg border border-slate-200 bg-white p-8 shadow-sm">
                  <h2 className="text-2xl font-semibold text-slate-900">Step 1: Page Analysis</h2>
                  <div className="mt-6 grid gap-4 lg:grid-cols-2">
                    <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
                      <h3 className="text-sm font-semibold uppercase text-slate-600">Title</h3>
                      <p className="mt-2 text-slate-900">{results.sandbox.title || '—'}</p>
                    </div>
                    <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
                      <h3 className="text-sm font-semibold uppercase text-slate-600">H1</h3>
                      <p className="mt-2 text-slate-900">{results.sandbox.h1 || '—'}</p>
                    </div>
                    <div className="rounded-lg border border-slate-200 bg-slate-50 p-4 lg:col-span-2">
                      <h3 className="text-sm font-semibold uppercase text-slate-600">Page Intent</h3>
                      <p className="mt-2 whitespace-pre-line text-slate-900">
                        {results.sandbox.intent || '—'}
                      </p>
                    </div>
                    <div className="rounded-lg border border-slate-200 bg-slate-50 p-4 lg:col-span-2">
                      <h3 className="text-sm font-semibold uppercase text-slate-600">AI Summary</h3>
                      <p className="mt-2 whitespace-pre-line text-slate-900">
                        {results.sandbox.aiSummary || '—'}
                      </p>
                    </div>
                  </div>
                </section>
              )}

              {/* Step 2: Generated Questions */}
              {results.generated_questions && results.generated_questions.length > 0 && (
                <section className="rounded-lg border border-slate-200 bg-white p-8 shadow-sm">
                  <h2 className="text-2xl font-semibold text-slate-900">Step 2: Generated User Questions</h2>
                  <p className="mt-2 text-slate-600">
                    {results.generated_questions.length} questions generated across intent, experience, and
                    transaction types.
                  </p>
                  <div className="mt-6 grid gap-4 md:grid-cols-3">
                    {['intent', 'experience', 'transaction'].map((type) => {
                      const typeQuestions = results.generated_questions.filter((q) => q.type === type);
                      return (
                        <div key={type} className="rounded-lg border border-slate-200 bg-slate-50 p-4">
                          <h3 className="text-sm font-semibold uppercase text-slate-600 mb-3">
                            {type.charAt(0).toUpperCase() + type.slice(1)} ({typeQuestions.length})
                          </h3>
                          <ul className="space-y-2">
                            {typeQuestions.map((q) => (
                              <li key={q.id} className="text-sm text-slate-700">
                                • {q.question}
                              </li>
                            ))}
                          </ul>
                        </div>
                      );
                    })}
                  </div>
                </section>
              )}

              {/* Step 3: Competitors */}
              {results.competitors && results.competitors.length > 0 && (
                <section className="rounded-lg border border-slate-200 bg-white p-8 shadow-sm">
                  <h2 className="text-2xl font-semibold text-slate-900">Step 3: Competitor Landscape</h2>
                  <p className="mt-2 text-slate-600">
                    {results.competitors.length} competitors identified from LLM answers.
                  </p>
                  <div className="mt-6 space-y-3">
                    {results.competitors.map((comp) => (
                      <div
                        key={comp.id}
                        className="rounded-lg border border-slate-200 bg-slate-50 p-4"
                      >
                        <h3 className="font-medium text-slate-900">
                          <a
                            href={comp.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-sky-700 hover:underline"
                          >
                            {comp.url}
                          </a>
                        </h3>
                        {comp.title && <p className="mt-1 text-sm text-slate-600">{comp.title}</p>}
                        {comp.aiSummary && (
                          <p className="mt-2 text-sm text-slate-700">{comp.aiSummary}</p>
                        )}
                      </div>
                    ))}
                  </div>
                </section>
              )}

              {/* Step 4: RAG Results */}
              {results.rag_results && results.rag_results.length > 0 && (
                <section className="rounded-lg border border-slate-200 bg-white p-8 shadow-sm">
                  <h2 className="text-2xl font-semibold text-slate-900">Step 4: RAG Simulation Results</h2>
                  <p className="mt-2 text-slate-600">
                    Results for {results.rag_results.length} questions with RAG-grounded answers.
                  </p>
                  <div className="mt-6 space-y-4">
                    {results.rag_results.map((rag) => (
                      <div
                        key={rag.id}
                        className={`rounded-lg border p-4 ${
                          rag.didSandboxAppear
                            ? 'border-emerald-200 bg-emerald-50'
                            : 'border-slate-200 bg-slate-50'
                        }`}
                      >
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <h3 className="font-medium text-slate-900">{rag.question}</h3>
                            <p className="mt-2 text-sm text-slate-700">{rag.answer}</p>
                            <div className="mt-3 flex flex-wrap gap-2">
                              <span
                                className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold ${
                                  rag.didSandboxAppear
                                    ? 'bg-emerald-200 text-emerald-800'
                                    : 'bg-slate-200 text-slate-800'
                                }`}
                              >
                                {rag.didSandboxAppear ? 'Sandbox Cited' : 'Sandbox Not Cited'}
                              </span>
                              <span className="inline-flex items-center rounded-full bg-sky-100 px-3 py-1 text-xs font-semibold text-sky-800">
                                {rag.chunksUsed} chunks used
                              </span>
                            </div>
                          </div>
                        </div>
                        {(rag.sandboxCitations.length > 0 || rag.competitorCitations.length > 0) && (
                          <div className="mt-3 text-xs text-slate-600">
                            <div>
                              <strong>Sandbox:</strong>{' '}
                              {rag.sandboxCitations.length > 0
                                ? rag.sandboxCitations.join(', ')
                                : 'None'}
                            </div>
                            <div className="mt-1">
                              <strong>Competitors:</strong>{' '}
                              {rag.competitorCitations.length > 0
                                ? rag.competitorCitations.slice(0, 3).join(', ')
                                : 'None'}
                              {rag.competitorCitations.length > 3 &&
                                ` (+${rag.competitorCitations.length - 3} more)`}
                            </div>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </section>
              )}

              {/* Step 5: Final Scores */}
              {results.scores && (
                <section className="rounded-lg border border-slate-200 bg-white p-8 shadow-sm">
                  <h2 className="text-2xl font-semibold text-slate-900">Step 5: Final AEO/GEO Scores</h2>
                  <div className="mt-6 grid gap-6 md:grid-cols-2 lg:grid-cols-4">
                    <div className="rounded-lg border border-slate-200 bg-gradient-to-br from-emerald-50 to-emerald-100 p-6">
                      <h3 className="text-sm font-semibold uppercase text-emerald-700">GEO Score</h3>
                      <p className="mt-2 text-3xl font-bold text-emerald-900">
                        {results.scores.geoScore.toFixed(1)}
                      </p>
                      <p className="mt-1 text-xs text-emerald-700">/ 100</p>
                    </div>
                    <div className="rounded-lg border border-slate-200 bg-gradient-to-br from-sky-50 to-sky-100 p-6">
                      <h3 className="text-sm font-semibold uppercase text-sky-700">AEO Score</h3>
                      <p className="mt-2 text-3xl font-bold text-sky-900">
                        {results.scores.aeoScore.toFixed(1)}
                      </p>
                      <p className="mt-1 text-xs text-sky-700">/ 100</p>
                    </div>
                    <div className="rounded-lg border border-slate-200 bg-slate-50 p-6">
                      <h3 className="text-sm font-semibold uppercase text-slate-600">Citation Rate</h3>
                      <p className="mt-2 text-3xl font-bold text-slate-900">
                        {results.scores.citationRate.toFixed(1)}%
                      </p>
                    </div>
                    <div className="rounded-lg border border-slate-200 bg-slate-50 p-6">
                      <h3 className="text-sm font-semibold uppercase text-slate-600">Coverage</h3>
                      <p className="mt-2 text-3xl font-bold text-slate-900">
                        {results.scores.coverage?.toFixed(1) || 'N/A'}%
                      </p>
                    </div>
                  </div>

                  {results.scores.recommendations && results.scores.recommendations.length > 0 && (
                    <div className="mt-8 rounded-lg border border-yellow-200 bg-[#FFFBEA] p-6">
                      <h3 className="text-lg font-semibold text-slate-900">Recommendations</h3>
                      <ul className="mt-4 list-disc space-y-2 pl-6 text-sm text-slate-800">
                        {results.scores.recommendations.map((rec, index) => (
                          <li key={index}>{rec}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </section>
              )}
            </div>
          )}
        </section>
      </main>
    </>
  );
};

export default Home;
