import { api } from "../api.js";
import { navigate } from "./router.js";

export async function startTopic(topicId) {
  try {
    const session = await api.startSession(topicId);
    navigate("session", session.id);
  } catch (e) {
    window.alert(e.message);
  }
}
