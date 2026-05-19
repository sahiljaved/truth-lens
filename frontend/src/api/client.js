import axios from "axios";

const apiRoot = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");
const baseURL = apiRoot ? `${apiRoot}/api` : "/api";

const client = axios.create({
  baseURL,
  timeout: 120000,
});

client.interceptors.response.use(
  (response) => response,
  (error) => {
    const data = error.response?.data;
    let message = "Request failed";
    if (typeof data?.error === "string") {
      message = data.error;
    } else if (typeof data?.message === "string") {
      message = data.message;
    } else if (typeof error.message === "string") {
      message = error.message;
    }
    return Promise.reject(new Error(message));
  }
);

export default client;
