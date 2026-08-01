import { useEffect, useState } from "react";
import { AppRoute } from "../types";

function readRoute(): AppRoute {
  const value = window.location.hash.replace(/^#\/?/, "");
  if (value === "policies") return { name: "library" };
  if (value === "how-it-works") return { name: "how" };
  if (value.startsWith("documents/")) {
    return { name: "document", id: decodeURIComponent(value.slice(10)) };
  }
  return { name: "assistant" };
}

function routeHash(route: AppRoute) {
  if (route.name === "library") return "#/policies";
  if (route.name === "how") return "#/how-it-works";
  if (route.name === "document") return `#/documents/${encodeURIComponent(route.id)}`;
  return "#/";
}

export function useHashRoute() {
  const [route, setRoute] = useState<AppRoute>(readRoute);
  useEffect(() => {
    const update = () => setRoute(readRoute());
    window.addEventListener("hashchange", update);
    return () => window.removeEventListener("hashchange", update);
  }, []);
  const navigate = (next: AppRoute) => {
    const hash = routeHash(next);
    if (window.location.hash === hash) setRoute(next);
    else window.location.hash = hash;
  };
  return { route, navigate };
}
