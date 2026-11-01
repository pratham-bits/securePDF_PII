import { Route, Routes } from "react-router-dom";

import Layout from "./components/Layout.jsx";
import RequireAuth from "./components/RequireAuth.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Home from "./pages/Home.jsx";
import Login from "./pages/Login.jsx";
import NotFound from "./pages/NotFound.jsx";
import Register from "./pages/Register.jsx";
import Review from "./pages/Review.jsx";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Home />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route element={<RequireAuth />}>
          <Route path="/dashboard" element={<Dashboard />} />
        </Route>
        <Route path="/documents/:id" element={<Review />} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  );
}
