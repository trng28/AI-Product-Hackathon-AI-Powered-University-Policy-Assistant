import { useEffect, useState } from "react";
import { Health, api } from "./api";
import { AppShell } from "./components/layout/AppShell";
import { useHashRoute } from "./hooks/useHashRoute";
import { AssistantPage } from "./pages/AssistantPage";
import { DocumentPage } from "./pages/DocumentPage";
import { HowItWorksPage } from "./pages/HowItWorksPage";
import { PolicyLibraryPage } from "./pages/PolicyLibraryPage";

function App() {
  const { route, navigate } = useHashRoute();
  const [health, setHealth] = useState<Health | null>(null);

  useEffect(() => {
    api.health().then(setHealth).catch(() => {
      setHealth({
        status: "configuration_required",
        index_ready: false,
        detail: "Không kết nối được backend.",
      });
    });
  }, []);

  return (
    <AppShell route={route} health={health} navigate={navigate}>
      <div className="route-panel" hidden={route.name !== "assistant"}>
        <AssistantPage health={health} />
      </div>
      <div className="route-panel" hidden={route.name !== "library"}>
        <PolicyLibraryPage navigate={navigate} />
      </div>
      {route.name === "document" && (
        <DocumentPage policyId={route.id} navigate={navigate} />
      )}
      <div className="route-panel" hidden={route.name !== "how"}>
        <HowItWorksPage navigate={navigate} />
      </div>
    </AppShell>
  );
}

export default App;
