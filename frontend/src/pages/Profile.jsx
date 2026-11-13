import { useNavigate } from "react-router-dom";
import FeedbackCard from "../components/FeedbackCard.jsx";
import { useAuth } from "../auth/useAuth.js";
import "./Profile.css";

export default function Profile() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  async function handleLogout() {
    await logout();
    navigate("/");
  }

  return (
    <div className="profile">
      <h1>Your profile</h1>
      <dl className="profile__details">
        <dt>Email</dt>
        <dd>{user.email}</dd>
      </dl>
      <FeedbackCard />
      <button type="button" className="btn" onClick={handleLogout}>
        Log out
      </button>
    </div>
  );
}
