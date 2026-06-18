import "./globals.css";

export const metadata = {
  title: "MedRagAssistant",
  description: "Role-Based Medical RAG Q&A System",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body className="bg-gray-50 min-h-screen">{children}</body>
    </html>
  );
}
