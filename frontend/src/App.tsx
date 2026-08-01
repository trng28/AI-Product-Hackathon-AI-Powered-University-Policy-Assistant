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

  let page = <AssistantPage health={health} />;
  if (route.name === "library") page = <PolicyLibraryPage navigate={navigate} />;
  if (route.name === "document") {
    page = <DocumentPage policyId={route.id} navigate={navigate} />;
  }
  if (route.name === "how") page = <HowItWorksPage navigate={navigate} />;

  return (
    <AppShell route={route} health={health} navigate={navigate}>
      {page}
    </AppShell>
  );
}

export default App;
