import { BrowserRouter, Route, Routes } from "react-router-dom";
import Viewer from "./pages/Viewer";
import CMS from "./pages/CMS";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Viewer />} />
        <Route path="/cms" element={<CMS />} />
      </Routes>
    </BrowserRouter>
  );
}