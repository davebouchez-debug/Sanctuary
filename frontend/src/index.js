import React from "react";
import ReactDOM from "react-dom/client";
import axios from "axios";
import "@/index.css";
import App from "@/App";

// Chambers learn who's here from the sign-in cookie, so every backend call carries it.
const BACKEND = process.env.REACT_APP_BACKEND_URL;
const nativeFetch = window.fetch.bind(window);
window.fetch = (input, init = {}) => {
  const url = typeof input === "string" ? input : input?.url || "";
  if (url.startsWith(BACKEND) && !init.credentials) init = { ...init, credentials: "include" };
  return nativeFetch(input, init);
};
axios.defaults.withCredentials = true;

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
