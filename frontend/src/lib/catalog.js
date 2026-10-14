// The learning map: five areas, which real subjects live in each, and the
// roadmap subjects that are planned but have NO content yet. Roadmap entries
// carry a name and a one-line description only — never invented units,
// concepts or questions — and are always labelled "Roadmap".

export const AREAS = [
  { id: "core-cs", name: "Core Computer Science", short: "Core CS", tone: "cobalt" },
  { id: "ai-ml", name: "AI & Machine Learning", short: "AI & ML", tone: "orange" },
  { id: "modern-ai", name: "Modern AI", short: "Modern AI", tone: "coral" },
  { id: "ai-eng", name: "AI Engineering", short: "AI Engineering", tone: "teal" },
  { id: "dsa", name: "DSA & Algorithms", short: "DSA", tone: "gold" },
];

// Real (database-backed) subjects by id → area and visual motif.
const SUBJECT_PLACE = {
  "computer-networks": { area: "core-cs", motif: "network" },
  "operating-systems": { area: "core-cs", motif: "os" },
  "cn-os-lab": { area: "core-cs", motif: "network" },
  "gender-sensitization": { area: "core-cs", motif: "paper", note: "VNR mandatory course" },
  "artificial-intelligence": { area: "ai-ml", motif: "ai" },
  "machine-learning": { area: "ai-ml", motif: "ml" },
  "explainable-ai": { area: "ai-ml", motif: "ml" },
  "ml-lab": { area: "ai-ml", motif: "ml" },
  dsa: { area: "dsa", motif: "dsa" },
};

export function placeOf(subject) {
  return SUBJECT_PLACE[subject.id] || { area: subject.area === "foundations" ? "dsa" : "core-cs", motif: "paper" };
}

// Planned subjects without content. Name + one line, nothing more.
export const ROADMAP = [
  { id: "rm-deep-learning", short: "Deep Learning", area: "ai-ml", motif: "ai", name: "Deep Learning", summary: "Neural networks, backpropagation and modern architectures." },
  { id: "rm-nlp", short: "NLP", area: "ai-ml", motif: "paper", name: "Natural Language Processing", summary: "Representing, understanding and generating text." },
  { id: "rm-cv", short: "Vision", area: "ai-ml", motif: "ml", name: "Computer Vision", summary: "Teaching models to interpret images and video." },
  { id: "rm-rl", short: "RL", area: "ai-ml", motif: "agent", name: "Reinforcement Learning", summary: "Learning to act from rewards and feedback." },
  { id: "rm-genai", short: "GenAI", area: "modern-ai", motif: "paper", name: "Generative AI", summary: "Models that produce new text, images and code." },
  { id: "rm-llm", short: "LLMs", area: "modern-ai", motif: "paper", name: "Large Language Models", summary: "How LLMs are trained, prompted and evaluated." },
  { id: "rm-rag", short: "RAG", area: "modern-ai", motif: "agent", name: "Retrieval-Augmented Generation", summary: "Grounding model answers in retrieved documents." },
  { id: "rm-agentic", short: "Agentic AI", area: "modern-ai", motif: "agent", name: "Agentic AI", summary: "Systems that plan, act and check their own work." },
  { id: "rm-tools", short: "Tool Use", area: "modern-ai", motif: "agent", name: "AI Agents & Tool Use", summary: "Letting models call tools and APIs safely." },
  { id: "rm-prompt", short: "Prompting", area: "modern-ai", motif: "paper", name: "Prompt Engineering", summary: "Writing instructions models follow reliably." },
  { id: "rm-eval", short: "Evaluation", area: "modern-ai", motif: "ml", name: "AI Evaluation", summary: "Measuring whether an AI system actually works." },
  { id: "rm-mlops", short: "MLOps", area: "ai-eng", motif: "mlops", name: "MLOps", summary: "Versioning, monitoring and retraining models in production." },
  { id: "rm-deploy", short: "Deployment", area: "ai-eng", motif: "mlops", name: "Model Deployment", summary: "Serving models reliably to real users." },
  { id: "rm-apis", short: "AI APIs", area: "ai-eng", motif: "network", name: "AI APIs", summary: "Building applications on hosted model APIs." },
  { id: "rm-vectordb", short: "Vector DBs", area: "ai-eng", motif: "dsa", name: "Vector Databases", summary: "Storing and searching embeddings at scale." },
  { id: "rm-dataeng", short: "Data Eng.", area: "ai-eng", motif: "os", name: "Data Engineering for ML", summary: "Pipelines that feed models clean, timely data." },
  { id: "rm-mlsys", short: "ML Systems", area: "ai-eng", motif: "mlops", name: "ML Systems Design", summary: "Designing end-to-end machine-learning systems." },
].map((r) => ({ ...r, roadmap: true }));

export const areaOf = (id) => AREAS.find((a) => a.id === id) || AREAS[0];
