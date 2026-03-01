import { BrowserRouter, Routes, Route } from "react-router-dom";
import Layout from "./components/shared/Layout";
import UploadPage from "./pages/UploadPage";
import DashboardPage from "./pages/DashboardPage";
import HistoryPage from "./pages/HistoryPage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<UploadPage />} />
          <Route path="analysis/:jobId" element={<DashboardPage />} />
          <Route path="history" element={<HistoryPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
