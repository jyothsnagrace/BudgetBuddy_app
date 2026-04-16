// API Configuration
const isLocalhost =
	window.location.hostname === "localhost" ||
	window.location.hostname === "127.0.0.1";

const localApiUrl = import.meta.env.VITE_API_URL_LOCAL || "http://localhost:8000";
const hostedApiUrl =
	import.meta.env.VITE_API_URL || "https://budgetbuddy-prod.up.railway.app";

export const API_URL = isLocalhost ? localApiUrl : hostedApiUrl;
