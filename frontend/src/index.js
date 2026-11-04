import React from "react";
import ReactDOM from "react-dom/client";
import axios from "axios";
import "@/index.css";
import App from "@/App";

// Chambers learn who's here from the sign-in cookie, so every backend call carries it.
// Signed-out visitors also carry a steady per-browser id so an open thread survives a reload.
const BACKEND = process.env.REACT_APP_BACKEND_URL;
const VISITOR_KEY = "sanctuary_visitor_id";
let visitorId = localStorage.getItem(VISITOR_KEY);
if (!visitorId) {
  visitorId = Array.from(crypto.getRandomValues(new Uint8Array(12)), (b) => b.toString(16).padStart(2, "0")).join("");
  localStorage.setItem(VISITOR_KEY, visitorId);
}
const nativeFetch = window.fetch.bind(window);
window.fetch = (input, init = {}) => {
  const url = typeof input === "string" ? input : input?.url || "";
  if (url.startsWith(BACKEND)) {
    const headers = new Headers(init.headers || (typeof input === "string" ? undefined : input.headers));
    headers.set("X-Visitor-Id", visitorId);
    init = { ...init, headers, credentials: init.credentials || "include" };
  }
  return nativeFetch(input, init);
};
axios.defaults.withCredentials = true;
axios.defaults.headers.common["X-Visitor-Id"] = visitorId;

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
