import { useAuth } from "../auth/useAuth.js";
import "./FeedbackCard.css";

// Only an https link is accepted, so a mistyped or malicious setting can never become a script link.
function safeFormUrl(raw) {
  try {
    const url = new URL(raw);
    return url.protocol === "https:" ? url.href : null;
  } catch {
    return null;
  }
}

// A link to the feedback form, shown only to logged-in users. The form's address comes from
// VITE_FEEDBACK_FORM_URL; if it is not set, nothing is shown. We deliberately pass nothing about
// the user or their documents to the form.
export default function FeedbackCard({ url }) {
  const { user } = useAuth();
  const link = safeFormUrl(url ?? import.meta.env.VITE_FEEDBACK_FORM_URL);

  if (!user || !link) return null;

  return (
    <aside className="feedback" aria-labelledby="feedback-title">
      <h2 id="feedback-title" className="feedback__title">
        Help us improve SecurePDF
      </h2>
      <a
        className="btn btn--primary"
        href={link}
        target="_blank"
        rel="noopener noreferrer"
      >
        Give feedback <span aria-hidden="true">↗</span>
        <span className="feedback__sr">(opens in a new tab)</span>
      </a>
      <p className="feedback__why">
        SecurePDF gets better from what you tell us: which documents it missed,
        what confused you, and what you wish it could do. It takes about two
        minutes, and every response is read.
      </p>
      <p className="feedback__note">
        Please do not include personal details from your documents in your
        answers.
      </p>
    </aside>
  );
}
