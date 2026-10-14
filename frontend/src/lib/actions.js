import { api } from "../api.js";
import { navigate } from "./router.js";

export async function startTopic(topicId, opts = {}) {
  try {
    const session = await api.startSession(topicId, opts);
    navigate("session", session.id);
  } catch (e) {
    window.alert(e.message);
  }
}

// Act on a recommendation produced by the backend recommendation engine.
export function actOn(rec) {
  const cta = rec.cta || {};
  switch (cta.kind) {
    case "diagnostic":
      return navigate("diagnostic");
    case "resume":
      return navigate("session", cta.session_id);
    case "flashcards":
      return navigate("practice", null, { tab: "flashcards" });
    case "rapid_round":
      return navigate("practice", null, { tab: "rapid" });
    case "session":
      return startTopic(cta.topic_id, {
        focus_concept: cta.concept_key || undefined,
        target_difficulty: cta.target_difficulty || undefined,
      });
    default:
      return undefined;
  }
}
