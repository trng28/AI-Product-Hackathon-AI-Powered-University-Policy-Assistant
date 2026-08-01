export type AppRoute =
  | { name: "assistant" }
  | { name: "library" }
  | { name: "how" }
  | { name: "document"; id: string };

export type Navigate = (route: AppRoute) => void;

export type ChatTurn = {
  id: string;
  question: string;
  pending: boolean;
  answer?: import("./api").Answer;
  error?: string;
};

export type PolicyDocument = {
  id: string;
  title: string;
  reference: string;
  category: "Academic" | "Student Affairs" | "Finance" | "Safety" | "Research";
  description: string;
  updated: string;
  sourceUrl: string;
  highlights: string[];
};
